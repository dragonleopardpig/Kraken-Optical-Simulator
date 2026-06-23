# 0112 — A selected element's move/rotate gizmo is buried behind an adjacent body

**Report (2026-06-23, flag_20260623_072036_710):**
> "when an element is selected the gizmo that hide under other element should
> highlight, not buried under it."

The flag bundle's `scene_state` has `selected_step_label = "optical"`; the
screenshot shows the selected pink **"optical"** optical solid whose move/rotate
gizmo (rotation arcs + arrowheads + translate arrows) is **buried** behind an
adjacent grey camera body. The handle you need to grab is hidden behind the
neighbour, so you can't see it — and a buried handle is awkward to pick.

---

## Root cause — gizmo handles share the scene's depth buffer

The gizmo handles were plain actors in the **main** renderer, so they were
depth-tested against every other body in the scene. When a neighbouring body
(e.g. a camera STEP) sits closer to the camera than a handle, that body wins the
depth test and the handle is occluded — exactly the "buried under it" the report
describes.

VTK 9.5.2 has **no clean per-actor depth-test disable** (no public
"always draw this actor in front" flag on `vtkActor`/`vtkProperty` that survives
the opaque pass). So the handles can't simply opt out of occlusion in place.

---

## Fix — render the gizmo handles in a dedicated always-on-top overlay renderer

The handles now live in a second `vtkRenderer` on its own layer that composites
over the finished scene:

- `SetLayer(2)` with `render_window.SetNumberOfLayers(3)` — above the main
  renderer (layer 0) and the orientation-marker widget (layer 1).
- `SetActiveCamera(self._renderer.GetActiveCamera())` — shares the main camera,
  so handles stay registered with the scene as the view orbits/pans/zooms.
- `SetPreserveColorBuffer(True)` — composite **over** the scene colour instead of
  clearing it (the scene stays visible underneath).
- `SetPreserveDepthBuffer(False)` — **clear the depth buffer** before drawing, so
  the handles are depth-tested only against each other and always draw in front
  of any scene body.
- `InteractiveOff()` — the overlay never steals interactor camera control.

`_add_mesh_actor(..., overlay_on_top=True)` routes a handle actor to the overlay
renderer instead of the main one. Every gizmo-handle creation site now passes it:

- **STEP rotation handles** (`open3d_step_rotation_handles.py`): all three handle
  kinds — rotation arc, arrowhead, translate arrow.
- **Placement handles** (`open3d_inspector.py`):
  `_add_scene_placement_translate_handles` and
  `_add_scene_placement_rotate_handles` (arc + arrowhead).

Handles are placed in the overlay renderer **only** (not duplicated in the main
renderer) to avoid a translucent double-blend; the arcs/arrows are semi-opaque,
so a second copy underneath would darken them.

### Keeping a buried handle grabbable (per-renderer picking)

`vtkCellPicker.Pick(x, y, z, renderer)` picks within **one** renderer by closest
geometry, not by what's drawn on top. With the handles moved to the overlay, a
pick of the main renderer alone would never see them. So the gizmo-interaction
pick sites now pick the **overlay first**, then fall back to the main renderer:

- `_pick_actor_with_gizmo_overlay(x, y)` — new helper: pick the overlay; if it
  returns an actor, use it; else pick the main renderer.
- `Open3DInteractionService._on_left_button_press` — picks the overlay first
  (`site="left_click_gizmo"`) when not in an active pick mode, so a click on a
  buried handle grabs the handle, not the body behind it.
- `Open3DInteractionService._passive_hover_pick_rotation_handle` — hovers the
  overlay renderer (`_gizmo_overlay_renderer or _renderer`) so a buried handle
  still hover-highlights.
- `_step_translate_state_from_current_pick` and
  `_placement_drag_state_from_current_pick` — drag-starts route through the
  overlay-first helper.

Non-gizmo pick sites (carry/measure/face-hover, `_axis_slide_state_*`,
`_apply_dimension_anchor_pick_motion`) deliberately keep picking the **main**
renderer — they resolve row bodies via `_actor_row_map`, never gizmos, so an
overlay-first pick there would be wrong (axis-slide) or is simply unaffected.

### Lifecycle — clear + remove on both renderers

- Full scene refresh (`open3d_scene_refresh.py`): after
  `self._renderer.RemoveAllViewProps()`, also
  `self._gizmo_overlay_renderer.RemoveAllViewProps()` so the next build's
  reconciled handles don't stack on stale overlay ones.
- Handle removal: `_remove_actor_from_renderers(actor)` strips an actor from
  **both** renderers; used by the rotation-handle service
  (`remove_actors` / `remove_for_label`) and
  `_remove_placement_rotation_handle_actors`, replacing the bare
  `self._renderer.RemoveActor(actor)`.

---

## Tests

- `python -m KrakenOS.UI.validate_open3d_gizmo_overlay_on_top` — two parts:
  - `run_checks()` (display-free, 7 source/structure assertions): the overlay
    renderer is declared and built with the right layer/preserve flags;
    `_add_mesh_actor` routes `overlay_on_top` actors to the overlay; the
    pick/remove helpers exist and the pick hits the overlay first; all three
    STEP rotation-handle kinds are on the overlay with dual-renderer removal and
    no bare remove; the inspector placement sites route ≥3 handles to the
    overlay; the full refresh clears the overlay; the interaction service picks
    the overlay first on click + hover.
  - `render_overlay_proof()` (image-snapshot, needs a GL context / Xvfb):
    reproduces the inspector's exact layered setup with a grey occluder cube in
    the main layer and a red gizmo cone geometrically **behind** it in the
    overlay, and asserts the gizmo pixel wins the centre (on top) while the same
    cone in the main layer stays occluded (grey). Verified under Xvfb: overlay
    centre RGB ≈ (239,13,13) red, main-layer centre RGB = (153,153,153) grey;
    PNG saved to `/tmp/gizmo_overlay_on_top.png`.
- Penta **phase 102** (new; baseline → 103 phases) runs `run_checks()` only (no
  rendering — keeps the validator marathon headless-safe).

In-app eyeball owed: headless can't drive a live VTK hover/drag pick — confirm
in-app that selecting an element whose gizmo sits behind an adjacent body now
draws the handles on top, and that hovering/grabbing a (formerly buried) handle
highlights and drags it.
