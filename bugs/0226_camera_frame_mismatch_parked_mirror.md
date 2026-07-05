# 0226 — camera STEP shifted after promoting a parked (off-beam) mirror

**Status: FIXED. On a scene with a parked off-beam promoted mirror (bugs/0224), the camera STEP no
longer jumps: its folded world pose is byte-stable across the parked promote and sits on the
detector (0.02 mm). In-app confirm owed.**

## The flag

`flag_20260705_131738_764`: "after random placed a imported STEP, promote it, the camera STEP
shifted in position." The 0224 fix kept every ROW seat, the detector and the axis inert — but the
CAMERA overlay still moved by the parked plate's thickness.

## Root cause — a frame mismatch

Two "straight-axis station" frames coexist on a parked-mirror scene:

- the **RAW frame**: cumulative row thickness (`_row_z_positions`, `_current_image_plane_z`) — the
  parked plate's thickness INCLUDED. The fold transform
  (`_optical_axis_fold_world_transform_for_row`) anchors here, and the bundle targets fold raw
  stations through it — self-consistent.
- the **EQUIVALENT frame**: the straight-equivalent rows where a parked mirror is a ZERO-length
  plate (bugs/0224) — the paraxial focus (`_paraxial_image_plane_z`) lives here.

`_camera_track_image_plane_z` (bugs/0220) returns the focus — an EQUIVALENT-frame station — but its
callers seat the camera on the RAW axis and fold it through the RAW-anchored transform. On a
parked-mirror scene the frames differ by exactly the parked plate, so the folded camera landed a
full plate up-fold of the detector. (First attempt anchored the fold transform in the equivalent
frame instead — that flung every RAW-station consumer, i.e. the detector target, down-fold by the
plate; the guards caught it. The transform + prescription stay RAW; the note comments in both now
say why.)

## The fix

`_camera_track_image_plane_z` converts the tracked focus into the RAW frame before comparing and
returning: `focus += _offbeam_inert_thickness_before(image_row)` — the new helper sums the thickness
of off-beam promoted mirror rows (bugs/0224 classification) before a row. Scenes without a parked
mirror add 0.0 — byte-identical behaviour.

## Verification

`validate_open3d_offbeam_promoted_mirror_inert` extended (6/6, penta phase 200): the folded CAMERA
world pose (fold-transform ∘ camera-track station) moves 0.0000 mm across the parked promote and
sits 0.020 mm from the detector; all prior checks (rows/detector/waist inert, genuine folds
unchanged, classification, wiring) stay green. Sweep: camera_tracks_folded_focus,
folded_image_snaps, folded_working_image_distance, camera_overlay_hover_alignment,
ra_mirror_external_reflection all PASS.
