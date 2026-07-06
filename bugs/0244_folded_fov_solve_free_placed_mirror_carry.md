# 0244 — Folded FOV solve mis-carries the free-placed trailing mirror (OPEN)

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
