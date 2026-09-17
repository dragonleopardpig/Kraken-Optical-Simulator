# 0808 -- the sensor rolls with the camera

flag_20260917_140152 (MV-CS050-60UM on the SPO TCL4.0X-65DI-5M):

> Since this is a rectangular sensor, can you make sure when I rotate the camera, the FOV length x
> width will become width x length?

## Measured

The user's saved scene has the camera body rolled to `camera_step_rotation_z_deg: 90` (it was 180).
Replayed with Trace Now:

| | roll 180 | roll 90 (before) |
|---|---|---|
| launched object field | +-1.056 x +-0.883 | +-1.056 x +-0.883 (unchanged) |
| landings on the sensor | +-4.223 x +-3.533 | +-4.223 x +-3.533 (unchanged) |
| HUD pixels | 2448 x 2048 | 2448 x 2048 |

The body turned; the FOV rectangle, sensor rectangle and launched field did not. No code read the roll:
every consumer -- drawn sensor and FOV rectangles, the launch field (`_camera_fov_object_half_extents`),
the fill-the-sensor solve (`_rectangular_target_magnification`), delivered-FOV readouts -- asks
`_current_camera_sensor_active_mm()` for the WORLD horizontal x vertical extent.

## Which way the sensor points

The camera STEP carries no sensor chip to measure (its thin parts are a 27 x 20 board and 11 x 11 /
7.5 x 7.5 packages, none with the sensor's 1.195 aspect). But the sensor is fixed inside the body, and
the body is posed by `_cad_mesh_aligned_to_optical_axis` as Rx(x) -> Ry(y) -> Rz(roll): the body's +X
lands at `atan2(sin roll cos y, cos roll cos y)` -- Rx never moves it, a y flip adds 180 deg, which a
rectangle does not see.

Survey of every saved scene with a camera STEP: all 14 with a 90/270 deg roll carry a SQUARE 23.04 mm
sensor (hr25MCX, CAM-SV25MCCXP); every non-square sensor (Basler 8.45x7.07, MV-CH120, MV-CS050,
Bopixel 29.9x22.4, shr661) sits at 0 or 180. Honouring the roll therefore changes no existing scene.

## Fix

* `_camera_sensor_orientation()`: roll angle, nearest quarter turn, `swapped`, residual.
* `_current_camera_sensor_active_mm()`: a quarter turn swaps width and height -- once, at the source,
  so the drawn rectangles, the launched field, the solves and the readouts all follow in the world
  frame.
* HUD: pixel counts and pixel sizes pair the same way; `Sensor roll: 90 deg (portrait)`; a
  non-quarter roll is SAID ("modelled at 0 deg -- only quarter turns rotate the field"), not drawn.

## The "FIELD REACHES THE SENSOR EDGE ... 0.69 mm" banner (older, same flag)

`_annotate_sensor_overflow` built its own in-plane frame with `u = n x X` and compared `|d.u|` to
the half WIDTH -- the width along Y, while `detector_coverage_overlay._basis` (the drawn rectangles)
puts it along X. A landscape field exactly filling the sensor was judged transposed: 0.69 = 4.223 -
3.533, 2166 = the 6 of 9 field points at |x| 4.223, x 361 rays. It appeared on every render of the
scene. The inside/outside test now uses the drawn frame, with a 1e-6 relative tolerance (774 corner
rays landed 3.8e-7 mm past the edge from rounding). The strip frame the bugs/0774-0776 split-field laws
measure along (om05a's traced |m|) is left as it was.

## Verified

* Roll 90 on the user's scene: launch +-0.883 x +-1.056, landings +-3.533 x +-4.223, overflow 0 of
  3249, HUD `Pixels: 2048 x 2448` + `Sensor roll: 90 deg (portrait)`; roll 180 unchanged.
* Rendered looking along +Z at the object plane and the sensor plane, roll 180 vs 90: the green FOV
  rectangle, the 9 launch stars, the orange sensor rectangle and the square body all turn portrait; the
  colours land inverted (top-centre cyan -> bottom-centre, top-right orange -> bottom-left).
* Guard `validate_open3d_0808_the_sensor_rolls_with_the_camera` (penta phase 590): A orientation
  (0/90/180/270/-90, y flip, 30 deg residual, no STEP), B world pair, C HUD lines, D overflow frame
  (exact fill inside at both rolls, a 0.5 mm overflow still counted), E the saved scene's launched field
  at 180 vs 90. Fails on the old code.
* 0774, 0775, 0776, 0779, 0806, 0628, 0762 pass. `fov_rect_orientation` C3/C4 fail identically on HEAD
  (a stale source-text check -- penta phase 74, already a known failure).

## Not done

Arbitrary (non-quarter) rolls rotate nothing -- the launch field and the solves are axis-aligned. The HUD
states the modelled angle. Per-branch cameras (`branch_detector_camera_assignments`) have no roll.

## Follow-up: flag_20260917_155044 -- "the Orange drawn sensor does not match the Camera STEP sensor size"

Measured on the saved scene (camera rolled 90 deg): the camera STEP's axial faces around the image
plane (z 225.026):

| z | what | x extent | y extent |
|---|---|---|---|
| 224.690 | a centred 136-cell rectangle | -6.45..+6.45 (12.90) | -7.85..+7.85 (15.70) |
| 225.026 | the drawn (orange) sensor | -3.533..+3.533 (7.066) | -4.223..+4.223 (8.446) |

The datasheet (`MV-CS050-60UMUC ... datasheet_20241205`): 2/3", 2448 x 2048 at 3.45 um -> active area
8.446 x 7.066 mm. The orange rectangle IS that active area; the STEP's 12.90 x 15.70 rectangle 0.34 mm
in front of the image plane is the sensor PACKAGE face, which the pixel area sits inside. Different
things, so not expected to be the same size -- no change.

It does independently confirm the orientation rule above: both rectangles are centred on the axis and
both are PORTRAIT at the 90 deg roll (long side along y), i.e. this camera's STEP carries its sensor's
width along the body's own X, as the roll rule assumes.
