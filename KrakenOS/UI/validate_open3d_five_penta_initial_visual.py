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
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _save_vtk_snapshot, _settle
from KrakenOS.UI.capture_vendor_prism_case_study_screenshots import PROJECT_ROOT
from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor, _load_python_data, _short_error_message
from KrakenOS.UI.scene_geometry import ray_path_terminal_status_from_events
from KrakenOS.UI.validate_penta_mirror_3d_cascade import _event_action, _event_face_id, _surface_events, _surface_sequence


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


def _terminal_direction(path: object) -> list[float]:
    points = np.asarray(getattr(path, "points_world", ()), dtype=float)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
        return []
    direction = points[-1, :3] - points[-2, :3]
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-12:
        return []
    return [round(float(value), 9) for value in (direction / norm)[:3]]


def _path_signature(path: object) -> dict[str, object]:
    points = np.asarray(getattr(path, "points_world", ()), dtype=float)
    terminal_point: list[float] = []
    max_abs_coordinate = 0.0
    if points.ndim == 2 and points.shape[0] and points.shape[1] >= 3:
        terminal_point = [round(float(value), 6) for value in points[-1, :3]]
        finite = points[:, :3][np.isfinite(points[:, :3])]
        if finite.size:
            max_abs_coordinate = float(np.max(np.abs(finite)))
    return {
        "ray_index": int(getattr(path, "ray_index", 0) or 0),
        "source_ray_index": int(getattr(path, "source_ray_index", getattr(path, "ray_index", 0)) or 0),
        "terminal_status": str(ray_path_terminal_status_from_events(path) or "unknown"),
        "terminal_point": terminal_point,
        "terminal_direction": _terminal_direction(path),
        "max_abs_coordinate": round(max_abs_coordinate, 6),
        "sequence": " -> ".join(_surface_sequence(path)),
    }


def _central_path(ray_paths: list[object]) -> object:
    if not ray_paths:
        raise RuntimeError("No ray paths were rendered.")

    def _score(path: object) -> tuple[float, int]:
        points = np.asarray(getattr(path, "points_world", ()), dtype=float)
        radius = float("inf")
        if points.ndim == 2 and points.shape[0] and points.shape[1] >= 2:
            radius = float(np.linalg.norm(points[0, :2]))
        return radius, int(getattr(path, "ray_index", 0) or 0)

    return min(ray_paths, key=_score)


def _snapshot_stats(path: Path) -> dict[str, object]:
    try:
        from PIL import Image
    except Exception:
        return {"path": str(path), "bytes": path.stat().st_size, "pixel_check": "PIL unavailable"}
    image = Image.open(path).convert("RGB")
    pixels = np.asarray(image, dtype=np.uint8)
    non_white = np.any(pixels < 245, axis=2)
    colored = (
        (np.abs(pixels[:, :, 0].astype(int) - pixels[:, :, 1].astype(int)) > 8)
        | (np.abs(pixels[:, :, 1].astype(int) - pixels[:, :, 2].astype(int)) > 8)
        | (np.abs(pixels[:, :, 0].astype(int) - pixels[:, :, 2].astype(int)) > 8)
    )
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "size": [int(image.width), int(image.height)],
        "non_white_pixels": int(np.count_nonzero(non_white)),
        "colored_pixels": int(np.count_nonzero(colored)),
    }


def _state_report(inspector: Kraken3DInspector, label: str, image_path: Path) -> dict[str, object]:
    scene_bundle = getattr(inspector, "_current_scene_bundle", None)
    ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
    central = _central_path(ray_paths)
    statuses = Counter(str(ray_path_terminal_status_from_events(path) or "unknown") for path in ray_paths)
    events = Counter(
        (_event_face_id(event), _event_action(event))
        for path in ray_paths
        for event in _surface_events(path)
    )
    sequences = Counter(_surface_sequence(path) for path in ray_paths)
    path_signatures = [_path_signature(path) for path in sorted(ray_paths, key=lambda item: int(getattr(item, "ray_index", 0) or 0))]
    return {
        "label": label,
        "sampling_mode": str(getattr(inspector, "_last_refresh_sampling_mode", "") or ""),
        "path_count": len(ray_paths),
        "terminal_counts": dict(sorted(statuses.items())),
        "central_path": _path_signature(central),
        "path_signatures": path_signatures,
        "surface_event_counts": {f"{face}:{action}": count for (face, action), count in sorted(events.items())},
        "surface_sequence_counts": {" -> ".join(sequence): count for sequence, count in sorted(sequences.items())},
        "image": _snapshot_stats(image_path),
    }


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
        initial = _state_report(inspector, "initial_open3d", initial_image)
        _assert_state_ok(initial)

        inspector._refresh_trace_now_scene("five-penta visual guard")
        _settle(inspector, 0.35)
        inspector.set_camera_preset("iso")
        trace_now_image = _save_vtk_snapshot(inspector, output_dir / "after_trace_now.png")
        trace_now = _state_report(inspector, "after_trace_now", trace_now_image)
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
