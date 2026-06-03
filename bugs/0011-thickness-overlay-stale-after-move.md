# 0011 — Thickness overlay not auto-updated after moving the lens (stale gaps)

**Status:** Open — documented from the flag, not yet fixed.
**Component:** Open 3D inspector — persistent thickness overlay
(`Open3DThicknessDimensionService.add_overlays`, the split from bug 0009) and
the STEP move-commit path (`Kraken3DInspector._finish_step_translate_drag`).
The live drag readout is correct; the *committed* persistent overlay is stale.
**Reported via:** in-app recorder, flag `flag_20260603_171735_941`
(2026-06-03T17:17:36). **Repro bundles are gitignored**, so the evidence below
is transcribed here.

## Symptoms (user's words)

> Thickness overlay not auto-updated.

After dragging the selected lens to a new axial position, the persistent split
overlay (the two `gap = .. mm` arrows from bug 0009) keeps showing the gaps from
the lens's *previous* position instead of recomputing for where it now sits.

## State evidence

`flag_20260603_171735_941/state.json` (recording active, lens selected):

* `selected_step_label = "optical"`, `picked_step_label = "optical"`,
  `selected_step_rotation_active_label = "optical"`,
  `rotation_handle_count = 6` — the STEP Move/Rotate gizmo is active.
* `row_actor_bounds`: row 0 Object at z = 0, row 1 Image at z = 100.
* `step_actor_bounds["optical"]` z = **70.749 .. 82.329** — the lens now sits at
  centre ≈ 76.54, thickness ≈ 11.58 mm. The *correct* gaps would be
  ≈ **70.75 mm** (Object→lens-front) and ≈ **17.67 mm** (lens-back→Image).
* `thickness_dimension_count = 4` — two `gap =` arrows + two framed labels.

But the screenshot reads **`gap = 46.25 mm`** (left) and **`gap = 42.17 mm`**
(right). Those plus the 11.58 mm body sum to exactly 100 mm and correspond to
the lens centred at z ≈ **52.04** (front 46.25, back 57.83) — its *previous*
position. So the overlay was computed before the move and never refreshed.

## Lead / suspected root cause (to confirm at fix time)

The gizmo move commits the new placement (the body actor and
`step_actor_bounds` show the new z = 70.75..82.33), but the persistent overlay
is not recomputed at the new position. The live drag readout updates during the
drag (bug 0009 confirmed it reads the already-populated `_step_actor_map`), yet
on release the committed `gap =` arrows keep the pre-move values. Likely
`_finish_step_translate_drag` applies the offset without triggering the scene
refresh that re-runs `_add_thickness_dimension_overlays` at the new bounds (or
it re-adds before the committed transform lands in `_step_actor_map`). This is
newly visible *because* bug 0009 made the persistent overlay position-dependent
(a split around the body), where before it was a fixed row→row span.

## Planned fix

TBD — once root-caused, ensure the move-commit path recomputes the persistent
thickness overlay at the committed position (e.g. trigger the same scene
refresh / `add_overlays` pass the live readout already relies on), so the
persistent gaps match the live readout after release.

## Planned tests

* Display-free unit test: move the imported body, commit, and assert the
  recomputed persistent `gap =` values match the new edge gaps (and the live
  readout) — pinning that the overlay tracks the body.
* **Image-snapshot** (visual): render after a committed move; assert the two
  `gap =` arrows straddle the body at its new position (no stale span).
* Regression phase in `validate_open3d_penta_telescope_comprehensive.py`, then
  regenerate the gate baseline.
