"""bugs/0750: audit a scene's rows against their AUTHORED placement.

bugs/0748 changed the SUM of the two lens sliding gaps in `om05a_folded_80mm.py`. Every row after
those gaps inherits the change through its station, so the whole arm-B block slid 8.54 mm while
arm A stayed put -- a "haywire prism assembly", misaligned mirrors and a sideways image plane, from
one two-row edit. bugs/0749 reverted it and established the rule: **the gap SUM must stay
invariant**, which is exactly why the bugs/0719 FOV solve moves a thickness PAIR.

This module makes that class of breakage cheap to detect. A promoted CAD row carries its authored
world placement in ``advanced["StepOverlayPromotion"]["center_world"]``; comparing that with the
live follower-walk pose gives a per-row drift.

Why this and not an arm A/B symmetry check (the first design, rejected on measurement):

* Pairing rows by an " A"/" B" name suffix invents a relationship the codebase nowhere else uses,
  and misfires on any unrelated pair ("Filter A"/"Filter B").
* The absolute test ``z_a + z_b == 2 * split_plane`` is red AT REST on historical scenes that carry
  1.0-2.9 mm of authored slop, so no single tolerance is both quiet and useful.
* A "spread" formulation is blind to common-mode drift: move the object row and every pair slides
  together, leaving the spread at 0.000000 while every mirror has moved.

The pinned drift has none of those problems: it needs no pairing, no split plane, and reads
**0.000000 mm** on a healthy scene against **8.5400 mm** for the real defect.

Use the DELTA form (:func:`compare_drifts`) when editing a scene: an absolute reading is red on
rows whose authored snapshot is merely stale -- `om05a_folded_80mm.py` row 16 "RA mirror 2 (40 mm)"
sits at 545.39 mm from an authored/live sign difference that predates all of this. The delta form
is silent by construction on an unmoved scene and still shows 0.0000 -> 8.5400 on the break.
"""

from __future__ import annotations

import numpy as np

# the walk accumulates ~1e-10 mm over a 20-row chain; a thickness round-trip is exact
NOISE_FLOOR_MM = 1.0e-6
DEFAULT_TOL_MM = 1.0e-3


def _promoted_center(row):
    """The row's AUTHORED world centre, or None when it carries no promotion snapshot."""
    advanced = row.advanced if isinstance(getattr(row, "advanced", None), dict) else {}
    promo = advanced.get("StepOverlayPromotion")
    if not isinstance(promo, dict):
        return None
    raw = promo.get("center_world")
    if raw is None:
        return None
    try:
        centre = np.asarray(raw, dtype=float).reshape(3)
    except (TypeError, ValueError):
        return None
    return centre if np.all(np.isfinite(centre)) else None


def pinned_placement_drifts(rows, poses=None):
    """Per-row drift of the live follower-walk pose from the row's AUTHORED placement.

    Returns a list of dicts: ``{"row", "name", "authored", "live", "drift_mm"}``, one per row that
    carries both a promotion snapshot and a walked pose. Rows carrying a snapshot but NO pose are
    reported with ``live=None`` and ``drift_mm=None`` -- unmeasurable, never silently dropped.
    """
    rows = list(rows or [])
    if poses is None:
        from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides

        poses = optical_solid_output_port_pose_overrides(None, rows)
    poses = poses or {}
    out = []
    for index, row in enumerate(rows):
        authored = _promoted_center(row)
        if authored is None:
            continue
        pose = poses.get(index)
        live = None
        if isinstance(pose, dict) and pose.get("center") is not None:
            try:
                candidate = np.asarray(pose["center"], dtype=float).reshape(3)
                if np.all(np.isfinite(candidate)):
                    live = candidate
            except (TypeError, ValueError):
                live = None
        out.append({
            "row": int(index),
            "name": str(getattr(row, "name", "") or ""),
            "authored": [float(v) for v in authored],
            "live": None if live is None else [float(v) for v in live],
            "drift_mm": None if live is None else float(np.linalg.norm(live - authored)),
        })
    return out


def compare_drifts(before, after, tol_mm=DEFAULT_TOL_MM):
    """Rows whose drift INCREASED between two readings -- the edit-safety check.

    ``before``/``after`` are :func:`pinned_placement_drifts` results. A row is reported when its
    drift grew by more than ``tol_mm``; a row that was already stale (om05a's row 16) stays silent
    unless the edit made it worse. Returns records sorted worst-first.
    """
    prior = {r["row"]: r for r in (before or [])}
    moved = []
    for record in after or []:
        was = prior.get(record["row"])
        if was is None or was.get("drift_mm") is None or record.get("drift_mm") is None:
            continue
        delta = float(record["drift_mm"]) - float(was["drift_mm"])
        if delta > float(tol_mm):
            moved.append({
                "row": record["row"],
                "name": record["name"],
                "before_mm": float(was["drift_mm"]),
                "after_mm": float(record["drift_mm"]),
                "moved_mm": delta,
            })
    moved.sort(key=lambda r: -r["moved_mm"])
    return moved


def format_drift_report(records, tol_mm=DEFAULT_TOL_MM):
    """Human-readable table for a CLI or a debug log."""
    lines = [f"{'row':>4}  {'name':32s} {'drift mm':>12}  authored -> live"]
    for r in records or []:
        if r.get("drift_mm") is None:
            lines.append(f"{r['row']:4d}  {r['name'][:32]:32s} {'unmeasurable':>12}  (no walked pose)")
            continue
        flag = "  <-- moved" if r["drift_mm"] > tol_mm else ""
        lines.append(
            f"{r['row']:4d}  {r['name'][:32]:32s} {r['drift_mm']:12.6f}  "
            f"{[round(v, 3) for v in r['authored']]} -> {[round(v, 3) for v in r['live']]}{flag}"
        )
    return "\n".join(lines)


def format_moved_report(moved):
    """Human-readable summary of :func:`compare_drifts`."""
    if not moved:
        return "no promoted row moved from its authored placement"
    lines = [f"{len(moved)} row(s) MOVED from their authored placement:"]
    for r in moved:
        lines.append(
            f"  row {r['row']:3d} {r['name'][:34]:36s} {r['before_mm']:.4f} -> {r['after_mm']:.4f} mm"
            f"  (moved {r['moved_mm']:+.4f})"
        )
    return "\n".join(lines)
