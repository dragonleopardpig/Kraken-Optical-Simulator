# 0012 — After promoting to an analytic lens, the Move gizmo can't slide it

**Status:** Fixed. The placement-translate drag on a promoted optical-solid row
now moves the body live with a cheap actor transform and defers the single heavy
optical retrace to drag release, so the lens slides smoothly instead of firing a
~0.5 s retrace on every snap step.
**Component:** Open 3D inspector — placement-handle (Move arrow) drag for a
promoted optical-solid row (`_apply_placement_drag_motion` /
`_finish_placement_drag`), and the forced full retrace for promoted solids
(`Open3DTraceRefreshService.has_promoted_step_optical_solid_rows`).
**Reported via:** in-app recorder, flag `flag_20260603_171838_255`
(2026-06-03T17:18:38). **Repro bundles are gitignored**, so the evidence below
is transcribed here.

## Symptoms (user's words)

> after changing to analytical lens, can't slide.

After promoting the imported STEP lens to analytic surfaces, the Move gizmo
still appears on the row, but dragging its axial arrow does not slide the lens
along the optical axis.

## State evidence

`flag_20260603_171838_255/state.json` (recording active, idle after a failed
drag):

* `picked_row_index = 1`, `picked_row_indices = [1]` — the promoted **analytic
  row 1** is picked (not a STEP overlay).
* `selected_step_label = null`, `picked_step_label = null` — no STEP body is
  selected; the body is now an analytic row.
* `row_actor_bounds["1"]` z = **70.729 .. 82.349** — the lens body, ~11.62 mm
  thick, centre ≈ 76.54.
* `placement_translate_handle_count = 6`, `placement_rotate_handle_count = 9`,
  `rotation_handle_count = 0` — the **placement** Move/Rotate arrows render
  (this is the promoted-row gizmo, not the STEP rotate gizmo).
* `thickness_dimension_count = 4` — `S0 Thickness = 100 mm` and
  `S1 Thickness = 40 mm` row→row arrows (analytic, not `gap =` splits).
* `interaction_mode = "idle"`; optical axis z = -91..231.

The screenshot shows the analytic lens with the green (vertical) / blue
(horizontal) double-arrow Move gizmo and a red rotation arc, plus the two
`Thickness =` labels and the status bar:
`Placement handles: S1 | spacing 2.5 mm | extent 50 mm | snap 1.25 mm / 5 deg |
placements 1 | handles 15`.

So the arrows are present (count 6) but the axial drag is a no-op for the
promoted row — i.e. the slide that works for a raw STEP body (bugs 0004/0006)
does not apply to the analytic row after promotion.

## Lead / suspected root cause (to confirm at fix time)

