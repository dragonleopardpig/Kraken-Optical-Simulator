from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from KrakenOS.UI.layout_editor import (
    ANALYSIS_PATH_FILTER_DEFAULT,
    ARM_VIEW_DEFAULT,
    LAYOUTS_DIR,
    SOURCE_MODEL_DEFAULT,
    KrakenLayoutEditor,
    SurfaceRow,
    _load_python_title,
)


@dataclass
class PresetRuntimeResetCheck:
    check: str
    ok: bool
    detail: str


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value


class _FakeInspector:
    def __init__(self) -> None:
        self.destroyed = False

    def destroy(self) -> None:
        self.destroyed = True


def validate_preset_runtime_reset() -> list[PresetRuntimeResetCheck]:
    app = KrakenLayoutEditor.__new__(KrakenLayoutEditor)
    inspector = _FakeInspector()
    app._three_d_inspector = inspector
    app._legacy_3d_plotter = None
    app._legacy_3d_after_id = None
    app.imported_camera_step_path = Path("/tmp/camera.step")
    app.imported_lens_step_path = Path("/tmp/lens.step")
    app.imported_led_step_path = Path("/tmp/led.step")
    app.camera_step_rotation_x_deg = 12.0
    app.lens_step_rotation_x_deg = 34.0
    app.led_step_rotation_x_deg = 56.0
    app.camera_step_rotation_z_deg = 78.0
    app.lens_step_rotation_z_deg = 90.0
    app.led_step_rotation_z_deg = 11.0
    app.led_object_edge_distance_mm = 3.0
    app.led_step_object_edge_local_z = 4.0
    app.lens_step_axis_offset_xy = (1.0, 2.0)
    app.camera_step_axis_offset_xy = (3.0, 4.0)
    app.led_step_axis_offset_xy = (5.0, 6.0)
    app._cad_axis_pick_label = "lens"
    app._cad_led_object_edge_pick = True
    app._selected_step_label = "camera"
    app._external_cad_mesh_cache = {"mesh": object()}
    app._external_cad_reference_cache = {"ref": object()}
    app._external_cad_section_cache = {"section": object()}
    app._last_scene_bundle = object()
    app._last_auto_leg_entries = [{"leg_id": "old"}]
    app._layout_pick_regions = {1: object()}
    app._layout_ray_pick_regions = [(1, object())]
    app.metal_catalogs = [{"old": True}]
    app.layout_scene_source_specs = [{"source_id": "old"}]
    app.layout_scene_row_order = "before_object"
    app.trace_mode = "Non-Sequential Preview"
    app.trace_mode_var = _Var("Non-Sequential Preview")
    app.nonseq_target_surface_var = _Var("7: Old STL")
    app.nonseq_ns_limit_var = _Var("10000")
    app.nonseq_energy_probability_var = _Var(True)
    app.arm_view_var = _Var("Path 99")
    app.analysis_branch_filter_var = _Var("Path 99")
    app.source_model_var = _Var("Gaussian beam")
    app.selected_analysis_modes = ["detector_map"]
    app.analysis_mode = "detector_map"
    app.secondary_analysis_mode = None
    app.layout_preview_mode = "detector_map"

    app._reset_complete_layout_runtime_state(close_viewers=True)

    checks = [
        PresetRuntimeResetCheck(
            "trace controls reset to sequential-safe Auto",
            app.trace_mode == "Auto"
            and app.trace_mode_var.get() == "Auto"
            and app.nonseq_target_surface_var.get() == "Auto"
            and app.nonseq_ns_limit_var.get() == "200"
            and app.nonseq_energy_probability_var.get() is False,
            (
                f"trace={app.trace_mode_var.get()}, target={app.nonseq_target_surface_var.get()}, "
                f"limit={app.nonseq_ns_limit_var.get()}, energy={app.nonseq_energy_probability_var.get()}"
            ),
        ),
        PresetRuntimeResetCheck(
            "path/source filters reset",
            app.arm_view_var.get() == ARM_VIEW_DEFAULT
            and app.analysis_branch_filter_var.get() == ANALYSIS_PATH_FILTER_DEFAULT
            and app.source_model_var.get() == SOURCE_MODEL_DEFAULT,
            (
                f"path={app.arm_view_var.get()}, filter={app.analysis_branch_filter_var.get()}, "
                f"source={app.source_model_var.get()}"
            ),
        ),
        PresetRuntimeResetCheck(
            "CAD/STEP imports and caches are cleared",
            app.imported_camera_step_path is None
            and app.imported_lens_step_path is None
            and app.imported_led_step_path is None
            and app._external_cad_mesh_cache == {}
            and app._external_cad_reference_cache == {}
            and app._external_cad_section_cache == {},
            (
                f"camera={app.imported_camera_step_path}, lens={app.imported_lens_step_path}, "
                f"led={app.imported_led_step_path}, caches="
                f"{len(app._external_cad_mesh_cache)}/"
                f"{len(app._external_cad_reference_cache)}/"
                f"{len(app._external_cad_section_cache)}"
            ),
        ),
        PresetRuntimeResetCheck(
            "scene viewers and old scene products are dropped",
            inspector.destroyed
            and app._three_d_inspector is None
            and app._last_scene_bundle is None
            and app._last_auto_leg_entries == []
            and app._layout_pick_regions == {}
            and app._layout_ray_pick_regions == [],
            (
                f"destroyed={inspector.destroyed}, inspector={app._three_d_inspector}, "
                f"scene={app._last_scene_bundle}, legs={app._last_auto_leg_entries}"
            ),
        ),
    ]

    layout_path = next(
        path
        for path in sorted(LAYOUTS_DIR.glob("*.py"))
        if not path.name.startswith("_")
        and path.name != "__init__.py"
        and str(_load_python_title(path)).strip() == "Zemax Double Gauss 28 Degree Field"
    )
    app2 = KrakenLayoutEditor.__new__(KrakenLayoutEditor)
    app2.headless = True
    app2.layout_files = {"Zemax Double Gauss 28 Degree Field": layout_path}
    app2.machine_vision_files = {}
    app2.rows = [
        SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
        SurfaceRow(
            surface="Standard",
            name="Optical solid",
            thickness=10.0,
            diameter=10.0,
            glass="BK7",
            advanced={"Solid_3d_stl": "/tmp/old-cube.stl"},
        ),
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
    ]
    app2.current_layout_file = None
    app2._three_d_inspector = None
    app2._legacy_3d_plotter = None
    app2._legacy_3d_after_id = None
    app2._external_cad_mesh_cache = {"old": object()}
    app2._external_cad_reference_cache = {}
    app2._external_cad_section_cache = {}
    app2.imported_camera_step_path = Path("/tmp/camera.step")
    app2.imported_lens_step_path = None
    app2.imported_led_step_path = None
    app2.camera_step_rotation_x_deg = 0.0
    app2.lens_step_rotation_x_deg = 0.0
    app2.led_step_rotation_x_deg = 0.0
    app2.camera_step_rotation_z_deg = 0.0
    app2.lens_step_rotation_z_deg = 0.0
    app2.led_step_rotation_z_deg = 0.0
    app2.led_object_edge_distance_mm = 0.0
    app2.led_step_object_edge_local_z = None
    app2.lens_step_axis_offset_xy = (0.0, 0.0)
    app2.camera_step_axis_offset_xy = (0.0, 0.0)
    app2.led_step_axis_offset_xy = (0.0, 0.0)
    app2._cad_axis_pick_label = None
    app2._cad_led_object_edge_pick = False
    app2._selected_step_label = None
    app2.trace_mode = "Non-Sequential Preview"
    app2.trace_mode_var = _Var("Non-Sequential Preview")
    app2.nonseq_target_surface_var = _Var("1: Optical solid")
    app2.nonseq_ns_limit_var = _Var("10000")
    app2.nonseq_energy_probability_var = _Var(True)
    app2.arm_view_var = _Var("Path 99")
    app2.analysis_branch_filter_var = _Var("Path 99")
    app2.source_model_var = _Var("Gaussian beam")
    app2.layout_var = _Var("Common Optical Layout")
    app2.machine_vision_var = _Var("Machine Vision Lens")
    app2.example_var = _Var("Examples")
    app2.status_var = _Var("")
    app2._begin_history_capture = lambda: None
    app2._commit_history_capture = lambda: None
    app2._normalized_rows_copy = lambda rows: rows
    app2._auto_assign_missing_elements = lambda rows: None
    app2._normalize_special_rows = lambda: None
    app2._sync_table = lambda: None
    app2._select_inserted_layout_rows = lambda *args, **kwargs: None
    app2._apply_initial_field_defaults = lambda: None
    app2._apply_initial_layout_view_defaults = lambda _name: None
    app2._apply_layout_settings = lambda _settings: None
    app2.refresh_plot = lambda *args, **kwargs: None
    app2.load_layout_by_name("Zemax Double Gauss 28 Degree Field", refresh=False)
    solid_rows_after = [
        row for row in app2.rows
        if isinstance(getattr(row, "advanced", None), dict) and row.advanced.get("Solid_3d_stl")
    ]
    checks.append(
        PresetRuntimeResetCheck(
            "complete layout load replaces stale CAD/STL runtime state",
            bool(app2.rows)
            and not solid_rows_after
            and app2.trace_mode_var.get() == "Auto"
            and app2.nonseq_target_surface_var.get() == "Auto"
            and app2._external_cad_mesh_cache == {}
            and app2.layout_var.get() == "Zemax Double Gauss 28 Degree Field",
            (
                f"rows={len(app2.rows)}, solid_rows={len(solid_rows_after)}, "
                f"trace={app2.trace_mode_var.get()}, target={app2.nonseq_target_surface_var.get()}, "
                f"cache={len(app2._external_cad_mesh_cache)}, layout={app2.layout_var.get()}"
            ),
        )
    )
    return checks


def _print_table(checks: list[PresetRuntimeResetCheck]) -> None:
    print("KrakenOS complete-preset runtime reset validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate complete preset load runtime-state reset.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_preset_runtime_reset()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
