# 0698 — flag_20260903_075132: camera's green (Y) rotate arc rotated about Z

The whole-body gizmo draws its arcs about the WORLD axes (red=X, green=Y,
blue=Z) and `rotate_step_world_axis` promises a world-axis rotation -- but it
composed the world delta straight onto the per-axis rotation fields, which
apply in the body's PRE-FOLD placement frame (the 0693 contract). On the om05a
sensor leg the camera's fold transform maps pre-fold Y to world Z, so the
green arc delivered a Z rotation. Same family as 0693 (offsets) -- third
occurrence of the world-vs-placement frame mix-up.

FIX: conjugate the delta into the placement frame, D_local = R.T @ D_world @ R
with R = `_step_offset_world_rotation(label)` (identity on unfolded scenes =
byte-identical legacy). The in-place pivot residual in the same function was
ALSO a raw world delta into the pre-fold offset -- converted with R.T too.
Guard: E1/E2 source pins in validate_open3d_0693_step_offset_frame (phase 509).

Durable rule (memory updated): ANY `*_step_*` write that promises WORLD
semantics -- offset, seat, or rotation -- must convert through
`_step_offset_world_rotation(label)` before touching the pre-fold fields.
