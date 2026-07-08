#!/usr/bin/env python3
"""Display-free guard for bugs/0257 (supersedes bugs/0252): clicking a navigation-cube CORNER
uses a SYMMETRIC diagonal standard pose -- the 0252 "wide-screen" ISO bias is DROPPED.

Why the premise flipped (user, 2026-07-08, after the 0254-0256 saga):
  0252 biased every corner toward the ISO toolbar direction (offset ``(-0.95, 0.55, 0.8)``,
  ~23.9 deg elevation, world-+Y up) so a corner framed the long optical axis wide-screen. But
  the corner ROLL then had to be reconciled against the current view, and three tries at a
  binary up/down flip (0254/0255/0256) all read "wrong orientation" after the scene was rotated.
  The user checked FreeCAD -- whose NaviCube snaps a corner to the nearest of SIX clean rolls --
  and said "drop the widescreen". So corners revert to the plain symmetric diagonal and the roll
  is handled by the FreeCAD port (:func:`nav_cube_orientation.nearest_orientation_up`, pinned by
  the phase-230 guard); THIS guard pins the standard POSE the port rolls from.

The fix (nav_cube_orientation.orientation_pose) drops the corner special-case: a corner now falls
through the SAME rule as an edge -- ``offset = normalize(sign)`` (the symmetric ``(+-1,+-1,+-1)``
diagonal) and ``view_up`` = world +Y projected perpendicular to it (the roll-0 STANDARD, itself one
of the six clean corner rolls). Faces stay the cardinal presets; edges are unchanged.

What it checks (no display required, pure math + source contract):
  A. All 8 corners: unit outward offset ALONG the ``(+-1,+-1,+-1)`` diagonal (sign-consistent
     octant), unit view_up perpendicular to the sight line and upright (world-+Y positive).
  B. Every corner sits at the SYMMETRIC elevation (~35.26 deg = arcsin(1/sqrt3)), NOT the old ISO
     23.9 deg -- the wide-screen bias is gone.
  C. The ISO-octant corner ``(-1,+1,+1)`` is NO LONGER the ISO button direction ``(-0.95,0.55,0.8)``
     -- a positive check that 0252's bias was removed.
  D. Regression: the 6 faces are still the cardinal presets and the 12 edges still use the
     perpendicular projected-up rule (this bug only touched corners).
  E. Source contract: orientation_pose no longer routes corners through ``iso_corner_pose`` (that
     helper is gone), the module exposes ``nearest_orientation_up`` (the FreeCAD roll port), and the
     widget still forwards the picked ``sign`` so the host can snap a corner's roll.
"""
from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.services import nav_cube_orientation as nco
from KrakenOS.UI.services.nav_cube_orientation import (
    ORIENTATION_KEYS,
    orientation_kind,
    orientation_pose,
)

# The historic ISO toolbar direction (open3d_inspector._iso_camera_offset_and_view_up, y-up).
_ISO_DIR = np.array([-0.95, 0.55, 0.8], dtype=float)
_ISO_DIR = _ISO_DIR / float(np.linalg.norm(_ISO_DIR))
_ISO_ELEVATION_DEG = float(np.degrees(np.arcsin(abs(_ISO_DIR[1]))))            # ~23.88 (dropped)
_SYMMETRIC_ELEVATION_DEG = float(np.degrees(np.arcsin(1.0 / np.sqrt(3.0))))    # ~35.26 (now)


