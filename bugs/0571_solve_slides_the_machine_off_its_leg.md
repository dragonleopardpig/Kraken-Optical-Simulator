# 0571 — the object solve slid the machine along the station axis, off its own leg

**Flag** `flag_20260806_125028_234` with the **full recording** `recording_20260806_125044.json`
(build d9a68012, `machine_vision_Pyrite85_BS.py`): *"swapped lens, elements dislocate."*

The recording holds exactly one command after the (unrecorded, menu-driven) swap:
`fov_solve{plane:"object", mode:"thickness", width:23, height:23}`. So the repro is
**swap → solve**, nothing else.

## Measured

Reproduced headless (`bugs/diag_0571_swap_then_solve.py`) — the swap moves nothing; the SOLVE
does all of it:

| | before | after (broken) |
|---|---|---|
| object gap (row 0) | 118.970 | 147.432 (+28.462) |
| lens front datum | (82.039, 0, **54.283**) | (82.039, 0, **82.745**) |
| fold mirror | (193.383, 0, **54.283**) | (193.383, 0, **82.745**) |
| sensor | (193.383, 0, 10.207) | (193.383, 0, 97.593) |
| BS-reflect guide axis | z 83.821 | z 55.359 |
| rays reaching the sensor | — | **0 of 558** (547 `no_next_intersection`) |

Every element moved **+28.462 mm in Z** — and the leg they all sit on runs along **+X**. They
did not move *along* the beam, they moved *across* it.

## Root cause

A row's pose is `station + desp_z` (bugs/0526). The object distance was changed by writing
`rows[0].thickness`, so every downstream WORLD-placed row's station grew by the delta — which on
a 0433-frozen scene translates them along **+Z**. That is the station axis, not the fold leg.

The lens **drag** already knew better (bugs/0524 + 0526): *"positions along a fold leg live in
`desp`, not in thicknesses"* (bugs/0499). Its composite:

* translates the block's rows by the slide along the leg direction,
* writes `gap before += slide` / `gap after -= slide`, so the first order sees the conjugate
  change (s_o + d, s_i − d; the swapped path is air, so reduced == geometric),
* cancels the station growth with `desp_z -= slide` for the rows in between,
* compensates the lens overlay's placement offset, whose aligner pins to the datum STATIONS
  (bugs/0527).

## Fix

`slide_lens_block_along_its_leg` extracts that composite, and the folded conjugate solve calls it
for its object-side delta instead of writing `rows[0].thickness`. **A drag and a solve are the
same gesture from opposite ends** — the user's own principle, now the same code.

Measured after (same repro): the lens block moves **+28.462 mm along +X at z 54.283 unchanged**,
and the beam splitter, the LED housing and the fold mirror do not move at all. The sensor travels
4.331 mm along the fold leg for focus.

Two supporting changes:

* `glued_illumination_unit_world_poses` / `restore_glued_illumination_unit_world_poses` bracket
  `snap_detector_to_image_plane`, so whichever of its three writers runs (the image-gap write, the
  collision resolver's mirror slide, the near-leg redistribution) the glued LED+BS unit is put
  back on its seat. Writer-agnostic on purpose: measure, don't derive.
* `row_is_station_neutral` now has ONE definition (in `paraxial_tools`), which
  `QuickEstimationService._row_is_station_neutral` delegates to (the bugs/0568 lesson).

Snapshots, from the flag's own camera, replace the eyeball:
`attachment/_0571_1_loaded.png`, `_2_swapped.png`, `_3_solved.png`
(`bugs/render_0571_swap_then_solve.py`).

## Guard — phase 446 `validate_open3d_0571_solve_slides_the_lens_along_its_leg`

* **A pure**: one definition of the station-neutral predicate (and the delegation); the
  illumination-unit measure/restore round-trips a +28.462 mm station write exactly.
* **B real scene**: a 23×23 object solve moves the lens **dz +0.0000 / dx +28.4622** (the
  pre-fix numbers were the exact opposite), leaves the BS, the LED body and the fold mirror
  where they are, and the fold never leaves its leg. Non-vacuity: the object gap really changed.

## Deliberately NOT changed, with the measurement that decided it

The camera-body collision remedy — *"the fold mirror needs to slide N mm further than the
lens-to-mirror leg can give"* — is refused on this scene because the near-leg span is the single
**station-neutral** BS row (thickness pinned at 0 by bugs/0435) while the real lens→mirror leg is
the 43 mm row before it. Widening the span (`gap_start` skipping station-neutral rows) DOES unblock
the remedy, and it was tried: `_apply_near_leg_delta` then applies it as a **thickness** write, and
on a frozen fold that moved the mirror **across** its leg — measured on a 40×40 solve, the mirror
left z 54.291 for **110.8**, i.e. exactly the dislocation this bug is about. The remedy has to be
expressed in WORLD terms first (as `_apply_folded_image_split` does via
`_rebake_frozen_row_world_center`). Until then the explicit refusal beats a fold that walks off the
beam, and the guards say so rather than asserting the stronger property:

* 0569's C3/C4/C6 now assert *the fold stays on its leg* and *a re-solve does not walk it* — the
  object side legitimately moves the lens now, so "lens-vs-mirror is invariant" is no longer true,
  and a re-solve still re-places the sensor by ~19.8 mm because the IMAGE side has not converged.
* 0570's B3/B4 now assert *never silent*: the snap either lands the focus or refuses for a stated
  geometric reason.

**Open, in one sentence:** the image side does not converge on this scene — the snap's adaptive
loop cannot verify its own move (its re-measure returns None here) and the collision remedy cannot
be applied in world terms, so "Solve for Thickness" still leaves a residual the status line
reports (e.g. `residual -51.22 -> -51.22`).
