# 0004 — STEP transform: combine rotate + translate into one Move/Rotate gizmo; arrows must clear the arcs; free axial travel; live edge-gap readout

**Status:** Fixed. The selected optical STEP overlay now carries ONE
combined Move/Rotate gizmo: three rotation arcs (six signed pick
arrowheads) plus three free-translation arrows whose grab heads reach
past the arcs. The arrows hover-highlight gold, press-hold-drag the body
1:1 with the cursor along a virtually-infinite axis (no track-length
clamp), and -- while dragging -- show a live edge-gap thickness overlay
to the previous component. The redundant "Slide along axis" checkbox
widget was retired (its state var stays dormant so the existing
slide-mode validators keep passing).
**Component:** Open 3D inspector — STEP overlay transform handles + carry toolbar
**Reported via:** in-app recorder, `attachment/recorded_bug_repros/flag_20260603_092347_494/`
("no slide handles"), and the follow-up consolidation request below.

## Symptoms (user's words)

> "no slide handles"

and, on how to fix it:

> "I think we can just combine 3 rotation + 3 lateral arrow in one go,
> one checkbox. The only thing I need to highlight is that the lateral
> arrow must be longer to avoid blocking by rotation handles. Please
> also check when mouse hover, the arrow highlight, mouse press and hold
> and drag, smoothly and responsively. The thickness overlay should be
> shown for user to see the real time distance between the current
> component edge/edge face and the previous components edge/edge face."

> "there shouldn't be any track length limitation as the optical axis is
> virtually infinite. Also, please prepare for future thickness
> optimization and quick solve to get best focus or best collimation."

## Behaviour before

Two separate carry-toolbar checkboxes drove two disjoint systems:
"Rotation handles" armed the three rotation arcs on the selected STEP
overlay, and "Slide along axis" toggled a single-axis slide *mode* that
re-purposed a left-drag — but it surfaced **no on-body handle**, so the
user had nothing to grab (the flagged "no slide handles"). The slide
also clamped travel to the lens-group track length, which fights the
"optical axis is virtually infinite" model, and gave no live spacing
feedback while dragging.

## Fix

