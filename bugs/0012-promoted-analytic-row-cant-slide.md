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

## Planned fix

TBD — once root-caused, wire the promoted-row placement drag to actually slide
the analytic row along the axis (free axial travel, no track-length
preservation), matching the raw-STEP-body behaviour the user expects.

## Planned tests

* Display-free unit test: simulate a placement-axis drag on a promoted analytic
  row and assert the row's axial position (or owning thickness) changes by the
  dragged delta — failing before, passing after.
* **Image-snapshot** (visual): render before/after a drag; assert the body
  silhouette translates along z.
* Regression phase in `validate_open3d_penta_telescope_comprehensive.py`, then
  regenerate the gate baseline.
