"""Validate STEP overlay import/reset state lives behind a service."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
from pathlib import Path

from KrakenOS.UI.services.step_overlay_import import StepOverlayImportService


@dataclass
class _Row:
    thickness: float


class _Editor:
    def __init__(self) -> None:
        self.rows = [_Row(10.0), _Row(30.0)]
        self.imported_lens_step_path = Path("/tmp/lens.step")
        self.imported_optical_step_path = Path("/tmp/optic.step")
        self.imported_camera_step_path = Path("/tmp/camera.step")
        self.imported_led_step_path = Path("/tmp/led.step")
        self.lens_step_largest_component_only = False
        self.lens_step_rotation_x_deg = 11.0
        self.lens_step_rotation_y_deg = 22.0
        self.lens_step_rotation_z_deg = 33.0
        self.lens_step_axis_offset_xy = (1.0, 2.0)
        self.lens_step_placement_offset_xyz = (3.0, 4.0, 5.0)
        self.led_object_edge_distance_mm = 12.0
        self.led_step_object_edge_local_z = 8.0
        self._selected_step_label = "lens"
        self._live_step_overlay_trace_plan_cache = {"stale": True}
        self._cleared_step_physics_preview_labels: list[str] = []
        self.invalidated = False

    def _invalidate_preview_scene_trace(self) -> None:
        self.invalidated = True

    def _clear_step_overlay_axis_anchor(self, _label: str) -> None:
        pass

    def _open3d_trace_refresh_service(self):
        editor = self

        class _TraceRefresh:
            def clear_step_overlay_physics_preview(self, label=None) -> None:
                editor._cleared_step_physics_preview_labels.append(str(label or ""))

        return _TraceRefresh()


def main() -> int:
    editor = _Editor()
    service = StepOverlayImportService(editor)
    checks = [
        (
            "service preserves lens-as-optical display mode",
            service.step_overlay_display_label("lens") == "Optical",
        ),
        (
            "service resolves imported STEP slots by label",
            service.step_path_for_label("optical") == Path("/tmp/optic.step")
            and service.step_path_for_label("unknown") is None,
        ),
        (
            "default optical STEP import offset follows current row span",
            service._default_optical_step_import_offset() == (0.0, 0.0, 20.0),
        ),
        (
            "Open 3D imports can suppress editor-level double refresh",
            "refresh_open_3d: bool = True" in inspect.getsource(StepOverlayImportService)
            and "if refresh_open_3d:" in inspect.getsource(StepOverlayImportService),
        ),
    ]
    service.clear_imported_step_overlay_state("lens")
    checks.extend(
        [
            (
                "clear resets the selected lens overlay slot",
                editor.imported_lens_step_path is None
                and editor.lens_step_rotation_x_deg == 0.0
                and editor.lens_step_rotation_y_deg == 0.0
                and editor.lens_step_rotation_z_deg == 0.0
                and editor.lens_step_axis_offset_xy == (0.0, 0.0)
                and editor.lens_step_placement_offset_xyz == (0.0, 0.0, 0.0),
            ),
            (
                "clear restores selection/cache flags through the editor",
                editor.lens_step_largest_component_only is True
                and editor._selected_step_label is None
                and editor._live_step_overlay_trace_plan_cache == {}
                and editor.invalidated is True,
            ),
            (
                "clear removes transient STEP physics-preview readiness",
                "lens" in editor._cleared_step_physics_preview_labels,
            ),
        ]
    )
    editor._selected_step_label = "led"
    service.clear_imported_step_overlay_state("led")
    checks.append(
        (
            "LED clear resets object-edge state",
            editor.imported_led_step_path is None
            and editor.led_object_edge_distance_mm == 0.0
            and editor.led_step_object_edge_local_z is None,
        )
    )
    failed = [name for name, ok in checks if not ok]
    if failed:
        print("STEP overlay import service validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("STEP overlay import service validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
