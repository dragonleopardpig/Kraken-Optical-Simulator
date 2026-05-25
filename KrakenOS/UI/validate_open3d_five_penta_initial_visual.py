"""Display-backed guard for first-open five-penta Open 3D rendering.

This diagnostic loads the saved five-penta cascade layout, opens the embedded
Open 3D view, captures the initial scene, then presses the same trace path used
by Trace Now and captures a second scene. It is intentionally not part of the
fast contract runner because it needs a VTK/Tk display.

Run under X, for example:

    env DISPLAY=:99 python -m KrakenOS.UI.validate_open3d_five_penta_initial_visual
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _save_vtk_snapshot, _settle
from KrakenOS.UI.capture_vendor_prism_case_study_screenshots import PROJECT_ROOT
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data, _short_error_message
from KrakenOS.UI.services.open3d_diagnostics import inspector_state_report


DEFAULT_LAYOUT_PATH = PROJECT_ROOT / "attachment" / "five_penta_prism_cascade.py"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "attachment" / "open3d_five_penta_initial_visual"
EXPECTED_RAYS = 13
EXPECTED_PENTA_COUNT = 5
EXPECTED_FINAL_DIRECTION = np.asarray((-1.0, 0.0, 0.0), dtype=float)
MAX_REASONABLE_COORDINATE_MM = 1000.0


def _load_saved_layout(app: KrakenLayoutEditor, path: Path) -> None:
    info = _load_python_data(path)
    app._reset_complete_layout_runtime_state(close_viewers=True)
    app.current_layout_file = path.resolve()
    app.rows = app._normalized_rows_copy([app._row_from_layout_item(item) for item in info["surfaces"]])
    app._auto_assign_missing_elements(app.rows)
    app._apply_layout_settings(info.get("settings", {}))
    app._normalize_special_rows()
    app._sync_table()
    app._select_table_row(0)
    app._invalidate_preview_scene_trace()
    app.auto_save_plot_var.set(False)
    app.update_idletasks()
    app.update()


def _assert_state_ok(state: dict[str, object]) -> None:
    label = str(state.get("label", "state"))
    path_count = int(state.get("path_count", 0) or 0)
    if path_count != EXPECTED_RAYS:
        raise RuntimeError(f"{label}: expected {EXPECTED_RAYS} ray paths, got {path_count}.")
    terminal_counts = dict(state.get("terminal_counts", {}) or {})
    if terminal_counts != {"escaped": EXPECTED_RAYS}:
        raise RuntimeError(f"{label}: expected all rays escaped, got {terminal_counts!r}.")
    events = dict(state.get("surface_event_counts", {}) or {})
    for face_id in ("F003", "F004"):
        expected = EXPECTED_RAYS * EXPECTED_PENTA_COUNT
        actual = int(events.get(f"{face_id}:reflection", 0) or 0)
        if actual != expected:
            raise RuntimeError(f"{label}: expected {expected} {face_id} reflections, got {actual}; events={events!r}.")
    central = dict(state.get("central_path", {}) or {})
    max_abs = float(central.get("max_abs_coordinate", 0.0) or 0.0)
    if max_abs > MAX_REASONABLE_COORDINATE_MM:
        raise RuntimeError(f"{label}: terminal path appears image-plane projected or unbounded, max_abs={max_abs:g}.")
    direction = np.asarray(central.get("terminal_direction", []), dtype=float)
    if direction.size != 3 or float(np.dot(direction, EXPECTED_FINAL_DIRECTION)) < 0.999:
        raise RuntimeError(f"{label}: central terminal direction {direction.tolist()} did not match -X.")
    image = dict(state.get("image", {}) or {})
    if int(image.get("bytes", 0) or 0) <= 4096:
        raise RuntimeError(f"{label}: snapshot was not written or is too small: {image!r}.")
    non_white = image.get("non_white_pixels")
    colored = image.get("colored_pixels")
    if non_white is not None and int(non_white or 0) < 2000:
        raise RuntimeError(f"{label}: snapshot appears blank: {image!r}.")
    if colored is not None and int(colored or 0) < 1000:
        raise RuntimeError(f"{label}: snapshot lacks colored ray/body content: {image!r}.")


def _compare_initial_and_trace_now(initial: dict[str, object], trace_now: dict[str, object]) -> None:
    initial_signatures = list(initial.get("path_signatures", []) or [])
    trace_signatures = list(trace_now.get("path_signatures", []) or [])
    if initial_signatures != trace_signatures:
        raise RuntimeError("Initial Open 3D ray paths differ from Trace Now paths.")


def capture_case(layout_path: Path = DEFAULT_LAYOUT_PATH, output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    if not layout_path.exists():
        raise RuntimeError(f"Expected saved five-penta layout: {layout_path}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry("1800x1040+20+20")
        _load_saved_layout(app, layout_path)
        inspector = _open_3d_inspector(app)
        _settle(inspector, 0.35)

        inspector.set_camera_preset("iso")
        initial_image = _save_vtk_snapshot(inspector, output_dir / "initial_open3d.png")
        initial = inspector_state_report(inspector, "initial_open3d", image_path=initial_image)
        _assert_state_ok(initial)

        inspector._refresh_trace_now_scene("five-penta visual guard")
        _settle(inspector, 0.35)
        inspector.set_camera_preset("iso")
        trace_now_image = _save_vtk_snapshot(inspector, output_dir / "after_trace_now.png")
        trace_now = inspector_state_report(inspector, "after_trace_now", image_path=trace_now_image)
        _assert_state_ok(trace_now)
        _compare_initial_and_trace_now(initial, trace_now)

        report: dict[str, object] = {
            "ok": True,
            "layout_path": str(layout_path.resolve()),
            "output_dir": str(output_dir),
            "initial_open3d": initial,
            "after_trace_now": trace_now,
        }
        report_path = output_dir / "open3d_five_penta_initial_visual_report.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report["report_path"] = str(report_path)
        return report
    finally:
        try:
            if app._three_d_inspector is not None:
                app._three_d_inspector._on_close()
        except Exception:
            pass
        app.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=None, help="Optional copy of the JSON report.")
    args = parser.parse_args()
    try:
        report = capture_case(args.layout, args.output_dir)
    except Exception as exc:
        report = {"ok": False, "error": _short_error_message(exc)}
        if args.report is not None:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
