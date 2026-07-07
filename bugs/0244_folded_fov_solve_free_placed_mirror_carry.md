# 0244 — Folded FOV solve mis-carries the free-placed trailing mirror (FIXED)

## Symptom
On the real PYRITE 85 layout (`attachment/machine_vision_Pyrite85_RA_Mirror.py`), the Quick
Estimation object-FOV solve (`fov_solve('object', 'thickness', 55, 55)`) produces a
geometrically inconsistent scene: the solve grows the object gap (+119.8 mm) and shrinks the
rear gap (-148.8 mm), and the free-placed 2nd RA mirror is carried straight down the arm by the
rear-gap delta — landing at arm-distance ~35.9 mm, BEFORE the lens block (~60..100 mm). The
beam then folds at mirror2 before ever reaching the lenses. Under the old display-bend pipeline
this was invisible (the drawn rays were bent copies of a straight-axis stand-in); the bugs/0243
real trace now shows it honestly — this is the remaining piece of the user's
"after setting FOV 55x55, still the same error" (flag_20260706_161136_145; the recording's
lens actors sit at y≈217..257 PAST mirror2 at y≈193 — physically impossible optics).

## Why the carry is wrong here
The PYRITE fixture (imported from the real ELS-85 CAD) authors mirror2 as a FREE-PLACED solid
at its hardware pose, while the prescription's rear gap row spans lens→mirror→sensor THROUGH
the corner (the bugs/0242 leg convention: near = rear gap row, far = the mirror row's own
thickness). `carry_free_placed_followers_after_fold` (bugs/0236) slides the mirror by raw
post-fold gap DELTAS — correct when the gap row is a pure lens→mirror distance (the AZ85
fixture), but on a corner-spanning convention the mirror must slide by the change in its
ALONG-BEAM position derived from the folded legs (e.g. via the same pose-override leg walk that
seats the followers), not by the raw row delta. The object-side gap change additionally moves
the fold vertex, which the carry only tracks in the station term.

## Definition of done
- After an object-FOV thickness solve on PYRITE 85, the scene stays ordered
  (object → M1 → lens block → M2 → sensor along the beam), mirror2 rides the beam at the
  prescription distance, and the real-trace on-axis cone focuses on the drawn sensor
  (the bugs/0243 stigmatic-focus result, which already holds on the AZ85 two-fold after
  `snap_detector_to_image_plane`).
- A display-free guard on a corner-spanning fixture replicating the PYRITE convention
  (free-placed mirror pose ≠ naive station arithmetic), plus a penta phase.

## Root cause
The stale free-pose offset. Both fixtures author the trailing mirror CLOSER to the lens than
its prescription rear gap says: on PYRITE, mirror2's real along-beam distance from the lens
rear is 84.71 mm but the rear-gap row reads 173.864 mm; on AZ85 it is 57.72 mm vs a 150.368 mm
row (a +92.6 mm stale offset). The total optical path is preserved — only the near/far split
differs from the bugs/0242 corner-spanning leg convention. `carry_free_placed_followers_after_fold`
(bugs/0236) slid the pinned mirror by the RAW post-fold row delta, which preserves that stale
offset. When the FOV solve writes the whole image_delta (PYRITE: −148.822 mm) into the rear-gap
row, the raw slide exceeds the mirror's real ~84.7 mm world clearance and drives its along-beam
coordinate BELOW the lens rear — mirror2 lands in front of the lens block and the on-axis cone
folds at the mirror before reaching the lenses (object → M1 → M2 → sensor, no lens).

## Fix
`KrakenOS/UI/nonseq_output_ports.py::carry_free_placed_followers_after_fold` — replace the raw
along-beam slide `post_fold_delta * r_hat` with a RE-SEAT at the leg-walk follower position.
Anchor on the nearest upstream follower the pose-override walk already seated
(`build_optical_solid_output_port_pose_overrides`), then place the mirror at
`pred_center · r_hat + near_leg`, where `near_leg` is the sum of the (post-solve) gap
thicknesses from that anchor to the mirror. So the mirror rides the beam at the SOLVED rear gap
regardless of the stale authored offset. The perpendicular (z_hat) drift term
`− post_fold_delta * z_hat` is unchanged (keeps the on-beam offset the bugs/0236 guard pins).
On a fixture with no stale offset (`along == near`) the r_hat coefficient `near_leg − along`
equals the old raw delta, so the AZ85 two-fold arm-follow / segment-split behaviour is bit-identical.

## Result
Headless PYRITE 85 `fov_solve('object','thickness',55,55)`:

    before fix : mirror2 along-beam Y=35.86 (BEFORE lens rear 99.97) — folds early, no lens
    after fix  : mirror2 along-beam Y=125.02 (AFTER lens rear 99.97) = rear gap 25.04 past it
    ordered object → M1 → lens (60..99.97) → M2 (125.02) → sensor; detector reach 265 → 1685

## Verification
`validate_open3d_folded_fov_free_mirror_reseat` (display-free, on the AZ85 two-fold fixture,
which carries the same +92.6 mm stale offset) pins five checks:
  1. RE-SEAT — after a large rear-gap shrink the mirror rides at `lens_rear + new rear gap`
     (139.953 mm), not the stale offset;
  2. NOT PAST THE LENS — the fix seats it AFTER the lens rear (139.953) where the old raw-delta
     slide would have thrown it BEFORE (47.304 < lens_rear 124.953) — the reported crash;
  3. PERP PRESERVED — the perpendicular beam offset is untouched (70.598 → 70.598);
  4. END-TO-END — the real `_apply_conjugate_pair` leaves the mirror after the lens;
  5. WIRED — the carry re-seats via the leg-walk anchor (`near_leg`), not a raw `r_hat − z_hat` slide.
Added as penta phase 222; the bugs/0236 two-fold arm-follow (phase 213), folded image-segment
split (phase 219) and folded FOV-solve guards all still pass unchanged (bit-identical on AZ85).
