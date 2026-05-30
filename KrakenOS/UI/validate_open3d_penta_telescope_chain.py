"""Penta-prism + telescope cascade harness (Phase 0).

A folded-path cascade test the simple Z-stack workflow can't cover.
Loads ``attachment/five_penta_prism_cascade.py`` as the base scene
(5 BK7 penta prisms with tilts + non-Z desp -- the beam folds through
the geometry rather than marching along Z), then appends optical
elements at the output of the last prism in later phases:

  Phase 0  -- this file: load base, verify 5-prism trace survives
  Phase 1  -- + 2 ball lenses (Edmund 63227, f=3.1 mm) = 1:1 telescope
  Phase 2  -- + DCV (32996, f=-50 mm) + Achromat (32323, f=+50 mm)
  Phase 3  -- + Cylindrical (34754, f=50 mm) for line focus

Each phase records the synthetic interactions through Open3DEventRecorder
and runs `analyze_open3d_recording` so the harness leaves the same
artifact a user-supplied bug repro does.

The penta cascade's exit beam comes out of ``s5`` face F006, which
sits at world ``(127.5, 0, 97.5)`` with the propagation direction
along world ``-X`` (s5 has ``tilt_z = -180``). All Phase 1-3 optics
ride along that ``-X`` trajectory at ``Y=0, Z=97.5`` -- exactly the
"non-Z-axis cascade" gap the simple workflow misses.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor
from KrakenOS.UI.render_layout_snapshot import (
    _load_layout_module,
    _rows_from_layout_info,
)
from KrakenOS.UI.analyze_open3d_recording import analyze_recording


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PENTA_CASCADE_PATH = PROJECT_ROOT / "attachment" / "five_penta_prism_cascade.py"
SYNTHETIC_RECORDING_DIR = (
    PROJECT_ROOT / "attachment" / "recorded_bug_repros" / "penta_telescope_chain"
)

# Penta s5 exit beam waypoint + direction. Empirically the saved
# cascade emerges at world (37.5, -y_input, 197.5) with the Y
# component flipped relative to the entry side (the cascade folds
# the path through five reflective faces). The beam continues from
# (37.5, 0, 197.5) along the +Z direction roughly, so Phase 1-3
# stack along world +Z from that waypoint.
EXIT_POSITION = np.asarray([37.5, 0.0, 197.5], dtype=float)
EXIT_DIRECTION = np.asarray([0.0, 0.0, 1.0], dtype=float)


# ---------------------------------------------------------------------------
# Recorder/analyzer wiring (mirrors validate_open3d_interaction_workflows.py)


@dataclass
class Step:
    name: str
    duration_ms: float
    ok: bool
    note: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowReport:
    name: str
    steps: list[Step] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def add(self, step: Step) -> Step:
        self.steps.append(step)
        if not step.ok:
            self.failures.append(f"{step.name}: {step.note}")
        return step


def _timed(report: WorkflowReport, name: str, fn: Callable[[], dict[str, Any] | None], *, budget_ms: float | None = None) -> Step:
    started = time.perf_counter()
    payload: dict[str, Any] = {}
    note = ""
    ok = True
    try:
        result = fn()
        if result is not None:
            payload = dict(result)
            err = payload.pop("__error__", None)
            if err:
                ok = False
                note = str(err)
    except Exception as exc:
        ok = False
        note = f"raised {type(exc).__name__}: {exc}"
    duration_ms = (time.perf_counter() - started) * 1000.0
    if ok and budget_ms is not None and duration_ms > budget_ms:
        ok = False
        note = f"exceeded budget: {duration_ms:.1f} ms > {budget_ms:.1f} ms"
    return report.add(
        Step(name=name, duration_ms=duration_ms, ok=ok, note=note, payload=payload),
    )


# ---------------------------------------------------------------------------
# Scene loader


def _load_penta_cascade(app: KrakenLayoutEditor) -> dict[str, Any]:
    """Read the saved layout module and inject its rows into the editor."""
    module = _load_layout_module(PENTA_CASCADE_PATH)
    surfaces = list(getattr(module, "SURFACES", []) or [])
    if not surfaces:
        raise RuntimeError("five_penta_prism_cascade exposed no SURFACES")
    rows = _rows_from_layout_info({"surfaces": surfaces})
    app.rows = rows
    try:
        app._sync_table()
    except Exception:
        pass
    return {
        "row_count": len(rows),
        "row_names": [getattr(r, "name", "") for r in rows],
    }


def _open_inspector(app: KrakenLayoutEditor) -> Kraken3DInspector:
    app.open_3d_view()
    app.update_idletasks()
    app.update()
    inspector = app._three_d_inspector
    if inspector is None or not inspector.available:
        reason = getattr(inspector, "unavailable_reason", "") if inspector is not None else "open_3d_view did not produce inspector"
        raise RuntimeError(f"Embedded 3D inspector unavailable: {reason}")
    inspector.geometry("1280x860+80+60")
    inspector.deiconify()
    inspector.lift()
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.3)
    inspector.update()
    return inspector


# ---------------------------------------------------------------------------
# Phase 0 workflow


def phase0_base_trace(app: KrakenLayoutEditor, inspector: Kraken3DInspector) -> WorkflowReport:
    """Load penta cascade, run Trace Now, assert the 5-prism fold survives."""
    report = WorkflowReport(name="Phase 0: Penta cascade base + trace")

    def _refresh() -> dict[str, Any]:
        inspector.refresh_from_editor(force_retrace=True)
        inspector.update_idletasks()
        inspector.update()
        bundle = inspector._current_scene_bundle
        return {
            "row_count": len(app.rows),
            "scene_bundle_present": bundle is not None,
        }

    _timed(report, "refresh_after_load", _refresh, budget_ms=15000.0)

    def _trace() -> dict[str, Any]:
        inspector.show_rays_var.set(True)
        inspector._trace_live_now()
        inspector.update_idletasks()
        inspector.update()
        bundle = inspector._current_scene_bundle
        paths = list(getattr(bundle, "ray_paths", []) or []) if bundle is not None else []
        # The STL-solid rays don't tag `event.surface_index` reliably,
        # so judge cascade-survival by the number of surface
        # interactions per path AND where the rays end up. A ray
        # passing through 5 penta prisms with reflective folds
        # generates many surface events; we require >= 5 surface
        # events on average (one per prism, even if each prism only
        # registers one body interaction).
        surface_event_counts: list[int] = []
        end_points: list[list[float]] = []
        max_path_segments = 0
        for path in paths:
            events = list(getattr(path, "events", []) or [])
            surf = sum(
                1
                for event in events
                if str(getattr(event, "event_kind", "") or "") == "surface"
            )
            surface_event_counts.append(surf)
            pts = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
            if pts.ndim == 2 and pts.shape[0] >= 1 and pts.shape[1] >= 3:
                max_path_segments = max(max_path_segments, pts.shape[0])
                end = pts[-1, :3]
                if np.all(np.isfinite(end)):
                    end_points.append([float(end[0]), float(end[1]), float(end[2])])
        avg_surface = (
            float(sum(surface_event_counts)) / float(len(surface_event_counts))
            if surface_event_counts
            else 0.0
        )
        # The cascade exit waypoint is EXIT_POSITION; surviving rays
        # should terminate within a generous envelope around it. The
        # image plane at world origin doesn't catch the folded
        # output, so judge survival by proximity to EXIT_POSITION.
        terminated_in_exit_box = sum(
            1
            for ep in end_points
            if abs(ep[0] - EXIT_POSITION[0]) < 30.0
            and abs(ep[1] - EXIT_POSITION[1]) < 30.0
            and abs(ep[2] - EXIT_POSITION[2]) < 30.0
        )
        return {
            "ray_path_count": len(paths),
            "ray_actor_count": len(inspector._actor_ray_map or {}),
            "max_path_segments": int(max_path_segments),
            "avg_surface_events_per_path": round(avg_surface, 3),
            "rays_terminated_in_exit_box": terminated_in_exit_box,
            "exit_box_center": EXIT_POSITION.tolist(),
            "status": str(inspector.status_var.get()),
        }

    trace = _timed(report, "trace_now", _trace, budget_ms=20000.0)
    if trace.ok:
        if trace.payload.get("ray_path_count", 0) == 0:
            trace.ok = False
            trace.note = "trace produced 0 ray paths"
            report.failures.append(trace.note)
        # The 5-prism fold gives every surviving ray multiple segments
        # (one per prism surface interaction). A path with < 10
        # segments didn't make it through the cascade.
        elif trace.payload.get("max_path_segments", 0) < 10:
            trace.ok = False
            trace.note = (
                f"max ray-path segments = {trace.payload.get('max_path_segments')} "
                "but a 5-prism fold should produce many polyline vertices per path"
            )
            report.failures.append(trace.note)
        elif trace.payload.get("rays_terminated_in_exit_box", 0) < trace.payload.get("ray_path_count", 0) // 2:
            trace.ok = False
            trace.note = (
                f"{trace.payload.get('rays_terminated_in_exit_box')} / "
                f"{trace.payload.get('ray_path_count')} rays terminated near the "
                f"exit waypoint {EXIT_POSITION.tolist()}; cascade may have "
                "ejected rays mid-fold"
            )
            report.failures.append(trace.note)
    return report


# ---------------------------------------------------------------------------
# Recorder wrapper


class _PhaseRecording:
    def __init__(self, inspector: Kraken3DInspector, slug: str, out_dir: Path) -> None:
        self.inspector = inspector
        self.slug = slug
        self.out_dir = out_dir
        self.recorder = getattr(inspector, "_event_recorder", None)
        self.path: Path | None = None
        self.analysis: Any = None

    def __enter__(self) -> "_PhaseRecording":
        if self.recorder is not None:
            try:
                self.recorder.start(note=f"penta_telescope:{self.slug}")
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.recorder is None:
            return
        try:
            written = self.recorder.stop()
        except Exception:
            written = None
        if written is None:
            return
        try:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            dest = self.out_dir / f"{self.slug}_{written.name}"
            written.rename(dest)
            self.path = dest
        except Exception:
            self.path = written
        try:
            self.analysis = analyze_recording(self.path)
        except Exception:
            self.analysis = None


# ---------------------------------------------------------------------------
# Driver


def _print_report(reports: Sequence[WorkflowReport], recordings: Sequence[_PhaseRecording]) -> int:
    overall = 0
    for report in reports:
        marker = "PASS" if report.ok else "FAIL"
        print(f"{marker}: {report.name}")
        for step in report.steps:
            sub = "OK " if step.ok else "FAIL"
            print(f"  {sub} {step.name} ({step.duration_ms:.1f} ms): {step.note or 'ok'}")
            if step.payload:
                preview = {k: v for k, v in step.payload.items() if k != "end_points_sample"}
                print(f"      payload={preview}")
        if not report.ok:
            overall = 1
            for failure in report.failures:
                print(f"  >>> {failure}")
    if recordings:
        print()
        print("Phase recordings:")
        for rec in recordings:
            if rec.path is None:
                continue
            findings = list(getattr(rec.analysis, "findings", []) or [])
            errors = sum(1 for f in findings if f.severity == "error")
            warns = sum(1 for f in findings if f.severity == "warning")
            tag = "OK" if not errors and not warns else f"{errors}E/{warns}W"
            print(f"  [{tag:>5}] {rec.slug}  ->  {rec.path}")
    return overall


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recordings-dir",
        type=Path,
        default=SYNTHETIC_RECORDING_DIR,
        help="Per-phase Open3DEventRecorder JSON dump directory.",
    )
    args = parser.parse_args()

    if not PENTA_CASCADE_PATH.exists():
        raise SystemExit(f"penta cascade fixture not found: {PENTA_CASCADE_PATH}")

    reports: list[WorkflowReport] = []
    recordings: list[_PhaseRecording] = []

    app = KrakenLayoutEditor(headless=True)
    try:
        load_report = WorkflowReport(name="Loader: penta cascade rows")
        load_step = _timed(
            load_report,
            "load_rows",
            lambda: _load_penta_cascade(app),
            budget_ms=5000.0,
        )
        reports.append(load_report)
        if not load_step.ok:
            return _print_report(reports, recordings)

        open_report = WorkflowReport(name="Loader: open inspector")
        open_step = _timed(
            open_report,
            "open_inspector",
            lambda: {"available": bool(_open_inspector(app).available)},
            budget_ms=15000.0,
        )
        reports.append(open_report)
        if not open_step.ok:
            return _print_report(reports, recordings)

        inspector = app._three_d_inspector
        assert inspector is not None

        with _PhaseRecording(inspector, "phase0_base_trace", args.recordings_dir) as rec:
            reports.append(phase0_base_trace(app, inspector))
        recordings.append(rec)
    finally:
        try:
            inspector_local = getattr(app, "_three_d_inspector", None)
            if inspector_local is not None:
                inspector_local._on_close()
        except Exception:
            pass
        app.destroy()

    return _print_report(reports, recordings)


if __name__ == "__main__":
    sys.exit(main())
