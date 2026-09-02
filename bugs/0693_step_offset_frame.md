# 0693 — flag_20260902_115321: rotated RA mirror; lens surrogate displaced from body

## User
"rotated RA mirror under the prism assembly, whole axis rotated as well, but the
lens surrogate displaced from lens body." Context (user, same window): this
rotation is PRODUCTION — one station checks Left/Right of the device, the other
Top/Bottom, so the whole om05a train must swing 90° about the incoming beam.

## What the rotation did (bugs/0693_repro_rotation.py — byte-exact repro)
`rotate_scene_row_pose_world_axis(RA mirror 1, y, -90°)`: tilts (0,90,-90) →
(-90,0,0), the 0488 fold-carry swung the emitted leg -x → -z and carried every
follower row + mirror2 + the camera/lens bodies about the fold point. Rows,
axis and rays all landed together (the user's "whole axis rotated as well" —
the carry works). Repro matches the flag EXACTLY: m2 desp (9.2197, 43.5303,
-657.1103), lens offset (15.5581, 0.2335, 9.2197).

## Root cause — TWO composed frame errors
1. **World delta into a PRE-FOLD offset.** The lens/camera overlays are aligned
   in the PLACEMENT frame and then folded to world
   (`_mesh_with_world_transform(aligned, fold_transform)` — the frame contract
   is documented at `_lens_step_overlay_axis_world_line`). So
   `*_step_placement_offset_xyz` translates PRE-fold, and the carry's body
   seater `_seat_step_body_world_center` wrote its world residual RAW into it —
   rotated on application. The permuted-components signature was visible right
   in the flag state: lens (15.56, 0.23, 9.22) vs camera (18.68, 9.22, 0.24) —
   the same physical laterals landing on different axes per body frame.
2. **The seat GOAL itself was wrong on a walk-posed scene.** Fixing (1) alone
   still left the body 17.5 mm off (repro run 2): at seat time the body already
   sat perfectly on its rows (x -7.90 = leg -9.456 + 1.56 mount asymmetry, mid
   z) because the mesh rides the datum row's fold transform naturally. The
   carry then "corrected" it toward the 0488 rigid fold-point rotation of its
   OLD pose — but the WALK (which really poses the rows, frame-desp seat and
   all) put the new leg at y 43.34 where the rigid model says y 52.8. Bodies
   must follow their ROWS' frame change, not an independently derived rigid
   transform. Straight scenes never saw either error (identity frames), which
   is why every earlier 0456/0485 carry passed.

## Fix (general, in the shared writers — never per-scene)
- New `_step_body_anchor_world_transform(label)`: the 4x4 the displayed body is
  pushed through (lens = front-datum fold; camera = branch transform, else the
  Image-row fold; optical/led = None), and
  `_step_offset_world_rotation(label)` = its rotation part (identity fallback).
- `_seat_step_body_world_center`: offset += R.T @ (goal - current);
  `_shift_step_offset`: offset += R.T @ world_delta.
- `_fold_slide_carry_before/apply`: each captured body also captures its anchor
  transform; the carry goal becomes T_after @ inv(T_before) @ centre ("follow
  your rows"), falling back to the 0488 rigid fold-point transform only when no
  anchor frame exists. Identity/None frames are byte-identical to the old code.

## Known follow-up (optically neutral, visually off)
Mirror2 (a frozen follower ROW) still carries by the rigid model: it lands
~18.7 mm off the new leg IN ITS OWN MIRROR PLANE (plane unchanged — the fold
still works, rays reach the sensor; verified in the flag itself). The drawn
prism sits visibly off the beam; carrying frozen follower rows anchor-relative
is the next step if the user flags it.

## Guards
`validate_open3d_0693_step_offset_frame` (penta phase 509): seater/shift write
R.T @ delta, identity stays byte-identical, frame lookup per label (branch
preference, straight-world labels, missing-transform degrade).
