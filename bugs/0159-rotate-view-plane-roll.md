# 0159 — rotate-view: roll about the sight line in a plane view

User report (follow-up to bugs/0158): *"the behaviour of the rotation button is
correct in ISO view, but in plane view for example YZ plane, it should spin
around the perpendicular axis."* … *"spin around the axis that go into the center
of the Monitor."*

So the 0158 rotate-view buttons are **right for an oblique / Iso view** but
**wrong for a face-on plane view** (the YZ/XY/XZ presets). There the rotate must
spin the plane *in place* about the axis pointing straight into the screen — the
sight line — not swing the camera onto a neighbouring face.

## Root cause / gap

0158 always called `vtkCamera.Azimuth(±90)` — a turntable about the **view-up**
vector. That is exactly right for an oblique view (Iso), where it views the scene
from the opposite side after two clicks. But in a face-on plane view the sight
line is along a principal axis and the view-up is perpendicular to it, so an
azimuth **rotates the camera position 90° around the view-up and lands it looking
down a *different* principal axis** — e.g. a YZ view (`+yz`, looking −X, up +Y)
azimuths into an XZ-ish view. The plane the user was looking at swings away
instead of spinning in place.

## Fix

Make the rotation **axis view-aware** (`open3d_inspector.py`):

* New `Kraken3DInspector._camera_sight_line_is_axis_aligned(camera)` — normalises
  the sight line (`focal − position`) and returns True when its largest component
  is ≈1 (the other two ≈0), i.e. the camera looks straight down ±X/±Y/±Z. The
  cardinal presets set this exactly; the Iso preset is oblique (~0.7 each).
* `rotate_camera_azimuth` is renamed `rotate_camera_view` and now branches:
  * **axis-aligned (plane view)** → `camera.Roll(±90)` — a roll about the sight
    line, the axis into the monitor, so the plane spins in place.
  * **oblique / Iso** → `camera.Azimuth(±90)` — the unchanged 0158 turntable.
  The rest is identical: treat the jump like a *settled* orbit
  (`_on_camera_interaction(None, "EndInteractionEvent")` re-fits clip range
  bugs/0048, re-squares perpendicular thickness labels bugs/0128/0140, re-places
  view-relative dimensions bugs/0152), then force a `render()`.
* The two View-toolbar buttons (`panels/open3d_top_controls.py`
  `build_view_toolbar`) now call `rotate_camera_view(±90)`.

**Why a roll keeps the plane face-on.** `vtkCamera.Roll` rotates the view-up
*about the direction of projection*; it never moves the camera position or focal
point, so the sight line into the screen is invariant — the plane stays face-on
and only spins. Four 90° rolls return the view-up to the start (4×90° = identity),
so it is a true turntable about the into-the-monitor axis. (Azimuth is still kept
for the oblique case, where bugs/0158's "no `OrthogonalizeViewUp`" rule still
holds — re-tilting the view-up would drift the turntable axis.)

## Guard

`KrakenOS/UI/validate_open3d_navigation_cube_rotate.py` (penta Phases 149+150) —
display-free: binds the real `rotate_camera_view` to a light fake `self` whose
fake renderer hands back a fake camera that **records** `Azimuth`/`Roll` calls and
exposes a controllable sight line. Checks: an **oblique** sight line forwards
`Azimuth(±90)` (not `Roll`); a **plane** sight line forwards `Roll(±90)` (not
`Azimuth`); the real discriminator `_camera_sight_line_is_axis_aligned` is True
for a principal-axis sight line and False for the Iso one; `OrthogonalizeViewUp`
is never called; no renderer/camera is a safe no-op; a raising rotation returns
before the refit/render; and a source-contract that `build_view_toolbar` wires
`rotate_camera_view` and the method calls both `.Azimuth(` and `.Roll(`.

Phase 150 additionally drives the **live** inspector (Xvfb): from the `+yz` plane
preset, `rotate_camera_view(90)` four times keeps the **sight line fixed** (a roll
never moves the camera position → it did NOT azimuth off the plane), moves the
view-up a real amount each click, and returns the view-up **exactly** to the start
after 4×90°.

## Notes

* Headless drive (Phase 150, Xvfb): `+yz` sight line axis-aligned; after 1–4×90°
  the sight-line drift is `0.0000` (the plane stays face-on) while the view-up
  rotates by √2≈`1.4142` per click and returns to start with delta `0.0000`.
* Phase 149 (Iso azimuth) re-ran green after the rename: 4×90° back-to-start
  `0.0000`, 2×90° opposite-side residual `0.0000`, min per-click move `1.2931`.
* The interactive cube (0156/0157) and the oblique-view turntable (0158) are
  unchanged.
* **In-app eyeball owed:** the camera math is fully headless-verified; the felt
  behaviour — in a YZ/plane view the rotate buttons spin the plane in place about
  the into-the-monitor axis, while Iso still swings to the opposite side — should
  be eyeballed in the running app, along with the ↺/↻ glyphs (bugs/0158).
