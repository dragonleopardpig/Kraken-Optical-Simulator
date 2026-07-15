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
from KrakenOS.UI.services import open3d_solid_resize as solid_resize
from KrakenOS.UI.services.cad_step_export import _affine_from_point_sets, _read_step_shape
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
from KrakenOS.UI.services.beam_splitter_factory import generate_beam_splitter
from KrakenOS.UI.services.led_clear_aperture_detect import (
    detect_clear_aperture_openings_from_analytic_faces,
)
from KrakenOS.UI.services.open3d_face_index_edges import (
    face_index_for_display_cell,
    triangle_array_and_face_index,
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
        # BS<->LED two-body glue: a direct drag of the promoted beam-splitter row carries the
        # glued LED overlay by the same vector (guarded against carry-back from the LED side).
        if (
            not getattr(self, "_optical_led_carry_active", False)
            and bool(getattr(self, "_optical_led_glued", False))
            and self._promoted_optical_solid_row_index("optical") == row_index
        ):
            self._carry_glued_optical_led("optical", delta[:3])
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

        # bugs/0204: read this row's origin straight from the ALREADY-BUILT system's
        # transform list (the mirror of _surface_reference_world_normal's [:3, 2] read
        # below), instead of rebuilding the whole system per call via
        # _surface_origin_for_rows. The thickness-dimension overlay calls this twice per
        # row (32x on the folded RA-mirror scene); each rebuild force-meshed the BK7 cube
        # via apply_optical_solid_output_port_system_overrides -> ~40 s per refresh
        # ("Creating solid objects for optical elements" x32). Falls back to the rebuild
        # when no system is passed (headless callers) or it carries no transforms.
        transforms = self._system_transform_list(system)
        if transforms is not None and 0 <= row_index < len(transforms):
            try:
                origin = np.asarray(transforms[row_index], dtype=float).reshape(4, 4)[:3, 3]
                if origin.size >= 3 and np.all(np.isfinite(origin)):
                    return origin.astype(float)
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
        path: Path | str | None = None,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        return self._step_overlay_import_service().import_optical_step(
            dialog_parent=dialog_parent,
            path=path,
            refresh_open_3d=refresh_open_3d,
        )

    def import_camera_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        path: Path | str | None = None,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        return self._step_overlay_import_service().import_camera_step(
            dialog_parent=dialog_parent,
            path=path,
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
        # bugs/0151: the LIVE "Object -> LED" dimension the user sees and clicks is
        # ``led_object_edge_distance_mm + placement_offset_z`` (a free carry-drag adds
        # the axial offset on top of the typed knob WITHOUT rewriting it -- see the
        # live_distance derivation in open3d_thickness_dimensions). The dialog used to
        # prefill and write the RAW knob, so after a drag it showed the stale knob
        # (e.g. 200) instead of the live 128.7, and typing V landed the LED at
        # V + offset_z, not V ("changing the Object LED distance is not working").
        # Prefill the live distance and fold the offset back out on commit so the
        # typed value IS the live distance; leave placement_offset untouched so the
        # bugs/0133 glue-carry (which tracks _led_step_z_translation, excluding
        # offset_z) shoves the glued beam splitter by the SAME net z-shift as the LED.
        offset_z = float(self._step_placement_offset_xyz("led")[2])
        current = max(float(getattr(self, "led_object_edge_distance_mm", 0.0)) + offset_z, 0.0)
        if current <= 0.0:
            current = self._default_led_object_edge_distance()
        value = self._ask_led_edge_distance(current)
        if value is None:
            return
        self._begin_history_capture()
        before_translation = self._led_step_z_translation()
        self.led_object_edge_distance_mm = float(value) - offset_z
        self._clear_led_edge_dimension_override()
        self._carry_led_glue_over_translation_change(before_translation)  # bugs/0133
        self._commit_history_capture()
        self.status_var.set(f"LED edge distance: {float(value):.3g} mm")
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
        before_translation = self._led_step_z_translation()
        local_z = float(feature_center[2]) - before_translation
        self._begin_history_capture()
        self.led_step_object_edge_local_z = local_z
        self._clear_led_edge_dimension_override()
        self._cad_led_object_edge_pick = False
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._selected_step_label = "led"
        self._carry_led_glue_over_translation_change(before_translation)  # bugs/0133
        self._commit_history_capture()
        self.status_var.set(
            f"LED object edge locked. Local Z={local_z:.3g} mm; "
            f"edge distance={self.led_object_edge_distance_mm:.3g} mm."
        )
        self._refresh_open_3d_views(step_label="led")

    @staticmethod
    def _led_reanchor_reference(face_world_z: float, current_translation: float):
        """bugs/0132: re-anchoring the amber object->LED arrow onto a picked LED face
        records that face as the LED's object-edge reference. Return
        ``(local_z, edge_distance)`` such that:

          * the LED does NOT jump now -- ``edge_distance`` is the face's *current*
            world z, so the recomputed translation equals the current one; and
          * a later edge-distance edit to ``V`` slides the LED so the picked face
            lands at ``V`` (translation = V - local_z  =>  face world == V).

        ``local_z`` is the face in the LED's pre-translation frame
        (``face_world_z - current_translation``)."""
        fz = float(face_world_z)
        return fz - float(current_translation), fz

    def apply_led_object_edge_reanchor(self, feature_center_xyz) -> None:
        """bugs/0132: re-anchor the amber object->LED arrow (sentinel row -7) onto a
        picked LED face/edge and make it the LED's PERSISTENT object-edge reference.

        Unlike the legacy object-edge pick (``apply_led_object_edge_pick``, which jumps
        the LED so the face lands at the *current* typed distance), this keeps the body
        put: it sets the typed edge distance to the picked face's current object
        distance. The amber arrow then points at the chosen face, the LED edge-distance
        dialog reflects that distance, and editing the value MOVES the LED so the chosen
        face tracks the new distance. Reverses bugs/0130's measurement-only behaviour
        (which, on a value-change, reverted to the typed endpoint -- a cable extremum --
        and left the LED parked)."""
        feature_center = np.asarray(feature_center_xyz, dtype=float).reshape(-1)
        if feature_center.size < 3 or not np.all(np.isfinite(feature_center[:3])):
            self.status_var.set("Invalid LED object-edge re-anchor pick.")
            return
        local_z, edge_distance = self._led_reanchor_reference(
            float(feature_center[2]), self._led_step_z_translation()
        )
        # bugs/0133: no glue carry here -- re-anchor sets the typed distance to the picked
        # face's CURRENT object distance, so the LED translation is unchanged (the body
        # stays put). The carry fires on the later edge-distance edit that actually moves it.
        self._begin_history_capture()
        self.led_step_object_edge_local_z = float(local_z)
        self.led_object_edge_distance_mm = max(float(edge_distance), 0.0)
        self._clear_led_edge_dimension_override()
        self._cad_led_object_edge_pick = False
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._selected_step_label = "led"
        self._commit_history_capture()
        self.status_var.set(
            f"Object→LED edge re-anchored. Distance={self.led_object_edge_distance_mm:.4g} mm; "
            "editing it now moves the LED."
        )
        self._refresh_open_3d_views(step_label="led")

    # ------------------------------------------------------------------
    # bugs/0053: thickness/distance dimension measurement re-anchoring.
    # A re-anchored dimension endpoint reports the distance to a picked
    # surface/edge instead of the adjacent surface. It is a MEASUREMENT
    # annotation -- it never moves an optical surface (rows[i].thickness is
    # untouched; that stays the plain-drag / inline-edit path). The object/LED
    # row's object-side endpoint instead feeds the existing object-edge
    # reference (led_step_object_edge_local_z) so the LED body sits with the
    # chosen face at the object distance.
    def _dimension_anchor_override_for_row(self, row_index: int) -> dict | None:
        overrides = getattr(self, "_dimension_anchor_overrides", None)
        if not isinstance(overrides, dict):
            return None
        spec = overrides.get(int(row_index))
        return spec if isinstance(spec, dict) else None

    def _clear_led_edge_dimension_override(self) -> None:
        """Drop any stale sentinel (-7) re-anchor override. bugs/0132 re-anchors the
        LED's object-edge reference directly (no measurement-only override is created
        anymore), but a prior-session / undo-history override could linger -- clear it on
        LED re-placement so the amber arrow measures to the live object-edge."""
        overrides = getattr(self, "_dimension_anchor_overrides", None)
        if isinstance(overrides, dict) and -7 in overrides:
            overrides = dict(overrides)
            overrides.pop(-7, None)
            self._dimension_anchor_overrides = overrides

    def _dimension_row_is_object_led(self, row_index: int, endpoint: str) -> bool:
        """The S0 object-side endpoint is the LED object edge (reuses the LED ref)."""
        return (
            int(row_index) == 0
            and str(endpoint) == "start"
            and getattr(self, "imported_led_step_path", None) is not None
        )

    def apply_dimension_anchor_override(
        self, row_index: int, endpoint: str, feature_center_xyz, fixed_z=None, feature_ref=None
    ) -> None:
        feature = np.asarray(feature_center_xyz, dtype=float).reshape(-1)
        if feature.size < 3 or not np.all(np.isfinite(feature[:3])):
            self.status_var.set("Invalid dimension re-anchor pick.")
            return
        endpoint = "start" if str(endpoint).strip().lower() == "start" else "end"
        try:
            row_index = int(row_index)
        except Exception:
            return
        # Object/LED row: route to the existing object-edge reference, which both
        # records the picked edge and re-seats the LED body at the object distance.
        if self._dimension_row_is_object_led(row_index, endpoint):
            self.apply_led_object_edge_pick(feature[:3])
            return
        # bugs/0132: the amber object->LED arrow (sentinel row -7) re-anchors the LED's
        # OWN object-edge reference so a later edge-distance edit MOVES the LED with the
        # arrow staying on the chosen face. (0130 stored a measurement-only override that
        # cleared on value-change, reverting the arrow to the typed cable extremum.)
        if int(row_index) == -7:  # Open3DThicknessDimensionService.LED_OBJECT_EDGE_DIM_ROW
            self.apply_led_object_edge_reanchor(feature[:3])
            return
        # General row: store the measured-to reference (axial z of the picked
        # feature). The drawn distance recomputes to it; the model is untouched.
        # ``fixed_z`` (the un-moved endpoint's axial z) is stored so a later value
        # edit can re-solve the measured distance without touching any optical
        # thickness (bugs/0053 #6 -- editing used to move the wrong element).
        ref_z = float(feature[2])
        ref_label = str(self._dimension_anchor_feature_label(feature[:3]))
        # bugs/0149: keep ONE independent anchor PER ENDPOINT. Re-anchoring the start
        # must not discard a previously re-anchored end (and vice versa), and each end
        # re-derives its live z from the feature it was pinned to so it TRACKS the
        # model on an FOV/layout change. The legacy mirror keys
        # (endpoint/ref_z/ref_label/fixed_z) are still written for the value-edit path
        # and pre-0149 readers.
        anchor = self._dimension_endpoint_anchor_from_feature(feature[:3], feature_ref)
        self._begin_history_capture()
        overrides = dict(getattr(self, "_dimension_anchor_overrides", {}) or {})
        spec = dict(overrides.get(row_index) or {})
        # Migrate a prior legacy frozen other-end z into an absolute anchor, so a
        # pre-0149 (or value-edit) override does not lose the other end when this end
        # is re-anchored. Skip if that end already carries a real anchor.
        other = "start" if endpoint == "end" else "end"
        if not isinstance(spec.get(other), dict):
            legacy_other_z = spec.get("fixed_z")
            try:
                if legacy_other_z is not None and np.isfinite(float(legacy_other_z)):
                    spec[other] = {
                        "kind": "absolute",
                        "abs_z": float(legacy_other_z),
                        "label": "",
                    }
            except Exception:
                pass
        spec[endpoint] = anchor
        spec["endpoint"] = endpoint
        spec["ref_z"] = ref_z
        spec["ref_label"] = ref_label
        try:
            if fixed_z is not None and np.isfinite(float(fixed_z)):
                spec["fixed_z"] = float(fixed_z)
        except Exception:
            pass
        overrides[row_index] = spec
        self._dimension_anchor_overrides = overrides
        self._commit_history_capture()
        tracked = " (tracks the model)" if str(anchor.get("kind")) == "surface" else ""
        self.status_var.set(
            f"S{row_index} dimension re-anchored ({endpoint}) to z={ref_z:.4g} mm"
            + (f" [{ref_label}]" if ref_label else "")
            + tracked
            + " -- measurement only; optical thickness unchanged."
        )
        self._refresh_open_3d_views()

    def _dimension_endpoint_anchor_from_feature(self, feature_xyz, feature_ref) -> dict:
        """bugs/0149: build one re-anchored ENDPOINT anchor. A pick that resolved to
        an optical surface row stores a ``surface`` anchor that re-derives its live
        axial z every redraw (tracks the model on an FOV/layout change); an
        empty-space / unresolved pick stores an ``absolute`` anchor frozen at the
        picked z (the pre-0149 behaviour, kept as the fallback)."""
        feat = np.asarray(feature_xyz, dtype=float).reshape(-1)[:3]
        abs_z = float(feat[2])
        label = str(self._dimension_anchor_feature_label(feat))
        row = None
        face_id = ""
        if isinstance(feature_ref, dict):
            raw_row = feature_ref.get("row")
            if raw_row is not None:
                try:
                    row = int(raw_row)
                except Exception:
                    row = None
            face_id = str(feature_ref.get("face_id") or "")
        if row is not None and 0 <= row < len(self.rows):
            anchor = {"kind": "surface", "row": int(row), "abs_z": abs_z, "label": label}
            if face_id:
                anchor["face_id"] = face_id
            # Anchor the frozen fallback to the surface's CURRENT station so the
            # committed draw matches the live resolve at pick time (no visible jump).
            try:
                pt = self._surface_reference_world_point(int(row), face_id=face_id)
                z = float(np.asarray(pt, dtype=float).reshape(-1)[:3][2])
                if np.isfinite(z):
                    anchor["abs_z"] = z
            except Exception:
                pass
            return anchor
        return {"kind": "absolute", "abs_z": abs_z, "label": label}

    def apply_reanchored_dimension_value(self, row_index: int, value: float) -> bool:
        """Edit a re-anchored dimension's value by MOVING the downstream element so
        the Previous->Next span becomes ``value`` (bugs/0053 #6 follow-up).

        Rule (confirmed with the user): thickness is a directed gap and element
        positions are cumulative, so editing the span moves the Next element (the
        endpoint downstream in ray-trace order, i.e. larger z) plus everything
        downstream of it as a rigid block, by adding the delta to the *single* gap
        immediately upstream of that element. Every other gap value -- and the
        Previous element and everything upstream -- stays put. The Quick Estimation
        conjugate solve is intentionally NOT run here (that is what moved the wrong
        element before); this is a pure sequential move.

        Returns True when an element was moved. Returns False (caller leaves the
        model untouched, shows a note) when there is no override, ``fixed_z`` is
        unknown, the downstream endpoint does not map to a real optical surface
        (e.g. re-anchored onto a STEP body face), there is no editable upstream
        gap, or the move would collapse/invert the chain.
        """
        overrides = dict(getattr(self, "_dimension_anchor_overrides", {}) or {})
        spec = overrides.get(int(row_index))
        if not isinstance(spec, dict):
            return False
        fixed_z = spec.get("fixed_z")
        cur_ref = spec.get("ref_z")
        if fixed_z is None or cur_ref is None:
            return False
        try:
            fixed_z = float(fixed_z)
            cur_ref = float(cur_ref)
            target_span = abs(float(value))
        except Exception:
            return False
        if not (np.isfinite(fixed_z) and np.isfinite(cur_ref) and np.isfinite(target_span)):
            return False

        prev_z = min(fixed_z, cur_ref)
        next_z = max(fixed_z, cur_ref)
        current_span = next_z - prev_z
        if current_span <= 1e-9:
            self.status_var.set("Re-anchored dimension has no length to edit.")
            return False

        z_positions = list(self._row_z_positions())
        if not z_positions:
            return False
        track = float(z_positions[-1] - z_positions[0]) if len(z_positions) > 1 else 0.0
        snap_tol = max(abs(track) * 0.02, 0.5)
        # Map the downstream endpoint to the optical surface it sits on; that row is
        # the Next element we move. The fixed endpoint always lands on a row exactly;
        # a re-anchored endpoint only maps if it was picked on a real surface.
        next_row = None
        best = snap_tol
        for idx, z in enumerate(z_positions):
            d = abs(float(z) - next_z)
            if d <= best:
                best = d
                next_row = idx
        if next_row is None or next_row < 1:
            # The moved endpoint sits on no optical surface. For the object->LED
            # row (S0 with an imported LED), it sits on the LED body instead, so
            # MOVE the LED body (its object-side placement) -- not an optical gap --
            # until the measured face lands at the typed object distance. The
            # optical model (rows[i].thickness) is untouched (bugs/0054).
            if int(row_index) == 0 and getattr(self, "imported_led_step_path", None) is not None:
                return self._move_led_for_reanchored_value(
                    row_index, spec, overrides, fixed_z, cur_ref, target_span
                )
            self.status_var.set(
                f"S{int(row_index)} re-anchored end is not on a movable optical surface; "
                "value edit can't move an element here."
            )
            return False
        gap_row = next_row - 1
        if not (0 <= gap_row < len(self.rows) - 1):
            self.status_var.set(
                f"S{int(row_index)} has no editable gap upstream of the moved element."
            )
            return False

        delta = target_span - current_span
        try:
            current_gap = float(self.rows[gap_row].thickness)
        except Exception:
            return False
        new_gap = current_gap + delta
        if not np.isfinite(new_gap) or new_gap < 0.0:
            self.status_var.set(
                f"S{int(row_index)} value {target_span:.6g} mm would collapse the chain; ignored."
            )
            return False

        # Follow the moved surfaces in the stored override (absolute z's): the
        # downstream endpoint -- and only it -- shifts by delta so the arrow stays
        # attached and the displayed number equals what was typed.
        new_spec = dict(spec)
        if cur_ref >= fixed_z:
            new_spec["ref_z"] = float(cur_ref + delta)
        else:
            new_spec["fixed_z"] = float(fixed_z + delta)

        self._begin_history_capture()
        self.rows[gap_row].thickness = float(new_gap)
        overrides[int(row_index)] = new_spec
        self._dimension_anchor_overrides = overrides
        try:
            self._sync_table()
        except Exception:
            pass
        try:
            self._invalidate_preview_scene_trace()
        except Exception:
            pass
        try:
            self._sync_trace_state_badge()
        except Exception:
            pass
        self._commit_history_capture()
        self.status_var.set(
            f"S{int(row_index)} set to {target_span:.6g} mm: moved the downstream element "
            f"(gap S{gap_row}) {delta:+.4g} mm; other gaps unchanged."
        )
        return True

    def apply_measure_dimension_value(self, lo_z: float, hi_z: float, value: float) -> bool:
        """Edit a manual MEASURE dimension's value by MOVING the downstream element so the axial
        span between the two measured points becomes ``value`` -- the same directed-gap move as a
        re-anchored thickness dimension (``apply_reanchored_dimension_value``), but driven by the
        measure's two row-anchored endpoints instead of a stored override. The measure endpoints
        are anchored to their rows (``r0``/``r1`` + ``dz``), so they FOLLOW the moved surface on
        the next render -- no endpoint rewrite is needed here.

        Returns True when an element moved; False (model untouched + a status note) when the two
        points share a z-plane, the downstream point is not on a movable optical surface, there is
        no editable upstream gap, or the move would collapse the chain.
        """
        try:
            prev_z = float(min(lo_z, hi_z))
            next_z = float(max(lo_z, hi_z))
            target_span = abs(float(value))
        except Exception:
            return False
        if not (np.isfinite(prev_z) and np.isfinite(next_z) and np.isfinite(target_span)):
            return False
        current_span = next_z - prev_z
        if current_span <= 1e-9:
            self.status_var.set(
                "Measure value edit: the two points share a z-plane (no axial gap to move)."
            )
            return False
        z_positions = list(self._row_z_positions())
        if not z_positions:
            return False
        track = float(z_positions[-1] - z_positions[0]) if len(z_positions) > 1 else 0.0
        snap_tol = max(abs(track) * 0.02, 0.5)
        # Map the downstream point to the optical surface it sits on; that row is the element we
        # move (mirrors apply_reanchored_dimension_value's Next-element rule).
        next_row = None
        best = snap_tol
        for idx, z in enumerate(z_positions):
            d = abs(float(z) - next_z)
            if d <= best:
                best = d
                next_row = idx
        if next_row is None or next_row < 1:
            self.status_var.set(
                "Measure value edit: the downstream point is not on a movable optical surface."
            )
            return False
        gap_row = next_row - 1
        if not (0 <= gap_row < len(self.rows) - 1):
            self.status_var.set(
                "Measure value edit: no editable gap upstream of the moved element."
            )
            return False
        delta = target_span - current_span
        try:
            current_gap = float(self.rows[gap_row].thickness)
        except Exception:
            return False
        new_gap = current_gap + delta
        if not np.isfinite(new_gap) or new_gap < 0.0:
            self.status_var.set(
                f"Measure value {target_span:.6g} mm would collapse the chain; ignored."
            )
            return False
        self._begin_history_capture()
        self.rows[gap_row].thickness = float(new_gap)
        try:
            self._sync_table()
        except Exception:
            pass
        try:
            self._invalidate_preview_scene_trace()
        except Exception:
            pass
        try:
            self._sync_trace_state_badge()
        except Exception:
            pass
        self._commit_history_capture()
        self.status_var.set(
            f"Measure set to {target_span:.6g} mm: moved the downstream element "
            f"(gap S{gap_row}) {delta:+.4g} mm; other gaps unchanged."
        )
        return True

    def _move_led_for_reanchored_value(
        self, row_index: int, spec: dict, overrides: dict,
        fixed_z: float, cur_ref: float, target_span: float,
    ) -> bool:
        """Edit the object->LED re-anchored value by MOVING the LED body so the
        measured (re-anchored) face lands at ``target_span`` from the object plane
        (bugs/0054). The LED is the imaged object, not an optical surface, so it is
        repositioned via ``led_object_edge_distance_mm`` -- the same knob the LED
        edge-distance dialog drives -- which rigidly translates the whole STEP. No
        optical thickness changes. Returns False if the move would put the LED
        behind the object plane.
        """
        sign = 1.0 if cur_ref >= fixed_z else -1.0
        new_ref = fixed_z + sign * target_span
        delta_z = new_ref - cur_ref
        current_distance = max(float(getattr(self, "led_object_edge_distance_mm", 0.0)), 0.0)
        new_distance = current_distance + delta_z
        if not np.isfinite(new_distance) or new_distance < 0.0:
            self.status_var.set(
                f"S{int(row_index)} object->LED distance {target_span:.6g} mm would place "
                "the LED behind the object plane; ignored."
            )
            return False
        new_spec = dict(spec)
        new_spec["ref_z"] = float(new_ref)
        self._begin_history_capture()
        before_translation = self._led_step_z_translation()
        self.led_object_edge_distance_mm = float(new_distance)
        overrides[int(row_index)] = new_spec
        self._dimension_anchor_overrides = overrides
        self._carry_led_glue_over_translation_change(before_translation)  # bugs/0133
        self._commit_history_capture()
        try:
            self._refresh_open_3d_views(step_label="led")
        except Exception:
            pass
        self.status_var.set(
            f"S{int(row_index)} object->LED distance set to {target_span:.6g} mm: "
            f"moved the LED body {delta_z:+.4g} mm; optical thicknesses unchanged."
        )
        return True

    def clear_dimension_anchor_override(self, row_index: int) -> None:
        overrides = dict(getattr(self, "_dimension_anchor_overrides", {}) or {})
        if int(row_index) in overrides:
            self._begin_history_capture()
            overrides.pop(int(row_index), None)
            self._dimension_anchor_overrides = overrides
            self._commit_history_capture()
            self.status_var.set(f"S{int(row_index)} dimension re-anchor cleared.")
            self._refresh_open_3d_views()

    def _hidden_thickness_dimension_set(self) -> "set[int]":
        hidden = getattr(self, "_hidden_thickness_dimension_rows", None)
        if not isinstance(hidden, set):
            hidden = set()
            self._hidden_thickness_dimension_rows = hidden
        return hidden

    def _thickness_dimension_is_hidden(self, row_index: int) -> bool:
        try:
            return int(row_index) in self._hidden_thickness_dimension_set()
        except Exception:
            return False

    def set_thickness_dimension_hidden(self, row_index: int, hidden: bool) -> None:
        """Turn a single row's blue Thickness dimension overlay on/off. The model
        thickness is untouched -- this only suppresses the drawn arrow + label."""
        try:
            row_index = int(row_index)
        except Exception:
            return
        current = self._hidden_thickness_dimension_set()
        if (row_index in current) == bool(hidden):
            return
        self._begin_history_capture()
        if hidden:
            current.add(row_index)
        else:
            current.discard(row_index)
        self._hidden_thickness_dimension_rows = current
        self._commit_history_capture()
        self.status_var.set(
            f"S{row_index} Thickness dimension {'hidden' if hidden else 'shown'}."
        )
        self._refresh_open_3d_views()

    def toggle_thickness_dimension_hidden(self, row_index: int) -> None:
        self.set_thickness_dimension_hidden(
            row_index, not self._thickness_dimension_is_hidden(row_index)
        )

    def show_all_thickness_dimensions(self) -> None:
        current = self._hidden_thickness_dimension_set()
        if not current:
            self.status_var.set("All Thickness dimensions are already shown.")
            return
        self._begin_history_capture()
        current.clear()
        self._hidden_thickness_dimension_rows = current
        self._commit_history_capture()
        self.status_var.set("All Thickness dimensions shown.")
        self._refresh_open_3d_views()

    def _dimension_anchor_feature_label(self, feature_center_xyz) -> str:
        """Best-effort human label for a re-anchored measurement target."""
        try:
            feature = np.asarray(feature_center_xyz, dtype=float).reshape(-1)[:3]
        except Exception:
            return ""
        if feature.size < 3 or not np.all(np.isfinite(feature)):
            return ""
        return f"z={float(feature[2]):.4g}"

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

    def _step_overlay_mutation_signature(self, label: str) -> tuple:
        """World-pose + shape signature of an overlay: everything a placement
        setter can mutate that moves or reshapes the body in world space
        (rotation, axis offset, placement offset, resize, axis anchor).

        bugs/0143: a placement setter re-applied with an *identical* value -- a
        zero-delta drag-release (a click that registers as a drag), a glue carry
        that nets to zero, an orient onto a face already at that pose, or a
        refresh re-applying the saved pose -- still popped the face-metadata
        cache and cleared the trace plan, so the next hover cold-rebaked the
        ~0.2 s (led) / ~1.9 s (camera) planar-clustering face metadata for no
        actual change. Comparing this signature before and after the mutation
        lets the setter skip the invalidation when nothing moved, while a genuine
        change still invalidates (so the bugs/0050 / bugs/0010 ghost-highlight
        fixes stay intact).
        """
        label = str(label).strip().lower()
        try:
            pose = self._step_overlay_pose_cache_signature(label)
        except Exception:
            pose = ()
        try:
            resize = self._step_resize_signature(label)
        except Exception:
            resize = None
        try:
            anchors = getattr(self, "_step_overlay_axis_anchor_by_label", {}) or {}
            # repr() keeps the comparison robust whatever the anchor value type
            # is (dict / tuple); an absent anchor and a present one never collide.
            anchor_key = repr(anchors.get(label)) if label in anchors else None
        except Exception:
            anchor_key = None
        return (pose, resize, anchor_key)

    def _invalidate_step_overlay_after_mutation(self, label: str, before_signature: tuple) -> None:
        """Run the placement-setter side-effects (face-metadata cache
        invalidate, trace-plan clear, preview-trace invalidate) only when the
        overlay's world pose/shape actually changed since ``before_signature``
        was captured (bugs/0143). An unchanged re-apply keeps the cached
        metadata and trace, sparing the cold face-metadata re-bake."""
        if self._step_overlay_mutation_signature(label) == before_signature:
            return
        self._invalidate_step_overlay_face_metadata_cache(label)  # bugs/0050
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()

    def _set_step_axis_offset_xy(self, label: str, offset_xy: tuple[float, float]) -> None:
        if label not in _step_overlay_label_set():
            return
        before_signature = self._step_overlay_mutation_signature(label)
        setattr(self, f"{label}_step_axis_offset_xy", (float(offset_xy[0]), float(offset_xy[1])))
        self._invalidate_step_overlay_after_mutation(label, before_signature)  # bugs/0143

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
        before_signature = self._step_overlay_mutation_signature(label)
        setattr(self, f"{label}_step_placement_offset_xyz", (float(values[0]), float(values[1]), float(values[2])))
        self._clear_step_overlay_axis_anchor(label)
        self._invalidate_step_overlay_after_mutation(label, before_signature)  # bugs/0143

    def snap_detector_to_image_plane(self) -> bool:
        """Move the detector (the final ``Image`` row) onto the optics' paraxial best-focus image
        plane, removing the defocus gap. Returns True when it actually moved. The detector is the
        analysis/sensor surface; the image plane is computed from the optics (it moves when the
        optics change), so a non-zero gap is exactly the simulated defocus -- this is the user's
        right-click "Snap detector to image plane" (item 2)."""
        if len(self.rows) < 3 or str(getattr(self.rows[-1], "surface", "") or "") != "Image":
            self.status_var.set("Snap detector: the layout has no final Image row to move.")
            return False
        image_z = self._paraxial_image_plane_z()
        if image_z is not None:
            detector_z = sum(float(r.thickness) for r in self.rows[:-1])
            delta = float(image_z) - float(detector_z)
            source = "image plane"
        else:
            # The paraxial conjugate is unavailable for this layout (a 3D solid / beam-splitter
            # cube in the path that the centered-refractive paraxial solve can't model). Fall
            # back to the REAL-RAY on-axis best focus so the one-click snap still works.
            delta = self._real_ray_best_focus_shift_for_rows()
            if delta is None:
                self.status_var.set("Snap detector: best focus is not computable for this layout.")
                return False
            source = "best focus (ray-traced)"
        if abs(delta) <= 1e-6:
            self.status_var.set("Detector already at best focus (no defocus).")
            return False
        gui = not bool(getattr(self, "headless", False))   # history/table sync are GUI-only
        if gui:
            self._begin_history_capture()
        self.rows[-2].thickness = float(self.rows[-2].thickness) + delta  # last gap = image distance
        if gui:
            try:
                self._sync_table()
            except Exception:
                pass
            self._commit_history_capture()
        self._invalidate_preview_scene_trace()
        self.status_var.set(f"Snapped detector to {source} (moved {delta:+.4g} mm to best focus).")
        return True

    def glue_step_overlay_to_surrogate(self, label: str) -> bool:
        """Re-apply the automatic "glue to optical surrogate" placement for an
        imported STEP overlay by clearing its manual drag offsets, so it snaps
        back to its auto-aligned station: a **lens** re-centres on its CAD
        cylinder axis (bugs/0077) with its front datum on the surrogate; the
        **camera** sensor returns to the Image plane; the **LED** returns to its
        object-distance station.  Orientation (user rotations) and any resize are
        preserved -- this only undoes lateral/axial drags.  Returns True when it
        actually moved the overlay (so the caller can refresh)."""
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return False
        if self._step_path_for_label(label) is None:
            self.status_var.set(f"No {label} STEP is imported to glue to its surrogate.")
            return False
        display = self._step_overlay_display_label(label)
        axis_off = self._step_axis_offset_xy(label)
        place_off = self._step_placement_offset_xyz(label)
        already_glued = (
            abs(float(axis_off[0])) <= 1e-9
            and abs(float(axis_off[1])) <= 1e-9
            and all(abs(float(v)) <= 1e-9 for v in place_off)
        )
        if already_glued:
            self.status_var.set(f"{display} STEP is already glued to its optical surrogate.")
            return False
        self._begin_history_capture()
        self._set_step_axis_offset_xy(label, (0.0, 0.0))
        self._set_step_placement_offset_xyz(label, (0.0, 0.0, 0.0))
        self._selected_step_label = label
        self._commit_history_capture()
        self.status_var.set(
            f"Glued {display} STEP to its optical surrogate "
            "(centred on the optical axis, datum aligned)."
        )
        return True

    def improve_lens_surrogate_rear_to_step(self) -> bool:
        """Item 4 ("vendor CAD is truth; improve the surrogate to fit it"): move the lens
        surrogate's 'Lens Rear Datum' onto the imaging-lens STEP's rear face so the surrogate's
        physical span matches the CAD. The front datum already pins the STEP front; this glues the
        rear. The optics + image stay FIXED -- the gap BEFORE the rear datum grows by the shift and
        the rear datum's own gap (to the image) shrinks by the same amount. Returns True when it
        moved the datum."""
        if self._step_path_for_label("lens") is None:
            self.status_var.set("Improve surrogate: no lens STEP is imported.")
            return False
        rear_idx = next(
            (i for i, r in enumerate(self.rows) if str(getattr(r, "name", "") or "") == "Lens Rear Datum"),
            None,
        )
        if rear_idx is None or rear_idx < 1 or rear_idx >= len(self.rows) - 1:
            self.status_var.set("Improve surrogate: layout has no 'Lens Rear Datum' row to glue.")
            return False
        mesh = self._transformed_imported_lens_step_mesh()
        if mesh is None:
            self.status_var.set("Improve surrogate: the lens STEP mesh is not available.")
            return False
        try:
            bounds = np.asarray(mesh.bounds, dtype=float).reshape(-1)
            zmin, zmax = float(bounds[4]), float(bounds[5])
        except Exception:
            self.status_var.set("Improve surrogate: could not read the STEP extent.")
            return False
        front_datum_z = float(self._lens_front_datum_z())
        # the STEP rear face = the axial extreme farther from the (front-pinned) front datum
        step_rear_z = zmax if abs(zmax - front_datum_z) >= abs(zmin - front_datum_z) else zmin
        rear_datum_z = float(self._row_z_positions()[rear_idx])
        delta = step_rear_z - rear_datum_z
        if not np.isfinite(delta) or abs(delta) <= 1e-3:
            self.status_var.set("Surrogate rear datum already on the STEP rear face (no change).")
            return False
        if float(self.rows[rear_idx].thickness) - delta < 0.0:
            self.status_var.set("Improve surrogate: rear-datum shift would invert the image gap; skipped.")
            return False
        gui = not bool(getattr(self, "headless", False))
        if gui:
            self._begin_history_capture()
        self.rows[rear_idx - 1].thickness = float(self.rows[rear_idx - 1].thickness) + delta  # rear datum -> STEP rear
        self.rows[rear_idx].thickness = float(self.rows[rear_idx].thickness) - delta            # keep image + optics
        if gui:
            try:
                self._sync_table()
            except Exception:
                pass
            self._commit_history_capture()
        self._invalidate_preview_scene_trace()
        self.status_var.set(
            f"Improved surrogate: rear datum glued to the lens STEP rear face "
            f"(moved {delta:+.4g} mm; span now matches the CAD; optics + image unchanged)."
        )
        return True

    def optical_led_glued(self) -> bool:
        """Item 3: whether the optical (beam splitter) STEP and the LED STEP are glued (move as one)."""
        return bool(getattr(self, "_optical_led_glued", False))

    def set_optical_led_glue(self, glued: bool) -> bool:
        """Item 3: glue/unglue the beam-splitter (optical) STEP to the LED STEP so they move as one
        rigid unit -- a later drag of either carries the other by the same delta, preserving their
        current relative pose. Requires both STEPs imported. Returns True when the state changed."""
        glued = bool(glued)
        if glued and (not self._optical_bs_body_present() or self._step_path_for_label("led") is None):
            self.status_var.set("Glue BS to LED: import the LED and import or promote the beam splitter first.")
            return False
        if bool(getattr(self, "_optical_led_glued", False)) == glued:
            self.status_var.set("Beam splitter is already glued to the LED." if glued else "Beam splitter is not glued to the LED.")
            return False
        self._optical_led_glued = glued
        self._invalidate_preview_scene_trace()
        self.status_var.set(
            "Beam splitter glued to the LED -- they now move together." if glued
            else "Beam splitter unglued from the LED."
        )
        return True

    def _promoted_optical_solid_row_index(self, label: str = "optical") -> "int | None":
        """Row index of the promoted optical solid that came from STEP overlay ``label``
        (a beam splitter promoted from the "optical" overlay), or None.  Lets the BS<->LED
        glue (item 3) keep working after the BS overlay is promoted away (bugs/0127)."""
        label = str(label or "").strip().lower()
        for index, row in enumerate(getattr(self, "rows", None) or []):
            try:
                if str(self._open3d_step_label_for_optical_solid_row(row) or "").strip().lower() == label:
                    return index
            except Exception:
                continue
        return None

    def _optical_bs_body_present(self) -> bool:
        """True when a beam-splitter body exists as EITHER the 'optical' STEP overlay or a
        promoted optical solid, so BS<->LED glue is meaningful even post-promotion (0127)."""
        try:
            if self._step_path_for_label("optical") is not None:
                return True
        except Exception:
            pass
        return self._promoted_optical_solid_row_index("optical") is not None

    def _carry_glued_optical_led(self, moved_label: str, applied) -> None:
        """Item 3 carry: when the BS<->LED rigid glue is active, move the glued PARTNER of the
        just-moved body by the same world delta, preserving their relative pose.  The beam
        splitter may be EITHER the 'optical' overlay OR a promoted optical solid (bugs/0127);
        the LED is always an overlay.  Re-entrancy guarded so the partner move never carries
        back (the LED move sets only an overlay offset; the BS move calls the row primitive
        with the guard up, which skips its own carry hook)."""
        if getattr(self, "_optical_led_carry_active", False):
            return
        if not bool(getattr(self, "_optical_led_glued", False)):
            return
        moved = str(moved_label or "").strip().lower()
        if moved not in ("optical", "led"):
            return
        try:
            delta = np.asarray(applied, dtype=float).reshape(-1)[:3]
        except Exception:
            return
        if delta.size < 3 or not np.all(np.isfinite(delta)) or not np.any(np.abs(delta) > 1e-9):
            return
        partner = "led" if moved == "optical" else "optical"
        self._optical_led_carry_active = True
        try:
            try:
                partner_is_overlay = self._step_path_for_label(partner) is not None
            except Exception:
                partner_is_overlay = False
            if partner_is_overlay:
                cur = np.asarray(self._step_placement_offset_xyz(partner), dtype=float).reshape(-1)[:3]
                self._set_step_placement_offset_xyz(partner, tuple(float(v) for v in (cur + delta)))
                return
            if partner == "optical":
                row_index = self._promoted_optical_solid_row_index("optical")
                if row_index is not None:
                    self.translate_scene_row_pose_vector(
                        row_index, delta, record_history=False, sync_table=False
                    )
        finally:
            self._optical_led_carry_active = False

    def _carry_led_glue_over_translation_change(self, before_translation) -> None:
        """bugs/0133: carry the BS<->LED glue across an LED object-edge *distance* move.

        The drag primitives carry the glue by handing ``_carry_glued_optical_led`` a
        world delta, but the LED object-edge *distance* paths -- the edge-distance
        dialog (``set_led_edge_distance``), the object->LED dimension re-anchor value
        edit (``_move_led_for_reanchored_value``), and the legacy object-edge pick
        (``apply_led_object_edge_pick``) -- reposition the LED by REWRITING
        ``led_object_edge_distance_mm`` / ``led_step_object_edge_local_z`` and letting
        ``_led_step_z_translation()`` recompute.  They never issue a delta, so a glued
        beam splitter was left behind: it detached from the LED and the blue
        object->solid gap stopped tracking the LED (flag_20260624_130423_829).  Derive
        the LED's net world z-shift from the translation change and shove the glued
        partner by it.  A no-op when nothing is glued or the LED did not move (so the
        zero-shift re-anchor path stays inert)."""
        try:
            dz = float(self._led_step_z_translation()) - float(before_translation)
        except Exception:
            return
        if np.isfinite(dz) and abs(dz) > 1e-9:
            self._carry_glued_optical_led("led", (0.0, 0.0, dz))

    # --- imported-solid resize (drag a face to grow a dimension) ------------- #
    # The resize is stored as per-axis target extents in the solid's *native*
    # (base-mesh) frame and applied to the loaded mesh before optical-axis
    # alignment, so the coupling axes from open3d_solid_resize.detect_coupling
    # line up with the mesh.  A beam-splitter's 45-deg coating only stays at
    # 45 deg when the two coupled axes share one factor, so the setter forces
    # them equal when ``coupled`` is set (bugs/0064-style drag-to-resize).
    def _step_resize_for_label(self, label: str) -> dict | None:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return None
        return getattr(self, f"{label}_step_resize", None)

    def _step_overlay_resize_active(self, label: str) -> bool:
        """True when ``label``'s overlay carries a non-trivial resize target, i.e.
        :meth:`_apply_step_overlay_resize` actually scales the mesh into a frame
        that no longer matches the STEP-native cylinder-axis point (bugs/0077)."""
        spec = self._step_resize_for_label(label)
        if not spec:
            return False
        target = spec.get("target_extents")
        return bool(target) and not all(v is None for v in target)

    def _set_step_resize_for_label(
        self,
        label: str,
        target_extents,
        *,
        anchor_axis: int | None = None,
        anchor_at_max: bool = False,
        coupled: bool = False,
    ) -> None:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return
        before_signature = self._step_overlay_mutation_signature(label)
        if target_extents is None:
            setattr(self, f"{label}_step_resize", None)
        else:
            values = list(target_extents)[:3]
            cleaned = [
                float(v) if (v is not None and np.isfinite(float(v)) and float(v) > 0.0) else None
                for v in values
            ]
            while len(cleaned) < 3:
                cleaned.append(None)
            setattr(
                self,
                f"{label}_step_resize",
                {
                    "target_extents": tuple(cleaned),
                    "anchor_axis": int(anchor_axis) if anchor_axis is not None else None,
                    "anchor_at_max": bool(anchor_at_max),
                    "coupled": bool(coupled),
                },
            )
        self._invalidate_step_overlay_after_mutation(label, before_signature)  # bugs/0143

    def _step_resize_signature(self, label: str):
        spec = self._step_resize_for_label(label)
        if not spec:
            return None
        target = spec.get("target_extents")
        return (
            tuple(round(v, 6) if v else None for v in target) if target else None,
            spec.get("anchor_axis"),
            bool(spec.get("anchor_at_max")),
            bool(spec.get("coupled")),
        )

    def _step_overlay_resize_axes(self, label: str):
        """Cached coupling axes (free + coupled pair) for a label, or ``None``.

        Reads the original B-rep's analytic planes once per (label, path); a
        plain element with no 45-deg coating yields ``None`` -> free resize.
        """
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return None
        path = self._step_path_for_label(label)
        if path is None:
            return None
        cache = self.__dict__.setdefault("_step_overlay_resize_axes_cache", {})
        key = (label, str(path))
        if key in cache:
            return cache[key]
        axes = None
        try:
            axes = solid_resize.detect_coupling(_read_step_shape(Path(path)))
        except Exception as exc:
            self.append_debug(f"{label.upper()} STEP resize-axis detection failed: {exc}")
        cache[key] = axes
        return axes

    def _step_overlay_original_extents(self, label: str):
        """Original (un-resized) base-frame extents (mm), for popup prefill."""
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return None
        path = self._step_path_for_label(label)
        if path is None:
            return None
        cache = self.__dict__.setdefault("_step_overlay_original_extents_cache", {})
        key = (label, str(path))
        if key in cache:
            return cache[key]
        extents = None
        try:
            from OCC.Core.Bnd import Bnd_Box
            from OCC.Core.BRepBndLib import brepbndlib

            shape = _read_step_shape(Path(path))
            box = Bnd_Box()
            brepbndlib.Add(shape, box)
            xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
            extents = np.array([xmax - xmin, ymax - ymin, zmax - zmin], dtype=float)
        except Exception as exc:
            self.append_debug(f"{label.upper()} STEP original-extents read failed: {exc}")
        cache[key] = extents
        return extents

    def _apply_step_overlay_resize(self, mesh, label: str):
        """Scale a freshly loaded base mesh per the stored resize spec.

        Runs in the native frame (before optical-axis alignment).  Returns the
        original mesh untouched when there is no resize, so the overlay path is
        a no-op for un-resized solids.
        """
        spec = self._step_resize_for_label(label)
        if not spec or mesh is None:
            return mesh
        target = spec.get("target_extents")
        if not target or all(v is None for v in target):
            return mesh
        try:
            points = np.asarray(getattr(mesh, "points", None), dtype=float)
        except Exception:
            return mesh
        if points.ndim != 2 or points.shape[0] == 0 or points.shape[1] < 3:
            return mesh
        if not np.all(np.isfinite(points[:, :3])):
            return mesh
        current = solid_resize.extents_of(points)
        wanted = np.array([target[i] if (i < len(target) and target[i]) else 0.0 for i in range(3)], dtype=float)
        scales = solid_resize.axis_scales_for_extents(current, wanted)
        if np.allclose(scales, 1.0):
            return mesh
        lo = np.min(points[:, :3], axis=0)
        hi = np.max(points[:, :3], axis=0)
        anchor_axis = spec.get("anchor_axis")
        if anchor_axis is None:
            anchor = 0.5 * (lo + hi)
        else:
            anchor = solid_resize.anchor_point_for_fixed_face(
                lo, hi, int(anchor_axis), bool(spec.get("anchor_at_max"))
            )
        try:
            resized = mesh.copy(deep=True)
            resized.points = solid_resize.resize_points(points, scales, anchor)
            return resized
        except Exception as exc:
            self.append_debug(f"{label.upper()} STEP resize apply failed: {exc}")
            return mesh

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
        # The axial<->optical-distance glue below (camera->detector, lens->object gap) ONLY applies
        # while the overlay sits in its GLUED, ON-AXIS pose. A body the user dropped OFF the rays
        # (e.g. a beam splitter placed beside the axis) is a free placement -- its axial drag must
        # just move the BODY, never drive the optical distance / ray path (flag_20260621_142758: an
        # off-axis BS sitting in the lens slot was adjusting the gap + rays when dragged).
        _cur_axis_off = np.asarray(self._step_axis_offset_xy(label), dtype=float).reshape(-1)
        _cur_place_off = np.asarray(self._step_placement_offset_xyz(label), dtype=float).reshape(-1)
        overlay_on_axis = (
            _cur_axis_off.size >= 2
            and _cur_place_off.size >= 2
            and abs(float(_cur_axis_off[0])) <= 1e-3
            and abs(float(_cur_axis_off[1])) <= 1e-3
            and abs(float(_cur_place_off[0])) <= 1e-3
            and abs(float(_cur_place_off[1])) <= 1e-3
        )
        # CAMERA <-> DETECTOR GLUE (item 1): the camera sensor is glued to the Image-row detector.
        # An AXIAL (+Z optical-axis) camera drag moves the DETECTOR -- the Image row, which is the
        # actual trace/analysis surface -- so the detector FOLLOWS the camera and the rays propagate
        # to it. Lateral drag still only centres the camera body. Single-axis (the on-axis Image row).
        axial_to_detector = 0.0
        if (
            label == "camera"
            and overlay_on_axis
            and len(self.rows) >= 3
            and str(getattr(self.rows[-1], "surface", "") or "") == "Image"
            and abs(float(getattr(self.rows[-1], "desp_y", 0.0) or 0.0)) <= 1e-6
            and abs(float(getattr(self.rows[-1], "desp_z", 0.0) or 0.0)) <= 1e-6
            and abs(float(delta[2])) > 1e-9
        ):
            axial_to_detector = float(delta[2])
        # LENS surrogate <-> STEP glue (item 4): an AXIAL lens drag slides the whole lens UNIT along
        # the optical axis. The 'Lens Front Datum' (which pins the STEP front), every lens row and the
        # glued rear datum move together by redirecting the +Z drag to the gap BEFORE the front datum
        # (the object-to-lens distance); the STEP follows and the rear datum stays glued (the optics
        # respond to the new lens position). Lateral drag still only centres the body.
        axial_lens_slide = 0.0
        lens_front_idx = None
        if label == "lens" and overlay_on_axis and abs(float(delta[2])) > 1e-9:
            lens_front_idx = next(
                (
                    i for i, r in enumerate(self.rows)
                    if "front" in str(getattr(r, "name", "") or "").lower()
                    and ("datum" in str(getattr(r, "name", "") or "").lower()
                         or "edge" in str(getattr(r, "name", "") or "").lower())
                ),
                None,
            )
            if lens_front_idx is not None and lens_front_idx >= 1:
                axial_lens_slide = float(delta[2])
            else:
                lens_front_idx = None
        redirect_axial = abs(axial_to_detector) > 1e-9 or abs(axial_lens_slide) > 1e-9
        applied = np.array(
            [float(delta[0]), float(delta[1]), 0.0 if redirect_axial else float(delta[2])],
            dtype=float,
        )
        current = np.asarray(self._step_placement_offset_xyz(label), dtype=float)
        next_offset = current + applied
        if record_history:
            self._begin_history_capture()
        if abs(axial_to_detector) > 1e-9:
            self.rows[-2].thickness = float(self.rows[-2].thickness) + axial_to_detector  # move the detector
            if not bool(getattr(self, "headless", False)):
                try:
                    self._sync_table()
                except Exception:
                    pass
            self._invalidate_preview_scene_trace()
        if abs(axial_lens_slide) > 1e-9 and lens_front_idx is not None:
            self.rows[lens_front_idx - 1].thickness = float(self.rows[lens_front_idx - 1].thickness) + axial_lens_slide
            if not bool(getattr(self, "headless", False)):
                try:
                    self._sync_table()
                except Exception:
                    pass
            self._invalidate_preview_scene_trace()
        self._set_step_placement_offset_xyz(label, next_offset)
        # Item 3: BS<->LED two-body glue -- the optical (beam splitter) + led overlays move as ONE
        # rigid unit. The partner may be a STEP overlay OR a promoted solid row (after the BS is
        # promoted), so _carry_glued_optical_led handles both and guards against carry-back.
        self._carry_glued_optical_led(label, applied)
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
        inpath_axial_placement: bool = False,
    ) -> dict[str, object] | None:
        # bugs/0082: the direct "Promote and set <face function>" right-click
        # (open3d_face_assignment) forwards inpath_axial_placement here, matching
        # the "Promote to Optical Element" path. This wrapper must accept and
        # thread it to the service method (which already gates it behind the
        # _INPATH_AXIAL_PLACEMENT_ENABLED kill switch); without the parameter the
        # gesture raised TypeError and silently never promoted.
        return self._step_overlay_promotion_service().promote_imported_step_to_optical_solid_row(
            label,
            insert_at=insert_at,
            open_face_editor=open_face_editor,
            clear_overlay=clear_overlay,
            refresh_open_3d=refresh_open_3d,
            inpath_axial_placement=inpath_axial_placement,
        )

    def unpromote_optical_solid_to_overlay(
        self, row_index: int, *, refresh_open_3d: bool = True
    ) -> dict[str, object] | None:
        # bugs/0093: the right-click "Unpromote to STEP overlay" invokes this on the
        # editor. Like promote_... above, it MUST have an explicit wrapper that
        # delegates to the service -- otherwise the call falls through tkinter's
        # __getattr__ and AttributeErrors, so the right-click silently no-ops
        # ("unpromote not functioning", recording flag_20260618_172636).
        return self._step_overlay_promotion_service().unpromote_optical_solid_to_overlay(
            int(row_index), refresh_open_3d=refresh_open_3d
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
        flip_optical_axis: bool = False,
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
            flip_optical_axis=flip_optical_axis,
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
        before_signature = self._step_overlay_mutation_signature(label)
        x_deg, y_deg, z_deg = (float(value) % 360.0 for value in angles)
        setattr(self, f"{label}_step_rotation_x_deg", x_deg)
        setattr(self, f"{label}_step_rotation_y_deg", y_deg)
        setattr(self, f"{label}_step_rotation_z_deg", z_deg)
        self._clear_step_overlay_axis_anchor(label)
        self._invalidate_step_overlay_after_mutation(label, before_signature)  # bugs/0143

    def _global_optical_axis_frame_near_point(self, reference_point) -> dict[str, object]:
        """Frame on the GLOBAL dotted optical-axis guide (the design axis at
        x=0, y=0) nearest the reference -- i.e. the projection (0, 0, z).

        bugs/0120: the translate-only "Center Picked Face -> Optical Axis" must
        target the GLOBAL axis, not the nearest *traced ray*. The nearest-ray
        helper (``_step_optical_axis_frame_near_point``) reads the cached scene
        bundle's ray paths even when rays are hidden, so for an off-axis body it
        returned an outer marginal-ray point a few mm off (0, 0) -- the face slid
        onto a ray, not onto the axis, and read as "still offset from the axis".
        The global guide is always the x=0/y=0 line (see
        ``_optical_axis_records_for_3d``), so the on-axis target is (0, 0, z)."""
        reference = np.asarray(reference_point, dtype=float).reshape(-1)[:3]
        if reference.size < 3 or not np.all(np.isfinite(reference[:3])):
            raise RuntimeError("STEP face reference point is not finite.")
        return {
            "target_point": np.asarray((0.0, 0.0, float(reference[2])), dtype=float),
            "direction": np.asarray((0.0, 0.0, 1.0), dtype=float),
            "axis_label": "global optical axis",
            "ray_index": -1,
            "branch_path": "",
        }

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
                # triangle_indices already index the display-transformed
                # `triangles`, so derive the cap centroid/normal from those
                # (area-weighted, exactly like the non-grouped faces) rather
                # than affine-transforming the source-frame analytic centroid:
                # that fit goes degenerate whenever the source and display
                # triangle counts differ (affine None) and silently froze the
                # cap at the body's pre-move pose, stranding the round-lens
                # hover outline at the old location (bug 0010).
                selected = np.asarray(triangles[np.asarray(indices, dtype=int)], dtype=float)
                cap_record = self._analytic_step_face_record_from_triangles(
                    document.outer_faces[0],
                    indices,
                    selected,
                )
                center = np.asarray(cap_record.get("centroid", ()), dtype=float).reshape(-1)[:3]
                normal = np.asarray(cap_record.get("normal", ()), dtype=float).reshape(-1)[:3]
                if center.size < 3 or not np.all(np.isfinite(center[:3])):
                    center = np.mean(selected.reshape((-1, 3)), axis=0)
                normal_norm = float(np.linalg.norm(normal[:3])) if normal.size >= 3 else 0.0
                if normal.size < 3 or normal_norm <= 1.0e-12 or not np.isfinite(normal_norm):
                    normal = np.asarray(record.get("normal", (0.0, 0.0, 1.0)), dtype=float).reshape(-1)[:3]
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

    # STEP overlay labels whose analytic-face metadata is dropped
    # because the geometry is display-only. None of these slots is
    # eligible for promotion to analytic Standard rows -- only the
    # ``optical`` label is promotable, via the explicit "Promote STEP to
    # Analytic Surfaces" action (import itself stays carry-first). So the
    # per-face analytic
    # descriptors from pythonocc-core have no consumer here: the
    # planar-clustering fallback below produces metadata that's good
    # enough for placement preview, snap, and pick UX without any OCC
    # work at all.
    #
    # The motivating freeze was a 51 MB camera body taking 35 s on the
    # first call. A large vendor imaging-lens housing in the ``lens``
    # slot has the same shape -- big vendor CAD, no optical role, no
    # consumer of analytic faces -- so it gets the same treatment to
    # avoid the next bug report.
    _DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC: frozenset[str] = frozenset({"camera", "led", "lens"})

    def _step_overlay_pose_cache_signature(self, label: str) -> tuple:
        """Transform inputs that move an imported overlay body in world space.

        These mirror the signature the overlay mesh builder keys on
        (``_transformed_imported_optical_step_mesh``): rotation, axis offset,
        and placement offset. The analytic face metadata bakes world-space
        ``centroid_world``/``normal_world`` from the transformed mesh, so its
        cache must invalidate on exactly these inputs or the hover outline is
        drawn at the body's former pose (bug 0010).
        """
        label = str(label).strip().lower()
        try:
            return (
                round(float(getattr(self, f"{label}_step_rotation_z_deg", 0.0)), 6),
                round(float(getattr(self, f"{label}_step_rotation_x_deg", 0.0)), 6),
                round(float(getattr(self, f"{label}_step_rotation_y_deg", 0.0)), 6),
                tuple(round(float(v), 6) for v in self._step_axis_offset_xy(label)),
                tuple(round(float(v), 6) for v in self._step_placement_offset_xyz(label)),
            )
        except Exception:
            return ()

    def _step_overlay_alignment_target_z(self, label: str):
        """Image-plane-driven axial alignment target for a display-only overlay.

        camera/led bodies are NOT moved by a translate/rotate gesture but by the
        layout's image plane: ``_transformed_imported_camera_step_mesh`` aligns
        the camera front to ``image_plane_z - front_to_sensor`` (the led to its
        own z). The rendered mesh re-keys on this target, but the pose-blind face
        metadata key did not -- so after the image plane moved (a solve,
        image-at-focus shift, thickness edit, or camera/sensor reassignment) the
        baked face geometry stayed at the body's former pose and the gold hover
        outline floated ~17 mm off the drawn body (bugs/0109). Returns ``None``
        for overlays whose pose is fully captured by the translate/rotate
        signature (the alignment target is then irrelevant to the cache key).
        """
        label = str(label).strip().lower()
        try:
            if label == "camera":
                return round(
                    float(self._camera_track_image_plane_z() - self._current_camera_front_to_sensor_mm()),  # bugs/0220
                    6,
                )
            if label == "led":
                return round(float(self._led_step_z_translation()), 6)
        except Exception:
            return None
        return None

    def _step_overlay_face_metadata(self, label: str) -> dict[str, object]:
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set() or self._step_path_for_label(label) is None:
            return normalize_optical_solid_face_metadata({})
        # Memoise on (label, source-path stat key[, pose signature]). The
        # expensive analytic-face metadata pipeline below iterates every outer
        # face, applies an affine fit, normalises records, and writes a snap
        # STL -- none of which depends on mouse position, so the per-mouse-move
        # hover path must not pay it (a 51 MB display-only camera body took
        # 35 s on the first call).
        #
        # But each record carries world-space ``centroid_world``/``normal_world``
        # baked from the *currently transformed* mesh. A pose change (Center
        # Row -> Optical Axis, a normal-axis snap, a STEP translate) moves the
        # body, and a stat-key-only cache would keep handing back old-pose world
        # coords -- so the hover outline got redrawn at the body's former
        # location (bug 0010, the "ghost" edge highlights). The analytic
        # ``optical`` recompute is ~22 ms, so analytic labels add a pose
        # signature to the key; the slow display-only labels keep the stat-only
        # key to avoid reintroducing the 35 s freeze.
        cache = self.__dict__.setdefault("_step_overlay_face_metadata_cache", {})
        source_path_obj = self._step_path_for_label(label)
        try:
            cache_key = (label, self._step_overlay_stat_key(source_path_obj))
            if label not in self._DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC:
                cache_key = cache_key + (self._step_overlay_pose_cache_signature(label),)
            # bugs/0111 (reverts bugs/0109): the display-only camera/led labels keep
            # the POSE-BLIND key, so the metadata is baked at most once per session.
            # bugs/0109 folded the image-plane alignment target into the key on the
            # mistaken belief that the recompute was "subsecond" -- but this is the
            # full planar-clustering + affine-fit + snap-STL pipeline, ~18-35 s for
            # the 228k-cell camera body (see the timing log + the comment above).
            # Re-keying on the alignment made that bake re-run whenever the image
            # plane moved OR on a deselect/refresh, freezing the UI for ~18 s. The
            # cosmetic hover-outline offset 0109 chased is tracked separately and
            # must be fixed without re-baking (apply the axial delta on read).
        except Exception:
            cache_key = None
        if cache_key is not None:
            cached = cache.get(cache_key)
            if isinstance(cached, dict):
                return cached
        from KrakenOS.UI.services.open3d_timing import open3d_timing_span as _span

        with _span("step_overlay_face_metadata", label=label):
            metadata = self._step_overlay_face_metadata_compute(label)
        if isinstance(metadata, dict) and label in self._DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC:
            # bugs/0113: the display-only camera/led metadata is pose-blind (baked
            # once per session to dodge the 18-35 s freeze), but the rendered body
            # is re-aligned to the live image plane every refresh. Stamp the
            # alignment target at bake time so the hover path can shift the cached
            # outline by the live axial delta (apply-on-read), instead of redrawing
            # it at the body's former z (the "ghost highlight").
            metadata["alignment_target_z_at_bake"] = self._step_overlay_alignment_target_z(label)
        if cache_key is not None and isinstance(metadata, dict):
            cache[cache_key] = metadata
        return metadata

    def _invalidate_step_overlay_face_metadata_cache(self, label: str) -> None:
        """Drop cached face metadata for ``label`` after its pose changes.

        The metadata bakes world-space face geometry (centroids, normals, the
        hover-outline meshes). For display-only labels (camera/led/lens) the
        cache key is *pose-blind* -- the per-pose recompute is skipped to dodge
        the cold-load freeze -- so a translate/rotate would otherwise keep
        handing back the body's *former* world coords and the face hover outline
        gets redrawn at the old, now-empty location (bug 0050; bug 0010
        resurfacing for the display-only solids the 0010 fix left pose-blind).

        Dropping the entry is safe and freeze-free: the metadata recompute is
        lazy (only the next hover/pick pays it, never the scene refresh), and the
        move's own refresh already rebuilt the transformed mesh, so the recompute
        is just the planar-clustering pass, not a CAD reload.
        """
        label = str(label).strip().lower()
        cache = self.__dict__.get("_step_overlay_face_metadata_cache")
        if not isinstance(cache, dict) or not cache:
            return
        for key in [k for k in cache if isinstance(k, tuple) and k and k[0] == label]:
            cache.pop(key, None)

    def _step_overlay_face_metadata_compute(self, label: str) -> dict[str, object]:
        if label not in self._DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC:
            try:
                analytic_metadata = self._step_overlay_analytic_face_metadata(label)
                if analytic_metadata is not None:
                    return analytic_metadata
            except Exception as exc:
                self.append_debug(f"Analytic STEP face metadata fell back to planar clustering for {label}: {_short_error_message(exc)}")
        mesh = self._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return normalize_optical_solid_face_metadata({})
        # Strip every cell-data array before extract_surface /
        # triangulate. Several layers add per-cell arrays sized to the
        # original tessellation:
        #
        #   - analytic-promote path attaches ``kraken_step_*`` face IDs;
        #   - VTK's connectivity filter (run by
        #     largest_connected_step_component) attaches ``RegionId``
        #     and ``vtkOriginalCellIds``.
        #
        # extract_surface() + triangulate() then changes the cell count
        # -- a quad becomes two triangles, a connectivity pass can drop
        # interior cells -- and the arrays go stale, tripping
        # PyVista's InvalidMeshWarning on every refresh and again on
        # mesh.save(). The planar-clustering branch only reads
        # ``mesh.points`` and the surface topology, so dropping every
        # cell array up front is safe and silences the warning chorus
        # without enumerating each new VTK-generated key by name.
        try:
            cell_data = getattr(mesh, "cell_data", None)
            if cell_data is not None:
                try:
                    cell_data.clear()
                except Exception:
                    for stale_key in list(cell_data.keys()):
                        try:
                            del cell_data[stale_key]
                        except Exception:
                            pass
        except Exception:
            pass
        # ``extract_surface`` itself appends ``vtkOriginalCellIds`` and
        # ``triangulate`` then changes the cell count, so the array
        # immediately becomes stale and the next ``copy`` / ``save``
        # call triggers PyVista's InvalidMeshWarning chorus. We strip
        # after each step so neither intermediate carries a misaligned
        # array forward.
        def _strip_cell_data(m):
            try:
                cd = getattr(m, "cell_data", None)
                if cd is not None:
                    try:
                        cd.clear()
                    except Exception:
                        for stale_key in list(cd.keys()):
                            try:
                                del cd[stale_key]
                            except Exception:
                                pass
            except Exception:
                pass
            return m
        try:
            surface = _strip_cell_data(mesh.extract_surface(algorithm="dataset_surface"))
            mesh = _strip_cell_data(surface.triangulate()).copy(deep=True)
        except Exception:
            try:
                mesh = _strip_cell_data(mesh.extract_surface(algorithm="dataset_surface")).copy(deep=True)
            except Exception:
                mesh = mesh.copy(deep=True)
        mesh = _strip_cell_data(mesh)
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

    def center_step_feature_on_optical_axis(
        self,
        label: str,
        feature_center_xyz,
        *,
        axis_frame: dict[str, object] | None = None,
        face_id: str = "",
    ) -> dict[str, object] | None:
        """Translate a STEP overlay so the picked face centre lands on the nearest
        optical axis -- a TRANSLATE-ONLY centre, the one-click sibling of
        ``snap_step_feature_normal_to_optical_axis``.

        bugs/0119: the right-click face menu used to offer only the normal snap,
        which *rotates* the body to make the face perpendicular to the axis. A user
        who wanted to "center this window on the axis" got an unwanted tilt instead.
        This moves the face centre onto the axis line and keeps the orientation.

        bugs/0120: the target is the GLOBAL optical axis (x=0, y=0, keep z), NOT
        the nearest traced ray -- ``_step_optical_axis_frame_near_point`` reads the
        cached ray bundle (alive even with rays hidden), so for an off-axis body it
        landed the face on an outer marginal ray a few mm off the axis. Caller
        passes the face *centroid* (not the raw click point) so the window's centre
        -- not wherever the cursor landed -- is what comes to rest on the axis."""
        label = str(label).strip().lower()
        if label not in _step_overlay_label_set():
            return None
        if self._step_path_for_label(label) is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return None
        feature_center = np.asarray(feature_center_xyz, dtype=float).reshape(-1)[:3]
        if feature_center.size < 3 or not np.all(np.isfinite(feature_center[:3])):
            self.status_var.set("Center Picked Face->Optical Axis needs a finite picked STEP face center.")
            return None
        frame = dict(axis_frame) if isinstance(axis_frame, dict) else self._global_optical_axis_frame_near_point(feature_center[:3])
        target_point = np.asarray(frame["target_point"], dtype=float).reshape(-1)[:3]
        if target_point.size < 3 or not np.all(np.isfinite(target_point[:3])):
            self.status_var.set("Center Picked Face->Optical Axis: invalid axis target point.")
            return None
        current_offset = np.asarray(self._step_placement_offset_xyz(label), dtype=float).reshape(3)
        placement_delta = target_point[:3] - feature_center[:3]
        next_offset = current_offset[:3] + placement_delta[:3]

        self._begin_history_capture()
        self._set_step_placement_offset_xyz(label, next_offset)
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label = label
        self._commit_history_capture()
        axis_label = str(frame.get("axis_label", "optical axis"))
        self.status_var.set(
            f"{label.upper()} STEP face center moved onto {axis_label} at "
            f"({target_point[0]:.6g}, {target_point[1]:.6g}, {target_point[2]:.6g}) mm (no rotation)."
        )
        self._record_step_overlay_axis_anchor(
            label,
            face_id=str(face_id or "").strip(),
            target_point=target_point[:3],
            anchor_mode="surface_center",
            axis_frame=frame,
            source="feature_center_axis_center",
        )
        self._refresh_open_3d_views(step_label=label)
        return {
            "label": label,
            "axis_label": axis_label,
            "target_point": tuple(float(value) for value in target_point[:3]),
            "placement_offset_xyz": tuple(float(value) for value in next_offset[:3]),
            "ray_index": int(frame.get("ray_index", -1)),
            "branch_path": str(frame.get("branch_path", "") or ""),
        }

    # ---- LED clear-aperture (CA) fine-face selection + persistence (bugs/0134) ----
    # The user selects the square rounded-corner CLEAR-APERTURE window on the front
    # of the LED's vendor STEP and persists it as the component's clear aperture: a
    # single analytic *selection* face index, recomputed live so the highlight +
    # axis-centring track every move/resize. This is distinct from the coarse
    # right-click face pick (which clusters planar facets and could not reliably grab
    # the CA -- the regression the user flagged): the CA pick resolves the precise
    # per-cell ``kraken_step_selection_face_index`` straight off the displayed cell.

    def _clear_aperture_store(self) -> dict:
        store = self.__dict__.get("_step_clear_aperture_by_label")
        if not isinstance(store, dict):
            store = {}
            self._step_clear_aperture_by_label = store
        return store

    def step_clear_aperture(self, label: str) -> dict[str, object] | None:
        """Return the persisted clear-aperture record for a STEP overlay, or None."""
        record = self._clear_aperture_store().get(str(label or "").strip().lower())
        return dict(record) if isinstance(record, dict) else None

    def _step_overlay_fine_face_centroid_normal(self, label: str, face_index):
        """World-frame (area-weighted centroid, unit normal, area_mm2) of one
        analytic selection face on the *transformed* STEP overlay, or None.

        The transformed mesh already carries the placement offset baked into its
        points, so the centroid is true world -- exactly what
        ``center_step_feature_on_optical_axis`` expects."""
        label = str(label or "").strip().lower()
        try:
            mesh = self._transformed_imported_step_mesh_for_label(label)
        except Exception:
            mesh = None
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return None
        try:
            target = int(face_index)
        except Exception:
            return None
        if target < 0:
            return None
        try:
            triangles, face_idx = triangle_array_and_face_index(mesh)
        except Exception:
            return None
        if (
            triangles.ndim != 3
            or triangles.shape[1:] != (3, 3)
            or face_idx.shape[0] != triangles.shape[0]
            or triangles.shape[0] == 0
        ):
            return None
        selected = triangles[np.asarray(face_idx, dtype=int) == target]
        if selected.shape[0] == 0:
            return None
        v0, v1, v2 = selected[:, 0], selected[:, 1], selected[:, 2]
        cross = np.cross(v1 - v0, v2 - v0)
        areas = 0.5 * np.linalg.norm(cross, axis=1)
        total = float(areas.sum())
        if not np.isfinite(total) or total <= 0.0:
            return None
        tri_centroids = selected.mean(axis=1)
        centroid = (tri_centroids * areas[:, None]).sum(axis=0) / total
        normal_vector = cross.sum(axis=0)
        normal_length = float(np.linalg.norm(normal_vector))
        normal = (
            normal_vector / normal_length
            if normal_length > 1.0e-12
            else np.asarray([0.0, 0.0, 1.0], dtype=float)
        )
        if not np.all(np.isfinite(centroid)):
            return None
        return np.asarray(centroid, dtype=float), np.asarray(normal, dtype=float), total

    def clear_aperture_face_index_for_display_cell(self, label: str, cell_id: int):
        """Resolve a VTK-picked displayed cell to its analytic selection face index.

        Picker cell ids are in the FULL cell space (stray ``VTK_LINE`` cells, then
        polygons), and ``face_index_for_display_cell`` reads the picker-aligned
        per-cell data -- so this returns the *fine* CA face under the cursor, not a
        coarse planar cluster."""
        label = str(label or "").strip().lower()
        try:
            mesh = self._transformed_imported_step_mesh_for_label(label)
        except Exception:
            mesh = None
        if mesh is None:
            return None
        return face_index_for_display_cell(mesh, int(cell_id))

    def set_step_clear_aperture(self, label: str, face_index) -> dict[str, object] | None:
        """Persist a STEP overlay's clear aperture as a single analytic face index."""
        label = str(label or "").strip().lower()
        if not label:
            return None
        try:
            fid = int(face_index)
        except Exception:
            return None
        if fid < 0:
            return None
        record: dict[str, object] = {"face_index": fid}
        resolved = self._step_overlay_fine_face_centroid_normal(label, fid)
        if resolved is not None:
            _centroid, _normal, area = resolved
            record["area_mm2"] = float(area)
        self._clear_aperture_store()[label] = dict(record)
        try:
            self._mark_plot_update_pending()
        except Exception:
            pass
        return dict(record)

    def auto_detect_step_clear_aperture_candidates(self, label: str):
        """Rank a STEP overlay's clear-aperture opening candidates (best first).

        Reads the overlay's analytic B-rep faces, scores the rim-around-a-hole
        opening signature (bugs/0319 C2), and keeps only candidates whose analytic
        enumeration index still resolves *cleanly* on the displayed selection mesh --
        so the returned ``face_index`` is exactly what ``set_step_clear_aperture``
        consumes.  Returns ``[]`` when nothing qualifies, so the caller can fall back
        to the manual ``STEP_CLEAR_APERTURE_PICK``."""
        label = str(label or "").strip().lower()
        if not label:
            return []
        source_path = self._step_path_for_label(label)
        if source_path is None or Path(source_path).suffix.lower() not in {".step", ".stp"}:
            return []
        try:
            document = self._load_step_analytic_document(Path(source_path))
        except Exception:
            return []
        outer_faces = getattr(document, "outer_faces", None)
        if not outer_faces:
            return []
        try:
            candidates = detect_clear_aperture_openings_from_analytic_faces(outer_faces)
        except Exception:
            return []
        verified = []
        for cand in candidates:
            ref_area = float(getattr(cand, "area_mm2", 0.0) or 0.0)
            if ref_area <= 0.0:
                continue
            resolved = self._step_overlay_fine_face_centroid_normal(label, cand.face_index)
            if resolved is None:
                continue
            _centroid, _normal, area = resolved
            # Guard: the analytic enumeration index must resolve the SAME face on the
            # displayed selection mesh. A square/rectangular opening is never grouped
            # (its enumeration index == selection index), but if some other candidate
            # got axisymmetric-collapsed the selection index would grab a larger
            # cluster and the area blows up -- drop those and let manual pick cover it.
            if abs(float(area) - ref_area) > 0.15 * ref_area:
                continue
            verified.append(cand)
        return verified

    def auto_set_step_clear_aperture(self, label: str) -> dict[str, object] | None:
        """Auto-detect and persist a STEP overlay's clear aperture (best candidate).

        Returns the persisted record, or ``None`` when nothing qualifies so the caller
        keeps the manual ``STEP_CLEAR_APERTURE_PICK`` as the dependable fallback."""
        candidates = self.auto_detect_step_clear_aperture_candidates(label)
        if not candidates:
            return None
        return self.set_step_clear_aperture(label, int(candidates[0].face_index))

    def clear_step_clear_aperture(self, label: str) -> dict[str, object] | None:
        """Forget a STEP overlay's persisted clear aperture."""
        removed = self._clear_aperture_store().pop(str(label or "").strip().lower(), None)
        if removed is not None:
            try:
                self._mark_plot_update_pending()
            except Exception:
                pass
        return removed

    def center_clear_aperture_on_optical_axis(self, label: str) -> dict[str, object] | None:
        """Translate a STEP overlay so its persisted clear-aperture centre lands on
        the optical axis (reuses the proven translate-only feature centre)."""
        label = str(label or "").strip().lower()
        record = self.step_clear_aperture(label)
        if record is None:
            self.status_var.set(f"No clear aperture is set for the {label.upper()} STEP.")
            return None
        resolved = self._step_overlay_fine_face_centroid_normal(label, record.get("face_index"))
        if resolved is None:
            self.status_var.set("Clear aperture face could not be resolved on the current body.")
            return None
        centroid_world, _normal, _area = resolved
        return self.center_step_feature_on_optical_axis(
            label,
            centroid_world,
            face_id=f"clear_aperture:{int(record.get('face_index', -1))}",
        )

    # ---- One-click "Add Beam Splitter to LED" orchestration (bugs/0319 C3) ------

    def _step_analytic_face_inplane_span(self, label: str, face_index) -> "float | None":
        """The smaller in-plane span (mm) of one analytic outer face's bbox, or None.
        Used to size a beam splitter to the LED clear-aperture opening it centres on."""
        source_path = self._step_path_for_label(label)
        if source_path is None or Path(source_path).suffix.lower() not in {".step", ".stp"}:
            return None
        try:
            document = self._load_step_analytic_document(Path(source_path))
        except Exception:
            return None
        faces = getattr(document, "outer_faces", None) or ()
        try:
            idx = int(face_index)
        except Exception:
            return None
        if not (0 <= idx < len(faces)):
            return None
        bbox = getattr(faces[idx], "bbox", None)
        if bbox is None:
            return None
        arr = np.asarray(bbox, dtype=float).reshape(-1)
        if arr.size < 6 or not np.all(np.isfinite(arr[:6])):
            return None
        extents = np.sort(np.maximum(arr[3:6] - arr[0:3], 0.0))  # [thickness, span_a, span_b]
        span_a = float(extents[1])
        return span_a if span_a > 0.0 else None

    def _led_beam_splitter_opening_plan(self):
        """Where a beam splitter should centre on the LED: ``(face_index, world
        centroid, side_mm)``, or None.

        Prefers the C2 auto-detect (rim-window signature); falls back to a manually
        picked clear aperture (``STEP_CLEAR_APERTURE_PICK``).  ``side_mm`` is the
        opening's smaller in-plane span (clamped) so the BS is sized to fit."""
        if self._step_path_for_label("led") is None:
            return None
        face_index = None
        candidates = self.auto_detect_step_clear_aperture_candidates("led")
        if candidates:
            face_index = int(candidates[0].face_index)
        else:
            record = self.step_clear_aperture("led")
            if isinstance(record, dict):
                try:
                    face_index = int(record.get("face_index"))
                except Exception:
                    face_index = None
        if face_index is None:
            return None
        resolved = self._step_overlay_fine_face_centroid_normal("led", face_index)
        if resolved is None:
            return None
        center_world, _normal, _area = resolved
        span = self._step_analytic_face_inplane_span("led", face_index)
        side_mm = float(span) if span and span > 0.0 else 25.0
        side_mm = float(min(max(side_mm, 8.0), 90.0))
        return int(face_index), np.asarray(center_world, dtype=float).reshape(-1)[:3], side_mm

    def _flag_beam_splitter_coating_face(self, row_index: int, *, tilt_deg: float = 45.0, tol_deg: float = 20.0):
        """Auto-flag the promoted BS row's 45-degree diagonal as the Beam Splitter
        coating (bugs/0319 decision 1: "no harm to auto-flag since it is a BS anyway").
        Picks the largest planar face whose normal sits ~``tilt_deg`` off +Z."""
        try:
            _row, _path, metadata = self._optical_solid_face_metadata_for_row(int(row_index))
        except Exception:
            return None
        zhat = np.asarray((0.0, 0.0, 1.0), dtype=float)
        best_face_id = ""
        best_area = -1.0
        for face in list(metadata.get("faces", []) or []):
            if not isinstance(face, dict):
                continue
            normal = np.asarray(face.get("normal", (0.0, 0.0, 1.0)), dtype=float).reshape(-1)[:3]
            norm = float(np.linalg.norm(normal))
            if norm <= 1.0e-9 or not np.isfinite(norm):
                continue
            cos_to_axis = float(np.clip(abs(float(np.dot(normal / norm, zhat))), 0.0, 1.0))
            angle = float(np.degrees(np.arccos(cos_to_axis)))
            if abs(angle - tilt_deg) > tol_deg:
                continue
            area = float(face.get("area_mm2", 0.0) or 0.0)
            if area > best_area:
                best_area = area
                best_face_id = str(face.get("face_id", "") or "").strip()
        if not best_face_id:
            return None
        try:
            return self.assign_optical_solid_face_function(
                int(row_index),
                best_face_id,
                optical_solid_metadata.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_SPLITTER,
            )
        except Exception:
            return None

    def add_beam_splitter_to_led(self, kind: str = "cube") -> dict[str, object] | None:
        """One-click "Add Beam Splitter to LED" (bugs/0319 C3).

        Generate a parametric BS (cube/plate) sized to the LED clear-aperture opening,
        overlay it as the "optical" STEP, centre both the LED opening and the BS on the
        global optical axis, glue the BS to the LED, promote it to a non-sequential
        optical solid, and auto-flag the 45-degree diagonal as the BS coating.

        The LED opening is auto-detected with the manual ``STEP_CLEAR_APERTURE_PICK`` as
        the dependable fallback (decision 2).  Returns a summary, or None on a graceful
        stop (with a status line telling the user what to do)."""
        kind = str(kind or "").strip().lower()
        if kind not in ("cube", "plate"):
            self.status_var.set(f"Add Beam Splitter to LED: unknown kind {kind!r} (want 'cube' or 'plate').")
            return None
        if self._step_path_for_label("led") is None:
            self.status_var.set("Add Beam Splitter to LED: import the LED STEP first.")
            return None
        plan = self._led_beam_splitter_opening_plan()
        if plan is None:
            self.status_var.set(
                "Add Beam Splitter to LED: could not find the LED clear-aperture opening. "
                "Right-click the LED window -> Set as Clear Aperture, then retry."
            )
            return None
        face_index, opening_center, side_mm = plan
        opening_z = float(opening_center[2])

        # 1) Generate the parametric BS, sized to the opening (regen if cache missing).
        try:
            if kind == "cube":
                solid = generate_beam_splitter("cube", side_mm=side_mm)
            else:
                solid = generate_beam_splitter(
                    "plate",
                    width_mm=side_mm,
                    height_mm=side_mm,
                    thickness_mm=float(min(max(side_mm * 0.12, 2.0), side_mm * 0.5)),
                    tilt_deg=45.0,
                )
        except Exception as exc:
            self.status_var.set(f"Add Beam Splitter to LED: BS generation failed ({exc}).")
            return None

        # 2) Overlay the BS as the "optical" STEP (programmatic path bypass).
        if self.import_optical_step(path=solid.path, refresh_open_3d=False) is None:
            self.status_var.set("Add Beam Splitter to LED: could not overlay the generated BS.")
            return None

        # 3) Set the LED clear aperture + centre it on the global optical axis.
        self.set_step_clear_aperture("led", face_index)
        self.center_clear_aperture_on_optical_axis("led")

        # 4) Centre the BS on that same opening (now at (0,0,z) on the axis). The BS
        #    template is origin-centred, so its placement offset IS its world centre.
        self._set_step_placement_offset_xyz("optical", (0.0, 0.0, opening_z))

        # 5) Glue the BS to the LED so they move as one.
        self.set_optical_led_glue(True)

        # 6) Promote the BS to a non-sequential optical solid (consume the overlay so
        #    the scene shows one body; the glue survives promotion, bugs/0127).
        promoted = self.promote_imported_step_to_optical_solid_row(
            "optical", open_face_editor=False, clear_overlay=True, refresh_open_3d=False
        )
        if promoted is None:
            self.status_var.set("Add Beam Splitter to LED: BS overlaid + glued, but promotion failed.")
            return None
        row_index = int(promoted.get("row_index", -1))

        # 7) Auto-flag the 45-degree diagonal as the BS coating (decision 1).
        coating = self._flag_beam_splitter_coating_face(row_index)

        self._refresh_open_3d_views()
        coating_note = (
            f"; coating on {coating.get('face_id')}"
            if isinstance(coating, dict)
            else "; coating auto-flag deferred"
        )
        self.status_var.set(
            f"Added {kind} beam splitter to the LED (S{row_index}, side {side_mm:.1f} mm){coating_note}."
        )
        return {
            "kind": kind,
            "row_index": row_index,
            "side_mm": float(side_mm),
            "opening_face_index": int(face_index),
            "opening_center": tuple(float(v) for v in opening_center[:3]),
            "bs_path": str(solid.path),
            "coating_tilt_deg": float(solid.coating_tilt_deg),
            "coating_face": (coating.get("face_id") if isinstance(coating, dict) else None),
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