The placement handles render for the promoted analytic row, but the drag→apply
path doesn't translate it. Likely `_apply_placement_drag_motion` /
`_placement_drag_state_from_current_pick` resolves the drag target via a
STEP-body label (`selected_step_label` is `null` here) and so has nothing to
move, or the analytic row's slide is expected to go through the row-thickness
edit seam (as in bug 0006's promoted-row sizing) but the placement drag isn't
wired to it. Note the optical-axis-slide-is-free rule (memory): the fix must let
the analytic row translate freely along z without preserving track length.

Contrast: bug 0006 fixed the promoted-row arrows *shrinking*; this is the
arrows being present but the *drag doing nothing*. Confirm whether this is a
regression from the 0004/0006 gizmo unification or a never-wired analytic path.

## Investigation (2026-06-03, headless)

Reproduced the three promotion paths against the tracked prism (display-backed
probes) to find where the slide breaks:

* **Optical-solid-row** promotion (`promote_imported_step_to_optical_solid_row`)
  → one solid row, **6 placement move handles** (x/y/z ±, matching the flag's
  `placement_translate_handle_count = 6`). Simulating the full left-drag on the
  +Z handle (pick → `_placement_drag_state_from_current_pick` → repeated
  `_apply_placement_drag_motion`) **rigidly slides** the body (zmin and zmax both
  move together). No `_step_translate`/`_axis_slide` preemption. So this path
  works end-to-end in the harness.
* **Analytic-surfaces** promotion (`promote_imported_step_to_analytic_surfaces`)
  → plain Standard rows, `_is_any_promoted_optical_solid_row = False` → **0
  placement handles**. If the user took this menu, "can't slide" = there is no
  Move handle at all.
* **Native-surface-rows** promotion
  (`promote_imported_step_to_native_surface_rows`, the path that sets
  `StepNativePromotion` and so is handle-eligible — the closest match to the
  flag's Standard `S1 Thickness = 40 mm` row *with* handles) → applying the +Z
  handle **stretched** the body (zmin +10, zmax unchanged) instead of sliding.
  But the prism promotes *degenerately* to a single `plane_exact` row whose body
  spans to z=100, so this result is not a faithful stand-in for the user's
  multi-surface aspheric lens.

## Root cause (confirmed)

The user clarified: they used the **bottom option of the right-click menu** —
"Promote STEP to Optical Solid Row" — and on drag "it seems to compute something
in the background hard, but not moving." That is the optical-solid-row path,
whose handle-drag *apply* slides correctly. The real defect is **performance**:

* A promoted optical-solid row makes
  `has_promoted_step_optical_solid_rows()` true, which forces
  `requires_open3d_retrace = True` on **every** `refresh_from_editor` —
  a full optical retrace (measured **~228 ms**).
* `_apply_scene_placement_translate_handle` committed **each snap step** of the
  drag with a full `refresh_from_editor`, so a single placement step cost
  **~578 ms**. A real drag fires one step per ~18 px, so the slide pegged the
  CPU and barely advanced — "computes hard, doesn't move."

So the body *was* moving, just one ~0.5 s retrace at a time — unusable as an
interactive slide.

## Fix

* **`KrakenOS/UI/open3d_inspector.py`** — `_apply_placement_drag_motion`'s
  translate branch no longer commits per step. It moves the row's body actors
  **and** its Move/Rotate handle actors live with `_translate_row_actors` /
  `_translate_placement_handle_actors` (cheap `AddPosition`, **no retrace**) and
  accumulates the delta in `state["pending_translate_mm"]`.
  `_finish_placement_drag` then commits the accumulated total once via
  `_apply_scene_placement_translate_handle` (one model update + one heavy
  refresh on release). This mirrors the existing STEP-translate / row-carry
  drags. Per-step cost drops ~578 ms → ~7 ms; the body and its gizmo slide live
  together and the final committed position matches the live preview (rigid
  slide). Rotation handles keep their per-step apply (out of scope; same retrace
  cost, separate follow-up).

### Follow-up regressions from the first cut (flags 20:37 / 20:38)

The first version moved only the *body* actors live and deferred the commit,
which surfaced two issues on re-test:

* **20:37 "the lens slide, but the handler stay where they are"** — the gizmo
  handles weren't moved during the live drag (only the body was). Fixed by
  `_translate_placement_handle_actors`, which `AddPosition`s the row's Move +
  Rotate handle actors by the same delta each step so the gizmo tracks the lens.
* **20:38 "releasing mouse hold, the lens go back to its original location"** —
  reported revert on release. Could not be reproduced headlessly (the deferred
  commit held — `desp_z` committed, body rigidly slid — in every probe, live on
  and off). The committed approach keeps the model authoritative on release (one
  `_apply_scene_placement_translate_handle` → rebuild from the committed pose),
  so the position sticks by construction. A *per-step* model commit was also
  tried but rejected: `translate_scene_row_pose` → `_sync_table` costs ~300 ms,
  reintroducing the lag. **If the revert persists, capture the exact lens** (and
  whether it carries a tilt — a tilted row would make the world-axis live move
  diverge from the local-`desp_z` commit, which could read as a jump).

## Tests

* **`validate_open3d_promoted_row_slide`** (boots its own Xvfb) — promotes the
  tracked prism to an optical-solid row, runs a 6-step placement-translate drag,
  and asserts the body moves **live** while `desp_z` stays **uncommitted**
  (deferred — proving no per-step retrace), then on release `desp_z` commits by
  the dragged total and the body slid **rigidly**. Fails before the fix (desp_z
  committed mid-drag), passes after.
* **Regression / end-to-end** — `Phase 18` in
  `validate_open3d_penta_telescope_comprehensive.py`.

## Note on the other promotion paths (from the headless investigation)

Recorded in case they resurface as separate reports: *Convert to Analytic
Surfaces* renders **0 placement handles** (a different "can't slide"), and
*native surface rows* on the prism stretched a degenerate single-plane body.
Neither is what this flag hit; both are out of scope here.

## Planned tests

* Display-free unit test: simulate a placement-axis drag on a promoted analytic
  row and assert the row's axial position (or owning thickness) changes by the
  dragged delta — failing before, passing after.
* **Image-snapshot** (visual): render before/after a drag; assert the body
  silhouette translates along z.
* Regression phase in `validate_open3d_penta_telescope_comprehensive.py`, then
  regenerate the gate baseline.
