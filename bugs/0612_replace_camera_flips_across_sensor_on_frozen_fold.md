# 0612 — "Replace a camera, it dislocate" (FIXED)

Flag `flag_20260811_204049_285`, build `3aab71ce`, scene `machine_vision_Apo75.py`.
After a camera replace the body parked far from the fold-leg sensor (the screenshot
shows it up the STRAIGHT axis while the sensor overlays sit correctly at the end of
the fold leg), with a STEP-carry session active at offset (0,0,0).

## Measured repro (fresh load, no solve)

Replacing the scene's camera (hr25MCX) with ITSELF — which must be a placement no-op:

- BEFORE: sensor (179.8, 0, −3.3), body centre (179.8, 0, −28.7), distance 25.3 mm.
- AFTER: body centre (179.8, 0, **+22.0**) — same 25.3 mm distance, **opposite side
  of the sensor plane** (a 50.7 mm jump = 2× the flange offset). The body lands
  upstream, in the incoming beam.

## Root cause

`replace_camera_from_folder` re-imports the STEP (landing the body by the bugs/0220
STRAIGHT-axis convention `image_plane_z − front_to_sensor`) and then restores only the
old TRANSVERSE offset, inheriting the fresh axial answer. On a 0433-frozen fold leg —
which runs BACKWARDS (world leg = `const − thickness`; see
`reference_frozen_gap_row_inverted`) — that sign convention seats the body on the
wrong side of its own sensor. The correct instrument already existed:
`seat_camera_on_sensor` (bugs/0471/0473/0480) reads the beam direction from the traced
detector normal, seats all three axes, and refuses rather than guessing — it was just
never wired into the replace flow (only the two menu items).

Another door of the "where is the sensor really" family — every consumer starts from
the resolver, never from a ±Z convention.

## Fix (two layers)

1. `replace_camera_from_folder` seats through `seat_camera_on_sensor("camera")` after
   the import; the old transverse-keep survives only as the fallback when seating
   REFUSES (status prefixed "Seat camera:"). "Already seated" counts as success.
2. **The seat itself carried the same disease deeper**: it trusted the chosen target's
   `normal_world` SIGN. On the frozen Apo75 the designed-image target stores (0,0,+1)
   while light arrives along −Z — the seat computed the mirror seat and ZEROED the
   −50.67 mm placement offset that had been holding the body right. Two evidence
   sources failed before the right one:
   - terminal-landing vote: nothing ENDS on a frozen world-placed Image plane in the
     analysis bundle (all `no_next_intersection` — the 0601 census);
   - plane-crossing vote: measured ZERO crossings within 60 mm — the raw analysis
     paths never reach that plane either.
   The working sign source is the RESOLVER: the final leg runs from the last optic's
   `row_placement.world_frame` position to the sensor; the stored normal is
   sign-corrected against it. Scoped to the row-based `designed_image_target`; a
   synthetic branch detector's normal is already ray-derived (bugs/0464).

Verified by the same-camera repro (guard B): body stays on the flange side at the
same offset, no flip.

Guard: phase 464 (`validate_open3d_0612_replace_camera_seats_on_fold`) — contract
(the replace flow calls the seat, fallback gated on refusal) + the same-camera
replace preserves the body-to-sensor VECTOR (side included) on the frozen scene.
