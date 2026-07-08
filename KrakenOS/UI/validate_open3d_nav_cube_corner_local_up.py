#!/usr/bin/env python3
"""Display-free guard for bugs/0257 (supersedes bugs/0254+0255+0256): a navigation-cube CORNER
click keeps the CURRENT view's roll, SNAPPED to the nearest of SIX clean orientations about the
corner diagonal -- a faithful port of FreeCAD's NaviCube ``getNearestOrientation``.

Why the whole model changed (user, 2026-07-08):
  0254/0255/0256 tried to make a corner's roll "relative" with a BINARY up/down flip -- keep the
  absolute ISO up, or flip it 180 deg when the view was upside down. Every variant (continuous roll,
  per-corner flip, one global flip) still read "wrong orientation" after the scene was rotated,
  because a binary flip only ever offers TWO rolls (0 or 180): any view whose natural nearest clean
  roll is 60/120/240/300 deg lands visibly wrong no matter how the flip is tuned. The user checked
  FreeCAD -- whose NaviCube snaps a corner to the nearest of SIX rolls -- and said "drop the
  widescreen". So the fix ports FreeCAD exactly.

The fix (:func:`nav_cube_orientation.nearest_orientation_up`, NaviCube.cpp:954): minimally rotate the
CURRENT camera so its view axis lands on the corner diagonal (this preserves the roll), measure the
residual roll of that intermediate up from the corner's roll-0 STANDARD up (world +Y projected
perpendicular to the diagonal -- itself one of the six clean rolls), round it to the nearest
``2*pi/6`` = 60 deg, and roll the standard up by it. Corners only; faces/edges keep their absolute up.

What it checks (no display required, pure math + source contract):
  A. Invariant for many (current axis, current up) samples per corner: the result is unit,
     perpendicular to the corner sight line, and a CLEAN 60-deg multiple roll from the standard up.
  B. Nearest-of-6 snap table: rolling the standard by k deg about the diagonal and clicking snaps
     to the nearest 60-deg gridpoint (output within 30 deg of k AND a 60-multiple) -- the crux that
     a binary 0/180 flip could never do.
  C. Idempotence: a current view that IS one of the six clean rolls comes back byte-for-byte (the
     roll is preserved, not reset) for every corner.
  D. Cross-axis (the real scenario): clicking a corner from a FACE/oblique view returns a clean
     snapped roll -- so a corner clicked after you rotated the scene is well-defined and upright-ish.
  E. Degenerate fallback: an antiparallel current axis, or a current up parallel to the sight line,
     still yields a finite unit vector perpendicular to the sight line.
  F. Source contract -- inspector: _apply_navigation_cube_orientation takes a ``sign`` arg, reads
     BOTH the live camera up (GetViewUp) and view direction (GetDirectionOfProjection), and calls
     nearest_orientation_up ONLY for a corner (orientation_kind == "corner"); faces/edges keep
     their absolute up.
  G. Source contract -- widget: handle_left_press forwards the picked ``sign`` as the third
     apply_orientation argument.
"""
from __future__ import annotations

import importlib.util
from itertools import product
from pathlib import Path

import numpy as np

from KrakenOS.UI.services.nav_cube_orientation import (
    nearest_orientation_up,
    orientation_pose,
    roll_view_up,
)

_CORNER_SIGNS = list(product((1, -1), repeat=3))  # the 8 octant corners
_STEP_DEG = 60.0


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
    """Angular distance from ``angle_deg`` to the nearest 60-deg gridpoint (0..30)."""
    r = angle_deg % _STEP_DEG
    return min(r, _STEP_DEG - r)


