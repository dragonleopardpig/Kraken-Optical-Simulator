# 0011 — Thickness overlay not auto-updated after moving the lens (stale gaps)

**Status:** Fixed. After a STEP Move/Rotate gizmo commit the persistent
thickness overlay now recomputes at the body's new position (when the dimensions
are shown), so the two `gap = .. mm` arrows follow the lens instead of freezing
at its old position.
**Component:** Open 3D inspector — persistent thickness overlay
(`Open3DThicknessDimensionService.add_overlays`, the split from bug 0009) and
the STEP move-commit path (`Kraken3DInspector._finish_step_translate_drag`).
The live drag readout is correct; the *committed* persistent overlay was stale.
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

## Root cause

`_finish_step_translate_drag` commits the move via `translate_step_overlay`,
then refreshes. When live physics is **off** (`inspector_physics_requested` →
`live_mode_var` is False, the flag's case — `show_rays` was off too), it took
the fast per-label path: `refresh_imported_step_overlay(label)`. That helper
rebuilds **only** the moved body (mesh, edges, handles) and returns True; it
never touches the thickness-dimension actors. The persistent dimensions span
*every* component (Object/Image rows plus the imported body), so a per-label
overlay refresh leaves the `gap =` arrows + framed labels anchored at the body's
pre-move position. The body slid; the committed overlay didn't.

The live drag readout was unaffected (it recomputes on demand from the already
up-to-date `_step_actor_map`), which is why the user saw it as correct. The
staleness is newly visible *because* bug 0009 made the persistent overlay
position-dependent (a split around the body), where before it was a fixed
row→row span.

Reproduced headlessly: centre the lens at z=40 → overlay reads
`gap = 27.5 / 47.5`; commit a +24 mm axial move (body → centre 64, span
51.5..76.5) → overlay **stayed** `27.5 / 47.5`; a full `refresh_from_editor`
then corrected it to `51.5 / 23.5`.

## Fix

**`KrakenOS/UI/open3d_inspector.py`** — in `_finish_step_translate_drag`'s
non-physics branch, consult `show_physical_distances_var`: when the thickness
dimensions are shown, do a full `refresh_from_editor(force_retrace=False)` (which
recomputes the dimensions at the new position, per bug 0009's draw ordering)
instead of the per-label `refresh_imported_step_overlay`. The fast per-label
path is kept when the dimensions are hidden. (The carry-drag commit
`_finish_step_carry_drag` already does a full refresh, so only the translate
path needed this.)

## Tests

* **`validate_open3d_thickness_overlay_live_update`** (boots its own Xvfb) —
  places the tracked prism at z=40 between Object(0)/Image(100), turns the
  dimensions on, commits a +24 mm axial Move, and asserts the rendered `gap =`
  labels change by the moved distance AND the gap-arrow geometry's clear band
  moves to the lens's new span (an arrow now covers the vacated old centre and
  none crosses the new centre). It also source-couples the
  `show_physical_distances_var` guard. Fails before the fix (stale labels, arrows
  still split at the old position), passes after.
* **Regression / end-to-end** — `Phase 17` in
  `validate_open3d_penta_telescope_comprehensive.py`.
