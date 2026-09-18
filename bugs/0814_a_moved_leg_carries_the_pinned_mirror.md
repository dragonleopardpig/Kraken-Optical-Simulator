# 0814 -- a moved leg carries the pinned mirror

From the validation census ("fix them all"): penta phases 194 and 202 reported the two-mirror AZ85
scene losing its image after the best-focus snap.

## Measured (before)

`snap_detector_to_image_plane()` on the two-mirror scene (the ELS85 with a second RA mirror promoted
at its flagged free-placed pose):

| | before the snap | after |
|---|---|---|
| rays reaching the sensor | 293 of 729 | **3** |
| on-axis rays reaching it | 65 of 81 | **0** |
| sensor seat | [181.37, 0, -62.05] | [160.36, 0, -34.55] |
| axial ray endpoints | on the seat | [214.59, 0, 71.90] -- still on the middle leg |

The snap wrote two gaps: the exit leg (the trailing mirror row, 40 -> 12.5 mm) and, through the
camera-body collision resolver, the NEAR leg (row 7, 150.37 -> 129.35 mm).

The near-leg write is the one that broke it. That mirror is **free-placed**: its promotion records a
`center_world`, so `_free_placed_solid_pinned_pose` pins it at `[desp_x, desp_y, z_station + desp_z]`
and its axial station feeds only global +Z. A delta on a leg AFTER the first fold walks the SENSOR
along the reflected leg while the pinned mirror stays where it was -- the sensor ends up 21 mm off the
beam and every ray misses.

This is exactly what bugs/0236 / bugs/0244 built `carry_free_placed_followers_after_fold` for, and the
folded FOV solve calls it after rewriting gaps (`quick_estimation`). The best-focus snap reaches the
near leg through `_apply_near_leg_delta` (bugs/0550's spreader), which rewrote thicknesses and
carried nothing.

## Fix

`_apply_near_leg_delta` records what it wrote per row and carries the free-placed followers with the
same helper the folded solve uses. Every caller of the spreader gets it (the snap's collision
resolver, the swap's refocus).

## Measured (after)

| | after the snap |
|---|---|
| rays reaching the sensor | **508** of 729 |
| on-axis rays reaching it | **65** of 81 (16 are stopped at surface 5, as before) |
| on-axis focus vs the drawn detector | gap **0.0 um**, endpoint RMS **0.0 um** |

## Verified

* Phase 194 (folded image snaps to the ray convergence) and phase 202 (the 2D layout matches the 3D
  folded focus) pass; both fail on the committed code.
* The folded family is unchanged or better: 183, 185, 186, 189, 203 pass.
* The solve family that shares the spreader passes: 433 (0546), 435 (0550), 441 (0566), 442 (0567),
  452 (0594), 483 (0645), 484 (0646).
* Still failing for their own reasons, unchanged by this fix: 181 (cone density), 213, 214, 261, 276
  (folded FOV solve refusals).
