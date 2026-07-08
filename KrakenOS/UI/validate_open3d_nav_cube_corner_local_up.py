#!/usr/bin/env python3
"""Display-free guard for bugs/0254 + 0255: a navigation-cube CORNER click gives a LOCAL ISO view
whose ROLL matches the CURRENT view's up/down sense (e.g. a corner click after you rolled "RIGHT"
upside down keeps it upside down) WHILE keeping the bugs/0252 wide-screen framing.

Why it exists (user flags 2026-07-08):
  0254: "clicking the Corner ... their tilting is refer to the global instead of local. ... I click
   the 'Right' face, then rotate the scene until the 'Right' is upside down. Now ... an ISO view by
   clicking the Corner ... it is more intuitive to just have an ISO view relative to the current
   one, meaning the 'Right' and all other visible alphabet remain upside down."
  0255 (after testing 0254): "clicking the corner button works but it does not apply the previous
   'wide screen' adjustment." -- a CONTINUOUS relative roll rotated the long optical axis off
   horizontal, so the orthographic zoom-fit (which only divides the horizontal span by the aspect)
   zoomed out to fit the axis in the short screen dimension, losing the wide screen.

The fix keeps the corner's ISO SIGHT DIRECTION (the picked octant's diagonal) and returns the
ABSOLUTE ISO up (``iso_corner_pose``'s world-+Y up) projected onto the plane perpendicular to that
sight line, FLIPPED 180 deg when the current view is upside down relative to it
(``relative_up_about_sight``). So the result is always COLLINEAR with the absolute ISO up (+/- a
flip): the up/down sense follows the current view, but +/-abs_up give the SAME wide-screen fit, so
an intermediate roll snaps to upright/flipped instead of leaking a tilt. The pure-math corner pose
(``iso_corner_pose``) is unchanged -- it supplies the sight direction + the absolute reference up --
so the bugs/0249/0252/0253 guards stay green; THIS guard pins the flip-snap math and the
widget/inspector wiring that applies it to corners only. (Refines penta Phase 230, no new phase.)

What it checks (no display required, pure math + source contract):
  A. relative_up_about_sight for every corner: the result is unit, perpendicular to the new sight
     line, and COLLINEAR with the absolute ISO up projected onto the sight plane (|dot| == 1, so
     the wide-screen fit is preserved -- the crux of 0255). An upside-down current up (world -Y)
     flips it (dot with the projected ISO up < 0, world-Y stays negative) and it differs from the
     absolute world-up ISO up; an UPRIGHT current up (world +Y) stays upright (dot > 0).
  E. No continuous-roll leak: an INTERMEDIATE current roll (e.g. 60 deg / 120 deg about the sight
     line) still returns +/- the absolute ISO up (collinear), snapping to upright below 90 deg and
     flipped above -- never the intermediate tilt that would break the wide-screen fit.
  B. Degenerate fallback: when the current up is (near) parallel to the sight line the projection
     is degenerate; the helper falls back to a finite, unit, perpendicular up (reference / world).
  C. Source contract -- inspector: _apply_navigation_cube_orientation takes a ``sign`` arg, reads
     the live camera up (GetViewUp) and applies relative_up_about_sight ONLY for a corner
     (orientation_kind == "corner"); faces/edges keep their absolute up.
  D. Source contract -- widget: handle_left_press forwards the picked ``sign`` as the third
     apply_orientation argument.
"""
from __future__ import annotations

import importlib.util
from itertools import product
from pathlib import Path

import numpy as np

from KrakenOS.UI.services.nav_cube_orientation import (
    iso_corner_pose,
    orientation_kind,
    relative_up_about_sight,
)

_CORNER_SIGNS = list(product((1, -1), repeat=3))  # the 8 octant corners


def _module_source(dotted: str) -> str:
    """Read a module's source from disk WITHOUT importing it (display-free, no VTK/Tk)."""
    spec = importlib.util.find_spec(dotted)
    if spec is None or not spec.origin:
        raise ImportError(f"cannot locate {dotted}")
    return Path(spec.origin).read_text()


