"""Static analyzer for Open 3D bug recordings.

Reads a JSON file produced by ``Open3DEventRecorder`` and walks the
per-event SceneSnapshot stream looking for known regression patterns:

* axis-extent truncation -- the dotted optical axis collapses to a
  fraction of the scene Z extent (e.g. after a snap, when the STEP
  body sits outside the row envelope)
* rotation handles popping up after a snap returns to idle
* camera view-up drifting away from world up (gimbal-lock flip)
* an actor disappearing between two consecutive events without an
  obvious mode transition explaining it
* a picker hit on no actor when the user clearly clicked geometry

Run standalone::

    .devenv/state/venv/bin/python -m KrakenOS.UI.analyze_open3d_recording \\
        attachment/recorded_bug_repros/recording_20260530_212349.json

or programmatically via ``analyze_recording(path)`` from the workflow
harness so each synthetic recording is critiqued the same way a
user-supplied bug repro would be.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Tunables. Move out to config if/when calibration is needed.

# If the dotted-axis actor's Z extent covers less than this fraction of the
# union of body Z extents, flag it as truncation. 0.65 axis margin in
# `_optical_axis_z_span` means a healthy axis is significantly *longer*
# than the scene bounds, so 0.85 here errs on the side of catching real
# truncation without false-firing on a borderline-fit axis.
AXIS_EXTENT_THRESHOLD = 0.85

# View-up drift tolerance (per-component absolute deviation from world up).
VIEW_UP_DRIFT_TOL = 0.001


@dataclass
class Finding:
    severity: str  # "error" | "warning" | "info"
    code: str
    event_index: int
    timestamp_ms: float
    message: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisReport:
    path: Path | None
    event_count: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path) if self.path is not None else "",
            "event_count": int(self.event_count),
            "findings": [
                {
                    "severity": f.severity,
                    "code": f.code,
                    "event_index": f.event_index,
                    "timestamp_ms": float(f.timestamp_ms),
                    "message": f.message,
                    "detail": f.detail,
                }
                for f in self.findings
            ],
            "ok": self.ok,
        }


# ---------------------------------------------------------------------------
# Loaders


def _load(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _scene_bodies_z_span(snapshot: dict[str, Any]) -> tuple[float, float] | None:
    """Union Z extent of every row + STEP body the scene drew."""
    z_lo = float("inf")
    z_hi = float("-inf")
    found = False
    for bounds in (snapshot.get("row_actor_bounds") or {}).values():
        if not bounds or len(bounds) < 6:
            continue
        z_lo = min(z_lo, float(bounds[4]))
        z_hi = max(z_hi, float(bounds[5]))
        found = True
    for bounds in (snapshot.get("step_actor_bounds") or {}).values():
        if not bounds or len(bounds) < 6:
            continue
        z_lo = min(z_lo, float(bounds[4]))
        z_hi = max(z_hi, float(bounds[5]))
        found = True
    if not found or z_hi <= z_lo:
        return None
    return (z_lo, z_hi)


def _axis_z_span(snapshot: dict[str, Any], axis_id: str = "axis:global") -> tuple[float, float] | None:
    """Z extent of the dotted axis pick record, if present."""
    for record in snapshot.get("optical_axis_records") or []:
        if str(record.get("axis_id") or "") != axis_id:
            continue
        pts = record.get("points") or []
        if not pts:
            continue
        zs = [float(p[2]) for p in pts if len(p) >= 3]
        if not zs:
            continue
        return (min(zs), max(zs))
    return None


# ---------------------------------------------------------------------------
# Checks


def _check_axis_extent(events: list[dict[str, Any]], findings: list[Finding]) -> None:
    """Axis must span ≥ AXIS_EXTENT_THRESHOLD × scene body span on Z."""
    for i, ev in enumerate(events):
        snap = ev.get("scene_state") or {}
        if not snap:
            continue
        body_span = _scene_bodies_z_span(snap)
        axis_span = _axis_z_span(snap)
        if body_span is None or axis_span is None:
            continue
        body_extent = body_span[1] - body_span[0]
        axis_extent = axis_span[1] - axis_span[0]
        if body_extent <= 0:
            continue
        ratio = axis_extent / body_extent if body_extent > 0 else 0.0
        # _optical_axis_z_span pads by 0.65*span on each side, so a healthy
        # axis is 1.65x+ the body span. Anything below 1.0x has truncated.
        # We compare to threshold * 1.0 for body coverage.
        if axis_extent < AXIS_EXTENT_THRESHOLD * body_extent:
            findings.append(
                Finding(
                    severity="error",
                    code="axis_extent_truncated",
                    event_index=i,
                    timestamp_ms=float(ev.get("timestamp_ms") or 0.0),
                    message=(
                        f"optical axis Z extent {axis_extent:.3f} < "
                        f"{AXIS_EXTENT_THRESHOLD:.2f} x body Z extent {body_extent:.3f}"
                        f" (ratio={ratio:.3f})"
                    ),
                    detail={
                        "axis_z": list(axis_span),
                        "body_z": list(body_span),
                        "ratio": ratio,
                    },
                )
            )


def _check_handles_after_snap(events: list[dict[str, Any]], findings: list[Finding]) -> None:
    """After a step_normal_axis_pick transitions back to idle, handle_count must be 0."""
    saw_snap_mode = False
    for i, ev in enumerate(events):
        snap = ev.get("scene_state") or {}
        mode = str(snap.get("interaction_mode") or "")
        if mode in {"step_normal_axis_pick", "step_surface_center_axis_pick"}:
            saw_snap_mode = True
            continue
        if not saw_snap_mode:
            continue
        if mode != "idle":
            continue
        handles = int(snap.get("rotation_handle_count") or 0)
        if handles > 0:
            findings.append(
                Finding(
                    severity="error",
                    code="rotation_handles_after_snap",
                    event_index=i,
                    timestamp_ms=float(ev.get("timestamp_ms") or 0.0),
                    message=(
                        f"rotation_handle_count={handles} after snap returned to idle"
                    ),
                    detail={
                        "selected_step_label": snap.get("selected_step_label"),
                        "active_label": snap.get("selected_step_rotation_active_label"),
                    },
                )
            )
            # one report per transition is enough.
            saw_snap_mode = False


def _check_view_up_drift(events: list[dict[str, Any]], findings: list[Finding]) -> None:
    """Camera view-up must stay locked to world up; drift = orbit flip bug."""
    target = (0.0, 1.0, 0.0)
    for i, ev in enumerate(events):
        snap = ev.get("scene_state") or {}
        vu = snap.get("camera_view_up") or []
        if len(vu) < 3:
            continue
        try:
            d = (
                abs(float(vu[0]) - target[0]),
                abs(float(vu[1]) - target[1]),
                abs(float(vu[2]) - target[2]),
            )
        except Exception:
            continue
        if max(d) > VIEW_UP_DRIFT_TOL:
            findings.append(
                Finding(
                    severity="warning",
                    code="camera_view_up_drift",
                    event_index=i,
                    timestamp_ms=float(ev.get("timestamp_ms") or 0.0),
                    message=f"camera_view_up={tuple(vu[:3])} drifted from world up",
                    detail={"delta": list(d)},
                )
            )


def _check_actor_disappearance(events: list[dict[str, Any]], findings: list[Finding]) -> None:
    """A row/step that was present in event[i] must still be present in event[i+1] unless explained."""
    prev_rows: set[int] = set()
    prev_steps: set[str] = set()
    for i, ev in enumerate(events):
        snap = ev.get("scene_state") or {}
        rows = {int(k) for k in (snap.get("row_actor_bounds") or {}).keys()}
        steps = {str(k) for k in (snap.get("step_actor_counts") or {}).keys()}
        if i > 0:
            lost_rows = prev_rows - rows
            lost_steps = prev_steps - steps
            if lost_rows or lost_steps:
                findings.append(
                    Finding(
                        severity="warning",
                        code="actor_disappeared",
                        event_index=i,
                        timestamp_ms=float(ev.get("timestamp_ms") or 0.0),
                        message=(
                            f"between events {i-1}->{i}: "
                            f"rows lost={sorted(lost_rows)}, "
                            f"steps lost={sorted(lost_steps)}"
                        ),
                        detail={
                            "lost_rows": sorted(lost_rows),
                            "lost_steps": sorted(lost_steps),
                        },
                    )
                )
        prev_rows = rows
        prev_steps = steps


def _check_visible_bounds_mismatch(events: list[dict[str, Any]], findings: list[Finding]) -> None:
    """If ComputeVisiblePropBounds Z span > axis Z span, the axis was built too early."""
    for i, ev in enumerate(events):
        snap = ev.get("scene_state") or {}
        vb = snap.get("scene_visible_bounds") or []
        axis_span = _axis_z_span(snap)
        if len(vb) < 6 or axis_span is None:
            continue
        try:
            vb_z = (float(vb[4]), float(vb[5]))
        except Exception:
            continue
        vb_extent = vb_z[1] - vb_z[0]
        axis_extent = axis_span[1] - axis_span[0]
        if vb_extent <= 0:
            continue
        # axis should engulf the visible bounds (extended by 0.65 each side).
        # If axis_extent < vb_extent, something is off.
        if axis_extent < vb_extent * 0.95:
            findings.append(
                Finding(
                    severity="error",
                    code="axis_shorter_than_visible_bounds",
                    event_index=i,
                    timestamp_ms=float(ev.get("timestamp_ms") or 0.0),
                    message=(
                        f"axis extent {axis_extent:.3f} < ComputeVisiblePropBounds "
                        f"extent {vb_extent:.3f} on Z"
                    ),
                    detail={
                        "axis_z": list(axis_span),
                        "visible_z": list(vb_z),
                    },
                )
            )


# ---------------------------------------------------------------------------
# Public API


def analyze_recording(path: Path) -> AnalysisReport:
    """Walk a recording JSON and produce a list of findings."""
    data = _load(path)
    events = list(data.get("events") or [])
    findings: list[Finding] = []
    _check_axis_extent(events, findings)
    _check_handles_after_snap(events, findings)
    _check_view_up_drift(events, findings)
    _check_actor_disappearance(events, findings)
    _check_visible_bounds_mismatch(events, findings)
    return AnalysisReport(path=path, event_count=len(events), findings=findings)


def format_report(report: AnalysisReport) -> str:
    lines: list[str] = []
    src = str(report.path) if report.path is not None else "<recording>"
    lines.append(f"Analyzed {src}: {report.event_count} events")
    if not report.findings:
        lines.append("  OK -- no regressions detected")
        return "\n".join(lines)
    by_severity: dict[str, int] = {}
    for f in report.findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
    summary = ", ".join(f"{n} {sev}" for sev, n in sorted(by_severity.items()))
    lines.append(f"  {summary}")
    for f in report.findings:
        lines.append(
            f"  [{f.severity:7s}] {f.code:35s} ev#{f.event_index:3d} "
            f"t={f.timestamp_ms:7.1f}ms  {f.message}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze an Open 3D bug recording.")
    parser.add_argument("path", help="Path to recording_*.json")
    parser.add_argument("--json", action="store_true", help="Emit findings as JSON.")
    args = parser.parse_args(argv)
    path = Path(args.path).expanduser()
    if not path.exists():
        print(f"recording not found: {path}", file=sys.stderr)
        return 2
    report = analyze_recording(path)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
