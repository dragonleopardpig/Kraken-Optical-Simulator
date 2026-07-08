#!/usr/bin/env python3
"""Display-free guard for bugs/0254: a navigation-cube CORNER click gives a LOCAL ISO view --
its roll is relative to the CURRENT view, so the visible face labels keep their up/down sense
(e.g. a corner click after you rolled "RIGHT" upside down keeps it upside down) instead of
snapping to the absolute world-up ISO that bugs/0252 installed.

Why it exists (user flag 2026-07-08):
  "clicking the Corner ... their tilting is refer to the global instead of local. I think local
   is more meaningful. ... I click the 'Right' face, then rotate the scene until the 'Right' is
   upside down. Now ... an ISO view by clicking the Corner, the existing behaviour is that it
   goes back to the absolute global ISO view. But it is more intuitive to just have an ISO view
   relative to the current one, meaning the 'Right' and all other visible alphabet remain upside
   down."

The fix keeps the corner's ISO SIGHT DIRECTION (the picked octant's diagonal) but derives the
view-up by projecting the camera's CURRENT up onto the plane perpendicular to that sight line
(``relative_up_about_sight``), so only the ROLL becomes relative. The pure-math corner pose
(``iso_corner_pose``) is unchanged -- it now supplies the sight direction + the absolute fallback
up -- so the bugs/0249/0252/0253 guards stay green; THIS guard pins the new relative-up math and
the widget/inspector wiring that applies it to corners only.

What it checks (no display required, pure math + source contract):
  A. relative_up_about_sight preserves the current roll for every corner: the result is unit,
     perpendicular to the new sight line, on the SAME side as the current up (dot > 0), differs
     from the absolute world-up ISO up, and an upside-down current up stays upside down (world-Y
     component keeps its sign). An UPRIGHT current up still reads upright (no regression to the
     common first-click ISO).
  B. Degenerate fallback: when the current up is (near) parallel to the sight line the projection
     is degenerate; the helper falls back to a finite, unit, perpendicular up (fallback / world).
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

    # --- A: relative up preserves the current roll for every corner ------------------
    for sign in _CORNER_SIGNS:
        offset, abs_up = iso_corner_pose(sign, up_axis="y")
        look = -np.asarray(offset, dtype=float)
        look = look / float(np.linalg.norm(look))

        # "upside down" current view: world -Y (never parallel to a corner sight)
        cur_down = np.array([0.0, -1.0, 0.0])
        rel = np.asarray(relative_up_about_sight(offset, cur_down, fallback_up=abs_up), dtype=float)
        if abs(float(np.linalg.norm(rel)) - 1.0) > 1e-6:
            failures.append(f"A FAIL: corner {sign} relative up not unit ({np.linalg.norm(rel):.4f})")
        if abs(float(np.dot(rel, look))) > 1e-6:
            failures.append(f"A FAIL: corner {sign} relative up not perpendicular to the sight line")
        if float(np.dot(rel, cur_down)) <= 1e-6:
            failures.append(
                f"A FAIL: corner {sign} relative up not on the same side as the current up "
                "(roll not preserved)"
            )
        if float(rel[1]) >= 0.0:
            failures.append(
                f"A FAIL: corner {sign} upside-down view did NOT stay upside down "
                f"(relative up world-Y {rel[1]:.3f} >= 0)"
            )
        if np.allclose(rel, np.asarray(abs_up, dtype=float)):
            failures.append(
                f"A FAIL: corner {sign} relative up equals the ABSOLUTE ISO up -- the corner roll "
                "is still global, not local"
            )

        # an UPRIGHT current view (world +Y) should still read upright (no regression)
        rel_up = np.asarray(relative_up_about_sight(offset, np.array([0.0, 1.0, 0.0]), fallback_up=abs_up), dtype=float)
        if float(rel_up[1]) <= 0.0:
            failures.append(
                f"A FAIL: corner {sign} upright view did not stay upright (world-Y {rel_up[1]:.3f})"
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
        print("[PASS] nav cube corner ISO is LOCAL: roll relative to the current view (bugs/0254)")
        return 0
    print("[FAIL] bugs/0254 nav-cube local-corner-ISO guard:")
    for note in notes:
        print(f"   - {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
