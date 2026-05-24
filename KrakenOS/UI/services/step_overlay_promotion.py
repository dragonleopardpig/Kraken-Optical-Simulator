"""Open 3D STEP overlay promotion service."""

from __future__ import annotations

from typing import Any
import hashlib

import numpy as np


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class StepOverlayPromotionService:
    """Plan and promote imported STEP overlays into row-backed optical solids."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

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
        le = _layout_module()
        CAD_CACHE_DIR = le.CAD_CACHE_DIR
        SCENE_PLACEMENT_ADVANCED_ATTR = le.SCENE_PLACEMENT_ADVANCED_ATTR
        STEP_OVERLAY_LABEL_SET = le.STEP_OVERLAY_LABEL_SET
        format_stl_mesh_diagnostics = le.format_stl_mesh_diagnostics
        inspect_stl_mesh = le.inspect_stl_mesh
        normalize_scene_placement_settings = le.normalize_scene_placement_settings
        short_stl_mesh_diagnostics = le.short_stl_mesh_diagnostics
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return None
        source_path = self._step_path_for_label(label)
        if source_path is None:
            if not quiet:
                self.status_var.set(f"No {label} STEP is imported.")
            return None
        mesh = self._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            if not quiet:
                self.status_var.set(f"{label.upper()} STEP mesh unavailable for optical-solid promotion.")
            return None
        try:
            mesh = mesh.extract_surface(algorithm="dataset_surface").triangulate().copy(deep=True)
        except Exception:
            try:
                mesh = mesh.extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                mesh = mesh.copy(deep=True)
        points = np.asarray(getattr(mesh, "points", np.empty((0, 3))), dtype=float)
        if points.ndim != 2 or points.shape[0] == 0 or points.shape[1] < 3 or not np.all(np.isfinite(points[:, :3])):
            if not quiet:
                self.status_var.set(f"{label.upper()} STEP promotion found no finite mesh points.")
            return None

        bounds_min = np.min(points[:, :3], axis=0)
        bounds_max = np.max(points[:, :3], axis=0)
        center_world = 0.5 * (bounds_min + bounds_max)
        extents = np.maximum(bounds_max - bounds_min, 0.0)
        local_mesh = mesh.copy(deep=True)
        local_mesh.points = points[:, :3] - center_world[:3]

        digest = hashlib.sha1()
        digest.update(str(source_path.resolve()).encode("utf-8", errors="ignore"))
        digest.update(str(label).encode("utf-8"))
        digest.update(np.ascontiguousarray(local_mesh.points, dtype=np.float64).tobytes())
        digest.update(
            repr(
                {
                    "rot_x": self._step_x_rotation_deg(label),
                    "rot_y": self._step_y_rotation_deg(label),
                    "rot_z": self._step_roll_deg(label),
                    "axis_offset_xy": None if transient_live_trace else self._step_axis_offset_xy(label),
                    "placement_offset_xyz": None if transient_live_trace else self._step_placement_offset_xyz(label),
                    "largest_component_only": bool(getattr(self, "lens_step_largest_component_only", True))
                    if label == "lens"
                    else None,
                    "transient_live_trace": bool(transient_live_trace),
                }
            ).encode("utf-8")
        )
        mesh_path = CAD_CACHE_DIR / str(cache_subdir or "promoted_step_overlays") / f"{label}_{digest.hexdigest()[:16]}.stl"
        if not mesh_path.exists() or mesh_path.stat().st_size <= 0:
            mesh_path.parent.mkdir(parents=True, exist_ok=True)
            local_mesh.save(str(mesh_path))
        diagnostics = inspect_stl_mesh(mesh_path)

        arm_key = ""
        if insert_at is None:
            selected_indices = self._selected_table_indices() if use_current_selection else []
            arm_key = self._current_arm_view_key() if use_current_selection else ""
            if selected_indices:
                resolved_insert_at = max(selected_indices) + 1
            elif arm_key:
                resolved_insert_at = self._default_insert_index_for_arm_key(arm_key)
            else:
                resolved_insert_at = len(self.rows)
                if self.rows and self.rows[-1].surface == "Image":
                    resolved_insert_at -= 1
        else:
            resolved_insert_at = int(insert_at)
            arm_key = self._current_arm_view_key() if use_current_selection else ""
        resolved_insert_at = max(
            1,
            min(resolved_insert_at, len(self.rows) - (1 if self.rows and self.rows[-1].surface == "Image" else 0)),
        )
        z_station = float(sum(float(getattr(row, "thickness", 0.0) or 0.0) for row in self.rows[:resolved_insert_at]))

        row = self._optical_stl_solid_row(
            mesh_path.resolve(),
            source_path=source_path.resolve(),
            source_format="STEP",
        )
        if arm_key:
            self._apply_arm_key_metadata_to_row(row, arm_key)
        span = float(max(float(np.max(extents)), 1.0))
        axial_span = float(max(float(extents[2]) if extents.size >= 3 else 0.0, 0.0))
        axial_reserve = max(
            float(row.thickness),
            axial_span,
            float(bounds_max[2] - z_station) if np.isfinite(float(bounds_max[2] - z_station)) else 0.0,
            1.0,
        )
        display_label = self._step_overlay_display_label(label)
        row.element = f"{display_label.upper()} STEP solid"
        row.name = (
            f"Live {display_label.upper()} STEP optical solid"
            if transient_live_trace
            else f"Promoted {display_label.upper()} STEP optical solid"
        )
        row.thickness = float(axial_reserve)
        row.diameter = span
        row.tilt_x = 0.0
        row.tilt_y = 0.0
        row.tilt_z = 0.0
        row.desp_x = float(center_world[0])
        row.desp_y = float(center_world[1])
        row.desp_z = float(center_world[2] - z_station)
        row.axis_move = 0.0
        row.advanced = dict(row.advanced or {})
        row.advanced["Note"] = (
            "Transient Open 3D live-trace optical STEP overlay. The cached Solid_3d_stl mesh is "
            "not inserted in the editable table until the user promotes or accepts placement. "
            "Face metadata, material, and placement are the same row-backed contract used by "
            "promoted STEP optical solids."
            if transient_live_trace
            else "Promoted from an Open 3D imported STEP overlay. The cached Solid_3d_stl mesh is saved "
            "in local coordinates around the overlay center, while row Desp stores the scene/world "
            "center. AxisMove stays zero so the scene object's placement does not move downstream "
            "Object/Image rows; explicit output ports provide the separate follower-row workflow. "
            "Review material and CAD/STL optical face roles before relying on traced physics."
        )
        row.advanced["StepOverlayPromotion"] = {
            "step_label": label,
            "source_step_path": str(source_path.resolve()),
            "promoted_mesh_path": str(mesh_path.resolve()),
            "mesh_coordinates": "local_centered_from_open3d_overlay",
            "center_world": [float(value) for value in center_world[:3]],
            "bounds_min_world": [float(value) for value in bounds_min[:3]],
            "bounds_max_world": [float(value) for value in bounds_max[:3]],
            "row_thickness_mm": float(row.thickness),
            "axial_reserve_mm": float(axial_reserve),
            "step_rotation_deg": [
                float(self._step_x_rotation_deg(label)),
                float(self._step_y_rotation_deg(label)),
                float(self._step_roll_deg(label)),
            ],
            "axis_offset_xy": [float(value) for value in self._step_axis_offset_xy(label)],
            "placement_offset_xyz": [float(value) for value in self._step_placement_offset_xyz(label)],
            "largest_component_only": bool(getattr(self, "lens_step_largest_component_only", True))
            if label == "lens"
            else None,
            "transient_live_trace": bool(transient_live_trace),
        }
        row.advanced["LiveStepOverlayTrace"] = {
            "enabled": bool(transient_live_trace),
            "step_label": label,
            "cache_mesh_path": str(mesh_path.resolve()),
        }
        placement = normalize_scene_placement_settings(
            {
                "enabled": True,
                "anchor": "row_pose",
                "snap_enabled": True,
                "snap_mm": max(span / 20.0, 0.1),
                "snap_deg": 5.0,
                "grid_visible": not bool(transient_live_trace),
                "grid_spacing_mm": max(span / 10.0, 0.5),
                "grid_extent_mm": max(span * 2.0, 25.0),
                "promotion_source": "open3d_step_overlay",
                "promotion_step_label": label,
                "promotion_source_step_path": str(source_path.resolve()),
                "promotion_mesh_coordinates": "local_centered_from_open3d_overlay",
                "transient_live_trace": bool(transient_live_trace),
            }
        )
        row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = placement
        return {
            "label": label,
            "row_index": int(resolved_insert_at),
            "row": row,
            "mesh_path": str(mesh_path.resolve()),
            "source_step_path": str(source_path.resolve()),
            "center_world": tuple(float(value) for value in center_world[:3]),
            "bounds_min_world": tuple(float(value) for value in bounds_min[:3]),
            "bounds_max_world": tuple(float(value) for value in bounds_max[:3]),
            "diagnostics": diagnostics,
            "transient_live_trace": bool(transient_live_trace),
        }

    def promote_imported_step_to_optical_solid_row(
        self,
        label: str,
        *,
        insert_at: int | None = None,
        open_face_editor: bool = True,
        clear_overlay: bool = False,
        refresh_open_3d: bool = True,
    ) -> dict[str, object] | None:
        le = _layout_module()
        CAD_CACHE_DIR = le.CAD_CACHE_DIR
        SCENE_PLACEMENT_ADVANCED_ATTR = le.SCENE_PLACEMENT_ADVANCED_ATTR
        STEP_OVERLAY_LABEL_SET = le.STEP_OVERLAY_LABEL_SET
        format_stl_mesh_diagnostics = le.format_stl_mesh_diagnostics
        inspect_stl_mesh = le.inspect_stl_mesh
        normalize_scene_placement_settings = le.normalize_scene_placement_settings
        short_stl_mesh_diagnostics = le.short_stl_mesh_diagnostics
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return None
        source_path = self._step_path_for_label(label)
        if source_path is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return None
        mesh = self._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            self.status_var.set(f"{label.upper()} STEP mesh unavailable for optical-solid promotion.")
            return None
        try:
            mesh = mesh.extract_surface(algorithm="dataset_surface").triangulate().copy(deep=True)
        except Exception:
            try:
                mesh = mesh.extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                mesh = mesh.copy(deep=True)
        points = np.asarray(getattr(mesh, "points", np.empty((0, 3))), dtype=float)
        if points.ndim != 2 or points.shape[0] == 0 or points.shape[1] < 3 or not np.all(np.isfinite(points[:, :3])):
            self.status_var.set(f"{label.upper()} STEP promotion found no finite mesh points.")
            return None
        bounds_min = np.min(points[:, :3], axis=0)
        bounds_max = np.max(points[:, :3], axis=0)
        center_world = 0.5 * (bounds_min + bounds_max)
        extents = np.maximum(bounds_max - bounds_min, 0.0)
        local_mesh = mesh.copy(deep=True)
        local_mesh.points = points[:, :3] - center_world[:3]

        digest = hashlib.sha1()
        digest.update(str(source_path.resolve()).encode("utf-8", errors="ignore"))
        digest.update(str(label).encode("utf-8"))
        digest.update(np.ascontiguousarray(local_mesh.points, dtype=np.float64).tobytes())
        digest.update(
            repr(
                {
                    "rot_x": self._step_x_rotation_deg(label),
                    "rot_y": self._step_y_rotation_deg(label),
                    "rot_z": self._step_roll_deg(label),
                    "axis_offset_xy": self._step_axis_offset_xy(label),
                    "placement_offset_xyz": self._step_placement_offset_xyz(label),
                    "largest_component_only": bool(getattr(self, "lens_step_largest_component_only", True))
                    if label == "lens"
                    else None,
                }
            ).encode("utf-8")
        )
        promoted_path = CAD_CACHE_DIR / "promoted_step_overlays" / f"{label}_{digest.hexdigest()[:16]}.stl"
        if not promoted_path.exists() or promoted_path.stat().st_size <= 0:
            promoted_path.parent.mkdir(parents=True, exist_ok=True)
            local_mesh.save(str(promoted_path))
        diagnostics = inspect_stl_mesh(promoted_path)

        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            raise RuntimeError(f"Could not read the surface table: {exc}") from exc

        if insert_at is None:
            selected_indices = self._selected_table_indices()
            arm_key = self._current_arm_view_key()
            if selected_indices:
                resolved_insert_at = max(selected_indices) + 1
            elif arm_key:
                resolved_insert_at = self._default_insert_index_for_arm_key(arm_key)
            else:
                resolved_insert_at = len(self.rows)
                if self.rows and self.rows[-1].surface == "Image":
                    resolved_insert_at -= 1
        else:
            resolved_insert_at = int(insert_at)
            arm_key = self._current_arm_view_key()
        resolved_insert_at = max(
            1,
            min(resolved_insert_at, len(self.rows) - (1 if self.rows and self.rows[-1].surface == "Image" else 0)),
        )
        z_station = float(sum(float(getattr(row, "thickness", 0.0) or 0.0) for row in self.rows[:resolved_insert_at]))

        row = self._optical_stl_solid_row(
            promoted_path.resolve(),
            source_path=source_path.resolve(),
            source_format="STEP",
        )
        if arm_key:
            self._apply_arm_key_metadata_to_row(row, arm_key)
        span = float(max(float(np.max(extents)), 1.0))
        axial_span = float(max(float(extents[2]) if extents.size >= 3 else 0.0, 0.0))
        axial_reserve = max(
            float(row.thickness),
            axial_span,
            float(bounds_max[2] - z_station) if np.isfinite(float(bounds_max[2] - z_station)) else 0.0,
            1.0,
        )
        display_label = self._step_overlay_display_label(label)
        row.element = f"{display_label.upper()} STEP solid"
        row.name = f"Promoted {display_label.upper()} STEP optical solid"
        row.thickness = float(axial_reserve)
        row.diameter = span
        row.tilt_x = 0.0
        row.tilt_y = 0.0
        row.tilt_z = 0.0
        row.desp_x = float(center_world[0])
        row.desp_y = float(center_world[1])
        row.desp_z = float(center_world[2] - z_station)
        row.axis_move = 0.0
        row.advanced = dict(row.advanced or {})
        row.advanced["Note"] = (
            "Promoted from an Open 3D imported STEP overlay. The cached Solid_3d_stl mesh is saved "
            "in local coordinates around the overlay center, while row Desp stores the scene/world "
            "center. AxisMove stays zero so the scene object's placement does not move downstream "
            "Object/Image rows; explicit output ports provide the separate follower-row workflow. "
            "Review material and CAD/STL optical face roles before relying on traced physics."
        )
        row.advanced["StepOverlayPromotion"] = {
            "step_label": label,
            "source_step_path": str(source_path.resolve()),
            "promoted_mesh_path": str(promoted_path.resolve()),
            "mesh_coordinates": "local_centered_from_open3d_overlay",
            "center_world": [float(value) for value in center_world[:3]],
            "bounds_min_world": [float(value) for value in bounds_min[:3]],
            "bounds_max_world": [float(value) for value in bounds_max[:3]],
            "row_thickness_mm": float(row.thickness),
            "axial_reserve_mm": float(axial_reserve),
            "step_rotation_deg": [
                float(self._step_x_rotation_deg(label)),
                float(self._step_y_rotation_deg(label)),
                float(self._step_roll_deg(label)),
            ],
            "axis_offset_xy": [float(value) for value in self._step_axis_offset_xy(label)],
            "placement_offset_xyz": [float(value) for value in self._step_placement_offset_xyz(label)],
            "largest_component_only": bool(getattr(self, "lens_step_largest_component_only", True))
            if label == "lens"
            else None,
        }
        placement = normalize_scene_placement_settings(
            {
                "enabled": True,
                "anchor": "row_pose",
                "snap_enabled": True,
                "snap_mm": max(span / 20.0, 0.1),
                "snap_deg": 5.0,
                "grid_visible": True,
                "grid_spacing_mm": max(span / 10.0, 0.5),
                "grid_extent_mm": max(span * 2.0, 25.0),
                "promotion_source": "open3d_step_overlay",
                "promotion_step_label": label,
                "promotion_source_step_path": str(source_path.resolve()),
                "promotion_mesh_coordinates": "local_centered_from_open3d_overlay",
            }
        )
        row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = placement

        self._begin_history_capture()
        self.rows.insert(resolved_insert_at, row)
        if clear_overlay:
            self._clear_imported_step_overlay_state(label)
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices([resolved_insert_at], focus_index=resolved_insert_at)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.append_debug(
            "Promoted {label} STEP overlay to optical solid S{row}: center=({x:.6g},{y:.6g},{z:.6g}) "
            "mesh={mesh}\n{diag}".format(
                label=label.upper(),
                row=int(resolved_insert_at),
                x=float(center_world[0]),
                y=float(center_world[1]),
                z=float(center_world[2]),
                mesh=promoted_path,
                diag=format_stl_mesh_diagnostics(diagnostics),
            )
        )
        if diagnostics.errors or diagnostics.warnings:
            self.status_var.set(
                f"Promoted {label.upper()} STEP to S{resolved_insert_at}; mesh diagnostics need review "
                f"({short_stl_mesh_diagnostics(diagnostics)})."
            )
        else:
            self.status_var.set(
                f"Promoted {label.upper()} STEP to optical solid row S{resolved_insert_at}. Assign faces/material, then Update."
            )
        if refresh_open_3d:
            self._refresh_open_3d_views()
        if open_face_editor:
            self.after(120, lambda idx=resolved_insert_at: self.open_optical_solid_face_role_editor(idx))
        return {
            "label": label,
            "row_index": int(resolved_insert_at),
            "mesh_path": str(promoted_path.resolve()),
            "source_step_path": str(source_path.resolve()),
            "center_world": tuple(float(value) for value in center_world[:3]),
            "diagnostics": diagnostics,
        }
