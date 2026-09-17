# 0806 -- the camera seats on the lens

flag_20260917_114837 -- the SPO TCL4.0X-65DI-5M swapped onto an MV-CS050-60UM (vendor STEP in the
lens folder):

> replaced with lens with vendor STEP file, Please check everything correct? Especially the lens fan
> out at the back of the lens.

The flag's banner also read `FIELD OVERFLOWS THE SENSOR by 121.1 mm per side: the field is 249.3 mm
across a 7.066 mm sensor, so only 2.8% of the device is imaged` and `Magnification: 4.16x`.

## Reference: the datasheet drawing

`TCL4.0X-65DI-5M-V2.pdf`: 4.0X, WD 65 +-2, NA 0.16, F/# 12.5, telecentricity angle < 0.02 deg, body
142.5 mm front face -> mounting shoulder, then the 4 mm C-mount thread, sensor **17.526 mm behind the
shoulder**. The surrogate matches: front datum 65.0, rear datum (the shoulder) 207.5 = 65 + 142.5, stop
15.08 mm at group 1's back focal plane (object-space telecentric, NA 0.16), lens STEP 65.000..211.482.

## Measured: replay of the swap

Scene `attachment/MV-CS050-60UM_V5_TCL4.0X-65DI-5M.py`, then **Swap Imaging Lens from Folder** on the
SPO folder, exactly as the flag (inside `devenv shell` -- the datasheet extractor needs it):

| | after swap (before) | after swap (fixed) |
|---|---|---|
| shoulder -> sensor (rear datum thickness) | **19.526** | 17.526 |
| camera front face vs lens shoulder | **+2.000 mm** | 0.000 |
| on-sensor spot RMS (every field) | **38 um** (~11 px at 3.45 um) | 0.000 |
| delivered magnification | **4.193** | 4.0001 |
| swap note | `focus limited to 19.5 mm so the camera body clears the upstream element` | none |

Rendered side view (`+yz`, zoomed on the mount): before, every bundle comes to a focus 2 mm IN FRONT
of the sensor ("Focused image 2 mm in front of the sensor", banner `FOCUS: the image forms 2 mm in front
of the sensor`) and **fans out again** to the sensor -- the fan-out the user saw. Fixed: the bundles
converge on the sensor, and the camera's front plate sits flush against the lens's Ø30 rear ring.

## Why

`_swap_auto_refocus_to_best_focus` refocuses (the snap put the sensor at 17.526, correctly) and then
applies two clearance layers written for a camera behind a **fold mirror** (bugs/0388-0392):

1. `_swap_refocus_min_gap` = `2.0 mm clearance + camera flange depth` = 19.526 > 17.526 -> the gap was
   floored to 19.526;
2. `_swap_camera_body_clearance_deficit` takes `rows[-2]`'s drawn actor as the obstacle -- here the
   rear datum's disc -- and would have added the same 2.0 mm again (measured: deficit 2.0, result `ok`).

`rows[-2]` was the lens's own **Rear Optical Vertex Datum**: the mount face the camera screws onto. It
is a seat, not an obstacle. The 2 mm is a spacer nobody fitted; focus, magnification and the solved FOV
all followed it.

## The banner's 249.3 mm

`_annotate_sensor_overflow` predicted the imaged extent from `inspection_part_spec`
(`max(width, depth) * |m|` = 60 x 4.155 = 249.3) **without checking `enabled`**. The part is switched
off in this scene; its 60 x 40 x 20 default was read as the device.

## Fix (general)

* `_camera_seats_on_lens_flange()` -- true when the sensor-gap row IS the imaging lens block's rear
  vertex datum (`_imaging_lens_block_indices`), i.e. the camera mounts on the lens.
* `_swap_refocus_min_gap`: a seated camera's floor is the flange depth alone (it cannot come closer, and
  nothing needs clearing); a camera behind a fold mirror keeps `clearance + flange` (unchanged).
* `_swap_camera_body_clearance_deficit`: skips a seated camera (`result: seat: ...`) -- a datum disc is
  a reference plane.
* the "focus limited" note says what actually limited focus for a seated camera (the flange depth), not
  "clears the upstream element".
* `_annotate_sensor_overflow` reads the device only from a part that is **enabled** (every om05a scene
  enables it; the prediction there is unchanged).

## Not changed, reported

* **Image-side chief rays are not telecentric in the surrogate** (7.56 deg at the 5.5 mm field). The
  datasheet's `< 0.02 deg` is object-space; no image-side figure is published (checked the SPO drawing
  and the distributor's TCL-ST/TCL-HR tables). The two-group conjugate solve (bugs/0792) places the
  groups 5 mm inside each end, which fixes the exit pupil at ~41 mm before the sensor. At the correct
  seat it changes neither focus nor magnification; it only matters when the sensor is OFF the contract
  plane -- which is exactly how the 2 mm error became a 4.8% magnification error.
* `FIELD REACHES THE SENSOR EDGE ... 66.7% of the landing rays`: the scene's field is the sensor
  half-DIAGONAL (5.506 mm, the camera coupling) traced as a meridional fan along one sensor axis, so the
  two edge fields land past that side of the 8.4 x 7.1 mm sensor. True as stated; unchanged.
* The saved scene still references the deleted `TCL4.0X-65DI-5M-V2.envelope.step`; re-save after the
  swap.
* The seat floor assumes the rear vertex datum IS the mount face. That holds for datasheet surrogates
  (the datum span is the drawing's body length -- 142.5 here); a `.zmx` surrogate whose rear datum is
  the last GLASS vertex can have the mount in front of it, and a best focus below the flange depth
  would still be clamped (by 17.526 now, 19.526 before). Not measured on such a lens in this bug.
* Scene census of the rule (`attachment/*.py` + `common_optical_layouts`): 20 camera scenes mount the
  camera on the lens (incl. `machine_vision_AZ85_RA_Mirror.py`, whose mirror is OBJECT-side), 12 keep
  the clearance (ELS85/Apo75/Pyrite85 fold mirrors, every om05a standoff/mirror arm).

## Guard

`validate_open3d_0806_the_camera_seats_on_the_lens` (penta phase 588):

* A1-A6 (display-free mixin): seat detected; floor = flange depth; best focus at 17.526 stays with no
  note; a lens wanting the sensor closer stops at the seat and says so; the datum disc is not a body.
* B1-B2: a camera after a FOLD MIRROR still reserves clearance + flange; no camera -> 2.0 floor.
* D1-D2: disabled part -> no overflow prediction; enabled 60 mm part -> still predicted.
* C1-C5 (live, SKIPs without the attachment/toolchain): the user's swap -> 17.526 +- 1 um, camera face
  on the shoulder, no note, every field focused on the sensor, |m| = 4.0.

A/B on the old `layout_table_workbench.py`: A1-A6 and D1 FAIL (A6 measured deficit 2.0), B1-B2 PASS.
