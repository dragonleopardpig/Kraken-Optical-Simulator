# 0014 — Promoted lens slid with the Move gizmo shows no live gap overlay

**Status:** Fixed (2026-06-04), with a same-day follow-up for a **lone leading
lens** (see "Follow-up" below). The placement Move-gizmo z-translate of a
promoted optical-solid row now draws the same live emerald leading-gap arrow +
label that the imported-STEP drag and the "Slide along axis" mode already drew —
and, after the follow-up, also when the lens is the only solid body in the scene
(measured to the previous optical surface from the model).
**Component:** Open 3D inspector — placement Move-gizmo translate drag
(`_apply_placement_drag_motion`) of a promoted optical-solid row, and the
transient gap overlay (`_draw_step_translate_gap_overlay`).
**Reported via:** in-app recorder, flag `flag_20260604_111615_630`
(2026-06-04T11:16:15). **Repro bundles are gitignored**, so the evidence below
is transcribed here.

## Symptoms (user's words)

> sliding of promoted analytical lens still not showing dynamic gap highlight
> similar to the unpromoted one.

After promoting an imported lens to an optical-solid row, dragging its axial
Move arrow slides the body (bugs/0012 fixed the slide itself) but shows **no**
live gap dimension — whereas the same lens *before* promotion does show one
while it's slid.

## State evidence

`flag_20260604_111615_630/state.json` (idle, mid-session):

* `picked_row_index = 1`, `picked_row_indices = [1]` — the promoted optical
  row 1 is selected.
* `placement_translate_handle_count = 6`, `placement_rotate_handle_count = 9`,
  `rotation_handle_count = 0` — the **placement** Move/Rotate gizmo is up (this
  is the promoted-row gizmo, not the STEP rotate gizmo).
* `thickness_dimension_count = 4` — only the persistent row→row `Thickness =`
  arrows (the screenshot shows `S0 Thickness = 100 mm`, `S1 Thickness = 40 mm`).
  There is **no** transient `gap =` overlay.
* `row_actor_bounds["1"]` z = **44.59 .. 56.21** (the lens body); optical axis
  z = -91 .. 231; `interaction_mode = "idle"`.

The screenshot shows the lens with the blue (horizontal) / green (vertical)
double-arrow Move gizmo and the red rotation arc, and only the two static
`Thickness =` labels — confirming the gizmo slide draws no live gap.

## Root cause (confirmed 2026-06-04, headless)

There are **three** ways a body is slid in the 3-D view, and only two drew the
live gap before this fix:

1. **Imported-STEP drag** (`_apply_step_translate_drag_motion` →
   `_update_step_translate_drag_overlay`) — *has* the overlay, read
   geometrically off the moved actors (`_step_overlay_axial_gap`). This is the
   "unpromoted one" the user compared against.
