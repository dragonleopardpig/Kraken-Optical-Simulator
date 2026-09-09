# 0761 -- the filter travels with the group, and "already delivered" means the image LANDS

Flag `20260909_122103_567`: *"changed to 30x30 device size, the Edmund Filter misplaced. The image
plane is in front of the sensor."* Two separate defects, both introduced by the bugs/0759
two-motor work.

## (a) Motor 1 left the filter behind

Measured on the flagged solve:

```
Front/Rear Optical Vertex (lens)   [-80.842, 0, 0]     Motor 2
RA mirror 2 + SENSOR               [-55.698, 0, 0]     Motor 1
Filter 48-926                      [  0.000, 0, 0]     STAYED
```

The user named the group precisely -- *"One Motor move the Lens + Filter + 40mm RA mirror +
Camera together"* -- and `_apply_camera_arm_move` wrote only the mirror's seat and the sensor
standoff. The filter rides the CHAIN, so it followed Motor 2 instead and ended 55.7 mm from the
mirror it travels with: the stray disc in the screenshot.

**It has to move as a PAIR**, exactly like the lens (bugs/0719). The first attempt wrote only the
gap before the filter, which shifted the whole chain:

```
RA mirror 2   [-55.698, 0, -55.698]     <- picked up a z component
SENSOR        [-259.391, 13.045, -61.669]
residual      [0.0203, -17.0857]
```

Correct form: the gap before the filter takes `+delta`, the filter->mirror gap takes `-delta`, so
the pair sums to zero and the mirror's station -- and everything measured from it -- does not move.

## (b) Idempotence ignored focus

bugs/0727 compared MAGNIFICATION only. A scene already at the requested |m| with the image well
off the sensor was declared finished:

```
SOLVE: delivering 31.5 x 31.5 mm (|m| 0.7314); the lens did not move -- the field was already delivered
FOCUS: the image forms 6.276 mm in front of the sensor
```

Delivered now also requires the image to land: the check asks the same first order the solve uses
and refuses when `|image_delta| > 0.1 mm` (inside the 0.153 mm one-pixel depth of focus).

## Result -- and a correction to bugs/0759

Fixing (a) moved the residual by an order of magnitude across the whole range:

| device | field | before | after |
|---|---|---|---|
| 20 mm | 20.989 | -0.3414 | **+0.0035** |
| 25 mm | 26.238 | -0.3009 | **+0.0201** |
| 30 mm | 31.488 | -0.3198 | **+0.0257** |
| 40 mm | 41.987 | -0.3194 | **+0.0266** |
| 54 mm | 56.686 | -0.0185 | **-0.0185** |
| 56 mm | 58.786 | -0.0173 | **-0.0173** |

**20-56 mm now lands within +-0.027 mm -- a fifth of a pixel**, both arms.

bugs/0759 recorded that small-field residual as "the first order disagreeing with the real folded
trace at high magnification, the bugs/0745 class". **That was wrong.** It was this bug: the
misplaced filter. A 1 mm N-BK7 plate 55.7 mm out of position is worth about 0.34 mm of focus, and
that is exactly what the residual was.

## Known remaining

Device 17 (the extreme end, `A5 = 1.236` with the lens all but touching the prism) reads
`[-96.5332, -0.0188]` with 559 rays on one arm -- the bugs/0757 pooled-bucket signature at a
sampling change. Its |m| (1.2916) and field (17.839 mm) are correct, so this is a readout defect,
not optics. 20 mm and up are clean.

## Guard

`validate_open3d_0761_filter_travels_and_focus_gates_idempotence.py` (penta phase 549): the carry
pair is written with opposite signs and sums to zero; a scene declaring no carry is untouched;
idempotence still short-circuits when the image lands and refuses when it does not; and the
tolerance is inside one pixel of depth of focus.
