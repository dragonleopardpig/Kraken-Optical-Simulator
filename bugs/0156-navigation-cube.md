# 0156 — Genuine FreeCAD-style navigation cube for the Open 3D canvas

User request (refer `attachment/2D.png`): *"can we have this kind of navigation
ball? I need to rotate the canvas view, for example, the object plane is now located
at North-West direction facing South-East, I want to be able to rotate it so that the
direction is reversed (object at South-East facing North-West). So to make it general,
I think better to add a Navigation Ball just like FreeCAD."*

Rework request (this iteration): the first cut wired VTK's native
`vtkCameraOrientationWidget`, but the user found it *"far from the cube function"* —
it renders as an axis ball, not a labelled cube. The ask sharpened to a **genuine
FreeCAD navigation cube**: full face **+ edge + corner** interaction (all 26 standard
orientations), **CAD-word labels** (FRONT/BACK/TOP/BOTTOM/LEFT/RIGHT), **plus discrete
rotation-step arrows** for angled/oblique views.

## What shipped

A custom, self-drawn navigation cube — `KrakenOS.UI.services.nav_cube_widget.
NavigationCube` — replaces `vtkCameraOrientationWidget` entirely. It is a real labelled
cube parked in the upper-right corner:

* **26 clickable orientations.** Clicking a **face** snaps to the six ortho presets
  (FRONT/BACK/TOP/BOTTOM/LEFT/RIGHT); clicking an **edge** gives the twelve 45° edge
  views; clicking a **corner** gives the eight isometric "angled" views. The opposite
  handle reverses the look direction — the original "reverse NW-facing-SE to
  SE-facing-NW" ask.
* **CAD-word labels.** An annotated cube carries the face words with the mapping
  +Z=FRONT, +Y=TOP, +X=RIGHT (and their negatives), matching the toolbar presets.
* **Discrete rotation-step arrows.** Six screen-fixed arrow handles apply a 45°
  step: roll (ccw/cw about the sight line), azimuth (left/right), elevation (up/down)
  — the "angled view" stepping the axis ball could not do.

It sits alongside the five fixed Iso / ±YZ / ±XY preset buttons and the passive
lower-left axes marker.

## Design

* **All camera MATH is VTK-free.** `nav_cube_widget` draws and picks; every
  orientation decision lives in `KrakenOS.UI.services.nav_cube_orientation` — a pure
  module (`classify_pick`, `orientation_pose`, `roll_view_up`, `FACE_LABELS`,
  `ORIENTATION_KEYS`, `STEP_KINDS`). Faces resolve to the *same* pose as
  `set_camera_preset`, so cube and toolbar never drift. Unit-tested standalone by
  `validate_open3d_nav_cube_orientation` (26 orientations partition 6/12/8, faces ==
  presets, roll == `vtkCamera.Roll`).

* **Two dedicated overlay renderers.** The cube lives on its own renderer (layer 3)
  whose camera is *mirrored* to the main camera each render (a `StartEvent` observer →
  `sync()`), so the cube always shows the scene's current orientation and its local
  axes equal world axes (a screen pick maps straight to a cube-local hit point — no
  inverse transform). The arrows live on a *screen-fixed* renderer (layer 4); its
  camera reframes each render (`_sync_arrow_camera`) to keep the horizontal azimuth
  arrows on-screen at any pixel aspect (the miss that hid them on a portrait 3D pane —
  half-width grows by `1/aspect`, `_ARROW_FIT_HALF = 1.42`). Both share the corner
  viewport `_CUBE_VIEWPORT = (0.80, 0.78, 0.995, 0.995)`, clear of the lower-left axes
  marker.

* **The cube does its OWN picking.** The app owns every left-click at the Tk level
  (`_install_pick_only_left_click_bindings` *replaces* the interactor's button
  bindings and dispatches a plain scene pick directly), so the interactor button
  events a VTK widget would observe never fire — the reason the first axis-ball cut was
  deaf. Instead the Tk left-press runs the service's
  `_handle_navigation_cube_left_press`, which forwards the interactor event position to
  `NavigationCube.handle_left_press`: it picks the **arrow** renderer first (a discrete
  step), then the **cube surface** (`classify_pick` → `orientation_pose`). A Ctrl-click
  falls through to the camera-orbit path.

