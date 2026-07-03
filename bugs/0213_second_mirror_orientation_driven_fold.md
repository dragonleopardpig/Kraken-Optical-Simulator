# 0213 — Fix B: a free-placed 2nd RA mirror folds by physics off its OWN orientation

**Status: FIXED (Fix B). The pinned 2nd promoted mirror (0212) is now a real second fold: BOTH the
detector AND the drawn rays follow the mirror's own world orientation (`r = d − 2(d·n)n`), with NO
hard-coded fold axis. Completes 0212 Fix A (which pinned the mirror but left it inert in the beam).**

## The user's architectural ask

0212 Fix A stopped the free-placed 2nd mirror being swept onto mirror 1's fold leg, but it did so by
making the mirror *inert* — pinned where dropped, not bending the beam. The user pushed back on the
narrow framing of an earlier proposal that hard-coded the fold direction:

> *"I wonder why need to specify the fold direction, shouldn't user be given the freedom to orientate
> the mirror and the rays should go according to physics? Your fix is just for special case rather
> than general?"* → decision: **"go with the general orientation-driven fix."**

Fix B is that general case: the user free-places **and orients** the mirror, and the beam folds off
its oriented face by reflection physics — no axis is assumed.

## Two display systems that must agree

The fold is drawn by two independent paths, and both had to become orientation-driven:

1. **Pose overrides** — `build_optical_solid_output_port_pose_overrides`
   (`KrakenOS/UI/nonseq_output_ports.py`) positions the solids + detector. It already reflects the
   propagation frame off each solid's **world-oriented** interaction face
   (`_optical_solid_faces_at_pose` → `normal_world = normal_local @ pose_rotation.T`).
2. **Display rays** — `_reflect_straight_equivalent_display_rays`
   (`KrakenOS/UI/services/three_d_scene_tools.py`) folds the drawn ray polylines by reflecting them
   about mirror planes derived from the sequential-fold `records`.

## Why the naive path fails (the core finding)

`promote` writes a free-placed solid's pose as `desp_x = center_world_x`, `desp_y = center_world_y`,
`desp_z = center_world_z − z_station`, and stamps `advanced["StepOverlayPromotion"]["center_world"]`.
That `desp` encodes the **folded-world drop point** (a big station-cancelling `desp_z ≈ −275`), NOT
an unfolded sequential station. So:

- `fold_promoted_mirror_specs_to_sequential` → `_solve_mirror_tilt` **cannot seat** the free-placed
  `desp_z` (its single-axis half-angle solve returns `None`) → mirror 2 yields **no sequential-fold
  record**;
- `reflect_straight_equivalent_ray_points` composes reflections about each mirror's **unfolded**
  plane — but the free-placed mirror only has a **folded-world** plane, incompatible with that frame.

So the display rays reflected only at mirror 1 and flew straight past the free-placed mirror 2 to
`(315.3, 0, 71.9)`, while the *detector* had already been folded onto a new leg — the two systems
disagreed (probe `bugs/probe_0213_raytrace.py`, before Edit 2: 1 kink, endpoint far off the
detector).

## Fix B — two edits, both keyed on the free-placed `center_world` marker

**Edit 1 — pin the mirror, fold the detector off its world face**
(`nonseq_output_ports.py`, new `_free_placed_solid_pinned_pose`): a faced free-placed solid (carries
a `StepOverlayPromotion`/`StepNativePromotion` `center_world`) is pinned at its **own authored world
pose** `center = [desp_x, desp_y, z_station + desp_z]` (which cancels back to `center_world`),
`rotation = rotation_matrix_from_kraken_tilts(tilt_x, tilt_y, tilt_z)`. The follower loop uses that
pinned pose instead of sweeping the mirror down mirror 1's leg; the existing
`_reflected_frame_from_interaction_face` re-frame then folds the downstream **detector** off mirror
2's world-oriented Mirror face.

**Edit 2 — fold the display rays about the mirror's REAL world plane**
(`services/folded_sequential_fold.py`, new `free_placed_mirror_world_planes`; wired in
`three_d_scene_tools.py`): for each free-placed faced mirror NOT already covered by a sequential
record, return `(row_index, world_centre, world_normal)` where

- `world_centre = promoted_mirror_world_center(specs, idx)` (`station + desp_z` → `center_world`);
- `world_normal = n_local @ R(tilt).T` — the Mirror face's local normal **rotated into the world by
  the row tilt**, so the fold direction is the mirror's **orientation**, never a fixed axis.

