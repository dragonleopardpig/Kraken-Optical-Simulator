# 0390 — folded rays that MISS the detector must also hide with clipping OFF

**Flags:** the 4-flag workflow `flag_20260721_162643/162754/162918/163056` (before swap → after
swap → after lens flip + rays on → after FOV 20×21 + thickness solve). Flag #4:
"…the ray still broken. I checked Overlays → Clipped, it is not ticked. How should I off ray
clip?" (scene `machine_vision_AZ85_RA_Mirror.py`, build baf1d7e7 = 0389).

## What was still wrong after 0389

0389 hid folded rays that vignette at an aperture (`stopped`). But the user, with **Show Clipped
Rays OFF**, still saw a spray of "broken rays" fanning **past the second RA mirror** along the
unfolded axis (screenshot: the beam folds up into the camera, but a cone of rays skips the
second mirror and sprays toward the lower-right).

Mechanism: with the larger FOV (20×21) the beam is wider than the **second** fold mirror's
aperture, so the field-edge rays **skip** it (in a folded display they are scored against the
detector and come back `missed_detector`, not `stopped`). 0389's predicate kept folded rays
visible for **every** terminal status except `stopped` — so these folded-then-`missed`
strays still rendered. (Confirmed no scene source is involved — these are imaging rays in
`world_cone` sampling, per the user.)

## Fix

Extend the clipped-ray classifier `ray_path_visible_without_clipping_from_events`
(`scene_geometry.py`): a folded ray hides with clipping OFF when it **failed at a real
downstream element** — `stopped` (vignetted, 0389) **or** `missed_detector` (missed an existing
detector's clear aperture, 0390):

```python
if ray_path_has_non_refractive_steering(path):
    if status in ("stopped", "missed_detector"):
        return False      # folded THEN blocked/missed = stray -> hide (North Star: misses hide)
    return True            # authored branch: hit_detector / absorbed / escaped (no detector)
```

This matches the North Star clipped-ray rule ("detector misses … are hidden") and the 2D
filter (which keeps only detector hits). A genuine beam-splitter 2nd path never lands here: it
reaches its detector (`hit_detector`), is `absorbed` (beam dump), or escapes with no detector
to land on (`no_hit`) — all still kept visible.

## Verification

- **Non-vacuous real-scene test** (`validate_open3d_folded_vignette_hidden`, penta phase 327):
  shrinking the AZ85 sensor to 2 mm forces **2504** folded imaging rays to `missed_detector`
  (the same class as spray-past-the-mirror) — all 2504 now hide, all 432 folded+`stopped`
  hide, and all folded imaging rays that still land stay visible.
- **Beam-splitter safety** (real MV-150 scene): the authored reflected branch is
  `absorbed`+folded — **117/117 stay visible**; 0 folded+`missed_detector` there, so nothing
  authored is hidden.
- **Contracts:** `validate_open3d_clipped_vignetting_parity` adds a `missed_folded → hidden`
  case next to `stopped_folded → hidden` and `escaped_folded → visible`. Passes.

## Files

- `KrakenOS/UI/scene_geometry.py` — extend the hide condition to `missed_detector`.
- `KrakenOS/UI/validate_open3d_clipped_vignetting_parity.py` — add the `missed_folded` case.
- `KrakenOS/UI/validate_open3d_folded_vignette_hidden.py` — add the non-vacuous shrunk-sensor
  `missed_detector` assertion.

## Caveat — running app / exact config

Verified on the real AZ85 folded scene (folded-miss and folded-stop hide; beam and MV-150
branch preserved). The user's exact broken-ray view is a modified config (swapped + **flipped**
lens + FOV 20×21 + constrained thickness solve) that couldn't be reproduced end-to-end here;
the fix targets the `missed_detector` class those spray rays fall into. The flag's build stamp
is the checkout, not the running process, so the app must be restarted on ≥ this commit to pick
up 0389/0390. If a spray persists after a clean restart, a fresh recording will show whether any
rays are scored raw `escaped` rather than `missed_detector` (a narrower case bordering the
beam-splitter-branch protection).
