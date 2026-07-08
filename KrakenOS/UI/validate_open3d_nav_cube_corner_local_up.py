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
  0256 (after testing 0255): "Right Top corner ... reversed" then the adjacent "Right Bottom corner
   ... completely wrong." 0255 decided the 180 deg flip from the current up projected onto EACH
   corner's OWN sight plane, so from a tumbled start adjacent corners could land on opposite sides.

The fix keeps the corner's ISO SIGHT DIRECTION (the picked octant's diagonal) and returns the
ABSOLUTE ISO up (``iso_corner_pose``'s world-+Y up) projected onto the plane perpendicular to that
sight line, FLIPPED 180 deg iff the current view is GLOBALLY upside down -- the live camera up
points against the absolute ISO up (``dot(current_up, fallback_up) < -eps``), ONE corner-independent
decision, so every corner flips together (``relative_up_about_sight``). The result is still always
COLLINEAR with the absolute ISO up (+/- a flip): +/-abs_up give the SAME wide-screen fit, so the
framing is preserved; a tumbled ~90 deg view (dot ~ 0, no well-defined up/down) stays upright. The
pure-math corner pose (``iso_corner_pose``) is unchanged -- it supplies the sight direction + the
absolute reference up -- so the bugs/0249/0252/0253 guards stay green; THIS guard pins the
global-flip math and the widget/inspector wiring that applies it to corners only. (Refines penta
Phase 230, no new phase.)

What it checks (no display required, pure math + source contract):
  A. relative_up_about_sight for every corner: the result is unit, perpendicular to the new sight
     line, and COLLINEAR with the absolute ISO up projected onto the sight plane (|dot| == 1, so
     the wide-screen fit is preserved -- the crux of 0255). An upside-down current up (world -Y)
     flips it (dot with the projected ISO up < 0, world-Y stays negative) and it differs from the
     absolute world-up ISO up; an UPRIGHT current up (world +Y) stays upright (dot > 0).
  E. GLOBAL consistency (the crux of 0256): a given current up drives ALL 8 corners to the SAME
     side (never the split that gave "Right Top reversed" but "Right Bottom completely wrong") --
     clearly-upside-down flips all, clearly-upright flips none -- and every corner stays collinear
     with the ISO up (wide-screen fit intact) regardless of side.
  F. Tumbled deadband: a ~90 deg view (current up . world up ~ 0, e.g. flag 1's up = (0,0,-1)) has
     no well-defined up/down, so every corner stays UPRIGHT rather than guessing a side.
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

    # --- E + F: the flip is GLOBAL and consistent across corners (bugs/0256) ---------
    def _corner_side(corner_sign, cur):
        """(+1 upright / -1 flipped, |collinear err|) for a corner given a current up."""
        offset, abs_up = iso_corner_pose(corner_sign, up_axis="y")
        look = -np.asarray(offset, dtype=float)
        look = look / float(np.linalg.norm(look))
        abs_perp = np.asarray(abs_up, dtype=float) - float(np.dot(abs_up, look)) * look
        abs_proj = abs_perp / float(np.linalg.norm(abs_perp))
        rel = np.asarray(relative_up_about_sight(offset, cur, fallback_up=abs_up), dtype=float)
        d = float(np.dot(rel, abs_proj))
        return (1 if d >= 0.0 else -1), abs(abs(d) - 1.0)

    # E: a given current up must drive ALL 8 corners to ONE side. 0255 keyed the flip off the
    #    PER-CORNER projected up, so adjacent corners could disagree ("Right Top reversed" yet
    #    the neighbouring "Right Bottom completely wrong"). Now it is one global decision.
    for label, cur, want in (
        ("clearly upside down", np.array([0.15, -0.96, -0.2]), -1),
        ("clearly upright", np.array([0.1, 0.97, 0.2]), 1),
        ("rolled 135 deg", np.array([0.0, -0.7071, -0.7071]), -1),
    ):
        sides = [_corner_side(s, cur)[0] for s in _CORNER_SIGNS]
        if len(set(sides)) != 1:
            failures.append(
                f"E FAIL: '{label}' current up gives INCONSISTENT corner flips {sides} -- "
                "adjacent corners disagree (the 0255 bug)"
            )
        elif sides[0] != want:
            failures.append(
                f"E FAIL: '{label}' flipped to the wrong side (got {sides[0]:+d}, want {want:+d})"
            )
        worst = max(_corner_side(s, cur)[1] for s in _CORNER_SIGNS)
        if worst > 1e-6:
            failures.append(
                f"E FAIL: '{label}' broke the wide-screen fit (max |collinear err| {worst:.1e})"
            )

    # F: a tumbled ~90 deg view (current up . world up ~ 0, no well-defined up/down) stays
    #    UPRIGHT for every corner rather than guessing -- the flag_...812 "Upside down Left"
    #    up = (0,0,-1) case that made 0255 pick inconsistently (bugs/0256 deadband).
    for label, cur in (
        ("tumbled -Z (flag 1)", np.array([0.0, 0.0, -1.0])),
        ("tumbled +Z", np.array([0.0, 0.0, 1.0])),
    ):
        sides = [_corner_side(s, cur)[0] for s in _CORNER_SIGNS]
        if any(s != 1 for s in sides):
            failures.append(
                f"F FAIL: '{label}' (dot world-up ~ 0) did not stay upright for all corners {sides}"
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
        print("[PASS] nav cube corner ISO: one global up/down flip for all corners keeps the "
              "current sense AND the wide-screen fit (bugs/0254+0255+0256)")
        return 0
    print("[FAIL] bugs/0254+0255+0256 nav-cube local-corner-ISO guard:")
    for note in notes:
        print(f"   - {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
