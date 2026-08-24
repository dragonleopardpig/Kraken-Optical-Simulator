# 0640 — an explicitly-assigned Beam-Splitter face is honored (user report)

flag_20260824_130527 + follow-ups (machine_vision_150mm_standoff_145mm / _test): the BS
cube's 45° diagonal face was assigned function "Beam Splitter", yet the app didn't
recognize the coating — no BS reflect axis, and the follower/axis logic didn't treat the
cube as a splitter. The two scenes are identical except the standoff distance, and both
behaved the same, so it wasn't a geometry effect.

## Root cause

`select_optical_solid_interaction_face` picks the SINGLE top-priority interaction face of
any function (`_interaction_face_priority`: Mirror 3.0, Transmit/TIR 2.0, Beam Splitter
1.0). The BS cube exposes BOTH the diagonal coating `S001/F001` ("Beam Splitter", 1.0,
flagged interior_duplicate/recovered) AND a `S001/F002` "Transmit/Port" interaction face
(2.0). So the generic selector returned the Transmit/Port face; `_solid_has_beam_splitter_
interaction_face` then asked "is IT a Beam Splitter?" → no → `beam_splitter_coating_world_
frames` returned 0. The user's explicit assignment was silently shadowed.

## Fix

New `beam_splitter_interaction_face(world_faces)` selects the Beam-Splitter face DIRECTLY
(highest-priority / largest among faces whose function is "Beam Splitter"). Both BS
detection (`_solid_has_beam_splitter_interaction_face`) and the reflect-axis coating
geometry (`beam_splitter_coating_world_frames`) use it; a solid MARKED a BS but exposing no
such face (a plate whose rotation baked the coating normal off the geometric test) still
falls back to the generic top-priority interaction face. `select_optical_solid_interaction_
face` is unchanged (it serves follower/mirror logic broadly).

## Verified

- Guard phase 479 (`validate_open3d_0640_beam_splitter_face_honored`): the selector finds
  the BS face despite a higher-priority Transmit face; detection True/False; the generic
  selector still shadows (regression witness); the coating builder uses the new helper.
- Real scene (headless): coatings 0→1, axis records 1→2 — the new `axis:global:split`
  "Optical Axis (BS reflect)" branches from the fold point (z≈173) out +X to x=78; the
  coating centroid tracks the BS position (1.3, 0, 174.6); `axis:global` unchanged.
- Adjacent guards pass: validate_open3d_bs_reflect_axis, validate_optical_solid_face_roles,
  validate_optical_solid_uncoated_interaction_fold, 0494 emitted-direction.

Because the reflect axis is derived from the BS coating pose, it now tracks the BS when the
glued BS/LED station is moved (the original "axis didn't move" — it now will).
