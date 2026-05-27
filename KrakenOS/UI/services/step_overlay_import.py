"""Open 3D STEP overlay import state service."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from typing import Any

import numpy as np

from KrakenOS.UI.services.step_overlay_labels import STEP_OVERLAY_LABEL_SET


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class StepOverlayImportService:
    """Own imported STEP overlay slots and reset state transitions."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def import_lens_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        title: str = "Import lens STEP",
        display_label: str = "Lens STEP",
        largest_component_only: bool = True,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        le = _layout_module()
        path = self._ask_step_file(title, le.ATTACHMENT_DIR, parent=dialog_parent)
        if path is None:
            return None
        self._begin_history_capture()
        self.imported_lens_step_path = path
        self.lens_step_largest_component_only = bool(largest_component_only)
        self.lens_step_rotation_x_deg = 0.0
        self.lens_step_rotation_y_deg = 0.0
        self.lens_step_rotation_z_deg = 0.0
        self.lens_step_axis_offset_xy = (0.0, 0.0)
        self.lens_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._selected_step_label = "lens"
        self._cad_axis_pick_any = False
        self._open3d_trace_refresh_service().clear_step_overlay_physics_preview("lens")
        self._commit_history_capture()
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()
        self.status_var.set(f"{display_label} imported: {path.name}. Open or refresh 3D view.")
        if refresh_open_3d:
            self._refresh_open_3d_views()
        return path

    def _default_optical_step_import_offset(self) -> tuple[float, float, float]:
        z_values = [0.0]
        z = 0.0
        for row in list(getattr(self, "rows", []) or []):
            try:
                z += float(getattr(row, "thickness", 0.0) or 0.0)
                z_values.append(float(z))
            except Exception:
                continue
        finite = [value for value in z_values if np.isfinite(value)]
        if not finite:
            return (0.0, 0.0, 0.0)
        return (0.0, 0.0, 0.5 * (min(finite) + max(finite)))

    @staticmethod
    def _optical_prescription_sidecars(path: Path) -> tuple[Path, ...]:
        path = Path(path).expanduser()
        parent = path.parent
        if not parent.exists():
            return ()
        suffixes = {".zmx", ".seq"}
        matches: list[Path] = []
        try:
            for candidate in parent.iterdir():
                if candidate.is_file() and candidate.suffix.lower() in suffixes:
                    matches.append(candidate)
        except OSError:
            return ()
        return tuple(sorted(matches, key=lambda item: (item.suffix.lower() != ".zmx", item.name.lower())))

    def _preserve_unpromoted_step_overlay(self, label: str) -> dict[str, object] | None:
        """Promote an un-promoted STEP overlay before its import slot is reused."""
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return None
        if self._step_path_for_label(label) is None:
            return None
        try:
            result = self.promote_imported_step_to_optical_solid_row(
                label,
                open_face_editor=False,
                clear_overlay=True,
                refresh_open_3d=False,
            )
        except Exception as exc:
            self.append_debug(f"Auto-keep of the existing {label} STEP overlay failed: {exc}")
            return None
        if result is not None:
            row_index = int(result.get("row_index", -1))
            self.append_debug(
                f"Auto-promoted the existing {label.upper()} STEP overlay to optical "
                f"solid row S{row_index} so the new import does not overwrite it."
            )
        return result

    def import_optical_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        le = _layout_module()
        path = self._ask_step_file("Import optical STEP", le.ATTACHMENT_DIR, parent=dialog_parent)
        if path is None:
            return None
        self._preserve_unpromoted_step_overlay("optical")
        self._begin_history_capture()
        self.imported_optical_step_path = path
        self.optical_step_rotation_x_deg = 0.0
        self.optical_step_rotation_y_deg = 0.0
        self.optical_step_rotation_z_deg = 0.0
        self.optical_step_axis_offset_xy = (0.0, 0.0)
        self.optical_step_placement_offset_xyz = self._default_optical_step_import_offset()
        self._selected_step_label = "optical"
        self._cad_axis_pick_any = False
        self._open3d_trace_refresh_service().clear_step_overlay_physics_preview("optical")
        self._commit_history_capture()
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()
        sidecars = self._optical_prescription_sidecars(path)
        if sidecars:
            self.status_var.set(
                f"Optical STEP imported as CAD solid: {path.name}. STEP has no glass prescription; "
                f"import {sidecars[0].name} for designed lens focus, or promote/assign STEP material and faces."
            )
        else:
            self.status_var.set(f"Optical STEP imported: {path.name}. Carry and place it in Open 3D.")
        if refresh_open_3d:
            self._refresh_open_3d_views(step_label="optical")
        return path

    def import_camera_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        le = _layout_module()
        path = self._ask_step_file("Import camera STEP", le.ATTACHMENT_DIR, parent=dialog_parent)
        if path is None:
            return None
        self._begin_history_capture()
        self.imported_camera_step_path = path
        self.camera_step_rotation_x_deg = 0.0
        self.camera_step_rotation_y_deg = 0.0
        self.camera_step_rotation_z_deg = 0.0
        self.camera_step_axis_offset_xy = (0.0, 0.0)
        self.camera_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._selected_step_label = "camera"
        self._cad_axis_pick_any = False
        self._open3d_trace_refresh_service().clear_step_overlay_physics_preview("camera")
        self._commit_history_capture()
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()
        self.status_var.set(f"Camera STEP imported: {path.name}. Open or refresh 3D view.")
        if refresh_open_3d:
            self._refresh_open_3d_views(camera_only=True)
        return path

    def import_led_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        le = _layout_module()
        initial_dir = le.ATTACHMENT_DIR
        path = self._ask_step_file("Import LED STEP", initial_dir, parent=dialog_parent)
        if path is None:
            return None
        initial_distance = max(float(getattr(self, "led_object_edge_distance_mm", 0.0)), 0.0)
        if initial_distance <= 0.0:
            initial_distance = self._default_led_object_edge_distance()
        edge_distance = self._ask_led_edge_distance(initial_distance, parent=dialog_parent)
        if edge_distance is None:
            self.status_var.set("LED STEP import cancelled.")
            return None
        self._begin_history_capture()
        self.imported_led_step_path = path
        self.led_step_rotation_x_deg = 0.0
        self.led_step_rotation_y_deg = 0.0
        self.led_step_rotation_z_deg = 0.0
        self.led_step_object_edge_local_z = None
        self.led_step_axis_offset_xy = (0.0, 0.0)
        self.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._selected_step_label = "led"
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._open3d_trace_refresh_service().clear_step_overlay_physics_preview("led")
        self.led_object_edge_distance_mm = float(edge_distance)
        self._commit_history_capture()
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()
        self.status_var.set(
            f"LED STEP imported: {path.name}; edge distance={self.led_object_edge_distance_mm:.3g} mm."
        )
        if refresh_open_3d:
            self._refresh_open_3d_views(step_label="led")
        return path

    @staticmethod
    def _step_overlay_display_label(label: str) -> str:
        label = str(label).strip().lower()
        if label == "lens":
            return "Lens"
        return {
            "optical": "Optical",
            "led": "LED",
            "camera": "Camera",
        }.get(label, "STEP")

    def step_overlay_display_label(self, label: str) -> str:
        label = str(label).strip().lower()
        if label == "lens" and not bool(getattr(self, "lens_step_largest_component_only", True)):
            return "Optical"
        return self._step_overlay_display_label(label)

    def step_path_for_label(self, label: str) -> Path | None:
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return None
        return {
            "lens": self.imported_lens_step_path,
            "optical": self.imported_optical_step_path,
            "led": self.imported_led_step_path,
            "camera": self.imported_camera_step_path,
        }.get(label)

    def clear_imported_step_overlay_state(self, label: str) -> None:
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return
        path_attrs = {
            "lens": "imported_lens_step_path",
            "optical": "imported_optical_step_path",
            "led": "imported_led_step_path",
            "camera": "imported_camera_step_path",
        }
        path_attr = path_attrs.get(label)
        if path_attr:
            setattr(self, path_attr, None)
        for axis in ("x", "y", "z"):
            attr = f"{label}_step_rotation_{axis}_deg"
            if hasattr(self, attr):
                setattr(self, attr, 0.0)
        axis_attr = f"{label}_step_axis_offset_xy"
        if hasattr(self, axis_attr):
            setattr(self, axis_attr, (0.0, 0.0))
        placement_attr = f"{label}_step_placement_offset_xyz"
        if hasattr(self, placement_attr):
            setattr(self, placement_attr, (0.0, 0.0, 0.0))
        self._live_step_overlay_trace_plan_cache = {}
        if label == "led":
            self.led_object_edge_distance_mm = 0.0
            self.led_step_object_edge_local_z = None
        if label == "lens":
            self.lens_step_largest_component_only = True
        self._open3d_trace_refresh_service().clear_step_overlay_physics_preview(label)
        if self._selected_step_label == label:
            self._selected_step_label = None
        self._invalidate_preview_scene_trace()
