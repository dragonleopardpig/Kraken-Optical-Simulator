# 0779 -- stray light that reached the sensor by another route is not the image

> "have you looked into the sudden appear of stray rays issue?"

Three flags pointed at it, and all three were right:

- `20260910_172158_555` -- "device 21x21x1mm, start to have hay wired rays. The one of the image
  plane is offset from the sensor, wiered, why the symmetry not hold?"
- `20260911_084908_485` -- "15x15x1mm, FOV 22.5 ... many stray lights showing up"
- `20260911_091713_149` -- "look carefully, the rays actually focus at sensor, not sure why it
  displaced at sensor for Face A?"

## What the stray rays are

The traced route of every landing ray, by surface id (1 First RA mirror A, 3 BS cube A, 5 Centre RA
mirror A, 7 RA mirror 1, 9-13 lens datums/groups/stop, 14 filter, 16 RA mirror 2, 17 First RA
mirror B, 18 BS cube B, 19 Centre RA mirror B, 25 sensor), om05a_folded_80mm, per arm:

| class | route | device 23 | device 21 | device 15, FOV 24 |
|---|---|---|---|---|
| image | `1 3 3 3 5 7 7 7 9 10 11 12 13 14 15 16 25` | 322 | 322 | 318 |
| vignetted at the stop | `1 3 3 3 5 7 7 7 9 10 11` | 779 | 770 | 770 |
| **cross-arm ghost, lands** | `1 3 3 3 18 18 18 18 17 1 3 3 3 5 ... 16 25` | **0** | **4** | **4** |
| cross-arm ghost, stopped | same route, ends at `11` | 0 | 2 | 2 |
| cross-arm, leaves the scene | `1 3 3 3 17 18 18 18 19 19 5 5 5` | 2 | 5 | 5 |
| no stop event, lands on the strip | `... 9 10 12 13 ...` | 0 | 0 | 4 |

Arm B is the exact mirror. The last class is bookkeeping only: those rays cross the stop plane at
3.7 mm radius against the 7.1 mm the imaging rays use, land on the strip's own ends, and arrive
inside the field's cone.

One ghost, device 21, edge field: it exits cube A at y 8.89 instead of 11.42, misses the centre RA
mirror, crosses the prism gap above the device, enters cube B 1 um above its bottom edge (y 5.771
against 5.770) and meets the bottom face 36 um later, reflects off First RA mirror B, comes back
across the gap 1.8-3.1 mm above the device to First RA mirror A, and then follows arm A to the
sensor. It lands at z = -36.088 against a strip spanning [-34.695, -33.649]: **1.39 mm outside the
image, 0.43 mm inside the sensor edge.**

## Why "suddenly"

Rays are stored in launch order, so ray *i* at device 23 is the same launch ray as ray *i* at
device 21. Exactly 9 per arm change route between the two, and all 9 were stopped at the aperture
stop at 23. At 21 they clear the centre mirror's edge: 4 reach the sensor as ghosts, 2 stop on the
ghost route, 3 leave the scene. A geometric threshold, made a jump by the discrete launch grid.

## What they broke

The ghosts share their field's launch point, so bugs/0778's grouping put them in that field's focus
group. Measured with the app's own `focus_waist_from_rays` on the saved traces:

| case | field | with ghosts | ghosts removed |
|---|---|---|---|
| device 21 | edge (105 + 1 ghost) | 656 um, image 5.99 mm off | **2.06 um, 0.019 mm** |
| device 21 | centre (108 + 2) | 419 um, 3.04 mm off | **0.51 um, 0.095 mm** |
| device 15, FOV 24 | edge (103 + 1) | 401 um, 1.37 mm off | **1.09 um, 0.040 mm** |
| device 15, FOV 24 | centre (108 + 2) | 413 um, 2.63 mm off | **0.40 um, 0.083 mm** |
| device 23 | all | 0.42-1.90 um | unchanged (no ghosts) |

Everything downstream of that number inherited it:

- the banner's "419 um" at device 21 and its "Move the device stage" advice;
- the "a 15 mm device needs FOV >= 28" conclusion -- at FOV 24 both arms land inside a pixel;
- bugs/0778's "at device 21 BOTH arms are 419 um blurred" -- both arms are sharp;
- the strip "migrating 1.393 mm past its law at 21.0" and "doubling to 2.439 mm" -- 1.393 mm IS the
  ghost's overshoot (u = -11.088 = z -36.088), and bugs/0776's "violated by 0.696 mm" is half of it;
- very probably bugs/0777's trigger (230 um at FOV 22.5), pending a re-run.

And the earlier dismissal of stray rays as the cause looked only for directions more than 5 deg
off; these arrive 1.5-3.4 deg off.

## The fix

The route is the physical identity of an image. Within a source, a route carrying at least 20% of
the landing rays (`_MIN_ROUTE_SHARE`, bugs/0753's sample share) forms an image; a sliver is stray.

- `split_stray_routes` / `landing_route` (detector_coverage_overlay.py, pure): the split, per source
  or per band. A group with no dominant route keeps everything.
- `_measure_focused_image_plane`: measures only image-forming rays, and keys focus groups on launch
  point **and** route -- a second route with a real share is a second image, not blur on the first.
- `discrete_launch_sources`: bugs/0778's discreteness test decided **per source** (the review of
  244c2994 found the pooled test lets an additive random emitter flip the arms back to
  `field_index`).
