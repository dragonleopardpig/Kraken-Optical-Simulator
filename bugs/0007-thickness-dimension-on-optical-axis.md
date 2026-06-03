# 0007 — Thickness dimension sits on the optical axis instead of offset to the side

**Status:** Fixed. The Open 3D Thickness dimension's double-ended arrow now
offsets into the *screen plane* (perpendicular to both the optical axis and the
camera view direction), so it reads to the side of the axis like the 2D layout's
physical-distance arrows, instead of collapsing onto the axis.
**Component:** Open 3D inspector — Thickness dimension overlay
(`Open3DThicknessDimensionService.add_overlays` / `offset_direction`).
**Reported via:** in-app recorder, flag `flag_20260603_113015_140`
("Thickness should be shown offset from the optical axis, just like how we put a
double ended arrow to annotate distance.").

## Symptoms (user's words)

> Thickness should be shown offset from the optical axis, just like how we put a
> double ended arrow to annotate distance.

State (`scene_state`): `thickness_dimension_count: 2`, `selected_step_label:
"optical"`, the optical axis runs along world **Z**
(`optical_axis_records … points [[0,0,-65],[0,0,165]]`), and the camera is the
default side view — `camera_position [-220.02, -0.096, 50]`, `camera_focal
[-0.023, -0.096, 50]`, `camera_view_up [0,1,0]` ⇒ the camera looks along world
**+X**. The screenshot shows the "S0 Thickness = … mm" label sitting directly on
the blue dashed optical axis, overlapping the lens body and the transform gizmo,
unreadable.

## Behaviour before

`add_overlays` draws each non-zero thickness as a double-ended arrow offset from
the surface-to-surface segment by `offset_direction(segment)`. `offset_direction`
returned a purely geometric perpendicular: for a segment along the reference
axis it cross-products with a fallback reference, and **for an optical-axis
(world-Z) segment it returns world -X**:

```
direction = (0,0,1) ⇒ |dot((0,0,1))| > 0.90 ⇒ reference = (0,1,0)
side = cross((0,0,1),(0,1,0)) = (-1,0,0)
```

In the default side view the camera looks along **+X**, so world -X is exactly
the **depth** axis (into the screen). The arrow and label were therefore offset
straight into the screen — their projection landed *on* the optical axis. The
offset magnitude (`base_offset = scene_span*0.045`) was irrelevant: any
displacement along the view direction projects to zero on screen.

## Root cause

`offset_direction` was camera-unaware. A dimension offset is only readable if it
lies in the **screen plane**; a perpendicular chosen from world axes alone can
point straight down the camera's view direction, which is what happened for the
canonical optical-axis-along-Z / side-view-along-X arrangement.

A second, lesser issue: even offset correctly, the arrow stood only ~4.5 % of the
view span off the axis and hugged the dashed axis line, whereas the 2D layout's
reference physical-distance arrows stand ~8 % off (`results_display`
`_draw_physical_distances`: `arrow_x = x0 + 0.08*span_x`).

## Fix

`KrakenOS/UI/services/open3d_thickness_dimensions.py`:

* `offset_direction(segment, view_normal=None, screen_up=None)` is now
  camera-aware. Given a `view_normal` it returns `cross(view, segment)`
  normalized — perpendicular to *both* the view direction (so the offset lies in
  the screen plane and is visible) and the segment (a proper dimension offset).
  `screen_up` only fixes the sign so the dimension sits consistently below the
  axis on screen. When the segment runs along the view axis (looking straight
  down the optical axis) it falls back to an in-screen direction. With no camera
  it preserves the old geometric perpendicular, so the non-camera caller (the
  STEP translate-gap overlay) is unchanged.
* `add_overlays` fetches `inspector._camera_view_normal()` and
  `inspector._camera_screen_world_axes()` and passes them into
  `offset_direction`, and raises the offset to `scene_span*0.08` (floored at
  2 mm) to match the 2D distance-arrow margin so the double-ended arrow clearly
  clears the axis.

For the default side view (view +X, optical axis +Z) the offset is now
`(0,-1,0)` — straight down on screen, perpendicular to the axis — instead of the
invisible `(-1,0,0)` depth offset.

## Tests

* **`validate_open3d_thickness_dimension_offset`** (display-free) — pins the
  camera-aware seam at a range of camera/axis orientations: the offset is
  perpendicular to the view direction (in the screen plane), perpendicular to the
  segment, and unit length; the default side view offsets along screen -Y with no
  depth (X) component; the looking-down-the-axis degenerate case still yields an
  in-screen offset; and a no-camera call preserves the legacy perpendicular.
  Source-couples `add_overlays` so it can't silently drop the camera vectors.
* **`validate_open3d_thickness_dimension_offset_snapshot`** (image-snapshot,
  boots its own Xvfb) — builds a two-gap system, renders the scene with the
  dimensions off then on, diffs the frames to isolate the dimension pixels, and
  asserts they (a) actually rendered, (b) sit a real distance off the projected
  optical axis, and (c) fall almost entirely on **one side** of the axis (the
  depth bug straddled it symmetrically). The fixer opens the PNG and confirms the
  double-ended arrow stands clearly below the axis with a readable label.
* **Regression / end-to-end** — `Phase 14` in
  `validate_open3d_penta_telescope_comprehensive.py`: builds the system, turns
  the dimensions on, and for every rendered dimension actor asserts its offset
  from the on-axis reference midpoint has a negligible component along the camera
  view direction (it lies in the screen plane) and a real in-screen magnitude;
  also re-checks the live-camera seam. Needs no external fixture, so it always
  runs.