`_reflect_straight_equivalent_display_rays` runs a POST-PASS after the records reflection: for each
free-placed plane it reflects the already-folded polyline about that real world plane
(`reflect_straight_equivalent_ray_points`, a pure isometry). The early-return now also fires when
there are free-placed planes even with zero records.

## Why orientation-driven (no hard-coded axis)

The fold is pure reflection `r = d − 2(d·n)n` off the mirror's own world normal. The causal contrast
proves the direction tracks orientation, with the same placement:

| mirror orientation | world normal        | reflected +X leg | detector & ray endpoint |
|--------------------|---------------------|------------------|-------------------------|
| `tilt_y = −90°`    | `(0.707, 0, +0.707)`| `(0, 0, −1)`     | `(210.703, 0, −32.721)` (−Z leg) |
| `tilt 0` (as m1)   | `(0.707, 0, −0.707)`| `(0, 0, +1)`     | `(210.697, 0, +176.521)` (+Z leg) |

Flip the mirror and the beam flips with it — both the detector override AND the drawn ray endpoint.

## Why penta-safe

Everything is keyed on the free-placed `center_world` marker, which only `promote` writes.
Layout-authored cascade prisms (penta) carry hand-authored faces + non-zero tilts but **no**
`center_world` marker, so `free_placed_mirror_world_planes` returns `[]` for them and
`_free_placed_solid_pinned_pose` returns `None` — both edits are inert for penta. A global change to
`mirror_fold_face_normal` (world instead of local normal) was **rejected** because penta engages the
sequential fold with non-zero-tilt prisms producing 0 records; a world-normal change there could flip
those to folds and break the cascade. The penta cascade PASSES under Xvfb after Fix B (chief-ray exit
`+Z, −Y, +X, +Z, +Y, −X` through all five folds, unchanged).

## Verification

Display-free guard `validate_open3d_second_mirror_orientation_driven_fold` (7/7), on the AZ85 scene,
building the ray-bundle geometry headlessly (no VTK draw):

1. the override **pins** the free-placed mirror at its dropped world pose `[210.7, 0, 71.9]`;
2. the override **folds the detector** off the mirror's world face onto the −Z leg (X≈210.7, Z<<0);
3. the **display rays fold twice** (one kink per mirror), on the cone-preserving reflection path, and
   the on-axis endpoint **coincides with the folded detector** — `(210.703, 0, −32.721)` for both
   (rays == detector, the two systems agree);
4. **causal / orientation-driven:** the same placement with `tilt 0` folds onto the **+Z** leg — both
   the ray endpoint AND the detector override flip their Z sign with the mirror orientation;
5. **penta-safe:** 1 free-placed plane for the marked scene, **0** for the marker-less stock AZ85 and
   the 0208 thickness-authored 2-mirror chain (layout-authored → never enters the post-pass);
6. the free-placed plane's world normal **tracks the tilt** (`tilt_y=−90` normal ≠ `tilt 0` normal);
7. the pin + post-pass are **wired** into both source modules (guard not vestigial).

Regressions: `validate_open3d_ra_mirror_chain_fold` (0208) PASS, `validate_open3d_second_mirror_
pinned_to_placed_pose` (0212) PASS. `validate_open3d_ra_mirror_folded_sequential_trace` FAILs, but
that is **pre-existing branch debt** (proven by `git stash` of the three edits — it fails identically
without them), not a regression here.

Registered as penta **phase 189** (`phase_189_second_mirror_orientation_driven_fold`), baseline
`pass`. The full validator marathon still SIGSEGVs on llvmpipe, so phases 0–188 are carried forward.

## Known limitation / what's next

Only the **display** (solid poses + detector + drawn rays) is orientation-driven. The **numerical
sequential trace** (spot diagram / focus analysis) still does not fold at the free-placed mirror 2 —
it yields no sequential record because `_solve_mirror_tilt` cannot seat the folded-leg `desp_z`. So a
quantitative through-focus / spot analysis on a free-placed 2-mirror scene images the single-fold
result, not the doubly-folded one. Generalising the sequential trace to un-fold a free-placed pose
into the sequential frame (so the analytic trace folds too) is a deeper 0207-style follow-up.

**In-app eyeball owed:** the headless guard proves both display systems agree at the physics-fold
point; the final rendered pose + rays through the full VTK draw should be confirmed once in-app.
