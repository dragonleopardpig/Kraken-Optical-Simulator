# 0012 — After promoting to an analytic lens, the Move gizmo can't slide it

**Status:** Open — documented from the flag, not yet fixed.
**Component:** Open 3D inspector — placement-handle (Move arrow) drag for a
*promoted/analytic* row. Suspects: `_placement_drag_state_from_current_pick`
and `_apply_placement_drag_motion` (the drag→apply seam) for a row that is now
an analytic surface rather than a raw imported STEP body.
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

So the behaviour is **promotion-path- and fixture-dependent**, and the only
portable fixture (the penta prism) cannot reproduce the user's aspheric-lens
case cleanly. Not fixed yet — shipping a blind change here risks regressing the
optical-solid-row path that already slides correctly.

**Open questions for a confirmed repro:** (1) which menu produced the
"analytical lens" — Convert to Analytic Surfaces, Promote to native surface
rows, or optical solid row? (2) on drag, does *nothing* move, or does the lens
*deform/partly move*? Candidate fix if it is the native multi-surface case:
translate every row in `_lens_row_group_for_row(row)` together (rigid group
slide, free axial travel) rather than only the picked surface row.

## Planned fix

TBD — pending a confirmed repro (see Investigation). Likely: slide the whole
lens-row group together along the axis (free axial travel, no track-length
preservation), matching the raw-STEP-body behaviour the user expects.

## Planned tests

* Display-free unit test: simulate a placement-axis drag on a promoted analytic
  row and assert the row's axial position (or owning thickness) changes by the
  dragged delta — failing before, passing after.
* **Image-snapshot** (visual): render before/after a drag; assert the body
  silhouette translates along z.
* Regression phase in `validate_open3d_penta_telescope_comprehensive.py`, then
  regenerate the gate baseline.
