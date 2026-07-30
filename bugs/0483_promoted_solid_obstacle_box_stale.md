# 0483 — the camera anti-crash was testing the fold mirror's PRE-SOLVE box

**Flag `flag_20260729_185536`**: *"unhide the Camera STEP: the anti-crash algorithm not
functioning. Camera crash to RA mirror."*

Found while trying to certify bugs/0482: the clearance could not be measured at all, because every
mirror position available to the check was stale.

## Cause

`_promoted_solid_current_center` (bugs/0393b) reads the centre from `_last_scene_bundle`'s
`optical_solid` placement. Its docstring states the assumption plainly:

> The promotion metadata's centre is STALE once the solid is moved, but the mirror does not move
> during a lens swap, so the last-refresh placement centre is its live position.

True for a lens swap. False for every action that moves a solid and then **asks before the next
refresh** — a FOV solve, a leg split, a focus move. `camera_body_collisions` (bugs/0476) sizes its
obstacle from this centre, so on those paths the anti-crash tests where the mirror *used to be*.

Measured on `attachment/machine_vision_AZ85_RA_Mirror_BS.py`, a 30 × 30 FOV solve with no refresh
in between:

| row | cached bundle centre | live row pose | error |
|---|---|---|---|
| 7 (RA mirror) | (229.930, 0, 53.803) | (216.603, 0, 85.365) | **13.3 mm in x, 31.6 mm in z** |
| 3 (BS) | (−0.122, 0, 54.459) | (−0.122, 0, 91.351) | **36.9 mm in z** |

So at 30 × 30 the mirror really occupied z[78.20, 103.20] while the check believed z[41.30, 66.30]
— two boxes that do not even overlap. The camera could sit anywhere and the check would report
nothing. Across a 23/30/35/40 mm field sweep the cached box never moved once.

## Fix

The **row's own pose** is the truth the ray trace and the frozen split writers already use:
`_split_row_world_center` = station + desp, carried through
`_optical_axis_fold_world_transform_for_row` when the row has an override. Prefer it; keep the
bundle placement as the fallback when the pose cannot be read (bugs/0393b's path is untouched),
and the promotion metadata still supplies the **size**, which no move can change.

This is safe because the two sources agree *by construction* whenever the bundle is fresh — the
placement is built from the row. Measured, they match to 1e-9 as loaded, after a refresh, and
after a re-refresh; they diverge only after an unrefreshed move, and a divergence therefore *means*
the row moved. So the change is identical when nothing has moved and correct when something has.

## Verification

`KrakenOS/UI/validate_open3d_0483_promoted_solid_live_center.py`, penta **phase 390**,
display-free (a stub editor whose bundle placement deliberately disagrees with its rows), 9
checks: fresh bundle unchanged (A1), size still from the promotion metadata (A2), the moved row's
centre follows the row by the full 36.9 mm (B1/B2), the obstacle box moves with it (B3), the
no-row-index fallback still returns a box (C1), a folded row is reported in folded coordinates
(D1), an unreadable pose falls back to the bundle (E1), and the anti-crash really does size its
obstacle from this helper (F1).

Reverting the preference makes B1/B2/B3 fail with the stale centre.

On the real scene it is what makes bugs/0482's clearance measurable: the mirror's box now tracks
52.37 → 78.20 → 96.64 → 113.68 across a 23/30/35/40 mm sweep instead of sitting at [41.30, 66.30],
and `camera_body_collisions()` returns `[]` at every size with 0482 applied while reporting the
crash at 30/35/40 without it.

## Note for the next reader

0476 taught this check to *see* promoted solids; 0471's follow-up taught callers to run it *after*
the rebuild. Neither helps a caller that asks before any refresh has happened, which is the
ordinary case for a solve. Reading the row instead of the cache removes the ordering requirement
rather than adding another rule to remember.
