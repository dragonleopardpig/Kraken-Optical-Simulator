# 0756 -- the camera's own leg is the third conjugate variable

User: *"make A5, C1 and C2 adjustable to achieve closest match FOV range derived from my
target."*

Their naming: **A5** = `prism exit gap (air)` (lens slide, front), **C1** =
`Rear Optical Vertex Datum` (lens slide, rear), **C2** = RA mirror 2 -> sensor.

## What the flag showed

Flag `20260908_154430_151`, device 55x55 mm. The solve had already worked out the answer:

```
image_gap_row: 24            <- the sensor standoff row
image_delta_mm: +10.78       <- exactly the C2 change that lands the image
reason: the sensor carries the vendor camera body (glued camera STEP)
```

bugs/0719 refuses **every** image-side write while a camera STEP is glued to the sensor. That is
right about the camera BODY and wrong about its POSITION. Translating the whole assembly along
its leg leaves the vendor geometry byte-identical --
[[feedback_vendor_hardware_immutable]] forbids reshaping vendor parts, not mounting them on a
stage. With C2 frozen the solve can deliver exactly ONE field (54.09 mm); everything else
detaches, which is every "image plane not landed" flag in this arc.

## Fix

A scene opts in through the layout settings, so it round-trips in the `.py`:

```python
'camera_focus_stage': {'enabled': True, 'row': 24, 'min_mm': 0.0, 'max_mm': 24.04}
```

* `_camera_focus_stage()` validates it (row in range, positive travel) or returns None.
* `_image_write_locked_by_vendor_hardware` lifts the camera lock **only** for the row the stage
  travels on. Every other image-side write, and the downstream vendor-solid check, are untouched.
* Running past either end is a refusal naming the number -- *"the camera stage would have to sit
  at 31.2 mm, outside its 0 to 24.04 mm travel"* -- through the same path as any other refusal,
  so the residual and the bugs/0754/0755 way-out line are reported as usual. Never a silent clamp.

`min_mm` is the hard floor where the camera body reaches the upstream optic. Measured on om05a:
the camera front edge stands **21.53 mm** ahead of the sensor and RA mirror 2's nearest point is
**31.19 mm** out, so the leg may not go below **36.31 mm**.

## Scene change

The stage was re-based to mid-travel so it can move BOTH ways with a non-negative thickness --
the gap distributor will not write a negative gap, which is why the first cut only ever moved
outward:

```
row 16 'RA mirror 2 (40 mm)'  45.13 -> 36.31      (the clearance floor)
row 24 'sensor standoff'       0.85 ->  9.67
total leg                     45.98 -> 45.98      UNCHANGED -- optics identical
```

Rows 17-23 (arm B) sit between them and would have slid by -8.82 mm (bugs/0748); their `desp_z`
is corrected by the same amount. The bugs/0750 audit reports **no promoted row moved**.

## Result -- traced, both arms

| device | A5 | standoff | leg | clearance | field | residual |
|---|---|---|---|---|---|---|
| 55 mm | 143.92 | 20.45 | 56.76 | 20.45 mm | 57.736 | **-0.018 mm** |
| 52 mm | 132.65 | 11.08 | 47.39 | 11.08 mm | 54.586 | **-0.020 mm** |
| 50 mm | 125.14 | 4.96 | 41.27 | 4.96 mm | 52.486 | **-0.022 mm** |
| 45 mm | -- | (refused) | -- | -- | -- | out of travel |
| 40 mm | -- | (refused) | -- | -- | -- | out of travel |

Every landed case is inside a third of a pixel of depth of focus, both arms 318 rays with
identical |m| to six digits. The two that cannot be reached refuse and say so.

**Delivered range: object field 50.7 - 58.9 mm, i.e. device 48.3 - 56.1 mm.**

## Known remaining defect

Arm B's focus readout still shows the bugs/0753 class of outlier at these stations (-93 to
-96 mm against arm A's -0.02) while both arms carry identical |m| to six digits. bugs/0753
fixed one instance of a bad field group winning the waist vote; this is another. The delivered
geometry is symmetric and correct -- the readout is not.

## Guard

`validate_open3d_0756_camera_focus_stage.py` sections C/D/E (penta phase 545).
