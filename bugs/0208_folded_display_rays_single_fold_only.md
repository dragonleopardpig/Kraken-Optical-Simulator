# 0208 — the folded display-ray fold was single-mirror-only; generalise it to a chain

**Status: RAY SIDE RESOLVED. The folded-mirror DISPLAY RAYS now fold correctly through an
arbitrary chain of promoted-mirror cubes (e.g. a second RA mirror between lens and camera), not
just a single fold. Two changes in `services/three_d_scene_tools.py`: (1) the routing feeds the
flat-plate equivalent + display reflection for ANY rotating fold (was gated to `single_fold`);
(2) `_reflect_straight_equivalent_display_rays` reflects each straight ray about EVERY mirror
plane in reverse station order. Guard `validate_open3d_ra_mirror_chain_fold.py`, penta phase 186.
FOLLOW-UP (not in this commit): the second mirror's CAD cube placement and the detector
fold-DIRECTION (the pose-override chaining) — see "Remaining" below.**

## Origin

The user asked, on the working folded AZ85 scene (`machine_vision_AZ85_RA_Mirror.py`), to add a
second RA mirror between the lens group and the camera, and to make the machinery general rather
than two-mirror-specific. A headless repro (a second promoted mirror inserted on the +X leg)
confirmed the single-fold assumption was baked into multiple places.

## Root cause (rays)

The 0197/0203/0205/0207 cone-preserving display path is: trace the UNFOLDED flat-plate equivalent
(a real converging cone on the straight axis), then REFLECT each ray about the mirror plane to
fold it. Two gates limited this to one fold:

- **routing** (`_trace_preview_rays_folded_aware`): the flat-plate equivalent was only used when
  `single_fold` (exactly one Mirror in the folded trace rows). A chain fell through to the
  sequential-Mirror trace, whose ideal Thin Lenses lose power through the fold and whose leg-2
  rays sit at the pre-0207 positions (~desp_z off the drawn lenses).
- **fold** (`_reflect_straight_equivalent_display_rays`): bailed at `len(records) != 1`.

## Fix (rays)

- **routing**: drop the `single_fold` gate — use `_folded_optical_solid_straight_equivalent_rows()`
  (which already flattens EVERY promoted mirror, preserving row count + air gaps) whenever it
  returns non-None (i.e. the scene has a rotating fold).
- **fold**: reflect each straight ray about every mirror's straight plane in REVERSE station order
  (deepest/last mirror first, first mirror last). The algebra: a leg-k vertex's folded position is
  `R1(R2(...Rk(v)))` where `Ri` is the reflection about mirror i's straight plane (centre
  `promoted_mirror_world_center`, normal `mirror_fold_face_normal`), so applying the primitive
  `Rk, ..., R1` in that order lands every leg on its real branch. Each `Ri` is an isometry, so the
  incoming cone and every fold's focus are preserved, and a vertex upstream of a mirror's plane is
  left untouched by that reflection — the legs compose cleanly.

## Verification (display-free)

`validate_open3d_ra_mirror_chain_fold.py`, on a 2-mirror AZ85 variant (a second promoted mirror on
the +X leg) AND the stock single-fold AZ85:

1. general fold detection: 2 records for the chain, 1 for the single fold;
2. both take the cone-preserving reflection path (`folded_straight_equivalent_reflected`);
3. one ~90° kink per mirror (the on-axis ray folds twice / once);
4. on the shared +X leg the on-axis ray coincides with the drawn lens rows to **0.000 mm**
   (rays == CAD — the 0207 consistency is preserved through the second fold; the pre-fix fallback
   strays 12.500 mm);
5. the incoming leg stays a 2D disk (cone, `s2 = 29.2`), not a flat fan;
6. backward-compat: the single-fold AZ85 focus still lands on its drawn detector (gap +0.000 mm).

Proven non-vacuous: FAILs on the pre-fix code (chain falls back, tag `ray_events`, strays 12.5 mm).

**Penta-safe:** the penta-prism cascade produces **0** rotating-fold records and a `None`
straight-equivalent, so it never enters the changed path — confirmed
`validate_open3d_penta_cascade_prism_by_prism` PASSES under Xvfb. The single-fold AZ85 guards
(phases 181/183/185, 0192) all still pass.

## Remaining (CAD side — follow-up)

This commit fixes the display RAYS. Two CAD-side items remain for a fully-consistent second mirror,
both in the pose-override / mesh-placement path (`build_optical_solid_output_port_pose_overrides`,
`_optical_axis_fold_world_transform_for_row`) which is **shared with the penta cascade**:

- the second mirror's own CUBE mesh draws at its unfolded straight station instead of on the +X leg
  (`_surface_reference_world_point` / the fold transform don't apply the chained follower override
  to a promoted-solid row);
- the detector/image plane folds by the pose-override ROTATION (which carries an uncorrected
  meridional flip at the second mirror → a 90° direction disagreement with the reflection-folded
  rays), i.e. the 0192 rotation-vs-reflection difference generalised to fold 2.

These need a faithfully-authored second mirror (interactive promote, so the fold direction matches
the user's placement) and in-app visual verification, and they touch penta-shared geometry — so
they are deliberately staged separately rather than changed blind. The ray generalisation here is
the foundation they build on.
