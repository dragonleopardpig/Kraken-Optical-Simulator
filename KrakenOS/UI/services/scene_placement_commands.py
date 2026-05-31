"""Scene-row and STEP placement command mixin for the Tk layout editor."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np

from KrakenOS.UI import optical_solid_metadata
from KrakenOS.UI.scene_placement import SCENE_PLACEMENT_ADVANCED_ATTR, normalize_scene_placement_settings
from KrakenOS.UI.scene_row_mapping import SCENE_ROW_SOURCE
from KrakenOS.UI.services import cad_cache_paths
from KrakenOS.UI.services.cad_step_export import _affine_from_point_sets
from KrakenOS.UI.services.element_scene_metadata import (
    SCENE_NORMAL_TARGET_LABELS,
    _normalize_scene_normal_target_kind,
)
from KrakenOS.UI.services.optical_solid_geometry import (
    _optical_solid_face_marker_label,
    _rotation_matrix_aligning_vectors,
    _rotation_matrix_from_kraken_tilts,
    auto_assign_optical_solid_face_roles,
    cluster_optical_solid_planar_faces,
    inspect_stl_mesh,
    match_optical_solid_world_face,
    normalize_optical_solid_face_metadata,
    normalize_optical_solid_face_record,
    optical_solid_face_record_from_candidate,
    optical_solid_face_world_records,
    select_optical_solid_anchor_face,
    transformed_stl_bounds,
)
from KrakenOS.UI.services.step_face_direction import StepFaceDirectionService
from KrakenOS.UI.services.step_native_reconstruction import axisymmetric_step_selection_face_records
from KrakenOS.UI.services.step_overlay_labels import STEP_OVERLAY_LABEL_SET
from KrakenOS.UI.services.step_overlay_import import StepOverlayImportService
from KrakenOS.UI.services.step_overlay_promotion import StepOverlayPromotionService
from KrakenOS.UI.source_trace_helpers import SOURCE_MODEL_DEFAULT
from KrakenOS.UI.surface_table_model import SurfaceRow


def _current_cad_cache_dir() -> Path:
    return Path(cad_cache_paths.CAD_CACHE_DIR)


def _step_overlay_label_set() -> set[str]:
    return set(STEP_OVERLAY_LABEL_SET)


def _short_error_message(exc: Exception, limit: int = 220) -> str:
    text = str(exc).strip()
    if not text:
        return exc.__class__.__name__
    first = text.splitlines()[0].strip()
    if len(first) > limit:
        return first[:limit] + "..."
    return first


class ScenePlacementMixin:
    def translate_scene_row_pose_vector(
        self,
        row_index: int,
        delta_xyz,
        *,
        record_history: bool = True,
        sync_table: bool = True,
    ) -> dict[str, object]:
        try:
            row_index = int(row_index)
        except Exception as exc:
            raise RuntimeError("Invalid row index for 3D placement translation") from exc
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError("3D placement translation row is outside the table")
        try:
            delta = np.asarray(delta_xyz, dtype=float).reshape(-1)[:3]
        except Exception as exc:
            raise RuntimeError("Invalid 3D placement translation vector") from exc
        if delta.size < 3 or not np.all(np.isfinite(delta[:3])):
            raise RuntimeError("3D placement translation vector is non-finite")
        if not np.any(np.abs(delta[:3]) > 1e-12):
            raise RuntimeError("3D placement translation vector is zero")
        row = self.rows[row_index]
        before = (float(row.desp_x), float(row.desp_y), float(row.desp_z))
        history_started = False
        if bool(record_history) and "_history_restoring" in self.__dict__ and "_history_pending_state" in self.__dict__:
            try:
                self._begin_history_capture()
                history_started = True
            except Exception:
                history_started = False
        row.desp_x = float(row.desp_x) + float(delta[0])
        row.desp_y = float(row.desp_y) + float(delta[1])
        row.desp_z = float(row.desp_z) + float(delta[2])
        row.advanced = dict(row.advanced or {})
        settings = normalize_scene_placement_settings(row.advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR, {}))
        settings["last_translate_axis"] = "xyz"
        settings["last_translate_delta_mm"] = [float(value) for value in delta[:3]]
        settings["last_translate_step_mm"] = float(np.linalg.norm(delta[:3]))
        settings["last_translate_mode"] = "free_drag"
        row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = settings
        if bool(sync_table) and "table" in self.__dict__:
            try:
                self._sync_table()
                self._select_table_row(row_index)
            except Exception:
                pass
        if history_started:
            self._commit_history_capture()
        try:
            self._mark_plot_update_pending()
        except Exception:
            pass
        self.append_debug(
            "3D placement translate S{row}: vector=({dx:.6g},{dy:.6g},{dz:.6g}) mm "
            "Desp=({x:.6g},{y:.6g},{z:.6g})".format(
                row=row_index,
                dx=float(delta[0]),
                dy=float(delta[1]),
                dz=float(delta[2]),
                x=float(row.desp_x),
                y=float(row.desp_y),
                z=float(row.desp_z),
            )
        )
        return {
            "row_index": row_index,
            "axis": "xyz",
            "delta_mm": tuple(float(value) for value in delta[:3]),
            "before_mm": before,
            "after_mm": (float(row.desp_x), float(row.desp_y), float(row.desp_z)),
            "scene_placement_settings": settings,
        }

    def slide_lens_along_axis(
        self,
        row_index: int,
        delta_z_mm: float,
        *,
        record_history: bool = True,
        sync_table: bool = True,
    ) -> dict[str, object]:
        """Slide a lens/element along the optical axis, preserving overall track length.

        Semantic: the element (single Tier-2 row or full Tier-3 row group)
        moves by ``delta_z_mm``; the row preceding the group has its
        thickness extended by ``delta_z_mm`` (the gap *before* the element
        grows), and the last row of the group has its thickness reduced by
        the same amount (the gap *after* shrinks). Every row downstream of
        the group stays at its original absolute position; the internal
        thicknesses of the group are unchanged so the lens geometry is
        rigid.
        """
        try:
            row_index = int(row_index)
        except Exception as exc:
            raise RuntimeError("Invalid row index for axis slide") from exc
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError("Axis-slide row is outside the table")
        try:
            delta = float(delta_z_mm)
        except Exception as exc:
            raise RuntimeError("Invalid axis-slide delta") from exc
        if not np.isfinite(delta):
            raise RuntimeError("Axis-slide delta is non-finite")
        if abs(delta) <= 1.0e-12:
            raise RuntimeError("Axis-slide delta is zero")
        group = self._lens_row_group_for_row(row_index)
        if not group:
            raise RuntimeError("No lens row group resolved for axis slide")
        first_row = group[0]
        last_row = group[-1]
        preceding_index = first_row - 1
        if preceding_index < 0:
            raise RuntimeError(
                "Cannot slide along axis: no preceding row to absorb the leading gap "
                f"(first group row is S{first_row})."
            )
        if last_row + 1 >= len(self.rows):
            raise RuntimeError(
                "Cannot slide along axis: no trailing row to absorb the slide "
                f"(last group row S{last_row} is the table tail)."
            )
        preceding_row = self.rows[preceding_index]
        last_group_row = self.rows[last_row]
        leading_before = float(preceding_row.thickness)
        trailing_before = float(last_group_row.thickness)
        leading_after = leading_before + delta
        trailing_after = trailing_before - delta
        if leading_after < 0.0:
            raise RuntimeError(
                f"Slide rejected: would push preceding gap S{preceding_index}.thickness "
                f"to {leading_after:.6g} mm (negative)."
            )
        if trailing_after < 0.0:
            raise RuntimeError(
                f"Slide rejected: would push trailing gap S{last_row}.thickness "
                f"to {trailing_after:.6g} mm (negative)."
            )
        history_started = False
        if bool(record_history) and "_history_restoring" in self.__dict__ and "_history_pending_state" in self.__dict__:
            try:
                self._begin_history_capture()
                history_started = True
            except Exception:
                history_started = False
        preceding_row.thickness = leading_after
        last_group_row.thickness = trailing_after
        if bool(sync_table) and "table" in self.__dict__:
            try:
                self._sync_table()
                self._select_table_indices(group, focus_index=first_row)
            except Exception:
                pass
        if history_started:
            self._commit_history_capture()
        try:
            self._mark_plot_update_pending()
        except Exception:
            pass
        self.append_debug(
            "Axis slide S{row} (group {first}-{last}): dz={delta:+.6g} mm "
            "leading S{pre}.thickness {lb:.6g}->{la:.6g}, "
            "trailing S{lr}.thickness {tb:.6g}->{ta:.6g}".format(
                row=row_index,
                first=first_row,
                last=last_row,
                delta=delta,
                pre=preceding_index,
                lb=leading_before,
                la=leading_after,
                lr=last_row,
                tb=trailing_before,
                ta=trailing_after,
            )
        )
        return {
            "row_index": row_index,
            "group_indices": list(group),
            "delta_z_mm": delta,
            "preceding_row_index": preceding_index,
            "preceding_thickness_before": leading_before,
            "preceding_thickness_after": leading_after,
            "trailing_row_index": last_row,
            "trailing_thickness_before": trailing_before,
            "trailing_thickness_after": trailing_after,
        }

    def rotate_scene_row_pose(self, row_index: int, axis: str, delta_deg: float) -> dict[str, object]:
        try:
            row_index = int(row_index)
        except Exception as exc:
            raise RuntimeError("Invalid row index for 3D placement rotation") from exc
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError("3D placement rotation row is outside the table")
        axis_key = str(axis or "").strip().lower()
        attr = {"x": "tilt_x", "y": "tilt_y", "z": "tilt_z"}.get(axis_key)
        if attr is None:
            raise RuntimeError(f"Unknown 3D placement rotation axis: {axis}")
        try:
            delta = float(delta_deg)
        except Exception as exc:
            raise RuntimeError("Invalid 3D placement rotation step") from exc
        if not np.isfinite(delta) or abs(delta) <= 1e-12:
            raise RuntimeError("3D placement rotation step is zero or non-finite")
        row = self.rows[row_index]
        before = float(getattr(row, attr))
        history_started = False
        if "_history_restoring" in self.__dict__ and "_history_pending_state" in self.__dict__:
            try:
                self._begin_history_capture()
                history_started = True
            except Exception:
                history_started = False
        setattr(row, attr, before + delta)
        row.advanced = dict(row.advanced or {})
        settings = normalize_scene_placement_settings(row.advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR, {}))
        settings["last_rotate_axis"] = axis_key
        settings["last_rotate_delta_deg"] = float(delta)
        settings["last_rotate_step_deg"] = abs(float(delta))
        row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = settings
        if "table" in self.__dict__:
            try:
                self._sync_table()
                self._select_table_row(row_index)
            except Exception:
                pass
        if history_started:
            self._commit_history_capture()
        try:
            self._mark_plot_update_pending()
        except Exception:
            pass
        self.append_debug(
            "3D placement rotate S{row}: axis={axis} delta={delta:.6g} deg "
            "Tilt=({x:.6g},{y:.6g},{z:.6g})".format(
                row=row_index,
                axis=axis_key.upper(),
                delta=float(delta),
                x=float(row.tilt_x),
                y=float(row.tilt_y),
                z=float(row.tilt_z),
            )
        )
        return {
            "row_index": row_index,
            "axis": axis_key,
            "delta_deg": float(delta),
            "before_deg": before,
            "after_deg": float(getattr(row, attr)),
            "scene_placement_settings": settings,
        }

    def rotate_scene_row_pose_world_axis(self, row_index: int, axis: str, delta_deg: float) -> dict[str, object]:
        try:
            row_index = int(row_index)
        except Exception as exc:
            raise RuntimeError("Invalid row index for 3D placement rotation") from exc
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError("3D placement rotation row is outside the table")
        axis_key = str(axis or "").strip().lower()
        if axis_key not in {"x", "y", "z"}:
            raise RuntimeError(f"Unknown 3D placement rotation axis: {axis}")
        try:
            delta = float(delta_deg)
        except Exception as exc:
            raise RuntimeError("Invalid 3D placement rotation step") from exc
        if not np.isfinite(delta) or abs(delta) <= 1e-12:
            raise RuntimeError("3D placement rotation step is zero or non-finite")
        row = self.rows[row_index]
        before = (float(row.tilt_x), float(row.tilt_y), float(row.tilt_z))
        current_matrix = _rotation_matrix_from_kraken_tilts(*before)
        delta_matrix = self._world_axis_rotation_matrix(axis_key, delta)
        next_tilts = tuple(float(value) for value in optical_solid_metadata.kraken_tilts_from_rotation_matrix(delta_matrix @ current_matrix))
        history_started = False
        if "_history_restoring" in self.__dict__ and "_history_pending_state" in self.__dict__:
            try:
                self._begin_history_capture()
                history_started = True
            except Exception:
                history_started = False
        row.tilt_x, row.tilt_y, row.tilt_z = next_tilts
        row.advanced = dict(row.advanced or {})
        settings = normalize_scene_placement_settings(row.advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR, {}))
        settings["last_rotate_axis"] = axis_key
        settings["last_rotate_delta_deg"] = float(delta)
        settings["last_rotate_step_deg"] = abs(float(delta))
        settings["last_rotate_mode"] = "world_axis"
        row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = settings
        if "table" in self.__dict__:
            try:
                self._sync_table()
                self._select_table_row(row_index)
            except Exception:
                pass
        if history_started:
            self._commit_history_capture()
        try:
            self._mark_plot_update_pending()
        except Exception:
            pass
        self.append_debug(
            "3D placement world-axis rotate S{row}: axis={axis} delta={delta:.6g} deg "
            "Tilt=({x:.6g},{y:.6g},{z:.6g})".format(
                row=row_index,
                axis=axis_key.upper(),
                delta=float(delta),
                x=float(row.tilt_x),
                y=float(row.tilt_y),
                z=float(row.tilt_z),
            )
        )
        return {
            "row_index": row_index,
            "axis": axis_key,
            "delta_deg": float(delta),
            "before_deg": before,
            "after_deg": next_tilts,
            "scene_placement_settings": settings,
        }

    def _surface_origin_for_rows(self, rows: list[SurfaceRow], row_index: int) -> np.ndarray:
        transform = self._surface_transform_for_rows(rows, int(row_index))
        return np.asarray(transform[:3, 3], dtype=float)

    def _surface_normal_for_rows(self, rows: list[SurfaceRow], row_index: int) -> np.ndarray:
        transform = self._surface_transform_for_rows(rows, int(row_index))
        normal = np.asarray(transform[:3, 2], dtype=float)
        norm = float(np.linalg.norm(normal))
        if norm <= 1e-12:
            return np.asarray((0.0, 0.0, 1.0), dtype=float)
        return normal / norm

    def _scene_source_aim_target_choices(self) -> list[str]:
        choices: list[str] = []
        for index, row in enumerate(self.rows):
            surface = str(row.surface or f"Row {index}").strip() or f"Row {index}"
            name = str(row.name or "").strip()
            label = surface if not name or name == surface else f"{name} ({surface})"
            if self._file_backed_stl_row_at(index) is not None:
                label = f"{label} CAD/STL center"
            choices.append(f"{index}: {label}")
            for face in self._scene_source_face_anchor_records(index):
                face_id = str(face.get("face_id", "") or "").strip()
                if not face_id:
                    continue
                face_label = _optical_solid_face_marker_label(face)
                choices.append(f"{index}/{face_id}: {label} face {face_label} [{face_id}]")
        return choices

    def _scene_source_target_choice_for(self, row_index: int, face_id: str = "") -> str:
        face = str(face_id or "").strip()
        prefix = f"{int(row_index)}/{face}:" if face else f"{int(row_index)}:"
        return next((choice for choice in self._scene_source_aim_target_choices() if choice.startswith(prefix)), "")

    def _scene_source_face_anchor_records(self, row_index: int) -> list[dict[str, object]]:
        row_index = int(row_index)
        if not (0 <= row_index < len(self.rows)):
            return []
        row = self.rows[row_index]
        try:
            faces = optical_solid_face_world_records(
                row,
                self._stl_row_z_station(row_index),
                assigned_only=True,
            )
        except Exception:
            return []
        output: list[dict[str, object]] = []
        seen: set[str] = set()
        for face in faces:
            face_id = str(face.get("face_id", "") or "").strip()
            centroid = np.asarray(face.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
            if not face_id or face_id in seen or centroid.size < 3 or not np.all(np.isfinite(centroid[:3])):
                continue
            seen.add(face_id)
            output.append(dict(face))
        return output

    def _scene_source_face_anchor_record(self, row_index: int, face_id: str) -> dict[str, object] | None:
        target = str(face_id or "").strip()
        if not target:
            return None
        for face in self._scene_source_face_anchor_records(int(row_index)):
            if str(face.get("face_id", "") or "").strip() == target:
                return dict(face)
        return None

    def scene_source_face_anchor_at_world_point(self, row_index: int, point_world, normal_world=None) -> dict[str, object] | None:
        faces = self._scene_source_face_anchor_records(int(row_index))
        if not faces:
            return None
        return match_optical_solid_world_face(faces, point_world, normal_world)

    def _surface_reference_world_point(self, row_index: int, *, face_id: str = "", system=None) -> np.ndarray:
        row_index = int(row_index)
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError("Target row is out of range.")

        anchor_face = self._scene_source_face_anchor_record(row_index, face_id)
        if anchor_face is not None:
            anchor = np.asarray(
                anchor_face.get("anchor_world", anchor_face.get("centroid_world", (0.0, 0.0, 0.0))),
                dtype=float,
            ).reshape(-1)[:3]
            if anchor.size >= 3 and np.all(np.isfinite(anchor)):
                return anchor.astype(float)
            raise RuntimeError("Selected CAD/STL face anchor has no finite world anchor point.")
        if str(face_id or "").strip():
            raise RuntimeError("Selected CAD/STL face anchor is not available for this row.")

        selected_stl = self._file_backed_stl_row_at(row_index)
        if selected_stl is not None:
            row, path = selected_stl
            tilts = (float(row.tilt_x), float(row.tilt_y), float(row.tilt_z))
            desp = (float(row.desp_x), float(row.desp_y), float(row.desp_z))
            _bounds_min, _bounds_max, center = transformed_stl_bounds(
                path,
                tilts,
                desp,
                self._stl_row_z_station(row_index),
            )
            center = np.asarray(center, dtype=float).reshape(-1)[:3]
            if center.size >= 3 and np.all(np.isfinite(center)):
                return center.astype(float)

        try:
            trace_state = self._resolved_trace_mode(system=system)
        except Exception:
            trace_state = {}
        if bool(trace_state.get("use_folded")):
            try:
                _point, _direction, _max_half, _extent, elements = self._compute_world_folded_layout_geometry_for_rows(
                    self.rows,
                    system=system,
                )
                for surface_index, (_surface_type, center, _row, *_rest) in enumerate(elements, start=1):
                    if surface_index == row_index:
                        center_2d = np.asarray(center, dtype=float).reshape(-1)
                        if center_2d.size >= 2 and np.all(np.isfinite(center_2d[:2])):
                            return np.asarray((0.0, float(center_2d[1]), float(center_2d[0])), dtype=float)
            except Exception:
                pass

        try:
            return self._surface_origin_for_rows(self.rows, row_index)
        except Exception:
            z_positions = self._row_z_positions()
            row = self.rows[row_index]
            z_station = float(z_positions[row_index]) if row_index < len(z_positions) else 0.0
            return np.asarray(
                (
                    float(row.desp_x),
                    float(row.desp_y),
                    z_station + float(row.desp_z),
                ),
                dtype=float,
            )

    def _surface_reference_world_normal(self, row_index: int, *, face_id: str = "", system=None) -> np.ndarray:
        row_index = int(row_index)
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError("Target row is out of range.")

        anchor_face = self._scene_source_face_anchor_record(row_index, face_id)
        if anchor_face is not None:
            normal = np.asarray(anchor_face.get("normal_world", (0.0, 0.0, 1.0)), dtype=float).reshape(-1)[:3]
            norm = float(np.linalg.norm(normal))
            if normal.size >= 3 and np.isfinite(norm) and norm > 1e-12:
                return normal.astype(float) / norm
            raise RuntimeError("Selected CAD/STL face anchor has no finite world normal.")
        if str(face_id or "").strip():
            raise RuntimeError("Selected CAD/STL face anchor is not available for this row.")

        transforms = self._system_transform_list(system)
        if transforms is not None and 0 <= row_index < len(transforms):
            try:
                normal = np.asarray(transforms[row_index], dtype=float).reshape(4, 4)[:3, 2]
                norm = float(np.linalg.norm(normal))
                if np.isfinite(norm) and norm > 1e-12:
                    return normal / norm
            except Exception:
                pass

        try:
            return self._surface_normal_for_rows(self.rows, row_index)
        except Exception:
            return np.asarray((0.0, 0.0, 1.0), dtype=float)

    def scene_source_direction_to_row(
        self,
        source_spec: dict[str, object],
        row_index: int,
        *,
        face_id: str = "",
        system=None,
    ) -> dict[str, object]:
        target = self._surface_reference_world_point(int(row_index), face_id=face_id, system=system)
        origin = self._source_spec_vector(
            dict(source_spec or {}),
            ("origin", "source_xyz", "xyz"),
            ("source_x", "source_y", "source_z"),
            (0.0, 0.0, 0.0),
        )[:3].astype(float)
        delta = np.asarray(target, dtype=float).reshape(3) - origin
        distance = float(np.linalg.norm(delta))
        if not np.isfinite(distance) or distance <= 1e-12:
            raise RuntimeError("Source origin is already at the target row center.")
        direction = delta / distance
        row = self.rows[int(row_index)]
        row_name = str(row.name or row.surface or f"Row {int(row_index)}").strip()
        anchor_face = self._scene_source_face_anchor_record(int(row_index), face_id)
        target_label = row_name
        normalized_face_id = str(face_id or "").strip()
        if anchor_face is not None:
            target_label = f"{row_name} face {_optical_solid_face_marker_label(anchor_face)}"
            normalized_face_id = str(anchor_face.get("face_id", "") or normalized_face_id).strip()
        return {
            "source_l": float(direction[0]),
            "source_m": float(direction[1]),
            "source_n": float(direction[2]),
            "target_point": tuple(float(value) for value in np.asarray(target, dtype=float).reshape(3)),
            "distance_mm": distance,
            "row_index": int(row_index),
            "row_name": row_name,
            "face_id": normalized_face_id,
            "target_label": target_label,
        }

    def scene_source_place_at_row_standoff(
        self,
        source_spec: dict[str, object],
        row_index: int,
        distance_mm: float,
        *,
        face_id: str = "",
        system=None,
    ) -> dict[str, object]:
        distance = float(distance_mm)
        if not np.isfinite(distance) or distance <= 0.0:
            raise RuntimeError("Placement standoff must be a positive distance.")
        target = self._surface_reference_world_point(int(row_index), face_id=face_id, system=system)
        direction = self._source_spec_vector(
            dict(source_spec or {}),
            ("direction", "source_lmn", "lmn"),
            ("source_l", "source_m", "source_n"),
            (0.0, 0.0, 1.0),
        )[:3].astype(float)
        norm = float(np.linalg.norm(direction))
        if not np.isfinite(norm) or norm <= 1e-12:
            raise RuntimeError("Set a non-zero source direction before placing at standoff.")
        direction = direction / norm
        origin = np.asarray(target, dtype=float).reshape(3) - direction * distance
        row = self.rows[int(row_index)]
        row_name = str(row.name or row.surface or f"Row {int(row_index)}").strip()
        anchor_face = self._scene_source_face_anchor_record(int(row_index), face_id)
        target_label = row_name
        normalized_face_id = str(face_id or "").strip()
        if anchor_face is not None:
            target_label = f"{row_name} face {_optical_solid_face_marker_label(anchor_face)}"
            normalized_face_id = str(anchor_face.get("face_id", "") or normalized_face_id).strip()
        return {
            "source_x": float(origin[0]),
            "source_y": float(origin[1]),
            "source_z": float(origin[2]),
            "source_l": float(direction[0]),
            "source_m": float(direction[1]),
            "source_n": float(direction[2]),
            "target_point": tuple(float(value) for value in np.asarray(target, dtype=float).reshape(3)),
            "distance_mm": distance,
            "row_index": int(row_index),
            "row_name": row_name,
            "face_id": normalized_face_id,
            "target_label": target_label,
        }

    @staticmethod
    def _closest_polyline_point(points: np.ndarray, target: np.ndarray) -> np.ndarray:
        return optical_solid_metadata.closest_polyline_point(points, target)

    @staticmethod
    def _closest_polyline_point_and_direction(points: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return optical_solid_metadata.closest_polyline_point_and_direction(points, target)

    @classmethod
    def _ray_point_on_surface_plane(cls, points: np.ndarray, origin: np.ndarray, normal: np.ndarray) -> np.ndarray:
        return optical_solid_metadata.ray_point_on_surface_plane(points, origin, normal)

    @classmethod
    def _ray_point_and_direction_on_surface_plane(
        cls,
        points: np.ndarray,
        origin: np.ndarray,
        normal: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        return optical_solid_metadata.ray_point_and_direction_on_surface_plane(points, origin, normal)

    @classmethod
    def _optical_solid_face_snap_anchor(
        cls,
        row: SurfaceRow,
        z_station: float,
        ray_points: np.ndarray,
    ) -> dict[str, object] | None:
        return optical_solid_metadata.optical_solid_face_snap_anchor(row, z_station, ray_points)

    @classmethod
    def _optical_solid_face_snap_anchor_by_id(
        cls,
        row: SurfaceRow,
        z_station: float,
        face_id: str,
    ) -> dict[str, object] | None:
        requested = str(face_id or "").strip()
        if not requested:
            return None
        for face in optical_solid_face_world_records(row, z_station, assigned_only=False):
            if str(face.get("face_id", "") or "").strip() != requested:
                continue
            payload = dict(face)
            payload["label"] = _optical_solid_face_marker_label(face)
            return payload
        return None

    def _row_decenter_delta_for_world_delta(self, row_index: int, world_delta: np.ndarray) -> np.ndarray:
        base_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        base_origin = self._surface_origin_for_rows(base_rows, row_index)
        columns: list[np.ndarray] = []
        eps = 1.0
        for attr in ("desp_x", "desp_y", "desp_z"):
            trial_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
            setattr(trial_rows[row_index], attr, float(getattr(trial_rows[row_index], attr)) + eps)
            try:
                shifted_origin = self._surface_origin_for_rows(trial_rows, row_index)
                columns.append((shifted_origin - base_origin) / eps)
            except Exception:
                columns.append(np.eye(3)[len(columns)])
        jacobian = np.column_stack(columns)
        try:
            solution, _residuals, rank, _singular_values = np.linalg.lstsq(jacobian, np.asarray(world_delta, dtype=float), rcond=None)
            if rank > 0 and np.all(np.isfinite(solution)):
                return np.asarray(solution, dtype=float)
        except Exception:
            pass
        return np.asarray(world_delta, dtype=float)

    @staticmethod
    def _orthonormal_rotation(matrix) -> np.ndarray:
        rotation = np.asarray(matrix, dtype=float).reshape(3, 3)
        try:
            u_matrix, _singular_values, vt_matrix = np.linalg.svd(rotation)
            fixed = u_matrix @ vt_matrix
            if float(np.linalg.det(fixed)) < 0.0:
                u_matrix[:, -1] *= -1.0
                fixed = u_matrix @ vt_matrix
            if np.all(np.isfinite(fixed)):
                return np.asarray(fixed, dtype=float)
        except Exception:
            pass
        return rotation

    def _row_tilts_for_world_rotation(self, row_index: int, desired_world_rotation) -> tuple[float, float, float]:
        row_index = int(row_index)
        zero_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        zero_rows[row_index].tilt_x = 0.0
        zero_rows[row_index].tilt_y = 0.0
        zero_rows[row_index].tilt_z = 0.0
        parent_rotation = self._orthonormal_rotation(self._surface_transform_for_rows(zero_rows, row_index)[:3, :3])
        desired = self._orthonormal_rotation(desired_world_rotation)
        try:
            local_rotation = np.linalg.inv(parent_rotation) @ desired
        except Exception:
            local_rotation = np.linalg.pinv(parent_rotation) @ desired
        local_rotation = self._orthonormal_rotation(local_rotation)
        return self._kraken_tilts_from_rotation_matrix(local_rotation)

    def center_surface_row_on_ray(self, row_index: int, ray_index: int, *, face_id: str = "") -> dict[str, object]:
        row_index = int(row_index)
        ray_index = int(ray_index)
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError(f"Surface row index is out of range: {row_index}")
        if self.rows[row_index].surface in {"Object", "Image"}:
            raise RuntimeError("Object/Image rows are references; choose a physical surface or CAD/STL row.")
        bundle = getattr(self, "_last_scene_bundle", None)
        ray_paths = list(getattr(bundle, "ray_paths", []) or []) if bundle is not None else []
        if not ray_paths:
            _system, _rays, bundle = self._build_preview_system_rays_bundle(update_state=True)
            ray_paths = list(getattr(bundle, "ray_paths", []) or [])
        ray_path = next((path for path in ray_paths if int(getattr(path, "ray_index", -1)) == ray_index), None)
        if ray_path is None and 0 <= ray_index < len(ray_paths):
            ray_path = ray_paths[ray_index]
        if ray_path is None:
            raise RuntimeError(f"Ray index is not available in the current 3D preview: {ray_index}")
        points = np.asarray(getattr(ray_path, "points_world", []), dtype=float)
        if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
            raise RuntimeError("Selected ray does not contain a valid 3D polyline.")
        anchor_label = ""
        anchor_face_id = ""
        anchor = None
        if self._file_backed_stl_row_at(row_index) is not None:
            anchor = self._optical_solid_face_snap_anchor_by_id(self.rows[row_index], self._stl_row_z_station(row_index), face_id)
            if anchor is None:
                anchor = self._optical_solid_face_snap_anchor(self.rows[row_index], self._stl_row_z_station(row_index), points[:, :3])
        if anchor is not None:
            origin = np.asarray(
                anchor.get("anchor_world", anchor.get("centroid_world", (0.0, 0.0, 0.0))),
                dtype=float,
            )
            normal = np.asarray(anchor.get("normal_world", (0.0, 0.0, 1.0)), dtype=float)
            target, ray_direction = self._ray_point_and_direction_on_surface_plane(points[:, :3], origin, normal)
            anchor_label = str(anchor.get("label", "") or "").strip()
            anchor_face_id = str(anchor.get("face_id", "") or "").strip()
        else:
            origin = self._surface_origin_for_rows(self.rows, row_index)
            normal = self._surface_normal_for_rows(self.rows, row_index)
            target, ray_direction = self._ray_point_and_direction_on_surface_plane(points[:, :3], origin, normal)
        world_delta = np.asarray(target - origin, dtype=float)
        decenter_delta = self._row_decenter_delta_for_world_delta(row_index, world_delta)
        row = self.rows[row_index]
        self._begin_history_capture()
        row.desp_x = float(row.desp_x) + float(decenter_delta[0])
        row.desp_y = float(row.desp_y) + float(decenter_delta[1])
        row.desp_z = float(row.desp_z) + float(decenter_delta[2])
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        anchor_text = f" anchor={anchor_label or anchor_face_id}" if anchor_label or anchor_face_id else ""
        self.append_debug(
            "Centered S{row} on ray {ray}: target=({tx:.6g},{ty:.6g},{tz:.6g}) "
            "world_delta=({wx:.6g},{wy:.6g},{wz:.6g}) decenter_delta=({dx:.6g},{dy:.6g},{dz:.6g}){anchor}".format(
                row=row_index,
                ray=ray_index,
                tx=float(target[0]),
                ty=float(target[1]),
                tz=float(target[2]),
                wx=float(world_delta[0]),
                wy=float(world_delta[1]),
                wz=float(world_delta[2]),
                dx=float(decenter_delta[0]),
                dy=float(decenter_delta[1]),
                dz=float(decenter_delta[2]),
                anchor=anchor_text,
            )
        )
        return {
            "row_index": row_index,
            "ray_index": ray_index,
            "target": tuple(float(value) for value in target[:3]),
            "world_delta": tuple(float(value) for value in world_delta[:3]),
            "decenter_delta": tuple(float(value) for value in decenter_delta[:3]),
            "ray_direction": tuple(float(value) for value in ray_direction[:3]),
            "anchor_label": anchor_label,
            "anchor_face_id": anchor_face_id,
        }

    def center_surface_row_on_optical_axis(self, row_index: int, axis_info: dict[str, object], *, face_id: str = "") -> dict[str, object]:
        row_index = int(row_index)
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError(f"Surface row index is out of range: {row_index}")
        if self.rows[row_index].surface in {"Object", "Image"}:
            raise RuntimeError("Object/Image rows are references; choose a physical surface or CAD/STL row.")
        points = np.asarray(axis_info.get("points"), dtype=float)
        if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
            target = np.asarray(axis_info.get("target_point", axis_info.get("picked_world", ())), dtype=float).reshape(-1)[:3]
            direction = np.asarray(axis_info.get("direction", ()), dtype=float).reshape(-1)[:3]
            if target.size >= 3 and direction.size >= 3 and np.all(np.isfinite(target[:3])) and np.all(np.isfinite(direction[:3])):
                norm = float(np.linalg.norm(direction[:3]))
                if np.isfinite(norm) and norm > 1e-12:
                    direction = direction[:3] / norm
                    points = np.vstack((target[:3] - direction, target[:3] + direction))
        if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
            raise RuntimeError("Selected optical axis does not contain a valid 3D polyline.")
        points = np.asarray(points[:, :3], dtype=float)
        axis_label = str(axis_info.get("axis_label", "Optical Axis") or "Optical Axis")
        branch_path = str(axis_info.get("branch_path", "") or "")
        source_id = str(axis_info.get("source_id", "") or "")
        try:
            axis_ray_index = int(axis_info.get("ray_index", -1))
        except Exception:
            axis_ray_index = -1
        anchor_label = ""
        anchor_face_id = ""
        anchor = None
        if self._file_backed_stl_row_at(row_index) is not None:
            anchor = self._optical_solid_face_snap_anchor_by_id(self.rows[row_index], self._stl_row_z_station(row_index), face_id)
            if anchor is None:
                anchor = self._optical_solid_face_snap_anchor(self.rows[row_index], self._stl_row_z_station(row_index), points[:, :3])
        if anchor is not None:
            origin = np.asarray(
                anchor.get("anchor_world", anchor.get("centroid_world", (0.0, 0.0, 0.0))),
                dtype=float,
            )
            normal = np.asarray(anchor.get("normal_world", (0.0, 0.0, 1.0)), dtype=float)
            target, axis_direction = self._ray_point_and_direction_on_surface_plane(points[:, :3], origin, normal)
            anchor_label = str(anchor.get("label", "") or "").strip()
            anchor_face_id = str(anchor.get("face_id", "") or "").strip()
        else:
            origin = self._surface_origin_for_rows(self.rows, row_index)
            normal = self._surface_normal_for_rows(self.rows, row_index)
            target, axis_direction = self._ray_point_and_direction_on_surface_plane(points[:, :3], origin, normal)
        world_delta = np.asarray(target - origin, dtype=float)
        decenter_delta = self._row_decenter_delta_for_world_delta(row_index, world_delta)
        row = self.rows[row_index]
        self._begin_history_capture()
        row.desp_x = float(row.desp_x) + float(decenter_delta[0])
        row.desp_y = float(row.desp_y) + float(decenter_delta[1])
        row.desp_z = float(row.desp_z) + float(decenter_delta[2])
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        anchor_text = f" anchor={anchor_label or anchor_face_id}" if anchor_label or anchor_face_id else ""
        branch_text = f" branch={branch_path}" if branch_path else ""
        self.append_debug(
            "Centered S{row} on {axis}: target=({tx:.6g},{ty:.6g},{tz:.6g}) "
            "world_delta=({wx:.6g},{wy:.6g},{wz:.6g}) decenter_delta=({dx:.6g},{dy:.6g},{dz:.6g}){branch}{anchor}".format(
                row=row_index,
                axis=axis_label,
                tx=float(target[0]),
                ty=float(target[1]),
                tz=float(target[2]),
                wx=float(world_delta[0]),
                wy=float(world_delta[1]),
                wz=float(world_delta[2]),
                dx=float(decenter_delta[0]),
                dy=float(decenter_delta[1]),
                dz=float(decenter_delta[2]),
                branch=branch_text,
                anchor=anchor_text,
            )
        )
        return {
            "row_index": row_index,
            "target": tuple(float(value) for value in target[:3]),
            "world_delta": tuple(float(value) for value in world_delta[:3]),
            "decenter_delta": tuple(float(value) for value in decenter_delta[:3]),
            "axis_direction": tuple(float(value) for value in axis_direction[:3]),
            "axis_label": axis_label,
            "branch_path": branch_path,
            "source_id": source_id,
            "ray_index": axis_ray_index,
            "anchor_label": anchor_label,
            "anchor_face_id": anchor_face_id,
        }

    def snap_scene_row_anchor_to_target(
        self,
        row_index: int,
        target_row_index: int,
        *,
        row_face_id: str = "",
        target_face_id: str = "",
        system=None,
    ) -> dict[str, object]:
        row_index = int(row_index)
        target_row_index = int(target_row_index)
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError(f"Source row index is out of range: {row_index}")
        if not (0 <= target_row_index < len(self.rows)):
            raise RuntimeError(f"Target row index is out of range: {target_row_index}")
        if self.rows[row_index].surface in {"Object", "Image"}:
            raise RuntimeError("Object/Image rows are references; choose a physical surface or CAD/STL row to move.")

        source_face = str(row_face_id or "").strip()
        target_face = str(target_face_id or "").strip()
        origin = self._surface_reference_world_point(row_index, face_id=source_face, system=system)
        target = self._surface_reference_world_point(target_row_index, face_id=target_face, system=system)
        origin = np.asarray(origin, dtype=float).reshape(-1)[:3]
        target = np.asarray(target, dtype=float).reshape(-1)[:3]
        if origin.size < 3 or target.size < 3 or not np.all(np.isfinite(origin)) or not np.all(np.isfinite(target)):
            raise RuntimeError("Snap Row->Target requires finite source and target world points.")
        world_delta = np.asarray(target - origin, dtype=float)
        decenter_delta = self._row_decenter_delta_for_world_delta(row_index, world_delta)
        if decenter_delta.size < 3 or not np.all(np.isfinite(decenter_delta[:3])):
            raise RuntimeError("Could not convert target snap into row decenter values.")

        row = self.rows[row_index]
        history_started = False
        if "_history_restoring" in self.__dict__ and "_history_pending_state" in self.__dict__:
            try:
                self._begin_history_capture()
                history_started = True
            except Exception:
                history_started = False
        row.desp_x = float(row.desp_x) + float(decenter_delta[0])
        row.desp_y = float(row.desp_y) + float(decenter_delta[1])
        row.desp_z = float(row.desp_z) + float(decenter_delta[2])
        row.advanced = dict(row.advanced or {})
        settings = normalize_scene_placement_settings(row.advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR, {}))
        settings["last_constraint_kind"] = "target_surface"
        settings["last_constraint_target_row"] = int(target_row_index)
        settings["last_constraint_target_face_id"] = target_face
        settings["last_constraint_anchor_face_id"] = source_face
        settings["last_constraint_target_point"] = [float(value) for value in target[:3]]
        settings["last_constraint_world_delta"] = [float(value) for value in world_delta[:3]]
        settings["last_constraint_decenter_delta"] = [float(value) for value in decenter_delta[:3]]
        row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = settings
        if "table" in self.__dict__:
            try:
                self._sync_table()
                self._select_table_row(row_index)
            except Exception:
                pass
        if history_started:
            self._commit_history_capture()
        try:
            self._mark_plot_update_pending()
        except Exception:
            pass

        source_label = f"S{row_index}"
        if source_face:
            source_label += f"/{source_face}"
        target_label = f"S{target_row_index}"
        if target_face:
            target_label += f"/{target_face}"
        self.append_debug(
            "Snapped {source} to {target_label}: target=({tx:.6g},{ty:.6g},{tz:.6g}) "
            "world_delta=({wx:.6g},{wy:.6g},{wz:.6g}) decenter_delta=({dx:.6g},{dy:.6g},{dz:.6g})".format(
                source=source_label,
                target_label=target_label,
                tx=float(target[0]),
                ty=float(target[1]),
                tz=float(target[2]),
                wx=float(world_delta[0]),
                wy=float(world_delta[1]),
                wz=float(world_delta[2]),
                dx=float(decenter_delta[0]),
                dy=float(decenter_delta[1]),
                dz=float(decenter_delta[2]),
            )
        )
        return {
            "row_index": row_index,
            "target_row_index": target_row_index,
            "row_face_id": source_face,
            "target_face_id": target_face,
            "origin": tuple(float(value) for value in origin[:3]),
            "target": tuple(float(value) for value in target[:3]),
            "world_delta": tuple(float(value) for value in world_delta[:3]),
            "decenter_delta": tuple(float(value) for value in decenter_delta[:3]),
            "scene_placement_settings": settings,
        }

    def orient_scene_row_anchor_to_target(
        self,
        row_index: int,
        target_row_index: int,
        *,
        row_face_id: str = "",
        target_face_id: str = "",
        system=None,
    ) -> dict[str, object]:
        row_index = int(row_index)
        target_row_index = int(target_row_index)
        if not (0 <= target_row_index < len(self.rows)):
            raise RuntimeError(f"Target row index is out of range: {target_row_index}")
        target_face = str(target_face_id or "").strip()
        target_normal = self._surface_reference_world_normal(target_row_index, face_id=target_face, system=system)
        target_label = f"S{target_row_index}"
        if target_face:
            target_label += f"/{target_face}"
        result = self.orient_scene_row_anchor_to_vector(
            row_index,
            target_normal,
            row_face_id=row_face_id,
            constraint_kind="target_normal",
            target_label=target_label,
            metadata={
                "last_constraint_target_row": int(target_row_index),
                "last_constraint_target_face_id": target_face,
            },
            system=system,
        )
        result["target_row_index"] = int(target_row_index)
        result["target_face_id"] = target_face
        return result

    @staticmethod
    def _scene_normal_target_matches(target: SceneTarget3D, target_kind: str) -> bool:
        role = str(getattr(target, "role", "") or "").strip()
        if target_kind == "active_target":
            return bool(getattr(target, "is_active_target", False))
        if target_kind == "detector":
            return bool(getattr(target, "is_detector", False)) or role == "detector"
        if target_kind == "object":
            return bool(getattr(target, "is_object", False)) or role in {"object_reference", "object_target"}
        return False

    @staticmethod
    def _scene_normal_target_priority(target: SceneTarget3D, target_kind: str) -> tuple[int, int]:
        row_index = int(getattr(target, "row_index", 0) or 0)
        role = str(getattr(target, "role", "") or "").strip()
        is_active = bool(getattr(target, "is_active_target", False))
        if target_kind == "active_target":
            return (0 if is_active else 50, row_index)
        if target_kind == "detector":
            if is_active and bool(getattr(target, "is_detector", False)):
                return (0, row_index)
            return (10, row_index)
        if target_kind == "object":
            if role == "object_target":
                return (0, row_index)
            if is_active and role in {"object_reference", "object_target"}:
                return (5, row_index)
            if role == "object_reference":
                return (10, row_index)
        return (100, row_index)

    @staticmethod
    def _scene_normal_target_label(target: SceneTarget3D, target_kind: str) -> str:
        kind_label = SCENE_NORMAL_TARGET_LABELS.get(target_kind, str(target_kind or "Target"))
        row_index = int(getattr(target, "row_index", 0) or 0)
        name = str(getattr(target, "name", "") or getattr(target, "surface", "") or f"S{row_index}").strip()
        role = str(getattr(target, "role", "") or "").strip()
        role_text = role.replace("_", " ")
        if role_text and role_text.startswith(kind_label.lower()):
            prefix = role_text.capitalize()
        elif role_text:
            prefix = f"{kind_label} {role_text}"
        else:
            prefix = kind_label
        return f"{prefix} S{row_index}: {name}"

    def _scene_named_normal_target(self, target_kind: object, *, system=None) -> dict[str, object]:
        normalized_kind = _normalize_scene_normal_target_kind(target_kind)
        try:
            trace_state = self._resolved_trace_mode(system=system)
        except Exception:
            trace_state = {"use_nonseq": False}
        targets = self._scene_targets_for_graph(trace_state)
        candidates: list[dict[str, object]] = []
        for target in targets:
            if not self._scene_normal_target_matches(target, normalized_kind):
                continue
            try:
                row_index = int(getattr(target, "row_index", -1))
            except Exception:
                continue
            if not (0 <= row_index < len(self.rows)):
                continue
            try:
                point = np.asarray(self._surface_reference_world_point(row_index, system=system), dtype=float).reshape(-1)[:3]
                normal = np.asarray(self._surface_reference_world_normal(row_index, system=system), dtype=float).reshape(-1)[:3]
            except Exception:
                point = np.asarray(getattr(target, "center_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)[:3]
                normal = np.asarray(getattr(target, "normal_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)[:3]
            norm = float(np.linalg.norm(normal)) if normal.size >= 3 else float("nan")
            if point.size < 3 or normal.size < 3 or not np.all(np.isfinite(point)) or not np.isfinite(norm) or norm <= 1e-12:
                continue
            normal = normal / norm
            candidates.append(
                {
                    "target_kind": normalized_kind,
                    "target": target,
                    "row_index": row_index,
                    "target_id": str(getattr(target, "target_id", "") or f"surface:{row_index}"),
                    "target_role": str(getattr(target, "role", "") or ""),
                    "target_name": str(getattr(target, "name", "") or self.rows[row_index].name or self.rows[row_index].surface),
                    "target_label": self._scene_normal_target_label(target, normalized_kind),
                    "target_point": point.astype(float),
                    "target_normal": normal.astype(float),
                    "is_detector": bool(getattr(target, "is_detector", False)),
                    "is_object": bool(getattr(target, "is_object", False))
                    or str(getattr(target, "role", "") or "") in {"object_reference", "object_target"},
                    "is_active_target": bool(getattr(target, "is_active_target", False)),
                    "priority": self._scene_normal_target_priority(target, normalized_kind),
                }
            )
        if not candidates:
            label = SCENE_NORMAL_TARGET_LABELS.get(normalized_kind, str(normalized_kind)).lower()
            raise RuntimeError(f"No {label} scene target with a finite normal is available.")
        candidates.sort(key=lambda item: item["priority"])
        selected = dict(candidates[0])
        selected.pop("priority", None)
        return selected

    def preview_scene_row_anchor_to_named_normal_target(
        self,
        row_index: int,
        target_kind: object,
        *,
        row_face_id: str = "",
        system=None,
    ) -> dict[str, object]:
        row_index = int(row_index)
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError(f"Source row index is out of range: {row_index}")
        if self.rows[row_index].surface in {"Object", "Image"}:
            raise RuntimeError("Object/Image rows are references; choose a physical surface or CAD/STL row to orient.")

        source_face = str(row_face_id or "").strip()
        target = self._scene_named_normal_target(target_kind, system=system)
        source_normal = np.asarray(self._surface_reference_world_normal(row_index, face_id=source_face, system=system), dtype=float).reshape(-1)[:3]
        source_norm = float(np.linalg.norm(source_normal)) if source_normal.size >= 3 else float("nan")
        target_normal = np.asarray(target["target_normal"], dtype=float).reshape(-1)[:3]
        target_norm = float(np.linalg.norm(target_normal)) if target_normal.size >= 3 else float("nan")
        if (
            source_normal.size < 3
            or target_normal.size < 3
            or not np.isfinite(source_norm)
            or not np.isfinite(target_norm)
            or source_norm <= 1e-12
            or target_norm <= 1e-12
        ):
            raise RuntimeError("Named normal preview requires finite source and target normals.")
        source_normal = source_normal / source_norm
        target_normal = target_normal / target_norm
        angle_error = float(np.rad2deg(np.arccos(np.clip(float(np.dot(source_normal, target_normal)), -1.0, 1.0))))
        return {
            "row_index": row_index,
            "row_face_id": source_face,
            "target_kind": str(target["target_kind"]),
            "target_row_index": int(target["row_index"]),
            "target_id": str(target["target_id"]),
            "target_role": str(target["target_role"]),
            "target_name": str(target["target_name"]),
            "target_label": str(target["target_label"]),
            "target_point": tuple(float(value) for value in np.asarray(target["target_point"], dtype=float)[:3]),
            "source_normal_before": tuple(float(value) for value in source_normal[:3]),
            "target_normal": tuple(float(value) for value in target_normal[:3]),
            "angle_error_deg": float(angle_error),
            "is_detector": bool(target["is_detector"]),
            "is_object": bool(target["is_object"]),
            "is_active_target": bool(target["is_active_target"]),
        }

    def orient_scene_row_anchor_to_named_normal_target(
        self,
        row_index: int,
        target_kind: object,
        *,
        row_face_id: str = "",
        system=None,
    ) -> dict[str, object]:
        target = self._scene_named_normal_target(target_kind, system=system)
        normalized_kind = str(target["target_kind"])
        constraint_kind = f"{normalized_kind}_normal"
        target_point = np.asarray(target["target_point"], dtype=float).reshape(-1)[:3]
        target_normal = np.asarray(target["target_normal"], dtype=float).reshape(-1)[:3]
        result = self.orient_scene_row_anchor_to_vector(
            row_index,
            target_normal,
            row_face_id=row_face_id,
            constraint_kind=constraint_kind,
            target_label=str(target["target_label"]),
            metadata={
                "last_constraint_target_kind": normalized_kind,
                "last_constraint_target_row": int(target["row_index"]),
                "last_constraint_target_id": str(target["target_id"]),
                "last_constraint_target_role": str(target["target_role"]),
                "last_constraint_target_name": str(target["target_name"]),
                "last_constraint_target_point": [float(value) for value in target_point[:3]],
                "last_constraint_target_normal": [float(value) for value in target_normal[:3]],
                "last_constraint_target_is_detector": bool(target["is_detector"]),
                "last_constraint_target_is_object": bool(target["is_object"]),
                "last_constraint_target_is_active": bool(target["is_active_target"]),
            },
            system=system,
        )
        result["target_kind"] = normalized_kind
        result["target_row_index"] = int(target["row_index"])
        result["target_id"] = str(target["target_id"])
        result["target_role"] = str(target["target_role"])
        result["target_name"] = str(target["target_name"])
        result["target_point"] = tuple(float(value) for value in target_point[:3])
        return result

    def orient_scene_row_anchor_to_vector(
        self,
        row_index: int,
        target_direction,
        *,
        row_face_id: str = "",
        constraint_kind: str = "target_vector",
        target_label: str = "target vector",
        metadata: dict[str, object] | None = None,
        system=None,
    ) -> dict[str, object]:
        row_index = int(row_index)
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError(f"Source row index is out of range: {row_index}")
        if self.rows[row_index].surface in {"Object", "Image"}:
            raise RuntimeError("Object/Image rows are references; choose a physical surface or CAD/STL row to orient.")

        source_face = str(row_face_id or "").strip()
        source_normal = self._surface_reference_world_normal(row_index, face_id=source_face, system=system)
        source_normal = np.asarray(source_normal, dtype=float).reshape(-1)[:3]
        target_vector = np.asarray(target_direction, dtype=float).reshape(-1)[:3]
        source_norm = float(np.linalg.norm(source_normal))
        target_norm = float(np.linalg.norm(target_vector))
        if (
            source_normal.size < 3
            or target_vector.size < 3
            or not np.isfinite(source_norm)
            or not np.isfinite(target_norm)
            or source_norm <= 1e-12
            or target_norm <= 1e-12
        ):
            raise RuntimeError("Orient Row->Vector requires finite non-zero source normal and target direction.")
        source_normal = source_normal / source_norm
        target_vector = target_vector / target_norm

        current_rotation = self._orthonormal_rotation(self._surface_transform_for_rows(self.rows, row_index)[:3, :3])
        align_rotation = _rotation_matrix_aligning_vectors(source_normal, target_vector)
        desired_world_rotation = self._orthonormal_rotation(align_rotation @ current_rotation)
        next_tilts = self._row_tilts_for_world_rotation(row_index, desired_world_rotation)
        if not np.all(np.isfinite(np.asarray(next_tilts, dtype=float))):
            raise RuntimeError("Could not convert target vector alignment into row TiltX/Y/Z values.")

        row = self.rows[row_index]
        before_tilts = (float(row.tilt_x), float(row.tilt_y), float(row.tilt_z))
        history_started = False
        if "_history_restoring" in self.__dict__ and "_history_pending_state" in self.__dict__:
            try:
                self._begin_history_capture()
                history_started = True
            except Exception:
                history_started = False
        row.tilt_x, row.tilt_y, row.tilt_z = (float(value) for value in next_tilts)
        after_normal = self._surface_reference_world_normal(row_index, face_id=source_face)
        after_normal = np.asarray(after_normal, dtype=float).reshape(-1)[:3]
        after_norm = float(np.linalg.norm(after_normal))
        if after_normal.size >= 3 and np.isfinite(after_norm) and after_norm > 1e-12:
            after_normal = after_normal / after_norm
        else:
            after_normal = np.asarray((np.nan, np.nan, np.nan), dtype=float)
        if np.all(np.isfinite(after_normal)):
            angle_error = float(
                np.rad2deg(np.arccos(np.clip(float(np.dot(after_normal, target_vector)), -1.0, 1.0)))
            )
        else:
            angle_error = float("nan")

        row.advanced = dict(row.advanced or {})
        settings = normalize_scene_placement_settings(row.advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR, {}))
        settings["last_constraint_kind"] = str(constraint_kind or "target_vector")
        settings["last_constraint_anchor_face_id"] = source_face
        settings["last_constraint_target_label"] = str(target_label or "target vector")
        settings["last_constraint_source_normal_before"] = [float(value) for value in source_normal[:3]]
        settings["last_constraint_target_vector"] = [float(value) for value in target_vector[:3]]
        if str(constraint_kind or "") == "target_normal":
            settings["last_constraint_target_normal"] = [float(value) for value in target_vector[:3]]
        for key, value in dict(metadata or {}).items():
            settings[str(key)] = value
        settings["last_constraint_source_normal_after"] = [float(value) for value in after_normal[:3]]
        settings["last_constraint_tilt_before_deg"] = [float(value) for value in before_tilts]
        settings["last_constraint_tilt_after_deg"] = [float(value) for value in next_tilts]
        settings["last_constraint_angle_error_deg"] = float(angle_error)
        row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = settings
        if "table" in self.__dict__:
            try:
                self._sync_table()
                self._select_table_row(row_index)
            except Exception:
                pass
        if history_started:
            self._commit_history_capture()
        try:
            self._mark_plot_update_pending()
        except Exception:
            pass

        source_label = f"S{row_index}"
        if source_face:
            source_label += f"/{source_face}"
        self.append_debug(
            "Oriented {source} normal to {target_label}: source_before=({sx:.6g},{sy:.6g},{sz:.6g}) "
            "target_vector=({tx:.6g},{ty:.6g},{tz:.6g}) Tilt=({rx:.6g},{ry:.6g},{rz:.6g}) error={err:.6g} deg".format(
                source=source_label,
                target_label=str(target_label or "target vector"),
                sx=float(source_normal[0]),
                sy=float(source_normal[1]),
                sz=float(source_normal[2]),
                tx=float(target_vector[0]),
                ty=float(target_vector[1]),
                tz=float(target_vector[2]),
                rx=float(row.tilt_x),
                ry=float(row.tilt_y),
                rz=float(row.tilt_z),
                err=float(angle_error),
            )
        )
        return {
            "row_index": row_index,
            "row_face_id": source_face,
            "constraint_kind": str(constraint_kind or "target_vector"),
            "target_label": str(target_label or "target vector"),
            "source_normal_before": tuple(float(value) for value in source_normal[:3]),
            "target_normal": tuple(float(value) for value in target_vector[:3]),
            "target_vector": tuple(float(value) for value in target_vector[:3]),
            "source_normal_after": tuple(float(value) for value in after_normal[:3]),
            "tilt_before_deg": tuple(float(value) for value in before_tilts),
            "tilt_after_deg": tuple(float(value) for value in next_tilts),
            "angle_error_deg": float(angle_error),
            "scene_placement_settings": settings,
            **dict(metadata or {}),
        }

    def orient_scene_row_anchor_to_current_source(
        self,
        row_index: int,
        *,
        row_face_id: str = "",
        system=None,
    ) -> dict[str, object]:
        direction = tuple(float(value) for value in self._current_source_direction())
        origin = tuple(float(value) for value in self._current_source_origin())
        source_model_var = self.__dict__.get("source_model_var")
        try:
            source_model = str(source_model_var.get() if source_model_var is not None else SOURCE_MODEL_DEFAULT)
        except Exception:
            source_model = SOURCE_MODEL_DEFAULT
        result = self.orient_scene_row_anchor_to_vector(
            row_index,
            direction,
            row_face_id=row_face_id,
            constraint_kind="source_vector",
            target_label="Source panel aim",
            metadata={
                "last_constraint_source_origin": [float(value) for value in origin],
                "last_constraint_source_direction": [float(value) for value in direction],
                "last_constraint_source_model": source_model,
            },
            system=system,
        )
        result["source_origin"] = origin
        result["source_direction"] = direction
        result["source_model"] = source_model
        return result

    def orient_scene_row_anchor_to_current_path_frame(
        self,
        row_index: int,
        *,
        row_face_id: str = "",
        system=None,
    ) -> dict[str, object]:
        source_face = str(row_face_id or "").strip()
        reference = self._surface_reference_world_point(int(row_index), face_id=source_face, system=system)
        frame = self._current_path_view_frame_near_point(reference)
        branch_path = str(frame.get("branch_path", "") or "")
        target_point = np.asarray(frame.get("target_point", reference), dtype=float).reshape(-1)[:3]
        target_label = f"Path {branch_path} frame" if branch_path else "Path view frame"
        result = self.orient_scene_row_anchor_to_vector(
            row_index,
            frame["direction"],
            row_face_id=source_face,
            constraint_kind="path_frame",
            target_label=target_label,
            metadata={
                "last_constraint_branch_path": branch_path,
                "last_constraint_path_branch_path": branch_path,
                "last_constraint_path_sample_count": int(frame.get("sample_count", 0) or 0),
                "last_constraint_origin_surface": int(frame.get("origin_surface", -1) or -1),
                "last_constraint_target_point": [float(value) for value in target_point[:3]],
            },
            system=system,
        )
        result["branch_path"] = branch_path
        result["sample_count"] = int(frame.get("sample_count", 0) or 0)
        result["origin_surface"] = int(frame.get("origin_surface", -1) or -1)
        result["target_point"] = tuple(float(value) for value in target_point[:3])
        return result

    def _row_local_axis_world_vector(self, row_index: int, axis: str, *, system=None) -> tuple[np.ndarray, str]:
        row_index = int(row_index)
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError(f"Axis row index is out of range: {row_index}")
        axis_text = str(axis or "+Z").strip().upper().replace(" ", "")
        sign = 1.0
        if axis_text.startswith("-"):
            sign = -1.0
            axis_text = axis_text[1:]
        elif axis_text.startswith("+"):
            axis_text = axis_text[1:]
        if axis_text not in {"X", "Y", "Z"}:
            raise RuntimeError("CAD/local axis must be one of +X, -X, +Y, -Y, +Z, or -Z.")
        axis_index = {"X": 0, "Y": 1, "Z": 2}[axis_text]
        transform = None
        transforms = self._system_transform_list(system)
        if transforms is not None and 0 <= row_index < len(transforms):
            try:
                transform = np.asarray(transforms[row_index], dtype=float).reshape(4, 4)
            except Exception:
                transform = None
        if transform is None:
            transform = self._surface_transform_for_rows(self.rows, row_index)
        vector = np.asarray(transform[:3, axis_index], dtype=float).reshape(-1)[:3] * sign
        norm = float(np.linalg.norm(vector))
        if vector.size < 3 or not np.isfinite(norm) or norm <= 1e-12:
            raise RuntimeError("Selected CAD/local axis does not have a finite world direction.")
        label = ("+" if sign >= 0.0 else "-") + axis_text
        return vector / norm, label

    def orient_scene_row_anchor_to_local_axis(
        self,
        row_index: int,
        axis: str,
        *,
        row_face_id: str = "",
        axis_row_index: int | None = None,
        system=None,
    ) -> dict[str, object]:
        target_row = int(row_index if axis_row_index is None else axis_row_index)
        target_vector, axis_label = self._row_local_axis_world_vector(target_row, axis, system=system)
        target_row_label = f"S{target_row}"
        if self._file_backed_stl_row_at(target_row) is not None:
            target_row_label += " CAD"
        result = self.orient_scene_row_anchor_to_vector(
            row_index,
            target_vector,
            row_face_id=row_face_id,
            constraint_kind="local_axis",
            target_label=f"{target_row_label} local {axis_label}",
            metadata={
                "last_constraint_axis_row": int(target_row),
                "last_constraint_axis": axis_label,
                "last_constraint_axis_vector": [float(value) for value in target_vector[:3]],
            },
            system=system,
        )
        result["axis_row_index"] = int(target_row)
        result["axis"] = axis_label
        result["axis_vector"] = tuple(float(value) for value in target_vector[:3])
        return result

    def _current_selected_scene_source_id(self) -> str:
        table = self.__dict__.get("table")
        if table is None:
            return ""
        candidates: list[str] = []
        try:
            candidates.extend(str(item) for item in table.selection())
        except Exception:
            pass
        try:
            focused = str(table.focus() or "")
            if focused:
                candidates.append(focused)
        except Exception:
            pass
        for item in candidates:
            record = self._table_item_scene_record(item)
            if record is None or getattr(record, "kind", "") != SCENE_ROW_SOURCE:
                continue
            source_id = str(getattr(record, "source_id", "") or "").strip()
            if source_id:
                return source_id
        return ""

    def _current_or_first_scene_source_id(self) -> str:
        selected = self._current_selected_scene_source_id()
        if selected:
            return selected
        sources = [
            source
            for source in self._collect_scene_sources(wavelength=self._current_wavelength())
            if bool(getattr(source, "enabled", True))
        ]
        if not sources:
            raise RuntimeError("No enabled scene sources are available.")
        physical = [source for source in sources if bool(getattr(source, "physical", True))]
        candidates = physical if physical else sources
        return str(getattr(candidates[0], "source_id", "") or "")

    def orient_scene_row_anchor_to_scene_source(
        self,
        row_index: int,
        source_id: str,
        *,
        row_face_id: str = "",
        system=None,
    ) -> dict[str, object]:
        target_id = str(source_id or "").strip()
        if not target_id:
            raise RuntimeError("Choose a scene source for orientation.")
        sources = self._collect_scene_sources(wavelength=self._current_wavelength())
        source = next((item for item in sources if str(getattr(item, "source_id", "") or "").strip() == target_id), None)
        if source is None:
            available = ", ".join(str(getattr(item, "source_id", "") or "") for item in sources) or "none"
            raise RuntimeError(f"Scene source {target_id!r} is not available. Available sources: {available}.")
        direction = np.asarray(getattr(source, "direction", (0.0, 0.0, 1.0)), dtype=float).reshape(-1)[:3]
        origin = np.asarray(getattr(source, "origin", (0.0, 0.0, 0.0)), dtype=float).reshape(-1)[:3]
        source_name = str(getattr(source, "name", "") or target_id)
        source_model = str(getattr(source, "model", "") or "")
        target_label = f"{source_name} ({target_id})"
        result = self.orient_scene_row_anchor_to_vector(
            row_index,
            direction,
            row_face_id=row_face_id,
            constraint_kind="scene_source_vector",
            target_label=target_label,
            metadata={
                "last_constraint_source_id": target_id,
                "last_constraint_source_name": source_name,
                "last_constraint_source_origin": [float(value) for value in origin[:3]],
                "last_constraint_source_direction": [float(value) for value in direction[:3]],
                "last_constraint_source_model": source_model,
                "last_constraint_source_physical": bool(getattr(source, "physical", True)),
                "last_constraint_source_ray_count": int(getattr(source, "ray_count", 0) or 0),
            },
            system=system,
        )
        result["source_id"] = target_id
        result["source_name"] = source_name
        result["source_origin"] = tuple(float(value) for value in origin[:3])
        result["source_direction"] = tuple(float(value) for value in direction[:3])
        result["source_model"] = source_model
        return result

    def open_optical_stl_placement_assistant(self) -> None:
        selected = self._selected_file_backed_stl_row("Place/Orient Selected CAD/STL Solid")
        if selected is None:
            return
        row_index, row, path = selected
        diagnostics = inspect_stl_mesh(path)
        if diagnostics.triangle_count <= 0:
            messagebox.showerror(
                "Place/Orient Selected CAD/STL Solid",
                "STL geometry could not be read:\n\n" + "\n".join(diagnostics.errors or ("No triangles found.",)),
                parent=self,
            )
            return

        self.open_3d_view()
        inspector = self._three_d_inspector
        if inspector is not None and inspector.available:
            inspector.start_stl_placement(row_index, refresh=False)
            self.status_var.set(f"Opened 3D CAD/STL placement handler for S{row_index}.")
            return
        plotter = self._legacy_3d_plotter
        if plotter is not None:
            self._legacy_3d_start_stl_placement(plotter, row_index)
            self.status_var.set(f"Opened legacy 3D CAD/STL placement mode for S{row_index}.")
            return
        self.status_var.set("3D CAD/STL placement unavailable; use row Tilt/Decenter fields.")
        self.append_debug("3D CAD/STL placement unavailable; neither embedded nor legacy 3D view is active.")

    def _open_optical_stl_numeric_placement_assistant(
        self,
        row_index: int,
        row: SurfaceRow,
        path: Path,
        diagnostics: StlMeshDiagnostics,
    ) -> None:
        self._main_optical_solid_dialogs()._open_optical_stl_numeric_placement_assistant(
            row_index,
            row,
            path,
            diagnostics,
        )

    def _step_overlay_import_service(self) -> StepOverlayImportService:
        service = self.__dict__.get("_step_overlay_import_service_instance")
        if service is None:
            service = StepOverlayImportService(self)
            self._step_overlay_import_service_instance = service
        return service

    def import_lens_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        title: str = "Import lens STEP",
        display_label: str = "Lens STEP",
        largest_component_only: bool = True,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        return self._step_overlay_import_service().import_lens_step(
            dialog_parent=dialog_parent,
            title=title,
            display_label=display_label,
            largest_component_only=largest_component_only,
            refresh_open_3d=refresh_open_3d,
        )

    def _default_optical_step_import_offset(self) -> tuple[float, float, float]:
        return self._step_overlay_import_service()._default_optical_step_import_offset()

    def _preserve_unpromoted_step_overlay(self, label: str) -> dict[str, object] | None:
        return self._step_overlay_import_service()._preserve_unpromoted_step_overlay(label)

    def import_optical_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        return self._step_overlay_import_service().import_optical_step(
            dialog_parent=dialog_parent,
            refresh_open_3d=refresh_open_3d,
        )

    def import_camera_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        return self._step_overlay_import_service().import_camera_step(
            dialog_parent=dialog_parent,
            refresh_open_3d=refresh_open_3d,
        )

    def rotate_camera_step_z(self, delta_deg: float) -> None:
        self.rotate_step_z("camera", delta_deg)

    def import_led_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        return self._step_overlay_import_service().import_led_step(
            dialog_parent=dialog_parent,
            refresh_open_3d=refresh_open_3d,
        )

    def _default_led_object_edge_distance(self) -> float:
        lens_front_z = max(float(self._lens_front_datum_z()), 0.0)
        if lens_front_z <= 1e-9:
            return 0.0
        return max(0.0, min(lens_front_z * 0.25, lens_front_z - 1.0))

    def set_led_edge_distance(self) -> None:
        current = max(float(getattr(self, "led_object_edge_distance_mm", 0.0)), 0.0)
        if current <= 0.0:
            current = self._default_led_object_edge_distance()
        value = self._ask_led_edge_distance(current)
        if value is None:
            return
        self._begin_history_capture()
        self.led_object_edge_distance_mm = float(value)
        self._commit_history_capture()
        self.status_var.set(f"LED edge distance: {self.led_object_edge_distance_mm:.3g} mm")
        self._refresh_open_3d_views(step_label="led")

    def _ask_led_edge_distance(self, initial_value: float, *, parent: tk.Misc | None = None) -> float | None:
        value_var = tk.StringVar(value=f"{max(float(initial_value), 0.0):g}")
        value_holder: dict[str, float] = {}

        dialog_parent = parent or self
        dialog = tk.Toplevel(dialog_parent)
        dialog.withdraw()
        dialog.title("LED Edge Distance")
        dialog.transient(dialog_parent)
        dialog.grab_set()
        dialog.resizable(False, False)

        ttk.Label(
            dialog,
            text="Distance from object plane to the object-side LED box edge [mm]",
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="w")
        entry = ttk.Entry(dialog, textvariable=value_var, width=18)
        entry.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")

        def accept() -> None:
            try:
                value_holder["value"] = max(float(value_var.get()), 0.0)
            except ValueError:
                self.status_var.set("Invalid LED edge distance.")
                return
            dialog.destroy()

        ttk.Button(dialog, text="Save", command=accept).grid(row=2, column=0, padx=(12, 4), pady=(0, 12), sticky="e")
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).grid(row=2, column=1, padx=(4, 12), pady=(0, 12), sticky="w")
        dialog.bind("<Return>", lambda _event: accept())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        self._show_centered_dialog(dialog)
        entry.focus_set()
        self.wait_window(dialog)

        value = value_holder.get("value")
        return float(value) if value is not None else None

    def rotate_led_step_z(self, delta_deg: float) -> None:
        self.rotate_step_z("led", delta_deg)

    def start_led_object_edge_pick(self) -> None:
        if self.imported_led_step_path is None:
            self.status_var.set("No LED STEP is imported.")
            return
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = True
        self._selected_step_label = "led"
        message = "Pick the LED body edge used for Object-to-LED distance."
        self.status_var.set(message)
        if self._three_d_inspector is not None:
            try:
                self._three_d_inspector.status_var.set(message)
                self._three_d_inspector._set_axis_pick_cursor(True)
                self._three_d_inspector._update_mode_badge()
            except Exception:
                pass

    def _led_step_z_translation(self) -> float:
        target_edge_z = max(float(getattr(self, "led_object_edge_distance_mm", 0.0)), 0.0)
        reference_z = getattr(self, "led_step_object_edge_local_z", None)
        if reference_z is None:
            return target_edge_z
        try:
            return target_edge_z - float(reference_z)
        except Exception:
            return target_edge_z

    def apply_led_object_edge_pick(self, feature_center_xyz: np.ndarray) -> None:
        feature_center = np.asarray(feature_center_xyz, dtype=float)
        if feature_center.size < 3 or not np.all(np.isfinite(feature_center[:3])):
            self.status_var.set("Invalid LED object-edge pick.")
            return
        # Store the picked edge in the LED's transformed local Z frame. Future
        # placement shifts the whole STEP so this edge, not a cable extremum,
        # lands at the Object-to-LED distance.
        local_z = float(feature_center[2]) - self._led_step_z_translation()
        self._begin_history_capture()
        self.led_step_object_edge_local_z = local_z
        self._cad_led_object_edge_pick = False
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._selected_step_label = "led"
        self._commit_history_capture()
        self.status_var.set(
            f"LED object edge locked. Local Z={local_z:.3g} mm; "
            f"edge distance={self.led_object_edge_distance_mm:.3g} mm."
        )
        self._refresh_open_3d_views(step_label="led")

    def _step_overlay_display_label(self, label: str) -> str:
        return self._step_overlay_import_service().step_overlay_display_label(label)

    def _step_path_for_label(self, label: str) -> Path | None:
        return self._step_overlay_import_service().step_path_for_label(label)

    def _clear_imported_step_overlay_state(self, label: str) -> None:
        self._step_overlay_import_service().clear_imported_step_overlay_state(label)

    def _step_overlay_axis_anchor(self, label: str) -> dict[str, object] | None:
        label = str(label).strip().lower()
        anchors = getattr(self, "_step_overlay_axis_anchor_by_label", {}) or {}
        anchor = anchors.get(label) if isinstance(anchors, dict) else None
        return dict(anchor) if isinstance(anchor, dict) else None

    def _clear_step_overlay_axis_anchor(self, label: str) -> None:
        label = str(label).strip().lower()
        anchors = dict(getattr(self, "_step_overlay_axis_anchor_by_label", {}) or {})
        if label in anchors:
            anchors.pop(label, None)
            self._step_overlay_axis_anchor_by_label = anchors

    def _record_step_overlay_axis_anchor(
        self,
        label: str,
        *,
        face_id: str = "",
        guide_face_id: str = "",
        target_point=None,
        target_direction=None,
        guide_direction=None,
        anchor_mode: str = "surface_center",
        axis_frame: dict[str, object] | None = None,
        source: str = "step_axis_snap",
    ) -> dict[str, object] | None:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return None
        try:
            target = np.asarray(target_point, dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if target.size < 3 or not np.all(np.isfinite(target[:3])):
            return None
        record: dict[str, object] = {
            "label": label,
            "source": str(source or "step_axis_snap"),
            "anchor_mode": str(anchor_mode or "surface_center"),
            "face_id": str(face_id or "").strip(),
            "guide_face_id": str(guide_face_id or "").strip(),
            "target_point": [float(value) for value in target[:3]],
        }
        for key, values in (("target_direction", target_direction), ("guide_direction", guide_direction)):
            try:
                vector = np.asarray(values, dtype=float).reshape(-1)[:3]
            except Exception:
                vector = np.asarray([], dtype=float)
            if vector.size >= 3 and np.all(np.isfinite(vector[:3])):
                record[key] = [float(value) for value in vector[:3]]
        frame = dict(axis_frame or {})
        for key in ("axis_id", "axis_kind", "axis_role", "axis_label", "segment_index", "ray_index", "branch_path"):
            if key in frame:
                value = frame.get(key)
                if key in {"segment_index", "ray_index"}:
                    try:
                        value = int(value)
                    except Exception:
                        value = -1
                record[key] = value
        anchors = dict(getattr(self, "_step_overlay_axis_anchor_by_label", {}) or {})
        anchors[label] = record
        self._step_overlay_axis_anchor_by_label = anchors
        return dict(record)

    def rotate_step_axis(self, label: str, axis: str, delta_deg: float, *, refresh: bool = True) -> None:
        label = str(label).strip().lower()
        axis = str(axis).strip().lower()
        if label not in _step_overlay_label_set() or axis not in {"x", "y", "z"}:
            return
        path = self._step_path_for_label(label)
        if path is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return
        attr = f"{label}_step_rotation_{axis}_deg"
        self._begin_history_capture()
        current = float(getattr(self, attr, 0.0))
        next_angle = float((current + float(delta_deg)) % 360.0)
        setattr(self, attr, next_angle)
        self._clear_step_overlay_axis_anchor(label)
        self._selected_step_label = label
        self._commit_history_capture()
        self.status_var.set(f"{label.upper()} STEP {axis.upper()} rotation: {next_angle:.0f} deg")
        if refresh:
            self._refresh_open_3d_views(step_label=label)

    def rotate_step_world_axis(
        self,
        label: str,
        axis: str,
        delta_deg: float,
        *,
        refresh: bool = True,
    ) -> tuple[float, float, float] | None:
        label = str(label).strip().lower()
        axis_key = str(axis).strip().lower()
        if label not in _step_overlay_label_set() or axis_key not in {"x", "y", "z"}:
            return None
        path = self._step_path_for_label(label)
        if path is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return None
        try:
            delta = float(delta_deg)
        except Exception:
            self.status_var.set("STEP rotation handle: invalid rotation step.")
            return None
        if not np.isfinite(delta) or abs(delta) <= 1e-12:
            self.status_var.set("STEP rotation handle: rotation step is zero or non-finite.")
            return None
        current_angles = self._step_rotation_deg_tuple(label)
        current_matrix = self._step_rotation_matrix_from_angles(*current_angles)
        delta_matrix = self._world_axis_rotation_matrix(axis_key, delta)
        next_angles = self._step_angles_from_rotation_matrix(delta_matrix @ current_matrix)
        current_offset = np.asarray(self._step_placement_offset_xyz(label), dtype=float).reshape(3)
        current_mesh = self._transformed_imported_step_mesh_for_label(label)
        try:
            current_center = np.asarray(current_mesh.center, dtype=float).reshape(3) if current_mesh is not None else None
        except Exception:
            current_center = None
        self._set_step_rotation_deg_tuple(label, next_angles)
        try:
            rotated_mesh = self._transformed_imported_step_mesh_for_label(label)
            rotated_center = np.asarray(rotated_mesh.center, dtype=float).reshape(3) if rotated_mesh is not None else None
        finally:
            self._set_step_rotation_deg_tuple(label, current_angles)
        next_offset = current_offset
        if (
            current_center is not None
            and rotated_center is not None
            and np.all(np.isfinite(current_center))
            and np.all(np.isfinite(rotated_center))
        ):
            next_offset = current_offset + (current_center - rotated_center)
        self._begin_history_capture()
        self._set_step_rotation_deg_tuple(label, next_angles)
        self._set_step_placement_offset_xyz(label, next_offset)
        self._clear_step_overlay_axis_anchor(label)
        self._selected_step_label = label
        self._commit_history_capture()
        self.status_var.set(
            f"{label.upper()} STEP world {axis_key.upper()}{delta:+.0f} deg -> "
            f"X={next_angles[0]:.0f}, Y={next_angles[1]:.0f}, Z={next_angles[2]:.0f} deg"
        )
        if refresh:
            self._refresh_open_3d_views(step_label=label)
        return next_angles

    def rotate_selected_step_axis(self, axis: str, delta_deg: float) -> None:
        label = self._selected_step_label
        if label not in _step_overlay_label_set():
            self.status_var.set("Select a STEP component in the 3D view first.")
            return
        self.rotate_step_axis(label, axis, delta_deg)

    def rotate_step_z(self, label: str, delta_deg: float) -> None:
        self.rotate_step_axis(label, "z", delta_deg)

    def rotate_selected_step_z(self, delta_deg: float) -> None:
        self.rotate_selected_step_axis("z", delta_deg)

    def rotate_step_x(self, label: str, delta_deg: float) -> None:
        self.rotate_step_axis(label, "x", delta_deg)

    def rotate_selected_step_x(self, delta_deg: float) -> None:
        self.rotate_selected_step_axis("x", delta_deg)

    def rotate_step_y(self, label: str, delta_deg: float) -> None:
        self.rotate_step_axis(label, "y", delta_deg)

    def rotate_selected_step_y(self, delta_deg: float) -> None:
        self.rotate_selected_step_axis("y", delta_deg)

    def select_step_component(self, label: str) -> None:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return
        self._selected_step_label = label
        self.status_var.set(
            f"Selected {label.upper()} STEP. Drag freely in Open 3D, click a face, then use Snap STEP Normal->Optical Axis."
        )

    def start_any_step_axis_pick(self) -> None:
        if not self._has_imported_step_cad():
            self.status_var.set("No lens, optical, LED, or camera STEP is imported.")
            return
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = True
        self._cad_led_object_edge_pick = False
        selected = self._selected_step_label if self._step_path_for_label(str(self._selected_step_label or "")) is not None else None
        target_note = (
            f" Selected {str(selected).upper()} STEP can also be centered on a KrakenOS surface."
            if selected is not None
            else " Select a STEP first if you want to center it on a KrakenOS surface."
        )
        message = (
            "Center STEP Axis: click a planar/circular outer feature on any imported STEP; "
            "the picked feature center will move to the optical axis." + target_note
        )
        self.status_var.set(message)
        if self._three_d_inspector is not None:
            try:
                self._three_d_inspector.status_var.set(message)
                self._three_d_inspector._set_axis_pick_cursor(True)
                self._three_d_inspector._update_mode_badge()
            except Exception:
                pass

    def start_step_axis_pick(self, label: str) -> None:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return
        path = self._step_path_for_label(label)
        if path is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return
        self._cad_axis_pick_label = label
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label = label
        message = (
            f"Pick a planar/circular feature on the {label} STEP to define its optical axis, "
            "or click a KrakenOS surface to center that STEP axis on the surface axis."
        )
        self.status_var.set(message)
        if self._three_d_inspector is not None:
            try:
                self._three_d_inspector.status_var.set(message)
                self._three_d_inspector._set_axis_pick_cursor(True)
                self._three_d_inspector._update_mode_badge()
            except Exception:
                pass

    def _step_axis_offset_xy(self, label: str) -> tuple[float, float]:
        value = getattr(self, f"{label}_step_axis_offset_xy", (0.0, 0.0))
        try:
            return (float(value[0]), float(value[1]))
        except Exception:
            return (0.0, 0.0)

    def _set_step_axis_offset_xy(self, label: str, offset_xy: tuple[float, float]) -> None:
        if label not in _step_overlay_label_set():
            return
        setattr(self, f"{label}_step_axis_offset_xy", (float(offset_xy[0]), float(offset_xy[1])))
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()

    def _step_placement_offset_xyz(self, label: str) -> tuple[float, float, float]:
        value = getattr(self, f"{label}_step_placement_offset_xyz", (0.0, 0.0, 0.0))
        try:
            return (float(value[0]), float(value[1]), float(value[2]))
        except Exception:
            return (0.0, 0.0, 0.0)

    def _set_step_placement_offset_xyz(self, label: str, offset_xyz) -> None:
        if label not in _step_overlay_label_set():
            return
        values = np.asarray(offset_xyz, dtype=float).reshape(-1)
        if values.size < 3 or not np.all(np.isfinite(values[:3])):
            return
        setattr(self, f"{label}_step_placement_offset_xyz", (float(values[0]), float(values[1]), float(values[2])))
        self._clear_step_overlay_axis_anchor(label)
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()

    def translate_step_overlay(
        self,
        label: str,
        delta_xyz,
        *,
        grid_spacing_mm: float | None = None,
        refresh: bool = True,
        record_history: bool = True,
    ) -> None:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return
        if self._step_path_for_label(label) is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return
        delta = np.asarray(delta_xyz, dtype=float).reshape(-1)
        if delta.size < 3 or not np.all(np.isfinite(delta[:3])):
            self.status_var.set(f"Invalid {label} STEP placement delta.")
            return
        current = np.asarray(self._step_placement_offset_xyz(label), dtype=float)
        next_offset = current + delta[:3]
        if record_history:
            self._begin_history_capture()
        self._set_step_placement_offset_xyz(label, next_offset)
        self._selected_step_label = label
        if record_history:
            self._commit_history_capture()
        step_text = f" on {float(grid_spacing_mm):.6g} mm snap step" if grid_spacing_mm is not None else ""
        self.status_var.set(
            f"{label.upper()} STEP moved{step_text}: "
            f"d=({float(delta[0]):.6g}, {float(delta[1]):.6g}, {float(delta[2]):.6g}) mm; "
            f"offset=({float(next_offset[0]):.6g}, {float(next_offset[1]):.6g}, {float(next_offset[2]):.6g}) mm."
        )
        if refresh:
            self._refresh_open_3d_views(step_label=label)

    def _transformed_imported_step_mesh_for_label(self, label: str):
        label = str(label).strip().lower()
        builders = {
            "lens": self._transformed_imported_lens_step_mesh,
            "optical": self._transformed_imported_optical_step_mesh,
            "camera": self._transformed_imported_camera_step_mesh,
            "led": self._transformed_imported_led_step_mesh,
        }
        builder = builders.get(label)
        return builder() if builder is not None else None

    def _step_overlay_promotion_service(self) -> StepOverlayPromotionService:
        service = self.__dict__.get("_step_overlay_promotion_service_instance")
        if service is None:
            service = StepOverlayPromotionService(self)
            self._step_overlay_promotion_service_instance = service
        return service

    def _step_face_direction_service(self) -> StepFaceDirectionService:
        service = self.__dict__.get("_step_face_direction_service_instance")
        if service is None:
            service = StepFaceDirectionService(self, valid_labels=_step_overlay_label_set())
            self._step_face_direction_service_instance = service
        return service

    def _step_overlay_optical_solid_row_plan(
        self,
        label: str,
        *,
        insert_at: int | None = None,
        cache_subdir: str = "promoted_step_overlays",
        transient_live_trace: bool = False,
        use_current_selection: bool = True,
        quiet: bool = False,
    ) -> dict[str, object] | None:
        return self._step_overlay_promotion_service()._step_overlay_optical_solid_row_plan(
            label,
            insert_at=insert_at,
            cache_subdir=cache_subdir,
            transient_live_trace=transient_live_trace,
            use_current_selection=use_current_selection,
            quiet=quiet,
        )

    def promote_imported_step_to_optical_solid_row(
        self,
        label: str,
        *,
        insert_at: int | None = None,
        open_face_editor: bool = True,
        clear_overlay: bool = False,
        refresh_open_3d: bool = True,
    ) -> dict[str, object] | None:
        return self._step_overlay_promotion_service().promote_imported_step_to_optical_solid_row(
            label,
            insert_at=insert_at,
            open_face_editor=open_face_editor,
            clear_overlay=clear_overlay,
            refresh_open_3d=refresh_open_3d,
        )

    def promote_imported_step_to_native_surface_rows(
        self,
        label: str,
        *,
        glass_sequence: object,
        insert_at: int | None = None,
        clear_overlay: bool = False,
        refresh_open_3d: bool = True,
    ) -> dict[str, object] | None:
        return self._step_overlay_promotion_service().promote_imported_step_to_native_surface_rows(
            label,
            glass_sequence=glass_sequence,
            insert_at=insert_at,
            clear_overlay=clear_overlay,
            refresh_open_3d=refresh_open_3d,
        )

    def preview_imported_step_analytic_surfaces(self, label: str) -> dict[str, object] | None:
        return self._step_overlay_promotion_service().preview_imported_step_analytic_surfaces(label)

    def _imported_step_solid_prefix_count(self, label: str) -> int:
        """Count distinct solid prefixes (``S001/...``, ``S002/...``) in face metadata.

        > 1 means a cemented compound -- the analytic fit only sees
        the outer surfaces because the interior cement face is
        missing from the imported metadata. Routing the promote
        through the OCC native-rows path recovers the interior
        Rc value.
        """
        try:
            md = self._step_overlay_face_metadata(label) or {}
        except Exception:
            return 1
        prefixes: set[str] = set()
        for face in list(md.get("faces") or []):
            fid = str(face.get("face_id", ""))
            if "/" in fid:
                prefixes.add(fid.split("/", 1)[0])
        return max(len(prefixes), 1)

    def _apply_chain_exit_direction_to_overlay(
        self,
        label: str,
        chain_exit_direction: tuple[float, float, float] | None,
    ) -> bool:
        """Pre-rotate the overlay so a downstream promote (analytic or native)
        inherits the cascade exit alignment.

        The OCC native-rows path reads the overlay's rotation_*_deg
        attributes directly when building rows; the analytic path
        already takes ``chain_exit_direction`` as a parameter. This
        helper bridges them: when a cascade-aware caller wants the
        native path to align with the folded beam, it temporarily
        sets the overlay's rotation to match.

        Returns True when a rotation was applied so the caller knows
        whether to expect post-promote rows to be tilted.
        """
        if chain_exit_direction is None:
            return False
        try:
            import numpy as _np  # local import to avoid module-load cost
            axis_vec = _np.asarray(chain_exit_direction, dtype=float).reshape(3)
            if float(_np.linalg.norm(axis_vec)) < 1e-9:
                return False
            axis_vec = axis_vec / float(_np.linalg.norm(axis_vec))
            dominant = int(_np.argmax(_np.abs(axis_vec)))
            snapped = _np.zeros(3, dtype=float)
            snapped[dominant] = float(_np.sign(axis_vec[dominant]))
        except Exception:
            return False
        # Tilt mapping: align the overlay's local +Z (the lens
        # optical axis convention in most STEP files) WITH
        # exit_direction so the body's optical axis runs along the
        # ray. Native promote rows inherit this same mapping via
        # step_overlay_promotion's chain_tilt branch.
        if _np.allclose(snapped, (0.0, 0.0, 1.0)):
            return False  # body's +Z already aligned with ray
        if _np.allclose(snapped, (0.0, 0.0, -1.0)):
            tilt = (180.0, 0.0, 0.0)
        elif _np.allclose(snapped, (1.0, 0.0, 0.0)):
            tilt = (0.0, 90.0, 0.0)
        elif _np.allclose(snapped, (-1.0, 0.0, 0.0)):
            tilt = (0.0, -90.0, 0.0)
        elif _np.allclose(snapped, (0.0, 1.0, 0.0)):
            tilt = (-90.0, 0.0, 0.0)
        elif _np.allclose(snapped, (0.0, -1.0, 0.0)):
            tilt = (90.0, 0.0, 0.0)
        else:
            return False
        for axis_name, deg in zip(("x", "y", "z"), tilt):
            if abs(deg) > 1e-9:
                try:
                    self.rotate_step_axis(label, axis_name, float(deg), refresh=False)
                except Exception:
                    pass
        return True

    def promote_imported_step_to_analytic_surfaces(
        self,
        label: str,
        *,
        glass_sequence: object,
        insert_at: int | None = None,
        clear_overlay: bool = True,
        refresh_open_3d: bool = True,
        chain_exit_direction: tuple[float, float, float] | None = None,
    ) -> dict[str, object] | None:
        # Cemented doublets/triplets: route to the OCC native path
        # when the user signals multi-glass intent. Detection uses
        # BOTH the body's solid-prefix count (S001+S002+... in the
        # face metadata) AND the glass sequence length. A user
        # passing a single glass for a doublet is opting into the
        # "singlet approximation"; passing N glasses for an N-solid
        # body unlocks the cement-recovery path.
        try:
            _seq_count = len(
                self._step_overlay_promotion_service()._normalize_glass_sequence(glass_sequence)
            )
        except Exception:
            _seq_count = 1
        if (
            self._imported_step_solid_prefix_count(label) > 1
            and _seq_count > 1
        ):
            # Pre-rotate the overlay so the native-rows path inherits
            # the cascade exit alignment (analytic path takes the
            # direction as a parameter; native reads overlay state).
            tilted = self._apply_chain_exit_direction_to_overlay(label, chain_exit_direction)
            try:
                result = self.promote_imported_step_to_native_surface_rows(
                    label,
                    glass_sequence=glass_sequence,
                    insert_at=insert_at,
                    clear_overlay=clear_overlay,
                    refresh_open_3d=refresh_open_3d,
                )
            except Exception:
                # Fall through to the analytic fit path on failure;
                # better a partial doublet than a hard error.
                result = None
            if isinstance(result, dict) and result.get("row_indices"):
                # Native-rows path keeps AxisMove=0 throughout (chain
                # stays world-aligned). The caller is responsible for
                # adjusting per-row desp / tilt to position the
                # doublet at its target world location -- see
                # build_penta_analytic_telescope_layout for the cascade
                # case.
                return result
        return self._step_overlay_promotion_service().promote_imported_step_to_analytic_surfaces(
            label,
            glass_sequence=glass_sequence,
            insert_at=insert_at,
            clear_overlay=clear_overlay,
            refresh_open_3d=refresh_open_3d,
            chain_exit_direction=chain_exit_direction,
        )



    def snap_step_overlay_center_to_world_point(
        self,
        label: str,
        target_world_xyz,
        *,
        target_kind: str = "ray",
    ) -> dict[str, object] | None:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return None
        if self._step_path_for_label(label) is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return None
        target = np.asarray(target_world_xyz, dtype=float).reshape(-1)
        if target.size < 3 or not np.all(np.isfinite(target[:3])):
            self.status_var.set(f"Invalid {label} STEP snap target.")
            return None
        mesh = self._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            self.status_var.set(f"{label.upper()} STEP mesh unavailable for snap.")
            return None
        try:
            bounds = np.asarray(mesh.bounds, dtype=float).reshape(6)
            center = np.asarray(
                (
                    0.5 * (float(bounds[0]) + float(bounds[1])),
                    0.5 * (float(bounds[2]) + float(bounds[3])),
                    0.5 * (float(bounds[4]) + float(bounds[5])),
                ),
                dtype=float,
            )
        except Exception:
            try:
                center = np.mean(np.asarray(mesh.points, dtype=float), axis=0)
            except Exception:
                center = np.zeros(3, dtype=float)
        if center.size < 3 or not np.all(np.isfinite(center[:3])):
            self.status_var.set(f"{label.upper()} STEP center unavailable for snap.")
            return None
        delta = target[:3] - center[:3]
        self.translate_step_overlay(label, delta, grid_spacing_mm=None)
        offset = self._step_placement_offset_xyz(label)
        result = {
            "label": label,
            "target_kind": str(target_kind or "target"),
            "target": tuple(float(value) for value in target[:3]),
            "previous_center": tuple(float(value) for value in center[:3]),
            "delta": tuple(float(value) for value in delta[:3]),
            "offset": offset,
        }
        self.status_var.set(
            "{label} STEP center snapped to {kind} at ({x:.6g}, {y:.6g}, {z:.6g}) mm; "
            "offset=({ox:.6g}, {oy:.6g}, {oz:.6g}) mm.".format(
                label=label.upper(),
                kind=str(target_kind or "target"),
                x=float(target[0]),
                y=float(target[1]),
                z=float(target[2]),
                ox=float(offset[0]),
                oy=float(offset[1]),
                oz=float(offset[2]),
            )
        )
        return result

    def snap_step_overlay_center_to_scene_target(
        self,
        label: str,
        row_index: int,
        *,
        face_id: str = "",
        system=None,
    ) -> dict[str, object] | None:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return None
        if self._step_path_for_label(label) is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return None
        try:
            row_index = int(row_index)
        except Exception:
            self.status_var.set("Snap STEP->Target row is invalid.")
            return None
        if not (0 <= row_index < len(self.rows)):
            self.status_var.set("Snap STEP->Target row is out of range.")
            return None

        face_id = str(face_id or "").strip()
        target_kind = "scene target"
        target_label = f"S{row_index}"
        if face_id:
            face = self._scene_source_face_anchor_record(row_index, face_id)
            if face is None:
                self.status_var.set(f"Snap STEP->Target face {face_id} is unavailable on S{row_index}.")
                return None
            try:
                target = self._surface_reference_world_point(row_index, face_id=face_id, system=system)
            except Exception as exc:
                self.status_var.set(f"Snap STEP->Target face anchor unavailable: {_short_error_message(exc)}")
                return None
            target_kind = "CAD/STL face anchor"
            target_label = f"S{row_index} face {_optical_solid_face_marker_label(face)} [{face_id}]"
        else:
            try:
                trace_state = self._resolved_trace_mode(system=system or getattr(self, "last_system", None))
            except Exception:
                trace_state = {}
            scene_targets = self._scene_targets_for_graph(trace_state)
            target_record = next(
                (
                    target_item
                    for target_item in scene_targets
                    if int(getattr(target_item, "row_index", -1)) == row_index
                ),
                None,
            )
            if target_record is not None:
                target = np.asarray(getattr(target_record, "center_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)[:3]
                role = str(getattr(target_record, "role", "") or "scene target").replace("_", " ")
                name = str(getattr(target_record, "name", "") or self.rows[row_index].name or self.rows[row_index].surface or "").strip()
                target_kind = role
                target_label = f"{role} S{row_index}{f': {name}' if name else ''}"
            elif self._file_backed_stl_row_at(row_index) is not None:
                try:
                    target = self._surface_reference_world_point(row_index, system=system)
                except Exception as exc:
                    self.status_var.set(f"Snap STEP->Target CAD/STL center unavailable: {_short_error_message(exc)}")
                    return None
                row = self.rows[row_index]
                name = str(row.name or row.surface or "").strip()
                target_kind = "CAD/STL center"
                target_label = f"S{row_index} CAD/STL center{f': {name}' if name else ''}"
            else:
                self.status_var.set(
                    "Snap STEP->Target needs a detector/object/active target row or CAD/STL face anchor."
                )
                return None

        target = np.asarray(target, dtype=float).reshape(-1)
        if target.size < 3 or not np.all(np.isfinite(target[:3])):
            self.status_var.set(f"Snap STEP->Target resolved a non-finite target for S{row_index}.")
            return None
        result = self.snap_step_overlay_center_to_world_point(label, target[:3], target_kind=target_kind)
        if result is None:
            return None
        result["target_row_index"] = row_index
        result["target_face_id"] = face_id
        result["target_label"] = target_label
        return result

    def _step_offset_delta_for_world_xy(self, label: str, world_xy) -> tuple[float, float]:
        values = np.asarray(world_xy, dtype=float).reshape(-1)
        if values.size < 2 or not np.all(np.isfinite(values[:2])):
            return (0.0, 0.0)
        angle = np.deg2rad(-self._step_roll_deg(str(label).strip().lower()))
        cos_a = float(np.cos(angle))
        sin_a = float(np.sin(angle))
        x = float(values[0])
        y = float(values[1])
        return ((cos_a * x) - (sin_a * y), (sin_a * x) + (cos_a * y))

    def center_step_axis_on_world_point(
        self,
        label: str,
        target_world_xyz,
        *,
        row_index: int | None = None,
    ) -> dict[str, object] | None:
        """Center an imported STEP overlay axis on a layout/world point.

        The imported lens/optical/camera/LED overlays use ``*_step_axis_offset_xy`` as
        a pre-rotation transverse offset. The transformed overlay axis lands at
        ``(-offset_x, -offset_y)`` in layout X/Y for the common unrotated case.
        Clicking a KrakenOS surface while STEP-axis centering is active is a
        target-selection workflow, not a STEP-feature workflow, so set the
        absolute offset from the target surface axis instead of accumulating a
        picked-feature correction.
        """
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return None
        if self._step_path_for_label(label) is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return None
        target = np.asarray(target_world_xyz, dtype=float).reshape(-1)
        if target.size < 2 or not np.all(np.isfinite(target[:2])):
            self.status_var.set(f"Invalid {label} STEP axis target.")
            return None
        delta = self._step_offset_delta_for_world_xy(label, target[:2])
        offset = (-float(delta[0]), -float(delta[1]))
        self._begin_history_capture()
        self._set_step_axis_offset_xy(label, offset)
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label = label
        if row_index is not None:
            try:
                self._select_table_row(int(row_index))
            except Exception:
                pass
        self._commit_history_capture()
        target_label = f"S{int(row_index)}" if row_index is not None else "world target"
        self.status_var.set(
            f"{label.upper()} STEP optical axis centered on {target_label} "
            f"(target X/Y={float(target[0]):.3g}, {float(target[1]):.3g} mm; "
            f"offset={offset[0]:.3g}, {offset[1]:.3g} mm)."
        )
        self._refresh_open_3d_views(step_label=label)
        return {
            "label": label,
            "row_index": int(row_index) if row_index is not None else None,
            "target": tuple(float(value) for value in target[:3]) if target.size >= 3 else (float(target[0]), float(target[1]), 0.0),
            "offset": offset,
        }

    def center_step_axis_on_surface(self, label: str, row_index: int) -> dict[str, object] | None:
        row_index = int(row_index)
        target = self._surface_reference_world_point(row_index)
        return self.center_step_axis_on_world_point(label, target, row_index=row_index)

    @staticmethod
    def _world_axis_rotation_matrix(axis: str, angle_deg: float) -> np.ndarray:
        angle = np.deg2rad(float(angle_deg))
        cos_a = float(np.cos(angle))
        sin_a = float(np.sin(angle))
        axis_key = str(axis or "").strip().lower()
        if axis_key == "x":
            return np.asarray(((1.0, 0.0, 0.0), (0.0, cos_a, -sin_a), (0.0, sin_a, cos_a)), dtype=float)
        if axis_key == "y":
            return np.asarray(((cos_a, 0.0, sin_a), (0.0, 1.0, 0.0), (-sin_a, 0.0, cos_a)), dtype=float)
        if axis_key == "z":
            return np.asarray(((cos_a, -sin_a, 0.0), (sin_a, cos_a, 0.0), (0.0, 0.0, 1.0)), dtype=float)
        raise ValueError(f"Unknown world rotation axis: {axis}")

    @staticmethod
    def _step_rotation_matrix_from_angles(x_deg: float, y_deg: float, z_deg: float) -> np.ndarray:
        x = np.deg2rad(float(x_deg))
        y = np.deg2rad(float(y_deg))
        z = np.deg2rad(float(z_deg))
        cx, sx = float(np.cos(x)), float(np.sin(x))
        cy, sy = float(np.cos(y)), float(np.sin(y))
        cz, sz = float(np.cos(z)), float(np.sin(z))
        rx = np.asarray(((1.0, 0.0, 0.0), (0.0, cx, -sx), (0.0, sx, cx)), dtype=float)
        ry = np.asarray(((cy, 0.0, sy), (0.0, 1.0, 0.0), (-sy, 0.0, cy)), dtype=float)
        rz = np.asarray(((cz, -sz, 0.0), (sz, cz, 0.0), (0.0, 0.0, 1.0)), dtype=float)
        return rz @ ry @ rx

    @staticmethod
    def _step_angles_from_rotation_matrix(matrix) -> tuple[float, float, float]:
        values = np.asarray(matrix, dtype=float).reshape(3, 3)
        sy = float(np.clip(-values[2, 0], -1.0, 1.0))
        y = float(np.arcsin(sy))
        cy = float(np.cos(y))
        if abs(cy) > 1e-9:
            x = float(np.arctan2(values[2, 1], values[2, 2]))
            z = float(np.arctan2(values[1, 0], values[0, 0]))
        else:
            x = 0.0
            z = float(np.arctan2(-values[0, 1], values[1, 1]))
        return tuple(float(np.rad2deg(angle) % 360.0) for angle in (x, y, z))

    @staticmethod
    def _rotation_matrix_between_vectors(source, target) -> np.ndarray:
        src = np.asarray(source, dtype=float).reshape(3)
        dst = np.asarray(target, dtype=float).reshape(3)
        src /= max(float(np.linalg.norm(src)), 1e-12)
        dst /= max(float(np.linalg.norm(dst)), 1e-12)
        cross = np.cross(src, dst)
        cross_norm = float(np.linalg.norm(cross))
        dot = float(np.clip(np.dot(src, dst), -1.0, 1.0))
        if cross_norm <= 1e-12:
            if dot > 0.0:
                return np.eye(3, dtype=float)
            axis = np.asarray((1.0, 0.0, 0.0), dtype=float)
            if abs(float(np.dot(axis, src))) > 0.9:
                axis = np.asarray((0.0, 1.0, 0.0), dtype=float)
            axis = np.cross(src, axis)
            axis /= max(float(np.linalg.norm(axis)), 1e-12)
            return (2.0 * np.outer(axis, axis)) - np.eye(3, dtype=float)
        axis = cross / cross_norm
        skew = np.asarray(
            (
                (0.0, -axis[2], axis[1]),
                (axis[2], 0.0, -axis[0]),
                (-axis[1], axis[0], 0.0),
            ),
            dtype=float,
        )
        angle = float(np.arctan2(cross_norm, dot))
        return np.eye(3, dtype=float) + (np.sin(angle) * skew) + ((1.0 - np.cos(angle)) * (skew @ skew))

    def _step_rotation_deg_tuple(self, label: str) -> tuple[float, float, float]:
        return (
            float(self._step_x_rotation_deg(label)),
            float(self._step_y_rotation_deg(label)),
            float(self._step_roll_deg(label)),
        )

    def _set_step_rotation_deg_tuple(self, label: str, angles: tuple[float, float, float]) -> None:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return
        x_deg, y_deg, z_deg = (float(value) % 360.0 for value in angles)
        setattr(self, f"{label}_step_rotation_x_deg", x_deg)
        setattr(self, f"{label}_step_rotation_y_deg", y_deg)
        setattr(self, f"{label}_step_rotation_z_deg", z_deg)
        self._clear_step_overlay_axis_anchor(label)
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()

    def _step_optical_axis_frame_near_point(self, reference_point) -> dict[str, object]:
        reference = np.asarray(reference_point, dtype=float).reshape(-1)[:3]
        if reference.size < 3 or not np.all(np.isfinite(reference[:3])):
            raise RuntimeError("STEP face reference point is not finite.")
        try:
            frame = self._nearest_traced_ray_frame_near_point(reference[:3])
            return {
                "target_point": np.asarray(frame["target_point"], dtype=float).reshape(3),
                "direction": self._normalized_vector(frame["direction"]),
                "axis_label": "nearest traced optical path"
                + (f" ray {int(frame.get('ray_index', -1))}" if int(frame.get("ray_index", -1)) >= 0 else ""),
                "ray_index": int(frame.get("ray_index", -1)),
                "branch_path": str(frame.get("branch_path", "") or ""),
            }
        except Exception:
            return {
                "target_point": np.asarray((0.0, 0.0, float(reference[2])), dtype=float),
                "direction": np.asarray((0.0, 0.0, 1.0), dtype=float),
                "axis_label": "global +Z optical axis",
                "ray_index": -1,
                "branch_path": "",
            }

    def _optical_axis_frame_from_record(
        self,
        axis_info: dict[str, object],
        *,
        reference_point=None,
    ) -> dict[str, object]:
        if not isinstance(axis_info, dict):
            raise RuntimeError("Optical-axis record is not available.")
        points = np.asarray(axis_info.get("points", ()), dtype=float)
        reference = np.asarray([], dtype=float)
        for key in ("target_point", "segment_midpoint", "picked_world"):
            try:
                candidate = np.asarray(axis_info.get(key, ()), dtype=float).reshape(-1)[:3]
            except Exception:
                candidate = np.asarray([], dtype=float)
            if candidate.size >= 3 and np.all(np.isfinite(candidate[:3])):
                reference = candidate[:3]
                break
        if reference.size < 3 and reference_point is not None:
            try:
                candidate = np.asarray(reference_point, dtype=float).reshape(-1)[:3]
            except Exception:
                candidate = np.asarray([], dtype=float)
            if candidate.size >= 3 and np.all(np.isfinite(candidate[:3])):
                reference = candidate[:3]
        if points.ndim == 2 and points.shape[0] >= 2 and points.shape[1] >= 3:
            points = np.asarray(points[:, :3], dtype=float)
            if reference.size < 3:
                reference = 0.5 * (points[0] + points[-1])
            target_point, direction = self._closest_polyline_point_and_direction(points, reference)
        else:
            target_point = reference
            direction = np.asarray(axis_info.get("direction", axis_info.get("segment_direction", ())), dtype=float).reshape(-1)[:3]
        if target_point.size < 3 or direction.size < 3:
            raise RuntimeError("Optical-axis record does not contain a valid 3D frame.")
        direction = self._normalized_vector(direction[:3])
        return {
            "target_point": np.asarray(target_point, dtype=float).reshape(3),
            "direction": np.asarray(direction, dtype=float).reshape(3),
            "axis_id": str(axis_info.get("axis_id", "") or ""),
            "axis_label": str(axis_info.get("axis_label", "Optical Axis") or "Optical Axis"),
            "axis_kind": str(axis_info.get("axis_kind", "") or ""),
            "axis_role": str(axis_info.get("axis_role", "") or ""),
            "branch_path": str(axis_info.get("branch_path", "") or ""),
            "ray_index": int(axis_info.get("ray_index", -1)),
            "source_id": str(axis_info.get("source_id", "") or ""),
            "segment_index": int(axis_info.get("segment_index", -1)),
        }

    @staticmethod
    def _analytic_step_face_record_from_triangles(face, triangle_indices: tuple[int, ...], triangles: np.ndarray) -> dict[str, object]:
        selected = np.asarray(triangles, dtype=float)
        if selected.ndim != 3 or selected.shape[1:] != (3, 3) or selected.shape[0] <= 0:
            record = face.as_optical_solid_record()
            record["triangle_indices"] = list(triangle_indices)
            record["triangle_count"] = len(triangle_indices)
            return record
        weighted_normal = np.zeros(3, dtype=float)
        weighted_centroid = np.zeros(3, dtype=float)
        total_area = 0.0
        for tri in selected:
            v0, v1, v2 = (np.asarray(vertex, dtype=float) for vertex in tri)
            cross = np.cross(v1 - v0, v2 - v0)
            norm = float(np.linalg.norm(cross))
            if norm <= 1.0e-12 or not np.isfinite(norm):
                continue
            area = 0.5 * norm
            weighted_normal += cross * 0.5
            weighted_centroid += ((v0 + v1 + v2) / 3.0) * area
            total_area += area
        if total_area > 0.0 and np.isfinite(total_area):
            centroid = weighted_centroid / total_area
        else:
            centroid = np.mean(selected.reshape((-1, 3)), axis=0)
        normal_norm = float(np.linalg.norm(weighted_normal))
        if normal_norm > 1.0e-12 and np.isfinite(normal_norm):
            normal = weighted_normal / normal_norm
        else:
            try:
                normal = np.asarray(face.normal, dtype=float).reshape(3)
            except Exception:
                normal = np.asarray((0.0, 0.0, 1.0), dtype=float)
        normal_norm = float(np.linalg.norm(normal))
        if normal_norm <= 1.0e-12 or not np.isfinite(normal_norm):
            normal = np.asarray((0.0, 0.0, 1.0), dtype=float)
        else:
            normal = normal / normal_norm
        record = face.as_optical_solid_record()
        record.update(
            {
                "centroid": [float(value) for value in centroid[:3]],
                "normal": [float(value) for value in normal[:3]],
                "area_mm2": float(total_area) if total_area > 0.0 else float(record.get("area_mm2", 0.0) or 0.0),
                "triangle_count": int(len(triangle_indices)),
                "triangle_indices": [int(value) for value in triangle_indices],
                "plane_offset_mm": float(np.dot(normal[:3], centroid[:3])),
                "assignment_source": "step_analytic_transformed",
            }
        )
        return record

    def _step_overlay_analytic_face_metadata(self, label: str) -> dict[str, object] | None:
        label = str(label).strip().lower()
        source_path = self._step_path_for_label(label)
        if source_path is None or Path(source_path).suffix.lower() not in {".step", ".stp"}:
            return None
        document = self._load_step_analytic_document(Path(source_path))
        mesh = self._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return None
        triangles, surface = self._triangle_array_from_polydata(mesh)
        if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or triangles.shape[0] <= 0:
            return None
        face_index_by_triangle = None
        try:
            candidate = np.asarray(surface.cell_data.get("kraken_step_face_index", ()), dtype=int)
            if candidate.shape[0] == triangles.shape[0]:
                face_index_by_triangle = candidate
        except Exception:
            face_index_by_triangle = None
        records: list[dict[str, object]] = []
        grouped_face_ids: set[str] = set()
        try:
            grouped_records = tuple(axisymmetric_step_selection_face_records(document))
        except Exception:
            grouped_records = ()
        if grouped_records:
            try:
                source_triangles = np.asarray(document.triangles, dtype=float).reshape((-1, 3, 3))
                affine = _affine_from_point_sets(source_triangles.reshape((-1, 3)), triangles.reshape((-1, 3)))
            except Exception:
                affine = None
            for grouped in grouped_records:
                record = dict(grouped)
                indices = tuple(
                    int(value)
                    for value in list(record.get("triangle_indices", ())) or ()
                    if 0 <= int(value) < int(triangles.shape[0])
                )
                if not indices:
                    continue
                source_ids = tuple(str(value) for value in list(record.get("source_face_ids", ())) if str(value))
                grouped_face_ids.update(source_ids)
                try:
                    center = np.asarray(record.get("centroid", ()), dtype=float).reshape(-1)[:3]
                    normal = np.asarray(record.get("normal", ()), dtype=float).reshape(-1)[:3]
                except Exception:
                    center = np.asarray([], dtype=float)
                    normal = np.asarray([], dtype=float)
                if affine is not None and center.size >= 3 and normal.size >= 3:
                    center = (affine @ np.asarray((center[0], center[1], center[2], 1.0), dtype=float))[:3]
                    normal = np.asarray(affine[:3, :3], dtype=float) @ normal[:3]
                if center.size < 3 or not np.all(np.isfinite(center[:3])):
                    selected = np.asarray(triangles[np.asarray(indices, dtype=int)], dtype=float)
                    center = np.mean(selected.reshape((-1, 3)), axis=0)
                normal_norm = float(np.linalg.norm(normal[:3])) if normal.size >= 3 else 0.0
                if normal.size < 3 or normal_norm <= 1.0e-12 or not np.isfinite(normal_norm):
                    selected = np.asarray(triangles[np.asarray(indices, dtype=int)], dtype=float)
                    fallback_record = self._analytic_step_face_record_from_triangles(
                        document.outer_faces[0],
                        indices,
                        selected,
                    )
                    normal = fallback_record.get("normal", (0.0, 0.0, 1.0))
                    normal = np.asarray(normal, dtype=float).reshape(-1)[:3]
                    normal_norm = float(np.linalg.norm(normal[:3])) if normal.size >= 3 else 0.0
                normal = np.asarray(normal[:3] / max(normal_norm, 1.0e-12), dtype=float)
                record.update(
                    {
                        "centroid": [float(value) for value in center[:3]],
                        "normal": [float(value) for value in normal[:3]],
                        "triangle_indices": [int(value) for value in indices],
                        "triangle_count": int(len(indices)),
                        "plane_offset_mm": float(np.dot(normal[:3], center[:3])),
                        "assignment_source": "step_analytic_axisymmetric_group_transformed",
                    }
                )
                records.append(record)
        for face_index, face in enumerate(document.outer_faces):
            if str(face.face_id) in grouped_face_ids:
                continue
            if face_index_by_triangle is not None:
                triangle_indices = tuple(int(value) for value in np.flatnonzero(face_index_by_triangle == int(face_index)))
            else:
                triangle_indices = tuple(
                    int(value)
                    for value in face.triangle_indices
                    if 0 <= int(value) < int(triangles.shape[0])
                )
            if not triangle_indices:
                continue
            selected = np.asarray(triangles[np.asarray(triangle_indices, dtype=int)], dtype=float)
            records.append(self._analytic_step_face_record_from_triangles(face, triangle_indices, selected))
        if not records:
            return None
        digest = hashlib.sha1()
        digest.update(f"analytic:{label}".encode("utf-8"))
        digest.update(str(Path(source_path).resolve()).encode("utf-8", errors="ignore"))
        digest.update(np.ascontiguousarray(triangles, dtype=np.float64).tobytes())
        mesh_path = _current_cad_cache_dir() / "step_overlay_face_snap" / f"{label}_analytic_{digest.hexdigest()[:16]}.stl"
        if not mesh_path.exists() or mesh_path.stat().st_size <= 0:
            mesh_path.parent.mkdir(parents=True, exist_ok=True)
            output_mesh = self._polydata_from_triangle_array(triangles)
            if output_mesh is not None:
                output_mesh.save(str(mesh_path))
        metadata = normalize_optical_solid_face_metadata(
            {
                "source_stl": str(mesh_path),
                "source_step": str(Path(source_path)),
                "source_backend": document.backend,
                "faces": auto_assign_optical_solid_face_roles(records),
            },
            source_stl=str(mesh_path),
        )
        metadata["source_step"] = str(Path(source_path))
        metadata["source_backend"] = document.backend
        metadata["source_face_count"] = int(document.source_face_count)
        metadata["outer_face_count"] = int(len(document.outer_faces))
        metadata["interior_duplicate_count"] = int(document.interior_duplicate_count)
        return metadata

    def _step_overlay_face_metadata(self, label: str) -> dict[str, object]:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set() or self._step_path_for_label(label) is None:
            return normalize_optical_solid_face_metadata({})
        try:
            analytic_metadata = self._step_overlay_analytic_face_metadata(label)
            if analytic_metadata is not None:
                return analytic_metadata
        except Exception as exc:
            self.append_debug(f"Analytic STEP face metadata fell back to planar clustering for {label}: {_short_error_message(exc)}")
        mesh = self._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return normalize_optical_solid_face_metadata({})
        try:
            mesh = mesh.extract_surface(algorithm="dataset_surface").triangulate().copy(deep=True)
        except Exception:
            try:
                mesh = mesh.extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                mesh = mesh.copy(deep=True)
        points = np.asarray(getattr(mesh, "points", np.empty((0, 3))), dtype=float)
        if points.ndim != 2 or points.shape[0] < 3 or points.shape[1] < 3 or not np.all(np.isfinite(points[:, :3])):
            return normalize_optical_solid_face_metadata({})
        digest = hashlib.sha1()
        digest.update(str(label).encode("utf-8"))
        source_path = self._step_path_for_label(label)
        if source_path is not None:
            digest.update(str(source_path.resolve()).encode("utf-8", errors="ignore"))
        digest.update(np.ascontiguousarray(points[:, :3], dtype=np.float64).tobytes())
        mesh_path = _current_cad_cache_dir() / "step_overlay_face_snap" / f"{label}_{digest.hexdigest()[:16]}.stl"
        if not mesh_path.exists() or mesh_path.stat().st_size <= 0:
            mesh_path.parent.mkdir(parents=True, exist_ok=True)
            mesh.save(str(mesh_path))
        candidates = cluster_optical_solid_planar_faces(mesh_path)
        records = auto_assign_optical_solid_face_roles(
            [optical_solid_face_record_from_candidate(candidate) for candidate in candidates]
        )
        return normalize_optical_solid_face_metadata(
            {"source_stl": str(mesh_path), "faces": records},
            candidates,
            source_stl=str(mesh_path),
        )

    def snap_step_overlay_face_to_optical_axis(
        self,
        label: str,
        axis_info: dict[str, object],
        *,
        face_id: str = "",
        guide_face_id: str = "",
        guide_direction=None,
    ) -> dict[str, object] | None:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set() or self._step_path_for_label(label) is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return None
        metadata = self._step_overlay_face_metadata(label)
        requested_face = str(face_id or "").strip()
        face = None
        faces = [face for face in list(metadata.get("faces", []) or []) if isinstance(face, dict)]
        if requested_face:
            for candidate in faces:
                if str(candidate.get("face_id", "") or "").strip() == requested_face:
                    face = normalize_optical_solid_face_record(candidate)
                    break
            if face is None:
                self.status_var.set(f"{label.upper()} STEP face {requested_face} is not available for optical-axis snap.")
                return None
        else:
            face = optical_solid_metadata.optical_solid_input_anchor_face(metadata) or select_optical_solid_anchor_face(metadata)
        if face is None:
            self.status_var.set(f"{label.upper()} STEP has no planar face available for optical-axis snap.")
            return None
        resolved_face_id = str(face.get("face_id", "") or "").strip()
        resolved_guide_face_id = str(guide_face_id or "").strip()
        if not resolved_guide_face_id:
            resolved_guide_face_id = self._default_step_pair_guide_face_id(label, metadata, resolved_face_id)
        if resolved_guide_face_id:
            pair_result = self.snap_step_overlay_face_pair_to_optical_axis(
                label,
                axis_info,
                anchor_face_id=resolved_face_id,
                guide_face_id=resolved_guide_face_id,
                guide_direction=guide_direction,
            )
            if pair_result is not None:
                return pair_result
        feature_center = np.asarray(face.get("centroid", ()), dtype=float).reshape(-1)[:3]
        feature_normal = np.asarray(face.get("normal", ()), dtype=float).reshape(-1)[:3]
        if feature_center.size < 3 or feature_normal.size < 3:
            self.status_var.set(f"{label.upper()} STEP face geometry is incomplete for optical-axis snap.")
            return None
        axis_frame = self._optical_axis_frame_from_record(axis_info, reference_point=feature_center[:3])
        result = self.snap_step_feature_normal_to_optical_axis(
            label,
            feature_center[:3],
            feature_normal[:3],
            axis_frame=axis_frame,
        )
        if result is None:
            return None
        result.update(
            {
                "face_id": str(face.get("face_id", "") or "").strip(),
                "face_label": _optical_solid_face_marker_label(face),
                "axis_id": str(axis_frame.get("axis_id", "") or ""),
                "axis_kind": str(axis_frame.get("axis_kind", "") or ""),
                "axis_role": str(axis_frame.get("axis_role", "") or ""),
                "segment_index": int(axis_frame.get("segment_index", -1)),
            }
        )
        self._record_step_overlay_axis_anchor(
            label,
            face_id=str(face.get("face_id", "") or "").strip(),
            target_point=result.get("target_point"),
            target_direction=result.get("target_direction"),
            anchor_mode="surface_center_normal",
            axis_frame=axis_frame,
            source="face_normal_axis_snap",
        )
        return result

    def _default_step_pair_guide_face_id(self, label: str, metadata: dict[str, object], anchor_face_id: str) -> str:
        """Return a second face when one-click STEP axis snap needs a roll constraint."""
        label = str(label).strip().lower()
        anchor = str(anchor_face_id or "").strip()
        face_ids = {
            str(face.get("face_id", "") or "").strip()
            for face in list(metadata.get("faces", []) or [])
            if isinstance(face, dict)
        }
        source_path = self._step_path_for_label(label)
        source_text = str(source_path or "")
        if anchor == "F005" and "F006" in face_ids and "42779" in source_text:
            return "F006"
        return ""

    @staticmethod
    def _project_direction_perpendicular(direction, normal) -> np.ndarray:
        candidate = np.asarray(direction, dtype=float).reshape(3)
        axis = np.asarray(normal, dtype=float).reshape(3)
        axis_norm = float(np.linalg.norm(axis))
        if axis_norm <= 1e-12 or not np.isfinite(axis_norm):
            raise ValueError("Projection normal must be finite and non-zero.")
        axis = axis / axis_norm
        candidate = candidate - axis * float(np.dot(candidate, axis))
        candidate_norm = float(np.linalg.norm(candidate))
        if candidate_norm <= 1e-9 or not np.isfinite(candidate_norm):
            raise ValueError("Guide direction is parallel to the snapped axis.")
        return candidate / candidate_norm

    def snap_step_overlay_face_pair_to_optical_axis(
        self,
        label: str,
        axis_info: dict[str, object],
        *,
        anchor_face_id: str,
        guide_face_id: str,
        guide_direction=None,
    ) -> dict[str, object] | None:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set() or self._step_path_for_label(label) is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return None
        metadata = self._step_overlay_face_metadata(label)
        faces = {
            str(face.get("face_id", "") or "").strip(): normalize_optical_solid_face_record(face)
            for face in list(metadata.get("faces", []) or [])
            if isinstance(face, dict) and str(face.get("face_id", "") or "").strip()
        }
        anchor_id = str(anchor_face_id or "").strip()
        guide_id = str(guide_face_id or "").strip()
        anchor = faces.get(anchor_id)
        guide = faces.get(guide_id)
        if anchor is None or guide is None:
            self.status_var.set(f"{label.upper()} STEP two-face snap needs faces {anchor_id}/{guide_id}.")
            return None
        anchor_center = np.asarray(anchor.get("centroid", ()), dtype=float).reshape(-1)[:3]
        anchor_normal = np.asarray(anchor.get("normal", ()), dtype=float).reshape(-1)[:3]
        guide_normal = np.asarray(guide.get("normal", ()), dtype=float).reshape(-1)[:3]
        if (
            anchor_center.size < 3
            or anchor_normal.size < 3
            or guide_normal.size < 3
            or not np.all(np.isfinite(anchor_center[:3]))
            or not np.all(np.isfinite(anchor_normal[:3]))
            or not np.all(np.isfinite(guide_normal[:3]))
        ):
            self.status_var.set(f"{label.upper()} STEP two-face snap has incomplete face geometry.")
            return None
        anchor_normal = self._normalized_vector(anchor_normal[:3])
        guide_normal = self._normalized_vector(guide_normal[:3])
        axis_frame = self._optical_axis_frame_from_record(axis_info, reference_point=anchor_center[:3])
        target_point = np.asarray(axis_frame["target_point"], dtype=float).reshape(3)
        axis_direction = self._normalized_vector(axis_frame["direction"])
        target_anchor_normal = -axis_direction
        if guide_direction is None:
            anchor_only_delta = self._rotation_matrix_between_vectors(anchor_normal, target_anchor_normal)
            target_guide_normal = self._project_direction_perpendicular(anchor_only_delta @ guide_normal, target_anchor_normal)
        else:
            target_guide_normal = self._project_direction_perpendicular(guide_direction, target_anchor_normal)

        current_mesh = self._transformed_imported_step_mesh_for_label(label)
        if current_mesh is None or int(getattr(current_mesh, "n_points", 0)) <= 0:
            self.status_var.set(f"{label.upper()} STEP mesh unavailable for optical-axis two-face snap.")
            return None
        current_points = np.asarray(getattr(current_mesh, "points", np.empty((0, 3))), dtype=float)
        if current_points.ndim != 2 or current_points.shape[0] < 4 or current_points.shape[1] < 3:
            self.status_var.set(f"{label.upper()} STEP mesh does not have enough points for optical-axis two-face snap.")
            return None

        current_angles = self._step_rotation_deg_tuple(label)
        current_offset = np.asarray(self._step_placement_offset_xyz(label), dtype=float).reshape(3)
        current_matrix = self._step_rotation_matrix_from_angles(*current_angles)
        try:
            delta_matrix = optical_solid_metadata.rotation_matrix_from_vector_pairs(
                source_primary=anchor_normal,
                source_secondary=guide_normal,
                target_primary=target_anchor_normal,
                target_secondary=target_guide_normal,
            )
        except Exception as exc:
            self.status_var.set(f"{label.upper()} STEP two-face snap failed: {_short_error_message(exc)}")
            return None
        next_matrix = delta_matrix @ current_matrix
        next_angles = self._step_angles_from_rotation_matrix(next_matrix)

        self._set_step_rotation_deg_tuple(label, next_angles)
        try:
            rotated_mesh = self._transformed_imported_step_mesh_for_label(label)
        finally:
            self._set_step_rotation_deg_tuple(label, current_angles)
        if rotated_mesh is None or int(getattr(rotated_mesh, "n_points", 0)) <= 0:
            self.status_var.set(f"{label.upper()} STEP rotated mesh unavailable for optical-axis two-face snap.")
            return None
        rotated_points = np.asarray(getattr(rotated_mesh, "points", np.empty((0, 3))), dtype=float)
        affine = _affine_from_point_sets(current_points[:, :3], rotated_points[:, :3])
        if affine is not None:
            rotated_anchor_center = (affine @ np.asarray((anchor_center[0], anchor_center[1], anchor_center[2], 1.0), dtype=float))[:3]
        else:
            rotated_anchor_center = anchor_center[:3]
        placement_delta = target_point[:3] - np.asarray(rotated_anchor_center, dtype=float).reshape(3)
        next_offset = current_offset[:3] + placement_delta[:3]

        self._begin_history_capture()
        self._set_step_rotation_deg_tuple(label, next_angles)
        self._set_step_placement_offset_xyz(label, next_offset)
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label = label
        self._commit_history_capture()
        rotated_anchor_normal = delta_matrix @ anchor_normal
        rotated_guide_normal = delta_matrix @ guide_normal
        anchor_error = float(
            np.rad2deg(np.arccos(np.clip(float(np.dot(rotated_anchor_normal, target_anchor_normal)), -1.0, 1.0)))
        )
        guide_error = float(
            np.rad2deg(np.arccos(np.clip(float(np.dot(rotated_guide_normal, target_guide_normal)), -1.0, 1.0)))
        )
        axis_label = str(axis_frame.get("axis_label", "optical axis"))
        self.status_var.set(
            f"{label.upper()} STEP {anchor_id}/{guide_id} snapped to {axis_label}; "
            f"entrance error {anchor_error:.6g} deg, roll error {guide_error:.6g} deg."
        )
        self._record_step_overlay_axis_anchor(
            label,
            face_id=anchor_id,
            guide_face_id=guide_id,
            target_point=target_point[:3],
            target_direction=target_anchor_normal[:3],
            guide_direction=target_guide_normal[:3],
            anchor_mode="surface_center_normal_with_roll",
            axis_frame=axis_frame,
            source="face_pair_axis_snap",
        )
        self._refresh_open_3d_views(step_label=label)
        return {
            "label": label,
            "axis_label": axis_label,
            "axis_id": str(axis_frame.get("axis_id", axis_info.get("axis_id", "")) or ""),
            "axis_kind": str(axis_frame.get("axis_kind", axis_info.get("axis_kind", "")) or ""),
            "axis_role": str(axis_frame.get("axis_role", axis_info.get("axis_role", "")) or ""),
            "segment_index": int(axis_frame.get("segment_index", axis_info.get("segment_index", -1))),
            "face_id": anchor_id,
            "guide_face_id": guide_id,
            "target_point": tuple(float(value) for value in target_point[:3]),
            "target_direction": tuple(float(value) for value in target_anchor_normal[:3]),
            "guide_direction": tuple(float(value) for value in target_guide_normal[:3]),
            "rotation_deg": tuple(float(value) for value in next_angles),
            "placement_offset_xyz": tuple(float(value) for value in next_offset[:3]),
            "angle_error_deg": anchor_error,
            "guide_angle_error_deg": guide_error,
            "ray_index": int(axis_frame.get("ray_index", -1)),
            "branch_path": str(axis_frame.get("branch_path", "") or ""),
        }

    def snap_step_feature_normal_to_optical_axis(
        self,
        label: str,
        feature_center_xyz,
        feature_normal_xyz,
        *,
        axis_frame: dict[str, object] | None = None,
    ) -> dict[str, object] | None:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return None
        if self._step_path_for_label(label) is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return None
        feature_center = np.asarray(feature_center_xyz, dtype=float).reshape(-1)[:3]
        feature_normal = np.asarray(feature_normal_xyz, dtype=float).reshape(-1)[:3]
        if (
            feature_center.size < 3
            or feature_normal.size < 3
            or not np.all(np.isfinite(feature_center[:3]))
            or not np.all(np.isfinite(feature_normal[:3]))
        ):
            self.status_var.set("Snap STEP Normal->Optical Axis needs a finite picked STEP face center and normal.")
            return None
        feature_normal = self._normalized_vector(feature_normal[:3])
        frame = dict(axis_frame) if isinstance(axis_frame, dict) else self._step_optical_axis_frame_near_point(feature_center[:3])
        target_point = np.asarray(frame["target_point"], dtype=float).reshape(3)
        axis_direction = self._normalized_vector(frame["direction"])
        target_normal = -axis_direction

        current_mesh = self._transformed_imported_step_mesh_for_label(label)
        if current_mesh is None or int(getattr(current_mesh, "n_points", 0)) <= 0:
            self.status_var.set(f"{label.upper()} STEP mesh unavailable for optical-axis normal snap.")
            return None
        current_points = np.asarray(getattr(current_mesh, "points", np.empty((0, 3))), dtype=float)
        if current_points.ndim != 2 or current_points.shape[0] < 4 or current_points.shape[1] < 3:
            self.status_var.set(f"{label.upper()} STEP mesh does not have enough points for optical-axis normal snap.")
            return None

        current_angles = self._step_rotation_deg_tuple(label)
        current_offset = np.asarray(self._step_placement_offset_xyz(label), dtype=float).reshape(3)
        current_matrix = self._step_rotation_matrix_from_angles(*current_angles)
        delta_matrix = self._rotation_matrix_between_vectors(feature_normal, target_normal)
        next_matrix = delta_matrix @ current_matrix
        next_angles = self._step_angles_from_rotation_matrix(next_matrix)

        self._set_step_rotation_deg_tuple(label, next_angles)
        try:
            rotated_mesh = self._transformed_imported_step_mesh_for_label(label)
        finally:
            self._set_step_rotation_deg_tuple(label, current_angles)
        if rotated_mesh is None or int(getattr(rotated_mesh, "n_points", 0)) <= 0:
            self.status_var.set(f"{label.upper()} STEP rotated mesh unavailable for optical-axis normal snap.")
            return None
        rotated_points = np.asarray(getattr(rotated_mesh, "points", np.empty((0, 3))), dtype=float)
        affine = _affine_from_point_sets(current_points[:, :3], rotated_points[:, :3])
        if affine is not None:
            rotated_feature_center = (affine @ np.asarray((feature_center[0], feature_center[1], feature_center[2], 1.0), dtype=float))[:3]
        else:
            rotated_feature_center = feature_center[:3]
        placement_delta = target_point[:3] - np.asarray(rotated_feature_center, dtype=float).reshape(3)
        next_offset = current_offset[:3] + placement_delta[:3]

        self._begin_history_capture()
        self._set_step_rotation_deg_tuple(label, next_angles)
        self._set_step_placement_offset_xyz(label, next_offset)
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label = label
        self._commit_history_capture()
        rotated_normal = self._rotation_matrix_between_vectors(feature_normal, target_normal) @ feature_normal
        angle_error = float(np.rad2deg(np.arccos(np.clip(float(np.dot(rotated_normal, target_normal)), -1.0, 1.0))))
        axis_label = str(frame.get("axis_label", "optical axis"))
        self.status_var.set(
            f"{label.upper()} STEP entrance normal aligned opposite {axis_label}; "
            f"face center moved to ({target_point[0]:.6g}, {target_point[1]:.6g}, {target_point[2]:.6g}) mm."
        )
        self._record_step_overlay_axis_anchor(
            label,
            target_point=target_point[:3],
            target_direction=target_normal[:3],
            anchor_mode="picked_point_normal",
            axis_frame=frame,
            source="feature_normal_axis_snap",
        )
        self._refresh_open_3d_views(step_label=label)
        return {
            "label": label,
            "axis_label": axis_label,
            "target_point": tuple(float(value) for value in target_point[:3]),
            "target_direction": tuple(float(value) for value in target_normal[:3]),
            "rotation_deg": tuple(float(value) for value in next_angles),
            "placement_offset_xyz": tuple(float(value) for value in next_offset[:3]),
            "angle_error_deg": angle_error,
            "ray_index": int(frame.get("ray_index", -1)),
            "branch_path": str(frame.get("branch_path", "") or ""),
        }

    @staticmethod
    def _step_orientation_direction_vector(direction_label: object) -> np.ndarray | None:
        return StepFaceDirectionService.direction_vector(direction_label)

    def orient_step_feature_normal_to_direction(
        self,
        label: str,
        feature_center_xyz,
        feature_normal_xyz,
        direction_label: str,
        *,
        face_id: str = "",
    ) -> dict[str, object] | None:
        try:
            plan = self._step_face_direction_service().plan_overlay_face_direction(
                label,
                feature_center_xyz,
                feature_normal_xyz,
                direction_label,
                face_id=face_id,
            )
        except ValueError as exc:
            self.status_var.set(str(exc))
            return None
        if plan is None:
            return None
        self._begin_history_capture()
        self._set_step_rotation_deg_tuple(plan.label, plan.rotation_deg)
        self._set_step_placement_offset_xyz(plan.label, plan.placement_offset_xyz)
        self._selected_step_label = plan.label
        self._commit_history_capture()
        face_note = f" {plan.face_id}" if plan.face_id else ""
        self.status_var.set(
            f"{plan.label.upper()} STEP face{face_note} normal set to {plan.direction_label}; "
            f"face center held at ({plan.surface_center[0]:.6g}, "
            f"{plan.surface_center[1]:.6g}, {plan.surface_center[2]:.6g}) mm."
        )
        self._refresh_open_3d_views(step_label=plan.label)
        return plan.as_result()
