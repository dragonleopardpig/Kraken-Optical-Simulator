# 0471 — the camera STEP sits centred on the sensor plane, so it collides with the fold mirror

Flags `flag_20260729_154141` ("Original, the sensor location does not match the camera STEP
sensor location"), `flag_20260729_154419` ("Unhide the camera STEP, camera STEP and sensor
location still mismatched. Camera crashes to RA mirror") and `flag_20260729_154803`, all on
build `822f6259`.

## Measured

    Image row (sensor plane)          z = 2.30
    camera STEP bounds                z = [-34.51, 39.12]   depth 73.63, centre 2.30
    camera's beam-facing (+Z) face    z = 39.12   ->  36.82 mm ABOVE the sensor plane
    RA mirror row 7                   z = 53.80   (substrate reaches down to ~52.4 at half-extent 12.5)

So the body's CENTRE is on the sensor plane and half the camera (36.8 mm) sticks up the beam
toward the mirror. Baseline clearance is 14.68 mm; after "remove defocus" moved the sensor
+20.02 mm (bugs/0470, working as intended) the camera top reached 57.4 against a mirror
substrate starting at ~52.4 -- a ~5 mm overlap, which is the reported crash
(`flag_20260729_154803`: camera z = [-16.2, 57.4], centre 20.62, mirror row at 64.9).

The body-carry itself is CORRECT: the camera centre tracked the sensor exactly through the
move (bugs/0456 doing its job). The anchor is what is wrong.

## Not a missing feature -- a displaced offset

The seating code already intends the right thing (bugs/0220):

    camera_front_z = _camera_track_image_plane_z() - _current_camera_front_to_sensor_mm()
                   = 2.303 - 11.48 = -9.177        (matches the "STEP CAD transform" log line)

and the vendor front-to-sensor distance is known (11.48 mm). But the body carries a PERSISTED
`placement_offset_xyz` of z = -25.335 in the saved scene, which lands its centre on the sensor
plane instead of its front face at -9.177. bugs/0456's `_seat_step_body_world_center` preserves
whatever offset exists (it re-seats relative to the body's own current pose), so the
mis-seating is carried faithfully through every solve rather than corrected.

## What a fix has to decide

The offset is USER-EDITABLE state (drags, glue, axis-to-axis moves all write it), so silently
recomputing it would throw away deliberate placement. Options, in order of preference:

1. A "seat camera on the sensor" action (menu, next to "Register STEP camera") that recomputes
   `placement_offset_xyz` so the vendor front-to-sensor distance puts the SENSOR on the Image
   row. Explicit, reversible, and it fixes existing scenes.
2. Do it automatically at camera REGISTRATION time only (when the user picks a vendor camera),
   leaving later manual placement untouched.
3. A collision warning when the body overlaps another solid, which treats the symptom.

(1) plus (3) is the honest combination: the user asked for the sensor to match the camera, and
separately a crash needs to be visible when it happens.

## Related, already shipped

* bugs/0470 -- "remove defocus" now works on this scene (axial RMS 0.805 -> 0.000 mm). It is
  what exposed the collision, by moving the sensor 20 mm.
* bugs/0456 -- the body-carry that keeps the camera on the sensor through a solve. Working.