def run_checks():
    """Return ``(passed, notes)`` -- notes is a list of failure strings (empty on pass)."""
    failures: list[str] = []

    # --- A + E: flip-snap keeps the up/down sense AND the wide-screen fit -------------
    for sign in _CORNER_SIGNS:
        offset, abs_up = iso_corner_pose(sign, up_axis="y")
        look = -np.asarray(offset, dtype=float)
        look = look / float(np.linalg.norm(look))
        # The absolute ISO up projected onto the sight plane -- the wide-screen roll. The
        # result must always be +/- this (collinear), never an intermediate tilt.
        abs_perp = np.asarray(abs_up, dtype=float) - float(np.dot(abs_up, look)) * look
        abs_proj = abs_perp / float(np.linalg.norm(abs_perp))
        side = np.cross(look, abs_proj)
        side = side / float(np.linalg.norm(side))

        def _rel(cur):
            return np.asarray(relative_up_about_sight(offset, cur, fallback_up=abs_up), dtype=float)

        # "upside down" current view: world -Y (never parallel to a corner sight)
        cur_down = np.array([0.0, -1.0, 0.0])
        rel = _rel(cur_down)
        if abs(float(np.linalg.norm(rel)) - 1.0) > 1e-6:
            failures.append(f"A FAIL: corner {sign} relative up not unit ({np.linalg.norm(rel):.4f})")
        if abs(float(np.dot(rel, look))) > 1e-6:
            failures.append(f"A FAIL: corner {sign} relative up not perpendicular to the sight line")
        if abs(abs(float(np.dot(rel, abs_proj))) - 1.0) > 1e-6:
            failures.append(
                f"A FAIL: corner {sign} relative up is NOT collinear with the absolute ISO up "
                f"(|dot| {abs(float(np.dot(rel, abs_proj))):.4f} != 1) -- wide-screen fit broken"
            )
        if float(np.dot(rel, abs_proj)) >= 0.0:
            failures.append(
                f"A FAIL: corner {sign} upside-down view did NOT flip (dot with ISO up "
                f"{float(np.dot(rel, abs_proj)):.3f} >= 0)"
            )
        if float(rel[1]) >= 0.0:
            failures.append(
                f"A FAIL: corner {sign} upside-down view did NOT stay upside down "
                f"(relative up world-Y {rel[1]:.3f} >= 0)"
            )
        if np.allclose(rel, np.asarray(abs_up, dtype=float)):
            failures.append(
                f"A FAIL: corner {sign} relative up equals the ABSOLUTE ISO up -- did not flip"
            )

        # an UPRIGHT current view (world +Y) should still read upright (no regression)
        rel_up = _rel(np.array([0.0, 1.0, 0.0]))
        if float(np.dot(rel_up, abs_proj)) <= 0.0 or float(rel_up[1]) <= 0.0:
            failures.append(
                f"A FAIL: corner {sign} upright view did not stay upright "
                f"(dot ISO up {float(np.dot(rel_up, abs_proj)):.3f}, world-Y {rel_up[1]:.3f})"
            )

        # E: an INTERMEDIATE roll must snap to +/- the ISO up, never leak the tilt.
        for angle_deg, want_sign in ((60.0, 1.0), (120.0, -1.0)):
            theta = np.radians(angle_deg)
            cur_mid = np.cos(theta) * abs_proj + np.sin(theta) * side
            rel_mid = _rel(cur_mid)
            if abs(abs(float(np.dot(rel_mid, abs_proj))) - 1.0) > 1e-6:
                failures.append(
                    f"E FAIL: corner {sign} {angle_deg:.0f} deg roll leaked a tilt "
                    f"(|dot ISO up| {abs(float(np.dot(rel_mid, abs_proj))):.4f} != 1)"
                )
            if float(np.dot(rel_mid, abs_proj)) * want_sign <= 0.0:
                failures.append(
                    f"E FAIL: corner {sign} {angle_deg:.0f} deg roll snapped to the wrong side "
                    f"(dot ISO up {float(np.dot(rel_mid, abs_proj)):.3f}, wanted sign {want_sign:+.0f})"
                )

    # --- B: degenerate fallback (current up parallel to the sight line) -------------
    offset, abs_up = iso_corner_pose((1, 1, 1), up_axis="y")
    look = -np.asarray(offset, dtype=float)
    look = look / float(np.linalg.norm(look))
    rel_fb = np.asarray(relative_up_about_sight(offset, look, fallback_up=abs_up), dtype=float)
    if not np.all(np.isfinite(rel_fb)) or abs(float(np.linalg.norm(rel_fb)) - 1.0) > 1e-6:
        failures.append(f"B FAIL: degenerate (parallel) up did not fall back to a unit vector ({rel_fb})")
    if abs(float(np.dot(rel_fb, look))) > 1e-6:
        failures.append("B FAIL: degenerate fallback up is not perpendicular to the sight line")
    rel_fb2 = np.asarray(relative_up_about_sight(offset, look, fallback_up=None), dtype=float)
    if not np.all(np.isfinite(rel_fb2)) or abs(float(np.linalg.norm(rel_fb2)) - 1.0) > 1e-6:
        failures.append("B FAIL: degenerate up with no fallback did not use the world-projected up")

    # --- C: inspector source contract ----------------------------------------------
    try:
        insp = _module_source("KrakenOS.UI.open3d_inspector")
        if "def _apply_navigation_cube_orientation(self, offset_unit, view_up, sign" not in insp:
            failures.append("C FAIL: _apply_navigation_cube_orientation does not take a `sign` argument")
        if "relative_up_about_sight(" not in insp:
            failures.append("C FAIL: the inspector never calls relative_up_about_sight -- corner roll is not local")
        if "GetViewUp()" not in insp:
            failures.append("C FAIL: the inspector does not read the live camera up (GetViewUp) for the relative roll")
        if 'orientation_kind(' not in insp or '"corner"' not in insp:
            failures.append(
                "C FAIL: the relative up is not gated on a CORNER (orientation_kind == 'corner') -- "
                "faces/edges must keep their absolute up"
            )
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"C FAIL: could not read inspector source: {exc!r}")

    # --- D: widget forwards the picked sign ----------------------------------------
    try:
        wid = _module_source("KrakenOS.UI.services.nav_cube_widget")
        if "self._apply_orientation(offset_unit, view_up, " not in wid:
            failures.append(
                "D FAIL: handle_left_press does not forward the picked sign as the 3rd "
                "apply_orientation argument -- the host can't tell a corner apart"
            )
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"D FAIL: could not read nav_cube_widget source: {exc!r}")

    return (not failures), failures


def main() -> int:
    passed, notes = run_checks()
    if passed:
        print("[PASS] nav cube corner ISO keeps the current up/down sense AND the wide-screen fit (bugs/0254+0255)")
        return 0
    print("[FAIL] bugs/0254+0255 nav-cube local-corner-ISO guard:")
    for note in notes:
        print(f"   - {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
