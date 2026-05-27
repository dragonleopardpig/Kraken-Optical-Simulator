"""Replay an Open 3D CAD import/selection workflow and report timing.

This diagnostic is intended for Xvfb or a real display. It follows the same
high-level path a user reported: load the Machine Vision 150 mm layout, open
Open 3D, hide rays/thickness overlays, add an optical STEP component, select it,
simulate a small hidden-ray STEP drop, then deselect it. Structured timings are
written to the Open 3D timing JSONL log and summarized at the end.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_timing import open3d_timing_log_path, reset_open3d_timing_log


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STEP = PROJECT_ROOT / "attachment" / "Lens" / "Aspherized_Achromatic_Lenses" / "step_49665.step"
DEFAULT_LAYOUT = "Machine Vision 150Mm Measured"


def _drain_tk(widget, *, seconds: float = 0.1) -> None:
    end = time.perf_counter() + max(float(seconds), 0.0)
    while time.perf_counter() < end:
        widget.update_idletasks()
        widget.update()
        time.sleep(0.01)


def _read_timing_events(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _timing_summary(path: Path) -> dict[str, object]:
    events = _read_timing_events(path)
    durations = [
        row
        for row in events
        if isinstance(row.get("duration_ms"), (int, float))
    ]
    durations.sort(key=lambda row: float(row.get("duration_ms", 0.0)), reverse=True)
    return {
        "log_path": str(path),
        "event_count": len(events),
        "duration_event_count": len(durations),
        "top_durations": [
            {
                "event": row.get("event"),
                "duration_ms": row.get("duration_ms"),
                "status": row.get("status"),
                "source_path": row.get("source_path"),
                "stl_path": row.get("stl_path"),
                "handler": row.get("handler"),
            }
            for row in durations[:20]
        ],
    }


def run_replay(layout_name: str, step_path: Path) -> dict[str, object]:
    timing_path = reset_open3d_timing_log(reason="diagnose_open3d_action_timing")
    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry("1500x920+20+20")
        app.auto_save_plot_var.set(False)
        app.load_layout_by_name(layout_name, refresh=False)
        app.show_physical_distances_var.set(False)
        app.open_3d_view()
        _drain_tk(app, seconds=0.3)
        inspector = app._three_d_inspector
        if inspector is None or not inspector.available:
            reason = getattr(inspector, "unavailable_reason", "") if inspector is not None else "inspector did not open"
            raise RuntimeError(f"Open 3D unavailable: {reason}")
        inspector.show_rays_var.set(False)
        inspector.show_detector_overlays_var.set(False)
        inspector.show_terminal_diagnostics_var.set(False)
        inspector.refresh_from_editor()
        _drain_tk(inspector, seconds=0.2)

        app.imported_optical_step_path = step_path
        app.optical_step_rotation_x_deg = 0.0
        app.optical_step_rotation_y_deg = 0.0
        app.optical_step_rotation_z_deg = 0.0
        app.optical_step_axis_offset_xy = (0.0, 0.0)
        app.optical_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        app.select_step_component("optical")
        app._invalidate_preview_scene_trace()

        inspector.refresh_from_editor()
        inspector.show_step_rotation_handler("optical")
        _drain_tk(inspector, seconds=0.2)
        drop_state = inspector._new_step_carry_motion_state("optical")
        if drop_state is not None:
            drop_state["applied_steps"] = 1
            app.optical_step_placement_offset_xyz = (1.0, 0.0, 0.0)
            inspector._finish_step_carry_drag(drop_state)
            _drain_tk(inspector, seconds=0.2)
        inspector._clear_open3d_selection(render=True)
        _drain_tk(inspector, seconds=0.2)

        summary = _timing_summary(timing_path)
        summary.update(
            {
                "layout": layout_name,
                "step_path": str(step_path),
                "step_size": int(step_path.stat().st_size) if step_path.exists() else None,
                "actor_counts": inspector._debug_actor_counts(),
                "status": str(inspector.status_var.get()),
            }
        )
        return summary
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", default=DEFAULT_LAYOUT, help="Common layout name to load.")
    parser.add_argument("--step", type=Path, default=DEFAULT_STEP, help="Optical STEP file to add.")
    parser.add_argument("--output", type=Path, help="Optional JSON summary path.")
    args = parser.parse_args(argv)

    step_path = Path(args.step).expanduser().resolve()
    report = run_replay(str(args.layout), step_path)
    text = json.dumps(report, indent=2, sort_keys=True, default=str)
    print(text)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