- `_annotate_sensor_overflow(landing_paths=...)`: the overflow count, strip centres and traced |m|
  use the image only.
- `measure_split_field_image_strips`: the drawn strip's half-width no longer follows a stray ray.
- `summarise_stray_landings` + the banner: `STRAY LIGHT: N ray(s) reach the sensor by another
  optical route and land up to D mm outside the image (P% of the landing rays) -- not part of the
  image, left out of the focus measurement`. Rays on another route that land ON the image are not
  called stray light.
- `ParaxialToolsMixin._traced_bundle_best_focus_shift` -- the measure the solve's focus snap reads
  FIRST -- drops stray routes before it picks the axial field. A live device-21 solve after the fix
  above still warned "the focus snap could not improve the defocus (residual +3.025 ...)". On the
  saved trace this function returns **3.0251 mm** without route data and **0.0945 mm** with it
  (device 15 at FOV 24: 2.6206 -> 0.0829 mm; device 23 unchanged at 0.0807 mm).

## Verified

The real method, driven by a stub on the saved traces (no app, no new trace):

| case | before (both arms) | after, arm A / arm B | stray light |
|---|---|---|---|
| device 23 | 0.42 um | 0.417 / 0.417 um, landed | none |
| device 25 | 0.35 um | 0.347 / 0.346 um, landed | none |
| device 30 | 0.22 um | 0.225 / 0.225 um, landed | 8 on the image, 0 outside (no line) |
| device 40 | 0.11 um | 0.110 / 0.110 um, landed | 8 on the image, 0 outside (no line) |
| device 50 | 0.06 um | 0.061 / 0.063 um, landed | none |
| **device 21** | **419.03 um** | **0.509 / 0.509 um, landed (2.34 um on the sensor)** | **8 outside, up to 1.39 mm** |
| **device 15, FOV 24** | **413.89 um** | **0.398 / 0.397 um, landed (2.10 um on the sensor)** | **8 outside, up to 1.74 mm** |

A live headless re-run of the size/FOV cases follows this commit.

## Is the ghost real?

In the model as built it is a valid path. An independent read-only review (eight agents, every
conclusion re-checked by a second agent) established why the model lets it through:

- the device under test is not traced geometry -- it reaches the trace only as launch parameters --
  so nothing at the part blocks light (the ghost passes about 1.8-3 mm above it; the
  leaves-the-scene class does cross the device-21 volume);
- no vendor non-optical body is traced, and the vendor section shows a thin body on the centre V's
  device-facing face that both cross-arm paths cross;
- the two cubes are 51 mm apart with open air between them, and the ghost enters cube B 1 um above
  its edge -- a knife-edge clearance;
- the ghost reflects off THREE cube cement planes (A, B, A) where image light reflects off one, and
  cement faces are traced as full mirrors (their stored 0.5 split ratio is ignored unless the face
  is a Beam Splitter), so it is drawn at four times the weight a 50/50 coating would give it.

Whether the real cell shows it cannot be settled from the code: a vendor STEP section at the rays'
positions, a trace with absorbing hardware, or a bench image would. Which bodies are opaque is the
user's modelling call (vendor hardware is immutable; per-label physical ray stops exist, bugs/0379).
The measurement fix is right either way -- even real stray light is not the image.

## Found alongside, not fixed here

- **Stop-rim bookkeeping (the "no stop event" class).** The non-sequential chooser tests a flat
  analytic row against a 32-sided mesh (the flat-surface resolution cap, commit 5fac5ec7) while the
  vignette uses the exact circle, so a ray in the band of up to 35 um just inside the rim gets no
  event on that row. Harmless on this air stop; on a flat row that does something (glass entry,
  coating, detector) it would skip a real interaction. Preview traces also run with vignetting
  ignored, so enlarging the mesh alone would let blocked rays through -- the chooser needs the
  analytic rim test.
- **The ghost looks exactly like image light** in the scene: nothing marks a landing ray as a
  cross-arm path.
- **The flag recorder counts only the first 2000 ray paths** (open3d_event_recorder.py), silently
  dropping 206 of om05a's 2206 -- including one of the device-21 ghosts.

## Guards

`KrakenOS/UI/validate_open3d_0779_stray_routes_are_not_the_image.py`, penta phase **562**, 42 checks.
It drives the REAL `_measure_focused_image_plane` and `_traced_bundle_best_focus_shift`
(display-free stubs) on a synthetic mirror-image split field with the ragged launch: the helpers
(A); stray rays change nothing and are reported, while without route data the same rays drag the
waist to 188.7 um (B); an additive random emitter does not flip the arms (C); the legacy
termination spelling (D); stray rays past the sensor edge are not overflow (E); the drawn strip is
the image's (F); the banner line and its share (G); the focus snap's measure is unchanged by stray
rays and moves from -0.600 to -0.877 mm without route data (H).

`validate_open3d_0778_focus_groups_follow_the_launch.py` is rewritten the same way. The review of
244c2994 showed its source-text checks passed with the two grouping branches swapped -- the exact
regression it existed to catch.
