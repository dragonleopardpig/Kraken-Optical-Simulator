# 0597 — Normal to Sensor un-hides the world instead of isolating the sensor (FIXED)

Flag `flag_20260810_083640_360`: *"Enabling Normal to Sensor: components not hidden."* Scene
`machine_vision_Apo75.py`, rays ON, Det overlay OFF, build `bf80dec3`. The screenshot shows the
BACK view with every ray fan and the LED plate still visible.

Reproduced headless exactly, with the recorder's per-actor detail confirming the state: rows 1–7
all visible, **no row-8 or synthetic-row actors exist at all**, and the debug pane reads the
bugs/0589 line: *"the sensor-plane isolation left NOTHING visible — restoring the full scene"*.

## Three defects composed

1. **The anchor is a phantom** (the bugs/0556/0589 class, through yet another door): the
   illumination-anchor resolver handed back a synthetic branch-detector target — row 100001 at
   world (−0.47, 0.06, 134.0) on the straight +Z axis — while the real sensor sits at
   (179.79, 0, −3.35) on the fold leg, **226.6 mm away**.
2. **The bugs/0589 correction could not engage**: `_drawn_sensor_center_world` cross-checks the
   anchor against the detector row's drawn actors, but with Det OFF this scene draws NO
   Image-row geometry at all (0 mesh items, 0 reference-aperture disks — the earlier "working"
   flags all had Det ON, whose coverage actors made the plane non-empty). Its docstring promised
   a camera-STEP fallback that was never implemented — and a body-centre would mis-place the
   plane by the flange depth anyway.
3. **The bugs/0589 no-blank fallback finished the job**: the isolation around the phantom plane
   hid everything (nothing lives there), the survivor count was zero, and restore-all un-hid the
   entire scene. "Never a blank canvas" became "never isolate".

## Fix

1. **When nothing is drawn to cross-check against, adopt `row_placement.world_frame`** for the
   terminal Image row — position AND orientation (normal/tangent/up recomputed from the rotation
   columns). This is the same resolver the frozen display seats rows with; bugs/0556's docstring
   counts five consumers that hand-rolled this and each got a frozen scene wrong. Measured: the
   anchor is corrected 226.637 mm onto the true sensor.
2. **When the isolation still keeps nothing, DRAW the sensor** rather than un-hide the world:
   add the detector coverage overlays plus the labelled scene-detector overlays (the same square
   + image circle the Det toggle shows), then re-apply the band filter so only the sensor-plane
   pieces stay. Restore-all remains as the true last resort (a scene with no configured detector).

Verified by rendered snapshot in the flagged state: the view now shows the orange sensor square,
the blue image circle Ø32.6 and their labels, with every component hidden — 5 of 67 actors
visible, all 5 within the isolation band of the resolver-true plane. Neighbouring guards pass
(`0556_sensor_anchor_frozen_aware`, `normal_to_sensor_isolation`, `normal_to_sensor_gesture_leave`,
`0595_sensor_square_single_edge`).

Guard: phase 455 (`validate_open3d_0597_sensor_view_draws_the_sensor`) — verified failing on all
three checks pre-fix (60/60 actors visible, the flag exactly).

## Note — the door count

This is the SIXTH consumer of "where is the sensor really" to fail on a frozen scene (0517
camera frame, 0519 solve gate, 0525 cone crease, 0547 swap placement, 0556 sensor anchor, and
now the 0589 cross-check's empty-scene hole). Every fix converges on the same instrument:
`row_placement.world_frame`. Any new consumer should start there.
