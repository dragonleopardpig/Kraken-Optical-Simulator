# 0097 — two branch detectors collapse onto the global Image on a two-arm splitter

**Date:** 2026-06-19 (M90aPro)
**Branch:** nonseq-display-refactor
**Status:** branch-detector collapse FIXED — `validate_branch_detector_multi_arm` green; in-app confirm pending. (Two sibling overlay bugs on the same scene still open: a mis-tilted reflect detector plane, and a thickness dimension spanning across arms.)

## Symptom (flag_20260619_154528, beam_splitter_two_arm_doublets)

"Transmitting path shows 2 unknown orange squares lying perpendicular to each other
at the end." From the recording's `row_actor_bounds`, both derived branch detectors
sit at **(0,0,192)** (the global Image):

  - `100001` — +Z normal, (0,0,192): the transmit detector (correct);
  - `100000` — **+Y normal**, also (0,0,192): the reflect detector — right orientation,
    wrong position (should be up the +Y reflect arm, ~y=130).

So a +Y square and a +Z square overlap at the transmit image → perpendicular.

## Root

`derive_branch_detectors` pins a leaf's focus to the reached sequential Image (the
bugs/0093 reached-image pin) so a transmit detector coincides with its image. But
`_reached_image_target` returns the single *furthest* global Image, and in a SPLIT
every terminal leaf that lands on a detector trips `reaches_image`
(`_leaf_reaches_existing_detector` → `hit_detector`). So the reflect leaf — rays
+Y, landing on its own +Y detector — was also pinned onto the +Z global Image,
collapsing both detectors onto (0,0,192).

## Fix

Only apply the reached-image pin when the image lies on **this** leaf's beam: ahead
of the mean exit point and aligned with the mean exit direction
(`dot(image − exit, mean_dir)/|image − exit| > 0.7`). The transmit leaf (+Z, image
ahead, align≈1) still pins; the reflect leaf (+Y, image behind, align≈−0.56) keeps
its own +Y convergence focus.

## Test

`KrakenOS/UI/validate_branch_detector_multi_arm.py` — synthetic two-arm bundles
(transmit converging at the +Z global image, reflect up +Y): the transmit detector
pins to (0,0,192), the reflect detector stays up the +Y arm. The three existing
branch-detector validators (0088 B1, 0092 supersedes-image, reflected-bounds) stay
green — the cube-scene pin is unchanged.
