# 0396 — adding a BS plate re-aims the camera onto the plate normal

**Flag:** `flag_20260722_075115_079` — "After right click LED STEP and add BS Plate, the Camera
is always facing the BS Plate at normal direction even after BS rotation."

**User intent (confirmed):** *"The camera should not follow this BS orientation at all. The bug
now is when I add a BS, the camera responds to it."*

## Root cause

A beam splitter's PRIMARY (imaging) path is a straight-through **transmit** — it peels a second
branch off by reflection (handled separately: branch detectors / two-arm fold). So its inferred
exit must never reposition the downstream imaging chain (camera / image); the beam keeps
travelling the incoming direction. `build_optical_solid_output_port_pose_overrides`
(`nonseq_output_ports.py`) already enforces this via a non-folding guard — but the guard fires
only when the selected output face is codirectional with the axis (`_exit_frame_is_non_folding`,
`+Z ≈ +Z`):

- A BS **cube** lands its axial +Z face as the inferred output → non-folding → **followers skipped**
  (camera stays straight). Correct (bugs/0084-0091).
- A BS **plate** tilted 45° has **no axial face** — the picked output face is a large plate face
  whose normal is ~45° off-axis. `_exit_frame_is_non_folding` returns False, so the guard misses
  it, and the follower loop repositions the camera/image onto the **tilted plate normal**. As the
  plate rotates, the normal rotates with it → the camera tracks the plate normal.

(The physics ray path already transmits straight through — `folded_sequential_fold.py` — so only
the camera *body* diverged.)

## Fix

Recognise a beam splitter's inferred exit as straight-through regardless of the selected output
face geometry:

- New predicate `_solid_has_beam_splitter_interaction_face(world_faces)` (mirror of the existing
  `_solid_has_full_mirror_interaction_face`): True when the solid's primary interaction face is a
  Beam Splitter.
- The non-folding guard now fires when the exit is codirectional **OR** the solid is a beam
  splitter. Inside the guard a BS is not a full mirror, so `reflected_frame` stays None and the
  followers are **skipped** — the camera does not respond to the BS at all.

The fix is surgical: a **Mirror** plate (no transmit path) still folds the chain; only a beam
splitter skips. It generalises to cube and plate, any tilt.

## Verification

- **Penta phase 26** (`validate_open3d_beam_splitter_transmit_and_second_axis`), extended: a
  tilted BS plate produces **no** follower overrides (`override_keys=[]`), while a tilted **mirror**
  plate still folds (`[2, 3]`) — proving the skip is surgical. All existing checks (facet-A
  straight-through/folded, cube +Z exit, reflected-branch axis) and the **real MV-150 BS-cube
  scene** (Image past the lens, transmit rays reach S1-S5, one reflected axis) still pass.

## Files

- `KrakenOS/UI/nonseq_output_ports.py` — `_solid_has_beam_splitter_interaction_face` + the
  non-folding guard.
- `KrakenOS/UI/validate_open3d_beam_splitter_transmit_and_second_axis.py` — tilted-plate checks
  (penta phase 26).

## In-app eyeball still owed

Confirm on the real scene: add a BS plate to the LED, rotate it — the camera should stay put.
