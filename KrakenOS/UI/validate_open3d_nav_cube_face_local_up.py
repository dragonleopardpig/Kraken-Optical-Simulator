#!/usr/bin/env python3
"""Display-free guard for bugs/0321: a navigation-cube FACE or EDGE click keeps the CURRENT view's
roll, SNAPPED to the nearest of FOUR clean orientations about the pick's sight axis -- the same
FreeCAD NaviCube ``getNearestOrientation`` port that bugs/0257 already applies to CORNERS (nearest
of six), now extended to faces/edges (nearest of four).

Why (user, 2026-07-16, flags flag_20260716_080215_410 + flag_20260716_080327_789):
  "After clicking the 'TOP', it doesn't respect the upside down 'TOP'. Can make all section at the
  Nav Cube respect the current orientation when clicked?" Before 0321 a face/edge click forced the
  canonical absolute up (TOP always snapped to +X up), so clicking TOP while you were looking at an
  upside-down TOP flipped the picture right-side-up -- jarring. FreeCAD's NaviCube instead snaps the
  clicked face to the nearest clean roll of the view you already had; 0321 matches that.

The fix (:func:`nav_cube_orientation.nearest_orientation_up`, steps=4) is IDENTICAL to the corner
path except the roll grid is ``2*pi/4`` = 90 deg (a face/edge has four clean rolls, a corner six).
The inspector (`_apply_navigation_cube_orientation`) now calls it for EVERY pick kind with
``steps=6 if kind == "corner" else 4``.

What it checks (no display required, pure math + source contract):
  A. Invariant across many (current axis, current up) samples for every FACE and EDGE: the result is
     unit, perpendicular to the pick sight line, and a CLEAN 90-deg multiple roll from the standard up.
  B. Nearest-of-4 snap table: rolling the standard by k deg about the sight axis and clicking snaps
     to the nearest 90-deg gridpoint (output within 45 deg of k AND a 90-multiple).
  C. Idempotence: a current view that IS one of the four clean rolls (0/90/180/270) comes back
     byte-for-byte -- the roll is preserved, not reset -- for every face and edge.
  D. The user regression -- "upside-down TOP stays upside-down": clicking the TOP face while the live
     up is -Z (a quarter-turn) returns -Z, and while the up is -X (fully flipped) returns -X. It must
     NOT snap to the canonical +X. Symmetric spot-checks for FRONT and RIGHT.
  E. Degenerate fallbacks: an antiparallel current axis, or a current up parallel to the sight line,
     still yields a finite unit vector perpendicular to the sight line.
  F. Source contract: _apply_navigation_cube_orientation applies the snap for face/edge/corner
     (``kind in ("face", "edge", "corner")``) and uses ``steps=6 if kind == "corner" else 4``.
"""
from __future__ import annotations

import importlib.util
from itertools import product
from pathlib import Path

import numpy as np

from KrakenOS.UI.services.nav_cube_orientation import (
    nearest_orientation_up,
    orientation_kind,
    orientation_pose,
    roll_view_up,
)

# faces: exactly one extreme axis; edges: exactly two. (corners are the other guard's job)
_FACE_SIGNS = [s for s in product((-1, 0, 1), repeat=3) if sum(abs(c) for c in s) == 1]
_EDGE_SIGNS = [s for s in product((-1, 0, 1), repeat=3) if sum(abs(c) for c in s) == 2]
_STEP_DEG = 90.0


def _module_source(dotted: str) -> str:
    """Read a module's source from disk WITHOUT importing it (display-free, no VTK/Tk)."""
    spec = importlib.util.find_spec(dotted)
    if spec is None or not spec.origin:
        raise ImportError(f"cannot locate {dotted}")
    return Path(spec.origin).read_text()


def _unit(v):
    v = np.asarray(v, dtype=float)
    return v / float(np.linalg.norm(v))


def _measured_roll(a, s, up):
    """Roll of ``up`` about +``a`` measured from ``s`` (0..360 deg)."""
    e2 = _unit(np.cross(a, s))
    return float(np.degrees(np.arctan2(float(np.dot(up, e2)), float(np.dot(up, s))))) % 360.0


