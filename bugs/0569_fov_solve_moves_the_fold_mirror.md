# 0569 — a folded FOV/thickness solve moved the fold mirror and the camera

**Flag** `attachment/recorded_bug_repros/flag_20260806_074148_944` (build 2564b7e6, the user's
`machine_vision_AZ85_RA_Mirror_BS`), with the **full recording** `recording_20260806_074228.json`:

> swapped lens, changed FOV, solve for thickness, camera and RA mirror misplaced.

The recording holds exactly one solve — `fov_solve(plane="object", mode="thickness",
width=23.0, height=23.0)` — so the repro is one call, not a gesture sequence.

## Measured (headless, the user's own layout)

`bugs/diag_0569_fov_solve_image_gap_row.py` replays it:

```
_folded_conjugate_gaps_for_magnification(|m|=1.00174)
  object_gap_row 0     object_delta 5.5e-10
  image_gap_row  6     image_delta  35.8492      <- row 6 is the promoted BEAM SPLITTER
```

| | before | after (broken) |
|---|---|---|
| S6 beam-splitter row thickness | 0.0000 | **35.8492** |
| S7 RA mirror, world | (193.383, 0, **54.283**) | (193.383, 0, **90.132**) |
| S8 sensor, world | (193.383, 0, **10.207**) | (193.383, 0, **46.056**) |
| camera body | on the beam | follows the sensor, off the beam |

The lens block does not move — matching the flag exactly (the flag's live scene, with the
PYRITE lens swapped in, had the same failure at 54.59 mm instead of 35.85).

## Root cause

`image_gap_row` is **where the image distance is MEASURED FROM**, not a leg that may be
stretched. `_folded_conjugate_gaps_for_magnification` computes it by walking back off the fold
mirror (`_row_is_promoted_mirror_fold`) so the distance runs from the last LENS surface — and on
this scene the row it lands on is the promoted **beam splitter**, which is

* **STATION-NEUTRAL** (bugs/0435): its thickness is deliberately pinned at 0 because a BS glued
  into the LED housing spans no distance on the imaging axis — "every station-fed consumer
  downstream ... shifted by that reserve";
* **not where its row index says** (bugs/0546): the BS is glued to the LED, physically *upstream*
  of the lens, yet its row sits after the lens block.

So the image-leg correction was added to a row that is not a gap at all, and every downstream
station moved with it: the RA mirror, the sensor, and the camera glued to the sensor.

Two further traps sit on the same line, both already documented and both violated here:

* the correction must not stretch the leg **before** the mirror — that slides the mirror, which
  a conjugate solve must never do;
* on a 0433-frozen fold the mirror→sensor gap row **runs backwards** (world leg = `const −
  thickness`, bugs/0478), so writing the correction into it moves the sensor the wrong way.

## Fix

1. **`shift_image_distance_frozen_aware(delta)`** (`paraxial_tools.py`) — move the sensor by
   `delta` *along its folded leg*, mirror unmoved, by handing `measured_world_leg + delta` to
   the existing world-terms writer `apply_image_distance_frozen_aware` (bugs/0478).
   The absolute that writer takes and the solve's `image_distance` are **different quantities in
   different frames**: `image_distance` is a sum of GAP ROWS from wherever `gap_start` landed
   (58.92 mm here), while the writer wants the world mirror→sensor leg (44.08 mm). Adding the
   *correction* to the *measured* leg is the one form that is right in both.
