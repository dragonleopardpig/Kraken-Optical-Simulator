# 0160 — navigation cube: snap must zoom-to-extent like the preset buttons

User report: *"that little cube navigator, when click, the default zoom is not
extent window, very small, different from the behaviour from the top bar
buttons."*

Clicking the interactive navigation cube (bugs/0156/0157, `vtkCameraOrientationWidget`)
reorients the camera to a face/edge/corner but leaves the scene looking **tiny** —
the zoom does not re-fit the scene extent the way the top-bar preset buttons
(`set_camera_preset`) do.

## Root cause / gap

`vtkCameraOrientationWidget` rotates the camera **position** about the focal point
to look down the picked axis, preserving the focal point, the camera-to-focal
distance, **and the parallel scale** (the orthographic zoom). It never reframes.

The cube's two observers both forwarded to `_on_camera_interaction` — the shared
orbit/zoom backstop that re-fits the *clip range* (bugs/0048), re-squares the
perpendicular thickness labels (bugs/0128/0140) and re-places the view-relative
dimensions (bugs/0152). That backstop deliberately **never touches the parallel
scale**, because it also runs on every mouse orbit, where auto-zoom-to-extent
would fight the user's wheel zoom. So a cube snap kept whatever (often zoomed-out)
parallel scale was active → the scene rendered small.

By contrast the top-bar preset buttons (`set_camera_preset`) recompute the
parallel scale via `_parallel_scale_for_orthographic_fit` for the new basis and
recenter on the scene, so they always frame the whole model.

## Fix

Give the cube snap its own handler that reframes like a preset button
(`open3d_inspector.py`):

* New `Kraken3DInspector._fit_view_to_scene_for_current_orientation()` — frames
  the whole scene for the camera's **current** orientation, whatever it is. It
  generalises `set_camera_preset`'s fit: the cardinal presets fit axis-aligned
  spans, the Iso branch projects the eight scene-bounds corners onto the camera's
  right / true-up axes. The cube can land on any face/edge/corner, so this always
  uses the corner-projection fit. It recenters the focal point on the scene
  centre, keeps the cube's chosen view direction + view-up (slides the camera back
  along that direction by a preset-style `radius·2.2` distance), and sets the
  parallel scale to fit. Returns True when it reframed.
* New `Kraken3DInspector._on_navigation_cube_snap(*_args)` — the cube's
  `EndInteractionEvent` handler: `_fit_view_to_scene_for_current_orientation()`
  first, then the usual settled-orbit backstop
  (`_on_camera_interaction(None, "EndInteractionEvent")` re-fits the clip range
  / re-squares labels / re-places dims for the new basis), then a forced
  `render()`.
* The cube wiring now binds `EndInteractionEvent` → `_on_navigation_cube_snap`
  (was `_on_camera_interaction`); `InteractionEvent` keeps `_on_camera_interaction`
  for any intermediate frames.

**Why cube-only.** The reframe is bound ONLY to the cube widget's own
`EndInteractionEvent`, so a mouse orbit (which routes through
`_on_camera_interaction` on the *main* interactor) keeps its zoom. A cube snap is
a discrete "frame this view" gesture, so zoom-to-extent is exactly what the user
expects — and exactly what the top-bar buttons already do.

**Why recenter, not just rescale.** The user asked for the cube to match the
top-bar buttons, which recenter AND rescale. Recentering preserves the cube's
chosen view direction (so the picked face/edge/corner orientation is respected)
and only slides the camera along that direction + laterally to centre the scene —
in parallel projection the camera distance is irrelevant to the image, so this is
purely a framing adjustment.

## Guard

`KrakenOS/UI/validate_open3d_navigation_cube_zoom_fit.py` (penta Phase 151) —
display-free: binds the real `_fit_view_to_scene_for_current_orientation` and
`_on_navigation_cube_snap` to a light fake `self` whose fake renderer hands back a
fake camera recording `SetParallelScale` / `SetParallelProjection` /
`SetPosition` / `SetFocalPoint`, with `_camera_fit_bounds` returning a known
asymmetric box. Checks: the fit turns parallel projection ON and sets the scale to
the `_parallel_scale_for_orthographic_fit` value for the box's projected spans;
the focal point lands on the box centre; the view direction is preserved (the
cube's orientation is respected); `_on_navigation_cube_snap` calls the fit THEN
`_on_camera_interaction` with an End event THEN renders; a no-renderer / no-camera
snap is a safe no-op; and a source-contract that the cube wiring binds
`_on_navigation_cube_snap` to `EndInteractionEvent` and the snap consults the fit.

Phase 151 additionally drives the **live** inspector (Xvfb): from the Iso preset
it records the fitted parallel scale + sight line, then deliberately mis-zooms and
pans the camera (mimicking the unfitted post-snap state) and calls
`_fit_view_to_scene_for_current_orientation()`; the parallel scale returns to the
Iso fit (rel-error ≈0), the focal point returns to the scene centre, and the sight
line is unchanged (the orientation is preserved). A second, arbitrary
(edge-like) orientation is fit and the scene's projected extent is checked to fill
the viewport within the 1.08 margin.

## Notes

* The cube hover/click itself cannot be driven headless (the gizmo needs real
  pointer picks on the embedded VTK canvas), so the guard + live phase drive the
  underlying `_fit_view_to_scene_for_current_orientation()` — the exact method the
  cube observer calls.
* **In-app eyeball owed:** clicking a navigation-cube face/edge/corner should now
  frame the whole model at the same zoom as the matching top-bar preset button,
  instead of leaving it small.
