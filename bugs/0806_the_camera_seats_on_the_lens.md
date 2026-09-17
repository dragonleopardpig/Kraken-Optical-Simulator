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

## Follow-up: flag_20260917_133231 -- "I still see rays fan out"

Build `92c9892b` (the fix was running). No swap in that session: the user had SAVED the scene at 12:10,
from the pre-fix session, so the file itself carried the error -- WD 64.9037 (a later solve had refocused
the object onto the misplaced sensor), shoulder->sensor 19.1260, camera face +1.600 mm off the
shoulder, |m| 4.155. Loading a file restores what it says; the fix only acts on a swap.

* Repaired through the app's own path (load -> Swap Imaging Lens from Folder -> save), original kept as
  `attachment/MV-CS050-60UM_V5_TCL4.0X-65DI-5M.pre0806_backup.py`. Reloaded: WD 65.000, shoulder->sensor
  17.526, camera face on the shoulder, paraxial |m| 4.000.

User (single-sided telecentric): "what looks weird is the rays sudden bend outward", "Shouldn't light
rays focus in crossed fashion? Inverted image kind of ray crossing."

Measured on the seated scene (chief ray interpolated to the stop centre across the 31-ray fan):

* object side: chief rays leave the object at **0.000 deg** -- the telecentricity SPO specifies;
* the image IS inverted (+1.376 mm -> -5.506 mm): the chief rays cross the axis **at the stop**
  (z 117.1), mid-barrel, where all fields overlap in the fat beam -- so the crossing is not visible;
* every bundle converges to one point on the sensor (spot 0) -- the cones end AT the sensor, which
  stops the light, so the X of a focus is only ever half drawn;
* the "sudden outward bend" is Blackbox Group 2 (f = -23.88) 5 mm inside the rear end: -5.9 deg of
  chief-ray bend, 7.61 deg arriving at the sensor (exit pupil z 183.8).

A negative rear group is FORCED, not an artefact: with both groups inside the barrel a 4x image in a
225 mm object->sensor track needs a telephoto rear (a positive G2 tops out at |m| 2.2 with G2 at the rear,
and |m| = 4 would need G1 at z 45, in front of the lens). Its POSITION is the surrogate's choice (bugs/0792:
5 mm inside each end), and that choice makes the kink as sharp and as late as it can be. The two-group
family, all delivering WD 65 / |m| 4 / NA 0.16 / identical focus:

| G1 z | G2 z | f2 | stop z | bend at G2 | chief angle at sensor |
|---|---|---|---|---|---|
| 70 | 202.5 (current) | -23.9 | 117.1 | -5.9 | 7.6 |
| 80 | 167.4 | -28.8 | **125.7 = drawn IRIS** | -2.5 | 4.2 |
| 85 | 144.6 | -24.0 | **125.7** | -1.5 | 3.5 |

The SPO drawing marks the IRIS 54.9..66.5 mm behind the front face (z 119.9..131.5); for an object-side
telecentric lens the iris IS the aperture stop, so it is vendor data that pins the placement the
current rule ignores (its stop sits at 117.1, in front of the iris ring). Constraint found while
checking: moving G1 back grows the front beam (G1 at 80: edge-field marginal ray r 14.4 against the
26.08 mm group disc) -- a placement change must re-size the group apertures or it vignettes.
Not changed here: it regenerates every datasheet telecentric surrogate and is the user's call.
