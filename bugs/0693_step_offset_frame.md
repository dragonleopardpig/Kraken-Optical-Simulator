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

## Part 2 (user: "proceed with item 3") — frozen follower ROWS follow the walk too
Mirror2 (a frozen follower ROW) still carried by the rigid model: it landed
~18.7 mm off the new leg IN ITS OWN MIRROR PLANE (optically neutral — the flag
itself showed rays reaching the sensor — but drawn visibly off the beam).
Fix, same principle as the bodies: `_fold_slide_carry_before` captures a
LEG-ANCHOR walk frame (the fold transform of a walk-posed row riding the
emitted leg, membership decided by the same `point_on_emitted_leg` primitive
the bodies use), and `_fold_slide_carry_apply` maps every carried row by
T_after @ inv(T_before) — position AND tilts (anchor rotation). The rigid
0488 fold-point transform remains the fallback when no walk frame exists
(fully-frozen scenes stay byte-identical).

Three carry models measured (bugs/0693_repro_rotation.py) before the final one:
- EMISSION-ORIGIN rigid (old): mirror2 18.7 mm off-leg; lens-rear→mirror2 arc
  shrank 35.2 → 25.7 mm (a hidden 9.5 mm defocus nobody had measured).
- FULL T_after@inv(T_before) map: position + arc exact, but the walk frame's
  transverse convention injected a spurious 180° ROLL — the sensor leg folded
  UP (y +106, 62.66 above mirror2 where the design sits 62.65 BELOW) and the
  one-sided split-field band flipped sides. Euler triples ((-180,0,-180) vs
  (180,0,0)) must be settled by TRACING, never by reading angles.
- FINAL: the rigid carry PIVOTED ON THE ANCHOR WALK-FRAME ORIGINS (on-axis =
  roll-invariant; at the anchor row's station = arc-exact) with the rigid leg
  rotation for tilts. Measured: mirror2 (-9.456, 43.294, -297.7), off-leg
  0.050 mm (= its authored CAD offset), arc 35.24 mm ✓, sensor folds DOWN to
  y -19.36 ✓, chain reach 580/1083 vs 521 baseline (a centred mirror2
  vignettes less), lens body rides its rows (residual ~1e-15).

## Known limitation — faceB's mirrored launch under a PARTIAL rotation
Post-rotation faceB reach is 0: the additive mirrored-launch instrument
(`mirror_launch_plane_z: -25`, 0680) assumes the SHARED train lies in the
symmetry plane — true for the saved scene (lens axis in z=-25), broken when
only the shared train swings. Face B's light physically still images (it joins
the common junction), but the mirror-trick launch aims at a stale mirrored
stop. Moot for production: the real second station rotates the WHOLE assembly
(part + both trains), which preserves the symmetry — the planned "rotate
station about the device axis" verb is the correct vehicle (and should carry
the mirror-plane spec with it). The 0672 guard's canonical-scene B5 (381)
stays green.

## Guards
`validate_open3d_0693_step_offset_frame` (penta phase 509): seater/shift write
R.T @ delta, identity stays byte-identical, frame lookup per label (branch
preference, straight-world labels, missing-transform degrade).
