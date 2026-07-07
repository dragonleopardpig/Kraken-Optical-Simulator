#!/usr/bin/env python3
"""Display-free guard for bugs/0252: clicking a navigation-cube CORNER frames the scene
the same way the ISO toolbar button does -- for every octant.

Why it exists (user flags 2026-07-08, `flag_20260708_073846_983` "The ISO button" +
`flag_20260708_073911_591` "Corner at the Nav Cube"):
  The ISO button gives a flat, upright, wide-screen-friendly 3/4 view (offset
  ``(-0.95, 0.55, 0.8)``, world-+Y up, ~23.9 deg elevation). But clicking the cube corner
  in the SAME octant (TOP+LEFT+FRONT = ``(-1,+1,+1)``) used to give a STEEPER symmetric
  ``(+-1,+-1,+-1)`` diagonal (35.3 deg) with a projected up -- a different picture that
  also framed the long optical axis worse on a wide screen. The user asked: "make the
  Corner clicking the same orientation as the ISO view (apply similar orientation to all
  corners)" and "the ISO fits the wide screen better".

The fix (nav_cube_orientation.orientation_pose) routes CORNERS through ``iso_corner_pose``:
the world up-axis takes the small 0.55 elevation, the other two axes the 0.95/0.8 spread,
each with the picked octant's sign, view_up world-+Y -- so every corner reproduces the ISO
view for its octant. Faces stay the cardinal presets; edges keep the projected-up rule.

What it checks (no display required, pure math + source contract):
  A. All 8 corners == iso_corner_pose: unit offset, world-+Y view_up, sign-consistent octant.
  B. The ISO octant corner ``(-1,+1,+1)`` equals the ISO button direction ``(-0.95,0.55,0.8)``
     normalized -- cube corner and toolbar button are the SAME camera.
  C. Every corner sits at the ISO elevation (~23.9 deg), NOT the old symmetric 35.3 deg.
  D. Regression: the 6 faces are still the cardinal presets and the 12 edges still use the
     perpendicular projected-up rule (this bug only touched corners).
  E. Source contract: orientation_pose dispatches corners to iso_corner_pose, and the widget
     forwards the ISO up-axis into the corner pose.
  F. up-axis generalization: iso_corner_pose honours a non-default up-axis (z -> +Z up).
"""
from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.services.nav_cube_orientation import (
    ORIENTATION_KEYS,
    iso_corner_pose,
    orientation_kind,
    orientation_pose,
)

# The historic ISO toolbar direction (open3d_inspector._iso_camera_offset_and_view_up, y-up).
_ISO_DIR = np.array([-0.95, 0.55, 0.8], dtype=float)
_ISO_DIR = _ISO_DIR / float(np.linalg.norm(_ISO_DIR))
_ISO_ELEVATION_DEG = float(np.degrees(np.arcsin(abs(_ISO_DIR[1]))))  # ~23.88
_SYMMETRIC_ELEVATION_DEG = float(np.degrees(np.arcsin(1.0 / np.sqrt(3.0))))  # ~35.26 (the old one)


def run_checks():
    """Return ``(passed, notes)`` -- notes is a list of failure strings (empty on pass)."""
    failures: list[str] = []

    corners = [s for s in ORIENTATION_KEYS if orientation_kind(s) == "corner"]
    if len(corners) != 8:
        failures.append(f"expected 8 corners, got {len(corners)}")

    # --- A: every corner is the ISO-style per-octant pose -------------------------
    for sign in corners:
        offset, view_up = orientation_pose(sign)
        want_off, want_up = iso_corner_pose(sign)
        offset = np.asarray(offset, dtype=float)
        view_up = np.asarray(view_up, dtype=float)
        if not np.allclose(offset, want_off, atol=1e-9) or not np.allclose(view_up, want_up, atol=1e-9):
            failures.append(f"A FAIL: corner {sign} pose != iso_corner_pose {want_off},{want_up}")
            continue
        if abs(float(np.linalg.norm(offset)) - 1.0) > 1e-9:
            failures.append(f"A FAIL: corner {sign} offset not unit ({np.linalg.norm(offset):.4f})")
        if not (abs(view_up[0]) < 1e-9 and abs(view_up[2]) < 1e-9 and view_up[1] > 1.0 - 1e-9):
            failures.append(f"A FAIL: corner {sign} view_up {view_up.tolist()} is not world-+Y")
        if not np.all(np.sign(offset).astype(int) == np.asarray(sign, dtype=int)):
            failures.append(f"A FAIL: corner {sign} offset {np.round(offset,3).tolist()} leaves the octant")

    # --- B: the ISO octant corner == the ISO toolbar direction --------------------
    iso_off, iso_up = orientation_pose((-1, 1, 1))
    if not (np.allclose(iso_off, _ISO_DIR, atol=1e-9) and np.allclose(iso_up, [0.0, 1.0, 0.0], atol=1e-9)):
        failures.append(
            f"B FAIL: ISO octant (-1,1,1) offset {np.round(iso_off,4).tolist()} != ISO button "
            f"{np.round(_ISO_DIR,4).tolist()} (up {list(iso_up)})"
        )

    # --- C: corners sit at the ISO elevation, not the old symmetric 35.3 deg ------
    for sign in corners:
        offset = np.asarray(orientation_pose(sign)[0], dtype=float)
        elev = float(np.degrees(np.arcsin(abs(offset[1]))))
        if abs(elev - _ISO_ELEVATION_DEG) > 0.1:
            failures.append(f"C FAIL: corner {sign} elevation {elev:.2f} deg != ISO {_ISO_ELEVATION_DEG:.2f} deg")
        if abs(elev - _SYMMETRIC_ELEVATION_DEG) < 0.1:
            failures.append(f"C FAIL: corner {sign} still at the old symmetric {elev:.2f} deg")

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
        if "iso_corner_pose" not in pose_src or '"corner"' not in pose_src:
            failures.append("E FAIL: orientation_pose no longer routes corners to iso_corner_pose")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"E FAIL: could not inspect orientation_pose: {exc!r}")
    try:
        from KrakenOS.UI.services import nav_cube_widget as W

        press_src = inspect.getsource(W.NavigationCube.handle_left_press)
        if "up_axis" not in press_src or "orientation_pose(sign" not in press_src:
            failures.append("E FAIL: handle_left_press no longer forwards up_axis into orientation_pose")
        init_src = inspect.getsource(W.NavigationCube.__init__)
        if "iso_up_axis" not in init_src:
            failures.append("E FAIL: NavigationCube.__init__ no longer accepts iso_up_axis")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"E FAIL: could not inspect NavigationCube: {exc!r}")

    # --- F: up-axis generalization (z-up puts the elevation on +Z) ----------------
    off_z, up_z = iso_corner_pose((-1, 1, 1), up_axis="z")
    if not np.allclose(up_z, [0.0, 0.0, 1.0], atol=1e-9):
        failures.append(f"F FAIL: iso_corner_pose up_axis='z' view_up {list(up_z)} != +Z")
    if abs(float(np.degrees(np.arcsin(abs(off_z[2])))) - _ISO_ELEVATION_DEG) > 0.1:
        failures.append("F FAIL: iso_corner_pose up_axis='z' does not put the ISO elevation on +Z")

    return (not failures), failures


def main() -> int:
    passed, notes = run_checks()
    if passed:
        print("[PASS] nav-cube corners reproduce the ISO view for every octant (bugs/0252)")
        return 0
    print("[FAIL] nav-cube corner-ISO guard:")
    for note in notes:
        print(f"   - {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