2. **"Slide along axis" mode** (`_apply_axis_slide_drag_motion` →
   `_update_axis_slide_gap_overlay`, request #66) — *has* the overlay, read from
   the live MODEL gap (the body refresh is debounced in that mode).
3. **Placement Move-gizmo translate** (`_apply_placement_drag_motion`) — the
   path a **promoted optical-solid row** uses (bugs/0012) — drew **no** gap
   overlay at all. `_apply_placement_drag_motion` moved the body + handles live
   and accumulated `pending_translate_mm`, but never called any gap-draw.

So the missing path is the gizmo translate, exactly the one the recorder shows.

## Fix

`KrakenOS/UI/open3d_inspector.py`:

* **New `_row_overlay_axial_gap(group_indices, axis_unit=None)`** — the row twin
  of the imported-STEP `_step_overlay_axial_gap`: it reads the edge-to-edge
  axial gap **geometrically** off the actor bounds (group's near edge `proj_min`
  to the previous *visible* component's far edge `proj_max`), excluding the
  dragged group's own rows so a sub-body can't be picked as its own
  predecessor. This is correct here precisely because the gizmo moves the body
  actors **live** (`_translate_row_actors`, bugs/0012) — unlike the debounced
  axis-slide mode, whose actors are stale so it must use the model gap.
* **New `_update_placement_drag_gap_overlay(state)`** — only acts on a *z-axis*
  (optical axis) *translate* (X/Y decenters have no axial gap; rotation is not a
  slide). Resolves the slid group via `_lens_row_group_for_row`, clears the old
  transient actors, and draws via `_draw_step_translate_gap_overlay` (the same
  thick emerald arrow + label as #65). It issues **no** render: the body move in
  the same motion event already rendered, so the refreshed dimension shows on
  the next frame (the established, imperceptible one-frame lag).
* **Wired** into `_apply_placement_drag_motion`'s translate branch (after the
  live body/handle move + `pending_translate_mm` update).
* **`_finish_placement_drag`** now clears the transient overlay
  (`_clear_step_translate_drag_overlay(render=True)` — self-gating, so a drag
  that nets to zero, hence no commit-render, still can't leave a ghost arrow).
  Cancel already clears via the blanket clear in `cancel_active_3d_operation`.

No new colour/styling: the gizmo slide reuses the emerald `(0.10, 0.90, 0.45)`
overlay from #65, so all three slide paths now read identically.

## Tests

* **Display-free unit** — `validate_open3d_axis_slide_gap_overlay_snapshot.py`
  gains `check_placement_gap_math`: against hand-placed fake bodies it asserts
  `_row_overlay_axial_gap` reads the gap **geometrically** (dragged body
  z[40,55] preceded by z[0,10] → far pinned to z=10, near to the live edge z=40,
  value 30), honours `exclude_rows` (a sub-row of the dragged group can't be the
  predecessor), and returns `None` for a first element. Source-coupling asserts
  `_apply_placement_drag_motion` calls `_update_placement_drag_gap_overlay`, that
  it reads `_row_overlay_axial_gap`, and that `_finish_placement_drag` clears the
  overlay. Teeth: deleting the one wiring line flips it to a clean FAIL.
* **Regression / end-to-end** — `Phase 22`
  (`phase_22_promoted_slide_gap_overlay`) in
  `validate_open3d_penta_telescope_comprehensive.py`. Loads the flattened penta
  cascade (5 abutting solid bodies on +Z), selects the **last** body row (slides
  into free space, no leapfrog), drives a 4-step +Z gizmo drag, and asserts the
  live gap overlay **appears** during the drag (the bug was zero actors), that
  the gap **tracks** the slide (grows by the dragged ~40 mm), and that release
  **clears** it. Gate baseline regenerated (`tools/penta_validator_baseline.json`).

## Follow-up (2026-06-04): lone leading lens still showed no gap

After the fix above the user retested and reported the gap **still** did not
appear. Reproduced headlessly: the first fix only draws a gap when a preceding
rendered **solid body** exists. The recorder scene
(`flag_20260604_111615_630`) is a **single** promoted lens — `row_actor_bounds`
has only key `"1"`, `step_actor_counts {}` — preceded only by the **non-solid
Object surface** (which renders no body). All three gap readers
(`_row_overlay_axial_gap`, the imported-STEP `_step_overlay_axial_gap`, and the
axis-slide `_row_slide_axial_gap`) scan only `_scene_component_axial_extents`
(rendered actors), so a lone leading lens has no predecessor → gap `None` → no
overlay. The persistent `S0 Thickness = 100 mm` dimension still showed, because
**it** is built from the model (`_surface_reference_world_point`), not from
rendered bodies — which is exactly the asymmetry the user saw. Phase 22 missed
this because it deliberately selects the **last** cascade body (a solid
predecessor always exists).

**Fix:** `_row_overlay_axial_gap` now falls back to the previous optical
**surface** position from the model when no preceding solid body is found —
`_model_previous_surface_axial(min(group_rows), axis)` projects
`editor._surface_reference_world_point(prev_row)` onto the axis, the **same**
reference the persistent `S{n} Thickness =` dimension uses, so the live readout
and that dimension now agree. The surface is static during a drag, so the gap
tracks the lens's live near edge exactly as the body-to-body case does. A solid
predecessor still wins when one exists (interior bodies unchanged); the fallback
returns `None` only when there is also no prior surface (the true first element)
or the model lookup fails. Scoped to the promoted-row path the user reported; the
imported-STEP path keeps its solid-body-only behaviour (an overlay isn't tied to
a row index, so it has no clean "previous surface").

**Follow-up tests:**

* **Display-free unit** — `check_placement_gap_model_fallback` in
  `validate_open3d_axis_slide_gap_overlay_snapshot.py`: a lone dragged body
  z[40,55] with the prior **surface** stubbed at z=7 (via a fake editor) now
  reports a gap (far=7, near=40, value=33); `_model_previous_surface_axial`
  returns 7 for that row and `None` before row 0; a **solid** predecessor at
  z[0,10] still wins (far=10, not 7); and with neither a body nor a model
  surface it returns `None` (graceful, no crash). Source-coupling asserts
  `_row_overlay_axial_gap` keeps the `_model_previous_surface_axial` call and
  that helper keeps reading `_surface_reference_world_point`. Teeth verified:
  stubbing the fallback to `None` flips it to a clean FAIL.
* **Regression / end-to-end** — `Phase 23`
  (`phase_23_lone_lens_slide_gap_overlay`): flattened penta cascade, selects the
  **first** body row (preceded only by the Object surface — asserts it has zero
  solid predecessors so it really is the lone-lens case), slides it **−Z**, and
  asserts the gap now appears (was zero actors), tracks the slide (shrinks by the
  dragged total toward the Object surface), and clears on release. Gate baseline
  regenerated.
