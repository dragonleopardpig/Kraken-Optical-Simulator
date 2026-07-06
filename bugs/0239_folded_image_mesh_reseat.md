# 0239 — Duplicate image plane persists as the sensor-disc MESH after the folded FOV solve

## Symptom
flag_20260706_130527_037, on the promoted two-fold AZ85 periscope: after setting a 55×55 mm FOV and
solving for thickness the user reported **"still 2 image and detector plane"**. bugs/0238 already
drops the stale unfolded kind="image" **curve**, but a second plane remained — the drawn solid
**sensor disc**, which is a separate kind="image" surface **mesh**, not a curve.

## Root cause
There are **three** distinct focus notions in the folded straight-equivalent display:

1. `_paraxial_image_plane_z()` — the **lens-only** paraxial best focus (AZ85: axial ≈ 422).
2. the detector **target** — folded by `_fold_promoted_mirror_table_row_targets` (bugs/0188) and then
   snapped by `_reconcile_folded_image_to_ray_convergence` (bugs/0217) onto the **real ray waist**
   where the traced cone actually converges.
3. the ~20 mm gap between them — the flattened mirror **plates'** glass path that the lens-only first
   order ignores.

The kind="image" surface **mesh** (the drawn sensor disc) is built at the lens-only paraxial plane and
folded onto the promoted-mirror branch, so it lands ~a plate-thickness **short** of the detector target
and the ray convergence. The disc then floats off the beam: the SECOND image/detector plane the user
still saw. bugs/0238 removes the curve sibling but leaves the mesh — dropping the mesh too would erase
the visible solid sensor disc, so the mesh must be **re-seated**, not dropped.

An earlier attempt fixed this solve-side (axially re-seating the Image-row gap in
`quick_estimation.py`). That was **reverted**: probing proved moving `rows[-2]` axially moves *neither*
drawn plane — the mesh binds to the paraxial plane (invariant to that gap) and the detector+rays bind
to the real convergence (also invariant). The fix must be **display-side**, on the mesh itself.

## Fix
`_reseat_superseded_image_meshes_to_folded_detector(bundle)` translates every kind="image" surface
mesh whose centroid has **diverged** (> `_SUPERSEDED_IMAGE_CURVE_TOL_MM` = 1.0 mm) from the nearest
**off-axis** folded detector target (in-plane radius `hypot(x, y)` > `_FOLDED_DETECTOR_OFF_AXIS_MM`
= 5.0 mm) onto that detector — the physics focus. Re-seating (not dropping) keeps the solid sensor
disc the unfolded scene draws, now coincident with the detector **and** the rays on ONE plane:
**display follows physics.**

It fires **only** on a folded scene (detector carried off the straight +Z axis); a plain / sequential
/ on-axis layout has no off-axis detector, so `det_centers` is empty and every mesh is left
byte-identical. The shift is recomputed from the live centroid each pass, so it is idempotent — a disc
already on the detector is within tolerance and skipped, which makes it cache-safe across a Show-Rays
rebuild.

**Call site matters.** The reseat runs in `ThreeDSceneToolsMixin._build_preview_system_rays_bundle`
**after** `_reconcile_folded_image_to_ray_convergence`, not inside `_build_scene_bundle`. At
`_build_scene_bundle` time the detector is still at its raw fold pose; `_apply_folded_display_bend` +
reconcile move it +~20 mm to the waist afterwards. Reseating there would land the disc 20 mm short
(double-apply). Running after reconcile pins the disc on the detector's **final** pose.

## Verification
`KrakenOS/UI/validate_open3d_folded_image_mesh_reseat.py` (penta **phase 216**):

- **COINCIDENT** — on the two-fold after `fov_solve("object","thickness",55,55)` the single
  kind="image" mesh centroid coincides (≤ 1 mm) with the folded off-axis detector target (and the ray
  waist).
- **RESEAT SYNTH** — a synthetic bundle with a coincident mesh (on the detector) and a diverged one
  (off-beam) → the reseat moves only the diverged mesh onto the detector and spares the coincident one
  (returns 1).
- **ON-AXIS NO-OP** — an on-axis (plain sequential) detector leaves every image mesh byte-identical.
- **STILL IMAGES** — rays still reach the single folded detector after the reseat.
- **WIRED** — `_build_preview_system_rays_bundle` calls the reseat **after**
  `_reconcile_folded_image_to_ray_convergence`, and the method is defined on the mixin.

Probes `/tmp/_probe_bind.py` and `/tmp/_probe_reseat.py` confirm the image mesh, detector target and
ray convergence all coincide (world z ≈ 83.9 with the object split, ≈ 93.9 without), and that a second
build on the same editor does not shift the disc further (idempotent). The disc is a VTK render and
can't be pixel-validated headless (llvmpipe SIGSEGV); this guard checks the bundle geometry the
renderer consumes. In-app visual confirm owed (restart the app onto this build, redo the folded solve,
confirm a single image plane on the beam).
