"""Capture screenshots for the 3D hardware-alignment case study.

This script needs a real display because it captures the actual Tk/VTK UI.
Run it from the project root with:

    python -m KrakenOS.UI.capture_3d_hardware_alignment_case_study_screenshots
"""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from KrakenOS.UI.capture_vendor_prism_case_study_screenshots import (
    PRISM_42779_STEP,
    PROJECT_ROOT,
    _apply_face_fit,
    _capture_window_image,
    _configure_app,
    _mesh_vendor_prism,
    _metadata_for_mesh,
    _set_sidebars,
    _show_state,
)
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, Kraken3DInspector


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "3d_hardware_alignment"


def _save_widget(widget, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    _capture_window_image(widget).save(path, optimize=True)
    return path


def _open_3d_inspector(app: KrakenLayoutEditor) -> Kraken3DInspector:
    app.open_3d_view()
    app.update_idletasks()
    app.update()
    inspector = app._three_d_inspector
    if inspector is None or not inspector.available:
        reason = getattr(inspector, "unavailable_reason", "") if inspector is not None else "3D inspector did not open"
        raise RuntimeError(f"Embedded 3D inspector unavailable: {reason}")
    inspector.geometry("1280x860+120+80")
    inspector.deiconify()
    inspector.lift()
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.8)
    inspector.update()
    return inspector


def _save_stl_placement_handler(inspector: Kraken3DInspector, output_dir: Path) -> Path:
    inspector.show_stl_placement_handler(1)
    popup = inspector._stl_placement_popup
    if popup is None:
        raise RuntimeError("CAD/STL placement handler did not open")
    popup.update_idletasks()
    popup.update()
    time.sleep(0.3)
    popup.update()
    path = _save_widget(popup, output_dir, "02_cad_stl_placement_handler.png")
    inspector._close_stl_placement_handler()
    return path


def _save_center_step_badge(app: KrakenLayoutEditor, inspector: Kraken3DInspector, output_dir: Path) -> Path:
    app.imported_lens_step_path = PRISM_42779_STEP
    app._selected_step_label = "lens"
    app.start_any_step_axis_pick()
    inspector._update_mode_badge()
    inspector.lift()
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.3)
    inspector.update()
    path = _save_widget(inspector, output_dir, "03_center_step_axis_mode_badge.png")
    app._cad_axis_pick_any = False
    app._cad_axis_pick_label = None
    app._cad_led_object_edge_pick = False
    inspector._set_axis_pick_cursor(False)
    inspector._update_mode_badge()
    return path


def _save_step_rotation_handles(app: KrakenLayoutEditor, inspector: Kraken3DInspector, output_dir: Path) -> Path:
    app._cad_axis_pick_any = False
    app._cad_axis_pick_label = None
    app._cad_led_object_edge_pick = False
    app.imported_lens_step_path = PRISM_42779_STEP
    app.select_step_component("lens")
    inspector.show_step_rotation_handler("lens")
    inspector.refresh_from_editor()
    if not getattr(inspector, "_actor_step_rotate_map", {}):
        raise RuntimeError("STEP rotation handles did not render")
    inspector._set_axis_pick_cursor(False)
    inspector._update_mode_badge()
    inspector.lift()
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.3)
    inspector.update()
    path = _save_widget(inspector, output_dir, "04_step_rotation_handler.png")
    inspector._close_step_rotation_handler()
    return path


def _save_step_carry_snap(app: KrakenLayoutEditor, inspector: Kraken3DInspector, output_dir: Path) -> Path:
    app.imported_lens_step_path = PRISM_42779_STEP
    app.select_step_component("lens")
    inspector.start_selected_step_carry()
    inspector.refresh_from_editor()
    press_xy = (320, 260)
    inspector._left_drag_active = True
    inspector._left_drag_moved = False
    inspector._left_drag_start_xy = press_xy
    inspector._left_drag_last_xy = press_xy
    inspector._step_carry_hold_candidate_label = "lens"
    inspector._step_carry_hold_press_xy = press_xy
    inspector._step_carry_hold_pick_world = None
    inspector._activate_step_carry_hold()
    if inspector._step_carry_drag_state is not None:
        inspector._apply_step_carry_drag_motion(0.0, 0.0, current_xy=(620, 260))
        inspector.refresh_from_editor()
    if "STEP carry lattice=0" not in str(inspector.status_var.get()):
        raise RuntimeError("STEP carry snap state did not render without cube-grid lines")
    inspector.lift()
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.3)
    inspector.update()
    path = _save_widget(inspector, output_dir, "06_step_carry_grid.png")
    inspector.stop_step_carry()
    return path


def _save_source_target_badge(inspector: Kraken3DInspector, output_dir: Path) -> Path:
    inspector.start_source_target_pick()
    inspector._update_mode_badge()
    inspector.lift()
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.3)
    inspector.update()
    path = _save_widget(inspector, output_dir, "05_source_target_mode_badge.png")
    inspector._source_target_pick_mode = False
    inspector._set_axis_pick_cursor(False)
    inspector._update_mode_badge()
    return path


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="kraken-3d-hardware-case-") as tmp_dir:
        cache_dir = Path(tmp_dir)
        mesh_path, _source_path, _source_format, _diagnostics = _mesh_vendor_prism(cache_dir)
        metadata = _metadata_for_mesh(mesh_path)
        app = KrakenLayoutEditor(headless=True)
        try:
            app.geometry("1760x960+40+40")
            _configure_app(app, mesh_path, metadata)
            _apply_face_fit(app, metadata)
            _set_sidebars(app, left=False, right=False)
            _show_state(app, analysis_mode="none")
            inspector = _open_3d_inspector(app)
            outputs.append(_save_widget(inspector, output_dir, "01_3d_inspector_axis_faces.png"))
            outputs.append(_save_stl_placement_handler(inspector, output_dir))
            outputs.append(_save_center_step_badge(app, inspector, output_dir))
            outputs.append(_save_step_rotation_handles(app, inspector, output_dir))
            outputs.append(_save_step_carry_snap(app, inspector, output_dir))
            outputs.append(_save_source_target_badge(inspector, output_dir))
        finally:
            try:
                if app._three_d_inspector is not None:
                    app._three_d_inspector._on_close()
            except Exception:
                pass
            app.destroy()
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    paths = capture(args.output_dir)
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
