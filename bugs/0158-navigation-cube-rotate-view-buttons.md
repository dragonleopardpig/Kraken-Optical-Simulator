# 0158 — rotate-view buttons (90° turntable, forward/reverse)

User report (follow-up to bugs/0156/0157): *"I am at ISO view, I want: click a
rotate button … Object Plane change from North-West to North-East. Click again
rotate another 90 degree, now located at South-East … For YZ view or any other
plane view, clicking such rotating buttons (forward and reverse) will rotate the
whole scene 90 degree as well. Refer what the cube navigator of FreeCAD does."*

Clarified by the user: this is **not** the click-to-snap-a-face behaviour that
bugs/0157 wired up. It is FreeCAD's navigation-cube **rotate arrows** — each click
swings the whole view 90°, and *"swing around the different side"*: at ISO an
object at NW facing SE ends, after two clicks (180°), at SE facing NW, with the
image plane taking the object plane's former screen spot.

## Root cause / gap

The interactive cube (`vtkCameraOrientationWidget`, bugs/0156) and its click
forwarding (bugs/0157) only ever **snap** the camera to a face/edge/corner
orthographic view. Nothing in the canvas sweeps the view by a fixed 90° step about
the scene, so there was no "rotate the whole scene 90°, forward and reverse"
control at all — only the seven fixed Iso/±YZ/±XY/±XZ preset jumps.

## Fix

A turntable rotation about the **view-up** vector, centred on the focal point —
exactly `vtkCamera.Azimuth(±90)`.

* New `Kraken3DInspector.rotate_camera_azimuth(angle_deg)` (next to
  `set_camera_preset`): `camera.Azimuth(angle_deg)`, then treat the jump like a
  *settled* orbit by calling `_on_camera_interaction(None, "EndInteractionEvent")`
  (re-fit clip range bugs/0048, re-square perpendicular thickness labels
  bugs/0128/0140, re-place view-relative dimensions bugs/0152), then force a
  `render()` — a button press, unlike a mouse orbit, has no VTK interaction event
  to trigger one.
* Two buttons in the View toolbar (`panels/open3d_top_controls.py`
  `build_view_toolbar`), right after the cardinal preset buttons: a **Rotate**
  label then **↺** (`rotate_camera_azimuth(-90)`) and **↻**
  (`rotate_camera_azimuth(+90)`).

**Why no `OrthogonalizeViewUp()`.** The obvious-looking "tidy the view-up after
rotating" call is a trap here: it re-tilts the view-up onto the new, slanted sight
line, so the *next* azimuth rotates about a drifting axis. With it in, four 90°
clicks did **not** return to the start (the +Y vertical leaked out of the
direction). Leaving the view-up fixed makes every click rotate about the same
axis, so it is a true turntable: 4×90° == identity, 2×90° == the opposite side.
VTK renders a non-perpendicular view-up fine (the Iso preset itself uses a
view-up that is not perpendicular to its sight line).

## Guard

`KrakenOS/UI/validate_open3d_navigation_cube_rotate.py` (penta Phase 149) —
display-free: binds the real `Kraken3DInspector.rotate_camera_azimuth` to a light
fake `self` whose fake renderer hands back a fake camera that **records**
`Azimuth` calls (and asserts `OrthogonalizeViewUp` is *not* called). Checks that
`+90`/`-90` forward straight to `camera.Azimuth`, that the settled-orbit refit and
a render are invoked, and that no renderer/camera is a safe no-op. Plus a
source-contract that `build_view_toolbar` wires both `rotate_camera_azimuth(90)`
and `rotate_camera_azimuth(-90)` buttons.

Phase 149 additionally drives the **live** inspector (Xvfb): from an Iso reset,
`rotate_camera_azimuth(90)` four times returns the sight line **exactly** to the
start; two clicks (180°) negate the horizontal (X,Z) components and preserve the
vertical (view-up Y) — i.e. the scene is viewed from the opposite side — and each
click moves the sight line by a real amount.

## Notes

* Headless probe (`/tmp/probe_rotate.py`, Xvfb): iso dir `[-0.699, 0.405, 0.589]`,
  view-up `+Y`; after 1–4×90° the Y-component stays `0.405` while X,Z rotate;
  4×90° back-to-start delta `0.0000`; 2×90° horizontal-flip and vertical-keep
  residuals `0.0000`; min per-click sight-line move `1.29`.
* The interactive cube (0156/0157) is left in place — clicking a face still snaps
  to that orthographic view; these buttons add the orthogonal "sweep 90°" motion.
* **In-app eyeball owed:** the camera math is fully headless-verified; the button
  glyphs (↺/↻, same font path as the existing ⚑/◀/▶ controls) and their placement
  in the toolbar should be eyeballed in the running app.
