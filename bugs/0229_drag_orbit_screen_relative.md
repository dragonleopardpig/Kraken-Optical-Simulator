# 0229 — dragging the 3D canvas did not orbit as intended in a rolled view

**Status: FIXED. Mouse-drag orbiting is now screen-relative in ANY view roll: a left-right drag
orbits about the screen-vertical axis (the current view-up), a top-bottom drag about the
screen-right axis. In an unrolled view the feel is identical to before. In-app confirm owed.**

## The report

"dragging the 3D canvas from left to right does not orbit as intended, same as dragging from top
to bottom" — reported right after using the new 0228 rotate buttons, i.e. in a ROLLED view
(the flag state shows `camera_view_up = (0, 0, -1)`).

## Root cause

`_orbit_camera_pose` (the bugs/0206 trackball) azimuthed horizontal drags about a **hard-coded
world +Y** ("turntable feel") — correct only while the view-up IS +Y. Once the view is rolled
(exactly what the 0228 rotate buttons do), world +Y points sideways/into the screen, so a
horizontal drag visibly spun the scene about a wrong-looking axis; the vertical drag's
screen-right axis derives from the up, so the whole gesture frame felt wrong.

## The fix

The azimuth axis is now the **current view-up** (the screen-vertical). Properties:
- unrolled views (up == +Y): byte-identical to the old turntable — no feel change;
- rolled views: both drag directions are screen-relative, as intended;
- a pure horizontal drag leaves the up untouched (a rotation about itself);
- this actually matches `vtkCamera.Azimuth`'s own definition (rotation about the view-up),
  which is why the guard's "below-pole pose-identical to VTK" check still passes at 2.6e-13 mm.

## Verification

`validate_open3d_drag_orbit_no_flip` extended with check (7): in a rolled view
(up = (0,0,−1)) a horizontal drag keeps the up bit-identical, keeps the offset's along-up
component invariant (the rotation plane ⊥ the screen-vertical), and actually moves the camera.
All prior checks (no flip over the pole, continuity, radius preservation, VTK below-pole parity,
no cross-coupled tilt) stay green; `validate_camera_iso_orbit_no_clip` green.