def _snap_dist_to_grid(angle_deg):
    """Angular distance from ``angle_deg`` to the nearest 90-deg gridpoint (0..45)."""
    r = angle_deg % _STEP_DEG
    return min(r, _STEP_DEG - r)


def run_checks():
    """Return ``(passed, notes)`` -- notes is a list of failure strings (empty on pass)."""
    failures: list[str] = []
    all_signs = _FACE_SIGNS + _EDGE_SIGNS

    # --- A: invariant across many current views for every face + edge -------------
    sample_axes = [
        (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0),
        (-0.3, 0.9, 0.3), (0.6, 0.2, -0.75), (0.0, -1.0, 0.0), (0.5, 0.5, 0.5),
    ]
    sample_ups = [
        (0.0, 1.0, 0.0), (0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, -1.0, 0.0),
    ]
    for sign in all_signs:
        kind = orientation_kind(sign)
        a, s = orientation_pose(sign)
        a = np.asarray(a, dtype=float)
        s = np.asarray(s, dtype=float)
        for ax in sample_axes:
            ax_u = _unit(ax)
            for up in sample_ups:
                up_v = np.asarray(up, dtype=float)
                # skip an up parallel to this current axis (no view-up defined) -- covered in E
                if float(np.linalg.norm(up_v - float(np.dot(up_v, ax_u)) * ax_u)) < 1e-6:
                    continue
                out = np.asarray(nearest_orientation_up(a, s, ax_u, up_v, steps=4), dtype=float)
                if abs(float(np.linalg.norm(out)) - 1.0) > 1e-6:
                    failures.append(f"A FAIL: {kind} {sign} axis {np.round(ax_u,2).tolist()} up {up}: result not unit")
                    continue
                if abs(float(np.dot(out, a))) > 1e-6:
                    failures.append(f"A FAIL: {kind} {sign} axis {np.round(ax_u,2).tolist()} up {up}: result not perpendicular to sight")
                roll = _measured_roll(a, s, out)
                if _snap_dist_to_grid(roll) > 1e-4:
                    failures.append(
                        f"A FAIL: {kind} {sign} axis {np.round(ax_u,2).tolist()} up {up}: result roll "
                        f"{roll:.2f} is not a clean 90-deg multiple"
                    )

    # --- B: nearest-of-4 snap table (pure roll about the face axis) ---------------
    a, s = orientation_pose((0, 1, 0))  # TOP
    a = np.asarray(a, dtype=float)
    s = np.asarray(s, dtype=float)
    for k in (0, 10, 30, 44, 60, 80, 100, 130, 170, 190, 220, 260, 280, 315, 350):
        cur_up = np.asarray(roll_view_up(a, s, k), dtype=float)   # roll standard by k about +a
        out = np.asarray(nearest_orientation_up(a, s, a, cur_up, steps=4), dtype=float)
        roll = _measured_roll(a, s, out)
        if _snap_dist_to_grid(roll) > 1e-4:
            failures.append(f"B FAIL: roll {k} -> {roll:.2f} is not a 90-deg multiple")
        gap = abs((roll - k + 180.0) % 360.0 - 180.0)
        if gap > _STEP_DEG / 2.0 + 1e-6:
            failures.append(f"B FAIL: roll {k} snapped to {roll:.2f}, farther than 45 deg (not nearest)")

    # --- C: idempotence -- a clean-roll current view returns the same vector ------
    for sign in all_signs:
        a, s = orientation_pose(sign)
        a = np.asarray(a, dtype=float)
        s = np.asarray(s, dtype=float)
        for k in (0.0, 90.0, 180.0, 270.0):
            cur_up = np.asarray(roll_view_up(a, s, k), dtype=float)
            out = np.asarray(nearest_orientation_up(a, s, a, cur_up, steps=4), dtype=float)
            if not np.allclose(out, cur_up, atol=1e-7):
                failures.append(
                    f"C FAIL: {orientation_kind(sign)} {sign} clean roll {k:.0f} not preserved "
                    f"(out {np.round(out,3).tolist()} != {np.round(cur_up,3).tolist()})"
                )

    # --- D: the user regression -- an upside-down/rolled face STAYS that way -------
    # TOP(+Y): standard up is +X; the four clean rolls are +X, -Z, -X, +Z. Clicking TOP must
    # NOT force the canonical +X when you were already looking at a rolled/flipped TOP.
    face_cases = [
        # sign,          current up,          expected out,      forbidden canonical
        ((0, 1, 0),  (0.0, 0.0, -1.0),  (0.0, 0.0, -1.0),  (1.0, 0.0, 0.0)),   # TOP quarter-turn
        ((0, 1, 0),  (-1.0, 0.0, 0.0),  (-1.0, 0.0, 0.0),  (1.0, 0.0, 0.0)),   # TOP fully flipped
        ((0, 1, 0),  (0.1, 0.05, -0.99), (0.0, 0.0, -1.0), (1.0, 0.0, 0.0)),   # TOP near -Z
        ((0, 0, 1),  (-1.0, 0.0, 0.0),  (-1.0, 0.0, 0.0),  (0.0, 1.0, 0.0)),   # FRONT rolled
        ((1, 0, 0),  (0.0, 0.0, 1.0),   (0.0, 0.0, 1.0),   (0.0, 1.0, 0.0)),   # RIGHT rolled
    ]
    for sign, cur_up, expected, forbidden in face_cases:
        a, s = orientation_pose(sign)
        a = np.asarray(a, dtype=float)
        s = np.asarray(s, dtype=float)
        out = np.asarray(nearest_orientation_up(a, s, a, _unit(cur_up), steps=4), dtype=float)
        exp = _unit(expected)
        if not np.allclose(out, exp, atol=1e-6):
            failures.append(
                f"D FAIL: face {sign} current up {cur_up} -> {np.round(out,3).tolist()} "
                f"(expected {np.round(exp,3).tolist()} -- respect the rolled view)"
            )
        if np.allclose(out, _unit(forbidden), atol=1e-6):
            failures.append(
                f"D FAIL: face {sign} snapped to the FORBIDDEN canonical up {forbidden} "
                f"instead of preserving the current roll (bugs/0321 regression)"
            )

    # --- E: degenerate fallbacks --------------------------------------------------
    a, s = orientation_pose((0, 1, 0))
    a = np.asarray(a, dtype=float)
    s = np.asarray(s, dtype=float)
    out = np.asarray(nearest_orientation_up(a, s, -a, s, steps=4), dtype=float)
    if not np.all(np.isfinite(out)) or abs(float(np.linalg.norm(out)) - 1.0) > 1e-6 or abs(float(np.dot(out, a))) > 1e-6:
        failures.append(f"E FAIL: antiparallel current axis did not fall back to a unit perpendicular up ({out})")
    out2 = np.asarray(nearest_orientation_up(a, s, a, a, steps=4), dtype=float)
    if not np.all(np.isfinite(out2)) or abs(float(np.linalg.norm(out2)) - 1.0) > 1e-6 or abs(float(np.dot(out2, a))) > 1e-6:
        failures.append(f"E FAIL: current up parallel to sight did not fall back to a unit perpendicular up ({out2})")

    # --- F: inspector source contract ---------------------------------------------
    try:
        insp = _module_source("KrakenOS.UI.open3d_inspector")
        if 'kind in ("face", "edge", "corner")' not in insp:
            failures.append(
                "F FAIL: the roll snap is not applied to EVERY pick kind (face/edge/corner) -- "
                "bugs/0321: clicking a face/edge must respect the current view's roll"
            )
        if 'steps=6 if kind == "corner" else 4' not in insp:
            failures.append(
                "F FAIL: the roll snap does not use SIX clean rolls for a corner and FOUR for a "
                "face/edge (steps=6 if kind == 'corner' else 4)"
            )
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"F FAIL: could not read inspector source: {exc!r}")

    return (not failures), failures


def main() -> int:
    passed, notes = run_checks()
    if passed:
        print("[PASS] nav cube FACE/EDGE roll snaps to the nearest of four clean orientations "
              "(respects the current view, bugs/0321)")
        return 0
    print("[FAIL] bugs/0321 nav-cube face/edge nearest-of-4 guard:")
    for note in notes:
        print(f"   - {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
