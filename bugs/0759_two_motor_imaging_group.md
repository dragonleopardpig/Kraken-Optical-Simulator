# 0759 -- the imaging group on one motor, the lens on another

User, describing the production bench:

> One Motor move the Lens + Filter + 40mm RA mirror + Camera together, another Motor move the
> lens alone.

That is the parametrisation the om05a actually has, and it is two genuinely independent knobs:

```
Motor 2   the lens alone       ->  s and s' trade off, the track K is FIXED   (the bugs/0719 pair)
Motor 1   the whole group      ->  s changes, s' FIXED, K changes            (new)
```

With both, any conjugate is reachable: Motor 2 sets `s'`, Motor 1 then sets `s`.

## What was wrong before

bugs/0756 booked the image-side correction by sliding the **sensor** along its leg. That works,
but it spends camera-to-mirror clearance, which capped the deliverable device at **48.4-56.1 mm**.
Moving the whole group changes the track without spending any clearance, because the camera and
the mirror travel together.

## The subtlety that cost five earlier attempts

Moving the fold mirror's **seat alone does not work**. Measured on the healthy scene:

```
dx =  0.0   fold vertex [279.299, 46.134, -23.982]   sensor [272.633, -2.609, -25.0]   residual [-0.0535, -0.0537]
dx = -5.0   fold vertex [273.854, 46.579, -23.451]   sensor [267.633, -7.609, -25.0]   residual [-0.0535, -0.0537]
```

The sensor picks up **-5 in x AND -5 in y**: the fold walk adds a displacement that pushes it
further from the mirror by exactly what the seat move gained. The conjugate is invariant to four
decimals. I concluded from this that C1 could not be freed -- wrong, because I had moved only the
mirror, not the assembly. Writing the SAME delta to the sensor standoff cancels the fold walk's
term and the group translates rigidly:

```
dx = -5, dstandoff = -5   ->  sensor [267.633, -2.609, -25.0]   residual +4.9879   (x only)
dx = -21.94, same         ->  sensor [250.693, -2.609, -25.0]   residual +21.0702
```

## Fix

* `camera_focus_stage` gains `arm_row` + `arm_min_mm` / `arm_max_mm` -- the fold mirror whose seat
  carries the group. A bad arm row degrades to the bugs/0756 sensor-only stage rather than
  disabling it.
* `_apply_camera_arm_move(delta)` writes the SAME delta to the seat and the standoff.
* `_apply_conjugate_pair` books `image_delta` through the arm when one is declared, bounded at
  both ends, refusing with the number ("the imaging group would have to travel to X mm, outside
  its A to B mm stage") rather than clamping.

## Clearance really is invariant

Measured world distance from RA mirror 2 to the sensor, across a 70.75 mm group travel:

| device | mirror x | sensor x | mirror-sensor |
|---|---|---|---|
| default | 272.683 | 272.633 | 55.3851 mm |
| 20 mm | 209.568 | 209.518 | 55.4122 mm |
| 40 mm | 239.466 | 239.416 | 55.3887 mm |
| 54 mm | 280.315 | 280.265 | 55.3868 mm |

## Delivered range -- traced through the real solve, both arms

| device | A5 | C1 | field | residual |
|---|---|---|---|---|
| 17 mm | **1.236** (lens at the prism) | 147.164 | 17.799 | -0.306 |
| 20 mm | 12.500 | 135.900 | 20.929 | -0.341 |
| 25 mm | 31.274 | 117.126 | 26.161 | -0.301 |
| 30 mm | 50.048 | 98.352 | 31.379 | -0.320 |
| 40 mm | 87.595 | 60.805 | 41.820 | -0.319 |
| 45 mm | 106.369 | 42.031 | 47.148 | +0.033 |
| 54 mm | 140.162 | 8.238 | 56.686 | -0.019 |
| 56 mm | 147.671 | **0.729** (lens at the filter) | 58.793 | -0.016 |

**Device 17 - 56 mm** (object field 17.8 - 58.8 mm), against 48.4 - 56.1 mm before. The user's
original 20 - 54 mm request is covered with margin.

Motor travel: **Motor 1 about 71 mm** (mirror x 209.57 - 280.32), **Motor 2 about 146 mm**
(C1 147.16 - 0.73).

## Known residual

The small-field end carries a systematic **-0.32 mm** (about 2 pixels of the 0.153 mm one-pixel
depth of focus). A third solve iteration converges to zero further moves, so this is not a
convergence failure -- it is the first order disagreeing with the real folded trace at high
magnification, the bugs/0745 class. The large-field end is clean (-0.016 to +0.033 mm).

## Guard

`validate_open3d_0759_two_motor_imaging_group.py` (penta phase 548) -- spec parsing and
degradation, the rigid-translation invariant (the same delta on seat and standoff), refusal
without an arm, the solve routing and its two-ended bound, and the bugs/0756 path surviving for
scenes that declare no arm.