2. **`_folded_image_leg_write_row`** (`quick_estimation.py`) — the image correction lands on the
   mirror→sensor gap (the fold split's `far_gap_row`, else the last gap before the Image), never
   on the row the distance was measured from.
3. **`_row_is_station_neutral` / `_gap_row_for_delta`** — no conjugate write may ever land on a
   station-neutral row; a delta aimed at one walks back to a row that can hold a distance.
4. The folded branch tries (1) first and skips the raw gap write when it is handled, and the
   status line then reports what actually happened ("the sensor moved +35.85 mm along its folded
   leg (the fold mirror stayed put)") instead of quoting a gap-row sum.
5. **The folded branch now finishes on the TRACED focus** like the plain one does. It returns
   early, so it had never reached the bugs/0490 finisher (`_finish_solve_on_traced_focus`) — the
   solve landed the *paraxial* plane and left the real-ray focus wherever the aberration and the
   BS/prism glass paths put it, on the very branch every folded scene takes. That is the
   recurring *"solve for FOV, ray still defocus at the sensor"* complaint (0567's flag).

After the fix, on the user's scene, the flagged gesture is a **no-op**: S6 stays 0.0000, the RA
mirror does not move (its offset from the lens rear datum is unchanged to 1e-6), and neither
does the sensor — because the scene was **already** at 23×23 (|m| = 1.002, sensor 23.04 mm). The
paraxial step moves the sensor +35.85 mm and the traced-focus finisher puts it back, which is
the right answer for "solve for the field you are already at". A genuinely different field
(40×40) does re-place the sensor by 67 mm, with both invariants still holding.

**Scope note (deliberate):** the fix changes *which element moves*, not the solve's paraxial
number — the 35.85 mm correction is the folded first order's own output and is untouched.

## Guard — phase 444 `validate_open3d_0569_fov_solve_keeps_the_fold`

* **A pure**: the station-neutral predicate; the walk-back; the image-leg write row (the fold
  split's far gap, never the station-neutral row, with and without a published split); the
  frozen shift is "measured world leg + correction"; and a scene with **no** frozen image fold
  declines, so a straight scene keeps its plain write.
* **B wiring**: the folded branch consults the frozen-aware shift *before* the gap distribution.
* **C real scene** (skip-if-absent): drives the shipped `fov_solve` on the flagged layout —
  the BS row still carries no distance; the fold mirror does not move **against the optics it
  folds** (its offset from the lens rear datum, which is the frame-honest invariant: the OBJECT
  side legitimately slides the whole machine, since row 0's thickness is the object distance and
  everything downstream of it is world-placed); re-solving for the field the scene is already at
  moves **nothing** (the flagged gesture, in a form that does not depend on what the user's live
  file currently holds); and a 40×40 solve really does re-place the sensor, so none of the above
  can pass on a machine that never moves.

## Pre-existing reds in this family (confirmed at HEAD with the work stashed out)

All three drive the user's LIVE `machine_vision_AZ85_RA_Mirror_BS.py`, which he keeps editing,
so they have drifted off the baseline that was cut on 2026-08-05 — they fail identically with
and without this fix:

| phase | guard | failure at HEAD |
|---|---|---|
| 380 | `0468_fov_solve_respects_collision_floor` | "the colliding field was not resolved by sliding" |
| 414 | `0515_snap_and_solve_keep_camera_clear` | A3 message assertion; B2 "residual traced defocus (got None)" |
| 418 | `0519_frozen_fov_solve_range` | wants "snapped to the traced focus" in the message |

418 is now closer: with fix (5) the folded solve **does** snap, but it reports the fallback
wording ("Snapped the detector to the traced focus") because `_traced_bundle_best_focus_shift()`
returns nothing on this scene — the same `None` that 414-B2 fails on, and the same
measurement-side hole as the item below. Left for their own turn rather than half-fixed.

## Open, found while measuring (not fixed here)

`_real_ray_best_focus_shift_for_rows()` returned **the identical value (35.849154373645376) with
the sensor 35.85 mm nearer, unmoved, and 35.85 mm further** — it is measured from the analysis
surface, so it says where the rays converge, not how far the *sensor* is from that convergence.
Any caller that treats it as a residual (a "snap to best focus" loop, bugs/0515's "iterate,
never single-shot") therefore cannot converge on this scene. Worth its own turn.