* **Opaque pick cube.** `vtkCellPicker` skips opacity-0 actors, so the pick geometry
  is a separate **opaque** unit cube behind the labelled annotated cube. Arrow handles
  are matched back to their step kind by VTK object identity (strong refs; `is` /
  `GetAddressAsString`, since `id()` is unstable).

* **Each snap reuses the orbit backstop + zoom-to-extent.** A face/edge/corner pick
  (`_apply_navigation_cube_orientation`) and a step arrow
  (`_apply_navigation_cube_step`, `vtkCamera.Roll/Azimuth/Elevation(±45)`) both route
  through `_on_navigation_cube_snap` → `_fit_view_to_scene_for_current_orientation`
  (recenter + zoom-to-extent like the preset buttons, bugs/0160) → `_on_camera_
  interaction` (re-fit clip range bugs/0048; re-square thickness labels bugs/0128,0140;
  re-place view-relative dims bugs/0152) → render. No new bookkeeping — the tested orbit
  path is reused.

* **Degrades cleanly.** Built in `Kraken3DInspector.__init__` after `Initialize()`
  (interactor live); a `NavigationCube` with no render window reports
  `available is False` and the inspector runs without it.

## Guards

* `validate_open3d_nav_cube_orientation` — the pure orientation math (folded into
  penta **Phase 147**).
* `validate_open3d_navigation_cube` (**Phase 147**) — widget/module contract:
  `STEP_KINDS` is the six roll/azimuth/elevation kinds; `_import_vtk` resolves the VTK
  classes; defensive construction with no window → `available False`; `__init__` builds
  and stores `self._navigation_cube` with the three callbacks; the routed inspector
  methods run `_on_navigation_cube_snap`, the step applies Roll/Azimuth/Elevation, the
  press gates on Ctrl + reads the event position, and `_on_camera_interaction` re-fits
  the clip + re-squares labels.
* `validate_open3d_navigation_cube_click` (**Phase 148**) — click routing: an
  out-of-viewport / unavailable click is ignored; an arrow hit fires `apply_step` and
  does NOT pick the cube; a face hit classifies and fires `apply_orientation` with the
  matching pose; a miss fires nothing; the inspector seam forwards a plain click and
  gates Ctrl; and the retired VTK button-event forwarding helpers are gone.
* `validate_open3d_navigation_cube_zoom_fit` (**Phase 151**) — a snap recenters +
  zooms-to-extent; its check E now asserts the routed callbacks run the snap (the old
  `EndInteractionEvent` observer binding is retired).

Phases 147/148 also drive the **live** inspector under Xvfb: the cube is available with
its cube/arrow renderers on layers 3/4 anchored upper-right (147); and scanning a pixel
grid over the corner viewport routes ≥ 2 distinct orientations **and** at least one
step arrow through the real service helper (148) — proving "I click the view never
change" is fixed end-to-end.

## Notes

* Verified end-to-end under Xvfb (`/tmp/nav_cube_integration_probe.py` and a targeted
  Phase 147–151 harness): available, layers 3/4, all six faces aim the camera == the
  presets, roll keeps the sight line fixed while turning the view-up, azimuth moves the
  sight line, and a 13×13 corner grid routed 22 distinct orientations + all six step
  kinds through `service._handle_navigation_cube_left_press`.
* **Phase 149** (toolbar rotate-view roll) fails *under llvmpipe/Xvfb only* — the iso
  preset's stored view-up is not perpendicular to its sight line under software
  rendering, so two 90° rolls don't flip the picture (residual 0.81). Confirmed
  **pre-existing and renderer-sensitive**: it fails identically with this change
  stashed, and the baseline (generated on a clean GPU) has it passing. Not a
  regression from this work.
* The full Xvfb penta marathon was deliberately **not** run (documented
  SIGSEGV/login-stall risk); the nav-cube phases were isolation-verified with a
  targeted harness.
* **In-app eyeball owed:** the cube's actual *appearance* (label legibility, arrow
  placement, hover feel) renders through the embedded VTK canvas, which the headless
  harness can't judge — the wiring, routing and camera math are proven; the visual
  polish needs an in-app confirm.