def run_checks():
    """Return ``(passed, notes)`` -- notes is a list of failure strings (empty on pass)."""
    failures: list[str] = []

    # --- A: invariant across many current views for every corner ------------------
    sample_axes = [
        (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0),
        (-0.3, 0.9, 0.3), (0.6, 0.2, -0.75), (0.0, -1.0, 0.0), (0.5, 0.5, 0.5),
    ]
    sample_ups = [
        (0.0, 1.0, 0.0), (0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, -1.0, 0.0),
    ]
    for sign in _CORNER_SIGNS:
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
                out = np.asarray(nearest_orientation_up(a, s, ax_u, up_v, steps=6), dtype=float)
                if abs(float(np.linalg.norm(out)) - 1.0) > 1e-6:
                    failures.append(f"A FAIL: corner {sign} axis {np.round(ax_u,2).tolist()} up {up}: result not unit")
                    continue
                if abs(float(np.dot(out, a))) > 1e-6:
                    failures.append(f"A FAIL: corner {sign} axis {np.round(ax_u,2).tolist()} up {up}: result not perpendicular to sight")
                roll = _measured_roll(a, s, out)
                if _snap_dist_to_grid(roll) > 1e-4:
                    failures.append(
                        f"A FAIL: corner {sign} axis {np.round(ax_u,2).tolist()} up {up}: result roll "
                        f"{roll:.2f} is not a clean 60-deg multiple"
                    )

    # --- B: nearest-of-6 snap table (pure roll about the diagonal) ----------------
    a, s = orientation_pose((1, 1, 1))
    a = np.asarray(a, dtype=float)
    s = np.asarray(s, dtype=float)
    for k in (0, 10, 20, 45, 59, 75, 90, 100, 130, 170, 190, 235, 250, 290, 320, 350):
        cur_up = np.asarray(roll_view_up(a, s, k), dtype=float)   # roll standard by k about +a
        out = np.asarray(nearest_orientation_up(a, s, a, cur_up, steps=6), dtype=float)
        roll = _measured_roll(a, s, out)
        if _snap_dist_to_grid(roll) > 1e-4:
            failures.append(f"B FAIL: roll {k} -> {roll:.2f} is not a 60-deg multiple")
        # the snapped roll must be the NEAREST gridpoint to k (within half a step)
        gap = abs((roll - k + 180.0) % 360.0 - 180.0)
        if gap > _STEP_DEG / 2.0 + 1e-6:
            failures.append(f"B FAIL: roll {k} snapped to {roll:.2f}, farther than 30 deg (not nearest)")

    # --- C: idempotence -- a clean-roll current view returns the same vector ------
    for sign in _CORNER_SIGNS:
        a, s = orientation_pose(sign)
        a = np.asarray(a, dtype=float)
        s = np.asarray(s, dtype=float)
        for k in (0.0, 60.0, 120.0, 180.0, 240.0, 300.0):
            cur_up = np.asarray(roll_view_up(a, s, k), dtype=float)
            out = np.asarray(nearest_orientation_up(a, s, a, cur_up, steps=6), dtype=float)
            if not np.allclose(out, cur_up, atol=1e-7):
                failures.append(
                    f"C FAIL: corner {sign} clean roll {k:.0f} not preserved "
                    f"(out {np.round(out,3).tolist()} != {np.round(cur_up,3).tolist()})"
                )

    # --- D: cross-axis -- click a corner from a face/oblique view -----------------
    for label, cur_axis, cur_up in (
        ("front +Z", (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
        ("top +Y", (0.0, 1.0, 0.0), (0.0, 0.0, -1.0)),
        ("oblique", (-0.3, 0.9, 0.3), (0.0, 0.3, -0.95)),
    ):
        for sign in _CORNER_SIGNS:
            a, s = orientation_pose(sign)
            a = np.asarray(a, dtype=float)
            s = np.asarray(s, dtype=float)
            out = np.asarray(nearest_orientation_up(a, s, _unit(cur_axis), _unit(cur_up), steps=6), dtype=float)
            roll = _measured_roll(a, s, out)
            if abs(float(np.linalg.norm(out)) - 1.0) > 1e-6 or abs(float(np.dot(out, a))) > 1e-6:
                failures.append(f"D FAIL: '{label}' corner {sign} result not a unit perpendicular up")
            elif _snap_dist_to_grid(roll) > 1e-4:
                failures.append(f"D FAIL: '{label}' corner {sign} roll {roll:.2f} not a clean 60-deg multiple")

    # --- E: degenerate fallbacks --------------------------------------------------
    a, s = orientation_pose((1, 1, 1))
    a = np.asarray(a, dtype=float)
    s = np.asarray(s, dtype=float)
    # antiparallel current axis (rotation axis undefined)
    out = np.asarray(nearest_orientation_up(a, s, -a, s, steps=6), dtype=float)
    if not np.all(np.isfinite(out)) or abs(float(np.linalg.norm(out)) - 1.0) > 1e-6 or abs(float(np.dot(out, a))) > 1e-6:
        failures.append(f"E FAIL: antiparallel current axis did not fall back to a unit perpendicular up ({out})")
    # current up parallel to the sight line (no roll defined)
    out2 = np.asarray(nearest_orientation_up(a, s, a, a, steps=6), dtype=float)
    if not np.all(np.isfinite(out2)) or abs(float(np.linalg.norm(out2)) - 1.0) > 1e-6 or abs(float(np.dot(out2, a))) > 1e-6:
        failures.append(f"E FAIL: current up parallel to sight did not fall back to a unit perpendicular up ({out2})")

    # --- F: inspector source contract ---------------------------------------------
    try:
        insp = _module_source("KrakenOS.UI.open3d_inspector")
        if "def _apply_navigation_cube_orientation(self, offset_unit, view_up, sign" not in insp:
            failures.append("F FAIL: _apply_navigation_cube_orientation does not take a `sign` argument")
        if "nearest_orientation_up(" not in insp:
            failures.append("F FAIL: the inspector never calls nearest_orientation_up -- corner roll is not snapped")
        if "GetViewUp()" not in insp:
            failures.append("F FAIL: the inspector does not read the live camera up (GetViewUp)")
        if "GetDirectionOfProjection()" not in insp:
            failures.append("F FAIL: the inspector does not read the live view direction (GetDirectionOfProjection) for the roll snap")
        if 'orientation_kind(' not in insp or '"corner"' not in insp:
            failures.append(
                "F FAIL: the roll snap is not gated on a CORNER (orientation_kind == 'corner') -- "
                "faces/edges must keep their absolute up"
            )
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"F FAIL: could not read inspector source: {exc!r}")

    # --- G: widget forwards the picked sign ---------------------------------------
    try:
        wid = _module_source("KrakenOS.UI.services.nav_cube_widget")
        if "self._apply_orientation(offset_unit, view_up, " not in wid:
            failures.append(
                "G FAIL: handle_left_press does not forward the picked sign as the 3rd "
                "apply_orientation argument -- the host can't tell a corner apart"
            )
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"G FAIL: could not read nav_cube_widget source: {exc!r}")

    return (not failures), failures


def main() -> int:
    passed, notes = run_checks()
    if passed:
        print("[PASS] nav cube corner roll snaps to the nearest of six clean orientations "
              "(FreeCAD getNearestOrientation port, bugs/0257)")
        return 0
    print("[FAIL] bugs/0257 nav-cube corner nearest-of-6 guard:")
    for note in notes:
        print(f"   - {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
