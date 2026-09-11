# 0782 -- MOTOR 1 moves the imaging group along the BEAM on any frame; production gets its stage

User:

> the production one have exactly 2 motors same as the 80mm version.

bugs/0770 had found production's MOTOR 1 throwing the sensor `(-10, +20, 0)` for a -10 mm request
and made the move refuse. That was honest, but it left the production scene with no image-side
motor at all, so every production solve reported a large focus residual (74.55 mm at 30x30,
bugs/0764) and its scene file was restored without a stage. The bench has two motors; the model
had one.

## The measurement

Each Motor-1 write on its own, +1 mm, read back as world points (row math, no ray trace):

| write | 80 mm build (lens leg +x) | production (lens leg -x) |
|---|---|---|
| seat `desp_x` +1 | mirror (+1, 0, 0), sensor **(+1, +1, 0)** | mirror (+1, 0, 0), sensor **(+1, -1, 0)** |
| standoff thickness +1 | sensor (0, -1, 0) | sensor (0, -1, 0) |
| carry pair (C1 +1, pair -1) | filter **+1 along the leg** | filter **+1 along the leg** |
| MOTOR 1 as coded | sensor (+1, 0, 0), mirror (+1, 0, 0), filter (+1, 0, 0) | sensor **(+1, -2, 0)**, mirror (+1, 0, 0), filter **(-1, 0, 0)** |

The standoff and the carry pair are chain THICKNESSES: they advance along the beam, identically on
both frames. The seat's `desp_x` is a WORLD axis. On the 80 mm frame +x is along the beam; on the
mirrored production frame it points back at the object. Writing all three with `+delta` therefore:

* doubled the fold-walk error instead of cancelling it -- the 22.36 mm for 10 mm bugs/0770 saw;
* sent the filter the OPPOSITE way to the mirror and camera it travels with (bugs/0761's group).

Only one of the three writes was wrong, and only its sign.

## Fix

`QuickEstimationService._camera_arm_seat_axis(stage)` measures the sign instead of assuming it:
nudge the seat `desp_x` by +1 mm, project the seat's world displacement on the lens leg (front
datum -> the row before the seat), restore the saved value. It returns `(sign, leg_unit)`, or
`(1.0, None)` -- the old write -- when any world point cannot be read.

* `_apply_camera_arm_move` writes `desp_x += sign * delta`; standoff and carry pair unchanged.
* The bugs/0770 check was distance-only, which passes a sensor that travels the right distance the
  WRONG way -- exactly what a seat-sign error produces once the fold walk cancels. Where the leg is
  known the travel must also point along `+delta`.
* The solve's stage bound (`_apply_conjugate_pair`) computes where the seat ends up with the same
  measured sign, so the bound and the write cannot disagree about direction.

## Result -- the real move, both scenes

| scene | measured sign | request | sensor | RA mirror 2 | filter | writes |
|---|---|---|---|---|---|---|
| `om05a_folded` (standoff scene) | -1 | -10 | **-10.000 along the beam** | -10.000 | -10.000 | applied |
| `om05a_folded` | -1 | +7.5 | **+7.500** | +7.500 | +7.500 | applied |
| `om05a_folded_80mm` | +1 | -10 | -10.000 | -10.000 | -10.000 | **bit-identical to before** |

## Two guards were already broken

`validate_open3d_0759_two_motor_imaging_group` and `..._0761_filter_travels_and_focus_gates_idempotence`
crash with `AttributeError: '_Row' object has no attribute 'desp_y'` -- identically at HEAD
(44cdb23b), before any of this. bugs/0770 added a full-pose snapshot of every row to the move and
their stub rows only had `desp_x`. The stubs now carry `desp_y`/`desp_z`; both pass (13/13, 12/12).

## Scene change -- production gets its stage (attachment, not in git)

`attachment/om05a_folded.py` now carries the bugs/0769 standoff row (`RA mirror 2 (40 mm)` 45.13 ->
36.31 + `sensor standoff` 8.82, sum preserved, nothing moves) and a `camera_focus_stage` whose limits
follow the bugs/0765/0772 rule -- the motors travel `A5 + C1` from the authored lens position --
with the measured sign on the seat:

```
row 23 (standoff)   min/max   -171.65 / 30.42      (8.82 - A5 180.47, 8.82 + C1 21.60)
arm_row 15 (seat)   min/max   -290.737 / -88.667   (seat -269.137 - C1, seat + A5; sign -1)
arm_carry_row 12 (C1)
```

Backups: `om05a_folded.py.pre-0782.bak` (the file before this change) and the earlier
`.stage-attempt.bak`.

## Traced solves on production -- the motors work, the production MODEL does not yet image there

Real Solve FOV through the app's solve, then one full trace and the focused-image-plane measure,
one device per production FOV (`remeasure_routes_scene.py`, one app per process):

| device @ FOV | MOTOR 1 booked | = first order (od + image corr) | traced result |
|---|---|---|---|
| 15 @ 20 | -88.68 mm | -151.43 + 62.75 = **-88.68** | the traced focus SNAP then moved the standoff **+30.45 mm** (-79.86 -> -49.41); 0 rays reach the sensor (1950 stop the aperture, 256 miss) |
| 30 @ 34 | -69.83 mm | -92.20 + 22.37 = **-69.83** | traced 3.81 mm out; the snap's +4.99 mm made it worse and was reverted (bugs/0764); 78 rays reach the image plane, 76 of them off the sensor |
| 50 @ 54 | -7.30 mm | -8.305 + 1.004 = **-7.30** | arm A **+5.673 mm** (126 um), arm B **-1.555 mm** (45 um) -- the arms disagree by 7.2 mm |

What this change set out to do holds: MOTOR 1 now books exactly the first-order correction on the
production frame, where before it refused. What it exposes is production's own model: its traced
image does not form where its first order says (3.8-5.7 mm), its two split-field arms no longer agree
(the pre-stage file traced -0.4565 / -0.4564 at its authored state, bugs/0760), and on the FOV 20
case the traced-focus snap moved the sensor the wrong way. None of that appears on the 80 mm build,
whose traced focus agrees with its first order within 0.05 mm on every size/FOV case measured.
Lens clearance is tight at production FOV 20: 1.8 mm (along-leg AABB, 2 mm allowance included) for a
15 mm device, and the lens moves 7.25 mm closer for a 0.5 mm one. Open, not fixed here.

## Guard

`KrakenOS/UI/validate_open3d_0782_motor1_follows_the_beam.py`, penta phase **565**, 20 checks on a
kinematic stub that reproduces the measured Jacobians of both frames: the sign is measured +1 / -1
and the probe nudge is restored bit-for-bit (A); on the mirrored frame the move applies and carries
sensor, mirror and filter exactly `delta` along the beam, where the old writes put the sensor 22.36
mm off (B); the 80 mm-like writes are bit-identical (C); right distance, wrong way is refused and
reverted (D); unmeasurable falls back to the old write (E); the stage bound uses the write's sign (F).
Related guards, run one at a time on this change: 0756, 0759, 0761, 0769, 0770, 0772 pass.