### 1 — Translate arrows in the same handle service (longer than the arcs)
`KrakenOS/UI/services/open3d_step_rotation_handles.py` `add_handles`
(rotation loop unchanged) now appends three `pv.Arrow` translate handles
after the six rotation arrowheads, one per world axis, sharing each
axis's color. Their length is `translate_len = max(extent*1.05,
radius*1.55)` where `radius` is the arc radius (`extent*0.62`), so the
arrow tip always extends past the arc ring — the explicit anti-occlusion
ask. Each arrow actor carries `pick_step_translate=(label, axis,
step_mm)` and `follow_step_label=label` so it both picks as a translate
handle and rides with the body. `add_handles` now returns **9** (3 arcs
are visual-only; 6 rotate + 3 translate are pickable). The remove path
(`remove_actors`) already unions `_actor_step_translate_map`, so arming
and clearing stay leak-free.

### 2 — Hover highlight (gold), shared with the rotation handles
`services/open3d_interaction.py:657-658` `_passive_hover_pick_rotation_handle`
adds `_actor_step_translate_map` to the lightweight passive-hover pick
list, so moving the cursor onto a translate arrow routes through the
same `_set_rotation_handle_hover` → `Open3DStepRotationHandleService.set_hover`
path that the arcs use. `set_hover`
(`services/open3d_step_rotation_handles.py:240`) lazily captures the
actor's base style and paints it gold `(1.0, 0.78, 0.08)`, restoring on
exit — translate arrows inherit it for free.

### 3 — Smooth press-hold-drag, free axial travel (no clamp)
`KrakenOS/UI/open3d_inspector.py`:
* `_step_translate_state_from_current_pick` (2764) — on left-press over a
  translate arrow, projects a 1 mm world-axis step to the screen once
  (camera is fixed for the drag) to get `pixels_per_mm` + a unit screen
  direction, with a `_placement_drag_*` fallback. Returns the drag state
  (label, axis, axis_unit, display_direction, pixels_per_mm,
  applied_delta_mm=0).
* `_apply_step_translate_drag_motion` (2839) — per motion event, projects
  the cursor delta onto the screen direction, converts pixels→mm via
  `pixels_per_mm`, and moves the follow-actors live with
  `_translate_step_overlay_actors(label, axis_unit*mm_inc)` (AddPosition
  + one render). **No track-length clamp**: the increment is applied
  verbatim, so the body tracks the cursor 1:1 along the virtually-infinite
  axis.
* `_finish_step_translate_drag` (2864) — on release, commits the TOTAL
  delta once via `editor.translate_step_overlay(label, total_xyz,
  refresh=physics_requested, record_history=True)` (additive, single
  undo entry) and clears the overlay.

The Tk mouse bindings (`services/open3d_mouse_bindings.py`) prefer the
translate drag over every other left-drag interaction at press
(`left_press` → `_step_translate_state_from_current_pick`), drive it in
`left_motion`, and finish it in `left_release` only when the gesture was
a real drag (`not should_pick and not ctrl_active`).

### 4 — Live edge-gap thickness overlay (clean, programmatic seam)
`KrakenOS/UI/open3d_inspector.py`:
* `_step_overlay_axial_gap(label, axis_unit)` (2978) — the queryable seam.
  Projects the dragged body's actor AABB and every other scene
  component's AABB onto the axis; "previous" = the component with the
  greatest `proj_max` among those whose `proj_center` is *behind* the
  dragged body. Returns `(near_point, prev_far_point, gap_mm)` with both
  points on the dragged body's lateral centerline so it reads as a pure
  axial edge-to-edge distance, or `None` when the body is first in the
  chain. Helpers: `_axial_extent_from_actor_keys` (2909) and
  `_scene_component_axial_extents` (2956), the latter walking
  `_step_actor_map` (excluding the dragged label) + `_row_actor_map`.
  This is deliberately self-contained so a FUTURE quick-solve
  (best-focus / best-collimation) can call it without going through the
  UI.
* `_draw_step_translate_gap_overlay` (3015) / `_add_step_translate_gap_label`
  (3056) — render the orange dimension arrow, two leader lines, and a
  billboard `gap = … mm` via the shared thickness-dimension service.
* `_update_step_translate_drag_overlay` (3085) — clears then redraws the
  overlay each motion **without** its own render (the body-move render in
  `_translate_step_overlay_actors` shows the refreshed dimension on the
  next frame), keeping motion at one render per event for smoothness.
  Sets a status string with the running move and edge gap.
* `_clear_step_translate_drag_overlay` (3116) — removes the gap view-props
  and unregisters their `_actor_by_key` entries; called on release and at
  the start of every redraw. Drag state + actor list are seeded in
  `__init__` (`_step_translate_drag_state` 482, `_step_translate_gap_actors`
  483).

### 5 — One checkbox; retire the redundant slide widget
`KrakenOS/UI/panels/open3d_top_controls.py` `build_carry_toolbar` renames
the first checkbutton "Rotation handles" → **"Move/Rotate handles"**
(still `show_rotation_handles_var` → `_toggle_rotation_handles`, which now
arms the whole 9-handle gizmo) and removes the "Slide along axis"
`pack_commit_checkbutton`. The `slide_along_axis_mode_var` state var and
the `_axis_slide_*` methods are left intact (dormant) so
`validate_axis_slide` / `validate_open3d_interaction_workflows` — which
drive the var programmatically — keep passing.

## Tests

* **`validate_step_rotation_handles`** (display-free) — updated for the
  combined gizmo: `_add_step_rotation_handles` returns 9 (3 visual arcs +
  6 signed rotate picks + 3 translate arrows); the rotate pick specs are
  the six `(label, axis, ±step)`; the translate arrows cover x/y/z and
  carry the label; and a geometric reach check asserts every translate
  arrow extends past the rotation arcs (anti-occlusion). The existing
  rotation-apply assertions are unchanged.
* **`validate_open3d_step_translate_gap`** (display-free, fakes only — no
  X server) — three groups (29 checks):
  - *gap math*: edge-to-edge distance picks the component BEHIND the
    dragged one, returns the near/far points on the centerline, and
    returns `None` when first or for an unknown label;
  - *overlay lifecycle*: a motion draws ≥2 view-props + a billboard and
    registers their keys, a rebuild does not leak, and clear restores the
    baseline `_actor_by_key` and removes the billboard; no-previous →
    plain move status, no actors;
  - *free-translation commit*: a 250 mm delta commits ONCE with the axial
    component verbatim (no clamp) and lateral axes untouched, a single
    history entry, a zero delta commits nothing ("no movement"), and
    `physics_requested=False` takes the partial-refresh path.
* **Regression / end-to-end** — `Phase 11` in
  `validate_open3d_penta_telescope_comprehensive.py`: arms the gizmo on a
  real imported optical STEP, asserts 6 rotate + 3 translate handles,
  drives a synthetic +150 mm Z drag built like the press path, and checks
  the body tracked the cursor, the committed offset is the 150 mm delta
  verbatim (uncapped — the virtually-infinite-axis contract), and the
  edge-gap overlay cleared on release. SKIP-passes when no lens fixture is
  checked out under `attachment/Lens/`.