def run_checks():
    """Return ``(passed, notes)`` -- notes is a list of failure strings (empty on pass)."""
    failures: list[str] = []

    corners = [s for s in ORIENTATION_KEYS if orientation_kind(s) == "corner"]
    if len(corners) != 8:
        failures.append(f"expected 8 corners, got {len(corners)}")

    # --- A: every corner is the symmetric diagonal + projected-up standard --------
    for sign in corners:
        offset, view_up = orientation_pose(sign)
        offset = np.asarray(offset, dtype=float)
        view_up = np.asarray(view_up, dtype=float)
        want_off = np.asarray(sign, dtype=float)
        want_off = want_off / float(np.linalg.norm(want_off))
        if not np.allclose(offset, want_off, atol=1e-9):
            failures.append(
                f"A FAIL: corner {sign} offset {np.round(offset,4).tolist()} != symmetric diagonal "
                f"{np.round(want_off,4).tolist()}"
            )
        if abs(float(np.linalg.norm(offset)) - 1.0) > 1e-9:
            failures.append(f"A FAIL: corner {sign} offset not unit ({np.linalg.norm(offset):.4f})")
        if abs(float(np.linalg.norm(view_up)) - 1.0) > 1e-9:
            failures.append(f"A FAIL: corner {sign} view_up not unit ({np.linalg.norm(view_up):.4f})")
        if abs(float(np.dot(offset, view_up))) > 1e-6:
            failures.append(f"A FAIL: corner {sign} view_up not perpendicular to the sight line")
        if float(view_up[1]) <= 1e-6:
            failures.append(f"A FAIL: corner {sign} view_up {np.round(view_up,3).tolist()} is not upright (world-+Y)")
        if not np.all(np.sign(offset).astype(int) == np.asarray(sign, dtype=int)):
            failures.append(f"A FAIL: corner {sign} offset {np.round(offset,3).tolist()} leaves the octant")

    # --- B: corners sit at the symmetric elevation, NOT the old ISO 23.9 deg ------
    for sign in corners:
        offset = np.asarray(orientation_pose(sign)[0], dtype=float)
        elev = float(np.degrees(np.arcsin(abs(offset[1]))))
        if abs(elev - _SYMMETRIC_ELEVATION_DEG) > 0.1:
            failures.append(f"B FAIL: corner {sign} elevation {elev:.2f} deg != symmetric {_SYMMETRIC_ELEVATION_DEG:.2f} deg")
        if abs(elev - _ISO_ELEVATION_DEG) < 0.1:
            failures.append(f"B FAIL: corner {sign} is still at the dropped ISO wide-screen {elev:.2f} deg")

    # --- C: the ISO octant corner is NO LONGER the ISO button direction -----------
    iso_off, _ = orientation_pose((-1, 1, 1))
    if np.allclose(iso_off, _ISO_DIR, atol=1e-6):
        failures.append(
            f"C FAIL: ISO octant (-1,1,1) offset {np.round(iso_off,4).tolist()} STILL equals the "
            f"dropped ISO button direction {np.round(_ISO_DIR,4).tolist()}"
        )

    # --- D: faces + edges unchanged (this bug only touched corners) ---------------
    _FACE_UP = {
        (1, 0, 0): (0.0, 1.0, 0.0), (-1, 0, 0): (0.0, 1.0, 0.0),
        (0, 0, 1): (0.0, 1.0, 0.0), (0, 0, -1): (0.0, 1.0, 0.0),
        (0, 1, 0): (1.0, 0.0, 0.0), (0, -1, 0): (1.0, 0.0, 0.0),
    }
    for face, up in _FACE_UP.items():
        off, got_up = orientation_pose(face)
        triple = np.asarray(face, dtype=float)
        if not (np.allclose(off, triple, atol=1e-9) and np.allclose(got_up, up, atol=1e-9)):
            failures.append(f"D FAIL: face {face} pose drifted from the cardinal preset ({off},{got_up})")
    for sign in [s for s in ORIENTATION_KEYS if orientation_kind(s) == "edge"]:
        offset, view_up = orientation_pose(sign)
        offset = np.asarray(offset, dtype=float)
        view_up = np.asarray(view_up, dtype=float)
        perp = abs(float(np.dot(offset, view_up)))
        triple = np.asarray(sign, dtype=float)
        triple /= float(np.linalg.norm(triple))
        if perp > 1e-6 or float(np.dot(offset, triple)) < 1.0 - 1e-6 or view_up[1] <= 1e-6:
            failures.append(f"D FAIL: edge {sign} no longer outward+perpendicular projected-up")

    # --- E: source contract -------------------------------------------------------
    try:
        pose_src = inspect.getsource(orientation_pose)
        if "iso_corner_pose" in pose_src:
            failures.append("E FAIL: orientation_pose still routes corners through iso_corner_pose (wide-screen not dropped)")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"E FAIL: could not inspect orientation_pose: {exc!r}")
    if hasattr(nco, "iso_corner_pose"):
        failures.append("E FAIL: nav_cube_orientation.iso_corner_pose still exists -- the 0252 wide-screen corner pose was not removed")
    if not hasattr(nco, "nearest_orientation_up"):
        failures.append("E FAIL: nav_cube_orientation.nearest_orientation_up missing -- the FreeCAD roll port is not present")
    try:
        from KrakenOS.UI.services import nav_cube_widget as W

        press_src = inspect.getsource(W.NavigationCube.handle_left_press)
        if "orientation_pose(sign" not in press_src or "tuple(int(s) for s in sign)" not in press_src:
            failures.append("E FAIL: handle_left_press no longer forwards the picked sign into orientation_pose/apply")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"E FAIL: could not inspect NavigationCube: {exc!r}")

    return (not failures), failures


def main() -> int:
    passed, notes = run_checks()
    if passed:
        print("[PASS] nav-cube corners use the symmetric diagonal standard (ISO wide-screen dropped, bugs/0257)")
        return 0
    print("[FAIL] nav-cube corner-standard guard:")
    for note in notes:
        print(f"   - {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
