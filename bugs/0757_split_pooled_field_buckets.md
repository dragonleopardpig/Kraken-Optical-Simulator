# 0757 -- a bucket that pools several field points is not a field group

The last symptom left from the camera-stage work: after a solve the two arms disagreed by 95 mm
about where the image forms, while carrying identical magnification to six digits.

```
 arm key                         rays      offset    waist um   sensor um
   A ('source:0', 3)              106      0.0235       0.805       1.177
   A ('source:0', 4)              106     -0.0200       0.055       0.733
   A ('source:0', 5)              106      0.0235       0.804       1.175
   B ('source:faceB', 8)          318    -95.3514    3865.294    8957.731
```

## Cause

Arm A arrived as **three** field groups. The mirrored second arm (bugs/0696) arrived as **one**
index carrying all 318 rays from three distinct field points.

bugs/0728 groups rays by field for exactly this reason -- *"rays from different field points stay
separated by the image height at every plane, so a least-squares waist over the whole bundle
would minimise the IMAGE SIZE, not the blur"*. With arm B pooled, its "waist" was the image
height (3865 um), and the drawn focus plane went 95 mm out.

This is NOT bugs/0753. There the vote was wrong; here the grouping the vote runs on is wrong. The
field decomposition is produced upstream (`_preview_field_index_by_source_ray`, one index per
launch bundle) and the mirrored twin can collapse to a single bundle depending on trace state.

## Fix

Do not depend on an upstream index that can collapse -- recover the decomposition from the rays.
`_split_pooled_field_buckets` splits a bucket whose launch points fall on a small number of
distinct positions into one group per position, before anything measures a waist.

A source that launches from a continuum (a random-area emitter) has as many positions as rays,
exceeds `max_groups`, and is left exactly as it was -- so bugs/0728's pooled fallback still
covers it. A split that would leave fewer than two well-sampled groups is declined.

## Result -- traced, both arms, across the delivered range

| device | residual before | residual after |
|---|---|---|
| 48.4 mm | -0.023 / **-97.46** | -0.023 / **-0.023** |
| 50 mm | -0.022 / **-96.48** | -0.0216 / **-0.0216** |
| 52 mm | -0.020 / **-95.35** | -0.020 / **-0.020** |
| 55 mm | -0.018 / **-93.81** | -0.0179 / **-0.0179** |

The two arms now agree exactly, which is what the mirror symmetry demands and what bugs/0752
made checkable in the first place.

## Guard

`validate_open3d_0757_split_pooled_field_buckets.py` (penta phase 546): the om05a shape splits
three ways with rays, polylines and launches kept in step and nothing lost; a genuine
single-field bucket and a 300-point continuum are both left untouched; a split that would leave
one well-sampled group is declined; and the production measurement runs it before partitioning.
