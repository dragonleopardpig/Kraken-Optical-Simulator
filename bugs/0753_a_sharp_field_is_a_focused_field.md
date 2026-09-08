# 0753 -- an already-sharp field is a focus measurement, and nine rays are not evidence

Found while measuring the leg sweep for the user's question ("we can change the distance from the
sensor to the RA mirror right before it, what will be the FOV coverage range?"). At the 54.09 mm
station the two arms disagreed absurdly:

```
armA residual  -0.0535 mm      |m| 0.4259531881      322 rays
armB residual -105.3673 mm     |m| 0.4259532503      322 rays
```

Identical magnification to seven digits, equal ray counts, mirror-image geometry -- and a 105 mm
disagreement about where the image forms. Not physical.

## Cause

The per-field vote in `focus_waist_from_grouped_rays` was `rms_waist < 0.5 * rms_plane` -- purely
**relative**. Arm B's four fields:

| field | rays | offset | waist | at sensor | old vote |
|---|---|---|---|---|---|
| 3 | 101 | **-0.0111 mm** | 0.73 um | 0.83 um | **rejected** |
| 4 | 106 | -25.5391 mm | 1996.74 um | 2257.49 um | rejected |
| 5 | 106 | -25.5430 mm | 1996.89 um | 2257.35 um | rejected |
| 6 | **9** | **-105.3673 mm** | 2846.79 um | 8855.00 um | **accepted** |

Two failures in one line:

* **A field already AT focus cannot tighten by 2x**, so it was rejected *for being sharp*. Field 3
  is the right answer -- 0.73 um, essentially on the sensor -- and it was the one thrown away.
* **A field blurred everywhere passes**, because 2.8 mm is less than half of 8.9 mm. Nothing
  required the "waist" to be small in absolute terms, or the field to be sampled by more than a
  handful of rays.

Arm B had no surviving voter, so nine junk rays set the plane. Arm A survived only by luck: its
106-ray field 1 also tightened, and `argmax(weights)` preferred it over its own 4-ray outlier at
-117.51 mm. The defect is pre-existing -- bugs/0752 made it visible by measuring the arms
separately instead of pooling them, where `argmax` over all eight groups masked it.

## Fix

Two filters, both applied before anything votes:

* **Sampling adequacy** (`_MIN_SAMPLE_SHARE = 0.2`): a group carrying less than a fifth of the
  best-sampled group's rays is not evidence and never reaches the vote. Drops the 9-ray field
  beside a 106-ray one.
* **Absolute sharpness** (`_SHARP_WAIST_FACTOR = 10.0`): a field votes if it tightens **or** if it
  converges (`waist <= plane`) and its waist is within 10x the sharpest waist in the bundle. Being
  in focus is a focus measurement. Admits field 3; still refuses fields 4 and 5, whose 2 mm waists
  are 2700x the sharpest available.

## Result

```
station gap1 130.89 / standoff +0.85    armA -0.0535    armB -0.0111   (was -105.3673)
today's scene, untouched                armA -17.2812   armB -17.2799  (unchanged)
production om05a_folded.py              armA  -0.4565   armB  -0.4564  (unchanged)
```

Both arms now agree, and the two scenes that were already right are bit-identical.

## Guard

`validate_open3d_0753_a_sharp_field_is_a_focused_field.py` (penta phase 543), display-free, on a
deterministic synthetic fixture that reproduces the exact shape: one well-sampled already-sharp
field, two well-sampled blurred ones, one 9-ray field blurred everywhere.

* A: the failure precondition is reproduced -- the junk field is the ONLY one the old test admits;
* B: the measurement now picks the well-sampled sharp field and reports its offset;
* C: each filter is exercised alone, including "an already-sharp field measures on its own";
* D: a genuinely defocused bundle is unchanged, and both fields still vote (bugs/0728 intact);
* E: the filters sit in the production path, sampling before vote before tally.
