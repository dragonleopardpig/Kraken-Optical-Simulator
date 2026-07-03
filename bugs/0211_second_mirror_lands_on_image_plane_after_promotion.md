# 0211 — after promotion the 2nd RA mirror lands on the image plane ("misplaced by itself")

**Status: DIAGNOSED, NOT blind-fixed. This is the in-app 2nd-fold authoring workflow (task #77)
surfacing: the default promote parks the 2nd mirror at the sequential tail (on top of the image
sensor) with no fold tilt. The real fix needs the user's intended 2nd-fold geometry, touches the
penta-shared fold/placement machinery, and can't be verified headless — so it is documented here for
an in-app pass, not blind-patched.**

## Flag

`attachment/recorded_bug_repros/flag_20260703_082955_542` + full recording
`recording_20260703_083038.json`:

> *"After promotion: 2nd RA mirror misplaced by itself."*

This is the **next step** after bugs/0210 (which made the re-imported 2nd-mirror overlay stay drawn
after placement). The user then **promoted** that placed overlay, and the resulting optical solid
jumped to the far end of the system.

## Evidence (prelude → flag diff — the promote itself is not a replayable recorder event)

**Prelude (recording start):** 9 rows, exactly **one** promoted mirror —
`S1/S2: Promoted OPTICAL STEP optical solid`, then the ELS-85 blackbox lens (S3–S7) and
`S8: Image / Sensor`. `step_paths` lists only `lens` + `camera` overlays (no `optical`), so the 2nd
mirror was **imported and promoted mid-recording** — neither is logged as a replayable event, so
only the prelude→flag snapshot diff shows it (the recorder-import gap, see the topic file's STILL
OPEN #1).

**Flag (captured state):** two promoted solid rows —

| row | role | `center_world` (promote) | drawn `row_actor_bounds` (X / Y / Z) | tilt |
|-----|------|--------------------------|--------------------------------------|------|
| 1 | mirror 1 | `[0, 0, 71.9]` | X`[-12.7, 12.7]` Y`[-12.7, 12.7]` Z`[59.2, 84.6]` | `[0,0,0]` |
| 8 | **mirror 2** | `[213.59, 0, 71.9]`, desp `[213.59, 0, -275.32]` | **X`[253.8, 284.3]`** Y`[-9.0, 21.5]` Z`[54.1, 89.7]` | `[0,0,0]` |
| 9 | Image/Sensor | — | X`[259.0, 291.6]` Y`[0, 40]` Z`[55.6, 88.2]` | — |

Mirror 1 is correct (world centre `[0,0,71.9]`). **Mirror 2 is drawn at X≈254–284 (centre ~269),
which overlaps the image sensor at X≈259–292 (centre ~275)** — the 2nd mirror sits *on top of the
detector*. The screenshot confirms it: the top-right cube is exactly where the rays converge.

## Mechanism

1. **Default insert index = the sequential tail.** With no table selection,
   `_step_overlay_insert_index(None)` (`services/step_overlay_promotion.py:562-564`) returns
   `len(self.rows) − 1` when the last row is `Image` — i.e. the 2nd mirror is inserted **just before
   the image plane**, at the very end of the optical train.
2. **The tail station maps onto the far +X leg.** `promote_imported_step_to_optical_solid_row` sets
   `desp_z = center_world[2] − z_station` where `z_station` is the cumulative thickness up to the
   insert index (≈347 mm here). Through mirror-1's fold, that tail station lands the row on the +X
   leg at the image distance (X≈269), so `desp = [213.59, 0, −275.32]` (the −275 mirrors the single
   AZ85 focus at X≈275, cf. bugs/0209).
3. **No fold.** The promoted mirror carries `tilt = [0,0,0]` — it does not bend the beam. It is just
   a BK7 block dropped onto the image plane, not a working second fold.

So "misplaced by itself" = the promote auto-parks the mirror at the sequential tail (on the sensor),
regardless of where on the +X leg the user wants the second fold. The overlay's placed centre
(`desp_x/y` = `center_world[0/1]`) is preserved, but it is dominated by the tail-station re-mapping.

## Why this is not blind-fixed (same class as bugs/0209)

- **Needs the user's intended geometry.** A working 2nd fold is a *design choice*: where on the +X
  leg (between the rear datum at X≈125 and the sensor at X≈275) the mirror sits, and which new
  direction it folds the beam / where the new detector goes. There is no unambiguous "correct" pose
  to snap to.
- **Penta-shared, regression-risky.** The insert-index, fold-tilt solve (`_solve_mirror_tilt`),
  `fold_promoted_mirror_specs_to_sequential`, and downstream pose-override chaining are the SAME
  machinery the penta cascade uses. The penta validator is the primary safety net and must stay
  green; changing tail-placement/fold behaviour blind risks it.
- **Can't be verified headless.** The recorder doesn't capture import/promote (so no replay), and the
  `_build_editor` harness can't drive the full promote (uninitialised `_history_restoring` /
  `_selected_step_label`, found in bugs/0210). So a faithful headless repro/guard isn't available
  without authoring the whole 2-fold scene in-app.

## What the fix is (task #77)

The 2nd-fold **authoring workflow**: insert the 2nd mirror on the +X leg between the rear datum and
the image (not at the tail), solve its fold tilt to bend the beam onto a new leg, and chain the
downstream image/sensor to follow the second fold — generalising the 0192 meridional re-fold and the
0207 `desp_z` fold-mapping from one fold to two. That is genuine in-app authoring against the penta
gate.

## What to do now

Confirm the intended 2nd-fold geometry (position on the +X leg + folded detector direction), then
build the authoring pass in-app and verify the penta cascade stays green. Until then, promoting a 2nd
mirror parks it on the image plane — expected, given there is no 2nd-fold placement yet.
