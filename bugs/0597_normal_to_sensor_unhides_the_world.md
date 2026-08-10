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


## Part 2 — the same phantom, two more doors (flags 20260810_091754 / 091853)

Within the hour the user hit the family twice more: *"turned illumination overlay ON, become
blank"* and *"Pixel Grid ON"* (the grid drawn far from the sensor with a ray spray across the
canvas). Both trace to the SAME root: `_source_illumination_anchor_target`'s tiebreaker
(`int(row_index)` max) picked a **draw-suppressed synthetic branch detector** (row 100001,
parked mid-air on the straight axis) over the real drawn Image row, because the phantom carries
the same 23×23 sensor dims and a higher row index. Every consumer of that anchor — the
illumination heatmap's drape, the pixel grid's lattice (whose "relative illumination" then read
a uniform 1.00 sampled at the phantom), and Normal-to-Sensor's aim — inherited the phantom.

**Fixes, invariant-level:**
1. **The resolver prefers what the user can SEE**: non-`draw_suppressed` detectors outrank
   suppressed phantoms (the bugs/0291 doctrine — a suppressed branch detector is a ray
   hard-stop, not a display anchor). This heals the heatmap, the pixel grid and the sensor
   view in one place.
2. **The isolation is enforced at render time**: overlay machinery adds actors through
   DEFERRED paths (after_idle draws, the async seated source trace) that land after the
   isolation pass — the flagged ray spray. `render()` now sweeps late arrivals against the
   band and hides off-plane ones, whichever code path created them.
3. **The labelled frame always rides along**: with Det OFF, a rebuild in the sensor view
   leaves only the heatmap quad — on a uniformly-lit scene a white rectangle on a white
   canvas. The guarantee now draws the coverage square + image circle unconditionally per
   rebuild while the view is active (Det ON already draws its own).
4. `_visible_actor_count` reads the RENDERER traversal, not `_actor_by_key` — the keyed map
   lies whenever a drawer registered an actor some other way, and a false zero fired the
   restore-all fallback (caught by the isolation guard's stub).

**Sequence-verified with rendered snapshots** (the user's exact clicks, driven through the
REAL checkbox callback `_on_scene_visibility_changed`, not a bare refresh): enter the view →
frame + circle + labels; illumination ON → frame + heatmap fill, no spray, no blank; pixel
grid ON → the lattice fills the sensor square. Guards: phase 455 extended (resolver contract,
render-time sweep, frame presence); the isolation/gesture/0556/0595/0593 guards all pass;
`illumination_flood_phantom_branch_detector` fails identically with and without these changes
(pre-existing, in the 2026-08-09 baseline's known-fail set).

**Process note**: the first version of this validation drove `refresh_from_editor()` directly
and missed all of this — the checkbox path is `_on_scene_visibility_changed`. Sequence
replays must drive the REAL UI callbacks.
