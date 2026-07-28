# 0460 — the one-click "Add Beam Splitter to LED" produces a BS that does not fold into the chain

Split out of bugs/0459 after the 6-flag walkthrough (build `6e0efacd`). **bugs/0457 is fixed and
confirmed** by that walkthrough: the user's Image row lands at (228.5, 0, 2.3), coincident with the
camera body and the reached-image detector, at every step.

## Measured

Replaying the interactive build (load AZ85 → delete the object-side RA mirror → `add_beam_splitter_to_led("plate")`):

| scene | BS row tilts | reached folds | neutralised | ray terminations |
|---|---|---|---|---|
| the user's SAVED `..._BS.py` | (0, 0, **−90**) | [3, 7] | none | **167 target_termination** |
| freshly added BS, untouched | (0, 0, **0**) | [2] only | **row 7 zeroed** | 558 no_next_intersection |
| same, with `tilt_z = −90` forced | (0, 0, −90) | **[2, 7]** | none | 485 no_next + 73 vignette |

So a freshly created BS is **not oriented to fold the beam into the lens chain**. Its diagonal reads
Y–Z, the beam folds toward −Y, and nothing reaches the chain. Forcing `tilt_z = −90` repairs the
fold-walk half (row 7 regains the bugs/0243 exemption and keeps its 51.5 mm — this is the bugs/0457
machinery working), but the scene still does not image, so orientation is only ONE of the
differences from a working BS.

## Two theories killed by measurement (recorded so they are not re-tried)

1. **"the save normalises the scene"** — FALSE. Saving the interactive scene and reloading it
   changes only `row0.diameter` (28.28 → 53.81) and `row2.thickness` (0.0 → 62.51), and it still
   does not image (556 no_next_intersection + 2 missed_image). The user's saved file works because
   of what they DID in that session (resize / reposition / rotate), not because saving fixed
   anything. Every earlier "live-vs-saved asymmetry" note in bugs/0457 and bugs/0459 is superseded
   by this.
2. **"the drawn rays are clipped by the display"** — FALSE for the saved scene:
   `scene_display_center_radius` gives radius 250.29 (sphere spans x −137…363), only 7 of 174
   records are bounded, and the output still has 174/174 reaching past x=200. The merged-ray path
   (`_flush_merged_ray_actors`) appends whole polylines and truncates nothing.

## What is still unexplained

The user's LIVE rebuilt scene is geometrically CORRECT (all six flags agree) yet its drawn beam
stops at the last lens element. That scene is not reproduced by either artifact available here: it
is not the saved `..._BS.py` (which images fine, 167 rays) and not the freshly-added BS (which is
mis-aimed from the start).

**Needed to finish this: the user's CURRENT scene saved to a file.** The saved `..._BS.py` cracked
bugs/0457 precisely because it was the exact failing geometry; the same is needed here. Without it
every remaining hypothesis is unfalsifiable.

## Fix direction for the one-click BS itself (independent of the above)

`add_beam_splitter_to_led` auto-flags the 45° diagonal but leaves the row's trace tilts at zero, so
the DRAWN plate and the TRACED plate disagree — the display-follows-physics rule. The native
promotion path (`promote_imported_step_to_native_surface_rows`) already does this correctly: it
writes `row.tilt_x/y/z` from `applied_pose["row_tilts_deg"]`. The parametric BS should do the
same, deriving the tilts from the solid's own orientation so the trace folds the beam exactly where
the user sees the diagonal.

**Acceptance test:** after `add_beam_splitter_to_led("plate")` on the mirror-deleted AZ85, the BS
row's tilts must match its drawn diagonal, `folded_beam_reached_mirror_fold_indices` must include
BOTH the BS and the downstream fold mirror, and rays must reach the sensor.
