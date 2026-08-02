# 0511 — lens dragged near the RA mirror: phantom mid-leg detector + object plane lost

Flag `flag_20260802_195029_983` ("lens dragged to close to RA mirror, sensor
dislocate, missing object plane"), recording `recording_20260802_195054.json`,
build `a3a6649e` (the 0508 A fix — which HOLDS: the real Image row is correct
throughout). Scene `attachment/machine_vision_AZ85_RA_Mirror_BS.py`.

## What the recording shows (293 events, change-traced)

Session: four LED station drags (t=0-46s, axis:global rides 0 -> -36.9 —
the 0505 machinery working), one RA-mirror drag (t=54s, image row follows the
new fold leg 229.9 -> 207.4 — followership working), then FIVE lens drags.

The flag state toggles ON and OFF with the committed lens position:

| commit | lens_x | row-8 (Image) | row-100000 (branch det) | object actor |
|---|---|---|---|---|
| after drag to 77 -> back to 150.6 | 150.6 | (207.4, z=9.4) OK | **(207.3, z=28.1) SPLIT** | **x=0 nominal** |
| drag left to 90.4 | 90.4 | (207.4, 9.4) OK | (207.4, 9.4) = Image, healed | x=-16.3 riding |
| drag right to 124.4 | 124.4 | OK | still healed | riding |
| drag right to 143.6 | 143.6 | OK | **(207.3, z=35.8) SPLIT** | **x=0 nominal** |
| FLAG t=119s | 143.6 | OK | 35.8 | nominal |

Flag-time ground truth: camera front z=20.84, front_to_sensor 11.48, Image row
z=9.36 = EXACTLY the sensor plane — **row 8 never dislocates**. The thing the
user sees floating between prism and camera is the SYNTHETIC branch-detector
plane (row 100000) at z=35.8/28.1, which normally coincides with the Image.
Ray census at flag: target_termination 225, missed_image 270,
aperture_stop_vignette 63 — the near-mirror lens position vignettes hard (the
converging cone is cut early at the 25 mm mirror face).

## Root-cause picture

**A — phantom detector**: with heavy vignetting, the imaging leaf's
converging-exit-ray fit lands MID-LEG (the 0109 lesson: an lsq over clipped
marginal rays lands at pupil-ish artifacts, not the image), 18.7-26.4 mm short
of the designed Image. That distance sits INSIDE the bugs/0100-part-3 trust
window (trust a forward convergence when -0.5*to_image < behind < -1.0; here
behind = -26.4 vs half-leg -29.4), so the derived focus is TRUSTED and the
detector un-pins from the designed Image — even though 225 rays terminate ON
the designed Image in the same trace. A leaf that demonstrably reaches the
Image must stay pinned (the 0448 force-pin family; the trust window needs a
"reaches the image -> pin" precedence, not just a distance heuristic).

**B — object plane**: the green FOV plate rides the slid station in healthy
builds (post-0505) but in the SAME broken rebuilds reverts to nominal x=0 /
suppressed. Same upstream: the degraded trace makes the first-order/mag
reference fail (the 0104-family None -> rect suppressed), and what remains at
x=0 is the engine-transform-anchored curve (TRANS surface 0 never carries the
object's lateral desp). Symptoms A and B flip together on every commit —
one shared gate (trace health), two consumers.

## Fix directions (not yet implemented)

1. Branch-detector derive: if a leaf's rays REACH the designed Image (any
   meaningful count), pin its detector to the Image regardless of where the
   convergence fit lands; the trust window only arbitrates leaves that reach
   nothing. Contrast fixture: the dual-lens reflect arm (whose ~30%-short
   trusted fit is the feature the window was built for) must keep trusting.
2. Object plane: make the FOV-plate anchor resilient to a failed mag reference
   on a slid station (ride axis_root_origin; fall back to the last good mag or
   the straightened reference rather than suppressing), per the 0505 checklist
   ("every launch/probe/overlay must ride axis_root_origin").
