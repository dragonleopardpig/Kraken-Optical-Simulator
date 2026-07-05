# 0228 — the rotate-view buttons must spin about the axis INTO the monitor, in every view

**Status: FIXED. The rotate-view toolbar buttons now ROLL the view about the sight line — the
axis going straight into the monitor — in EVERY view (ISO/oblique included), per the user's 4-step
recording. The sight line never changes, the picture rotates in place, and four 90° clicks return
exactly to the start. In-app confirm owed.**

## The flags

`flag_20260705_1354xx` ×4 ("before rotation" → "rotate once" → "rotate twice" → "rotate 3 times"),
with: "regarding the Rotation of the ISO scene. It should rotate through the axis into the
Monitor." The screenshots show each click orbiting the scene ~90° about the world-vertical axis —
the object FOV walking around the beam column (left → behind → right) — instead of the picture
spinning in place.

## History

- bugs/0158: the buttons were added as a turntable (`vtkCamera.Azimuth`) everywhere.
- bugs/0159: face-on plane views became a ROLL about the sight line ("the axis that go into the
  center of the Monitor") because azimuth swung the camera off the plane; ISO kept the turntable.
- bugs/0228 (this): the user's recording shows the ISO turntable is not wanted either — the
  rotation axis should be the screen normal in every view.

## The fix

`rotate_camera_view` now always calls `camera.Roll(angle_deg)` — the view-aware branch and its
`_camera_sight_line_is_axis_aligned` consultation are gone (the helper remains for other users).
Properties that fall out of a pure roll: the sight line is bit-invariant (nothing can swing to
another side of the scene), and 4×90° restores the exact starting view.

## Verification

`validate_open3d_navigation_cube_rotate` rewritten to the new contract (its penta phase runs it
unchanged): ISO and plane views both forward exactly `Roll(±90)` and NEVER `Azimuth` (the flagged
behaviour is an explicit failure message), the settled-orbit refit + forced render still run, a
REAL `vtkCamera` at the Iso pose keeps its sight line bit-identical across rotates and returns its
view-up after 4×90° (drift < 1e-6), no `OrthogonalizeViewUp`, no-op/raise safety, and the toolbar
wiring.
