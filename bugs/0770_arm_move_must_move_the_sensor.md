# 0770 -- MOTOR 1 must be shown to have moved the sensor, or not move at all

Chasing why `om05a_folded` still would not focus after bugs/0769 gave it a `sensor standoff`
row and a stage. The lens tracked the device perfectly (A = 172.17 / 159.67 / 147.42 for a
50 / 25 / 0.5 mm device -- deltas of exactly `(50-S)/2`), yet the image landed 5.67 mm off at the
nominal cell and 300 mm / NaN elsewhere.

## The measurement

Step MOTOR 1 by -10 mm and read the sensor's WORLD position:

| build | sensor moves | \|d\| | model gain | traced gain |
|---|---|---|---|---|
| `om05a_folded_80mm` | `(-10, 0, 0)` | 10.00 | 1.0000 | **1.0042** |
| `om05a_folded` | `(-10, +20, 0)` | **22.36** | 1.0000 | **0.4142** |

The production frame throws the sensor **20 mm sideways in y** for 10 mm of intended travel.
The 0.4142 "traced gain" is nothing but that wrong 3D motion projected onto the optical axis
(and 0.41424 is `sqrt(2)-1` to four decimals, which is what sent me looking at 45 deg geometry
before the world measurement showed the real story).

## Why

`_apply_camera_arm_move` writes the seat in `desp_x` and the pad as a **thickness**. A thickness
advances along whatever direction the chain points *after the fold*. Those two axes coincide on
the 80 mm frame and do not on `om05a_folded`, whose mirror 2 carries `tilt_y 90, tilt_z 180`.
Permuted x/y components are the tell ([[reference_step_offset_frame]], bugs/0693).

bugs/0759's docstring says "the sensor moves in x only". That was true of the scene it was
measured on. It was never checked again.

**The first order cannot see this at all.** It books stations, so it reported a clean 1.0000 gain
throughout -- `image_delta` went to `-5e-13` and the solve returned `-0.0014 mm` while the traced
focus sat 7.31 mm out. Any verification against `image_delta` would have passed. This is the same
shape as bugs/0764: a model that agrees with itself while the rays disagree.

## The fix

The move measures the sensor before and after (`_surface_reference_world_point`, row math only,
no ray trace) and **reverts every field it wrote** -- seat `desp_x`, pad thickness, and the
bugs/0761 carry pair -- when the sensor did not travel `delta`. A motor that cannot be shown to
have moved the sensor along the beam must not leave its write standing.

Tolerance `_ARM_MOVE_TOL_MM = 0.05` mm, well inside one pixel of depth of focus (0.153 mm) and
far under the 12.36 mm error the production frame showed for a 10 mm request.

Deliberately NOT done: correcting the direction. Writing the pad along the seat's axis is a
fold-frame change with a wide blast radius, and until it is measured on both builds a "fix" would
be another unverified assumption. Refusing is honest and safe; the 80 mm build is untouched
(verified: the flagged 30x30 case still lands at 0.052 mm / 1.51 um, and FOV 34 and 54 at 0.046
and 0.054).

## Result

`om05a_folded` now refuses MOTOR 1 with a reason naming the request and the actual travel,
instead of writing geometry that looks solved. Its scene file was restored to the original
(`.pre-standoff.bak`); the standoff attempt is kept at `.stage-attempt.bak` for the next pass.

## Guard

`KrakenOS/UI/validate_open3d_0770_arm_move_must_move_the_sensor.py`, penta phase **554**:
a well-behaved frame applies (A); a mis-aligned one reverts with a reason naming both numbers
(B); the revert restores every field including the carry pair (C); a scene that cannot report a
sensor point still applies -- the guard stands down rather than blocking everything -- and the
tolerance is sub-pixel, and the sensor is read twice, not once (D).
