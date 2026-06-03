# 0010 — Hover edge highlights stranded after the Center-Row→Optical-Axis snap ("ghosts")

**Status:** Open — documented from the flag, not yet fixed.
**Component:** Open 3D inspector — the lens **hover edge highlight**
(`Kraken3DInspector._set_step_hover_outline` /
`_set_step_hover_outline_impl`, open3d_inspector.py ~10588; the cached actor
`_hover_step_outline_actor` keyed by `_hover_step_cell_key`) **vs** the
snap that repositions the lens without clearing it:
`_apply_center_row_to_optical_axis` (open3d_inspector.py ~10294), armed by
**Place → Center Row → Optical axis** (`start_center_row_to_ray`,
open3d_application_logic.py ~52).
**Reported via:** in-app recorder, flag `flag_20260603_171626_741`
(2026-06-03T17:16:26). **Repro bundles are gitignored**, so the evidence below
is transcribed here.

## Symptoms (user's words)

> still have ghost surfaces above the lens

Precise repro (user, at sign-off): the "ghosts" are actually the **highlighted
edges** that appear when the mouse hovers the **aspheric lens**.

1. Hover the aspheric lens → its edges highlight (the hover outline).
2. **Place → Center Row → Optical axis** → the lens **snaps** onto the optical
   axis (it moves).
3. But the highlighted edges **stay where they were** (the lens's pre-snap
   position). They sit there **invisible until the mouse hovers that — now
   empty — region again**, where they light up again.

So stale hover highlight / pick geometry is left behind at the lens's former
location after the snap; "a few elsewhere too" → several such ghosts accumulate
as the lens is repositioned more than once.

## State evidence

`flag_20260603_171626_741/state.json` (recording active, nothing selected):

* `selected_step_label = null`, `picked_step_label = null`,
  `picked_row_index = null` — nothing is selected; this is a passive hover.
* `step_actor_bounds["optical"]` = x[-12.50, 12.50] y[**-12.54, 12.46**]
  z[12.11, 23.69] — the imported lens body tops out at y ≈ +12.46.
* `scene_visible_bounds` y-max = **29.706** — a visible prop sits ~17 mm
  **above** the top of the lens body. That extra prop is the ghost.
* `cursor.png_xy = [546, 329]` — the cursor (and the floating gold rounded-rect
  + green/magenta hover crosshair + `OPTICAL STEP S002/F002 face` tooltip) are
  near the top-centre of the frame, well above the lens.
* `thickness_dimension_count = 0`, all handle counts `0` — no gizmo/overlay; the
  only "extra" geometry is the hover highlight itself.
* Lens is parked near the Object end (z ≈ 12.1–23.7); optical axis z = -65..165.

The screenshot shows the lens (side view, on-axis) with a small gold rounded
rectangle floating high above it, the hover crosshair, and the
`OPTICAL STEP S002/F002 face` tooltip — i.e. the face-hover highlight for face
F002 is being drawn as a tiny box up in empty space instead of on the face.

## Lead / suspected root cause (to confirm at fix time)

The snap repositions the lens but leaves the hover highlight (and the geometry
it is picked from) anchored at the *old* location. Threads to chase:

1. **Snap doesn't clear the highlight.** `_apply_center_row_to_optical_axis`
   moves the lens body onto the axis and rebuilds/repositions the body mesh, but
   does not appear to clear the active hover outline
   (`_set_step_hover_outline(None, None)`). The cached
   `_hover_step_outline_actor` lingers in the renderer at the pre-snap
   position. The many existing `_set_step_hover_outline(None, None, render=...)`
   clears fire on hover transitions and selection changes — but evidently *not*
   on this placement snap.
2. **Stale pick geometry.** "Invisible until I hover the region again, then they
   highlight" implies the face/edge geometry used for hover-picking still sits
   at the lens's former position after the snap, so hovering that now-empty
   region re-picks the stale face and re-draws its edge outline there. The snap
   needs to refresh the pick/hover geometry to the new position, not just the
   visible body.
3. **Hover-key short-circuit.** `_set_step_hover_outline` early-returns when
   `hover_key == _hover_step_cell_key`. After a move, re-hovering the *same*
   face key must still rebuild the outline at the new position — confirm the key
   is reset on reposition so the rebuild isn't skipped.

State corroboration: in `flag_20260603_171626_741` nothing is selected, the lens
body tops out at y ≈ +12.46, yet `scene_visible_bounds` y-max = **29.71** — a
visible prop ~17 mm above the body, i.e. a stranded highlight from a prior hover.

## Planned fix

TBD — once root-caused, keep it minimal: clear the hover outline **and** refresh
the hover/pick geometry whenever the lens is repositioned (the Center-Row snap
and any move/refresh), and reset `_hover_step_cell_key` so a re-hover rebuilds
at the new position. No stale outline should survive a reposition.

## Planned tests

* Display-free unit test: arm `start_center_row_to_ray`, hover a face to create
  an outline, run the snap, and assert no hover-outline actor / hover key
  survives at the old position (and a re-hover rebuilds at the new one) — without
  an X server.
* **Image-snapshot** (visual bug, mandatory): hover the aspheric lens (edges
  highlight), snap it to the axis, then assert **no** highlight pixels remain at
  the old location and a re-hover lights up the lens at its new position.
  Inspect by eye.
* Regression phase in `validate_open3d_penta_telescope_comprehensive.py`, then
  regenerate the gate baseline.
