# 0238 — Two image/detector planes on the folded periscope after an object-distance solve

## Symptom
flag_20260706_113107_413, on the promoted two-fold AZ85 periscope: after a folded object-distance
solve the user saw **"two image and detector plane"** on the sensor arm — one on the folded beam
where the detector belongs, and a second stale one off the beam on the straight (unfolded) axis.

## Root cause
The two-fold resolves to **Non-Sequential Preview** (`use_folded=False`). In that mode the scene
builder builds the surface curves on the **unfolded +Z axis** (`_build_sequential_surface_curves`),
whereas a folded-sequential scene builds them folded (`_build_folded_surface_curves`) so they
coincide with the folded targets.

Separately, `_fold_promoted_mirror_table_row_targets` (bugs/0188) **always** carries the detector
**target** onto the promoted-mirror reflected branch — even in Non-Sequential Preview. So after the
single-mirror fold:

- the detector **target** (which draws the footprint actor + coverage disc + "Image / Sensor" label)
  sits on the **folded** beam, but
- the kind="image" **surface curve** is left behind on the **unfolded** +Z axis.

That stranded curve is a SECOND image/detector plane off the beam. The two-arm splitter path already
drops its superseded terminal curves after folding; the single promoted-mirror fold did not.

## Fix
After the single-mirror fold carries the detector target,
`_drop_unfolded_superseded_image_curves(bundle)` removes any kind="image" surface curve whose
centroid is farther than `_SUPERSEDED_IMAGE_CURVE_TOL_MM` (1.0 mm) from **every** folded detector
target. A curve that **still** sits on its detector — a plain sequential scene, or a folded-sequential
curve that was built folded — is within tolerance and kept, so only the genuine off-beam duplicate is
removed. With no detector targets (nothing to compare against) the drop is a no-op.

This mirrors the two-arm splitter path, which already relies on the folded detector footprint to draw
the terminal plane and drops its superseded curves. The detector target keeps drawing the single
image plane at the folded pose (footprint + coverage disc + label), so exactly one plane remains.

Wired in `LayoutSceneBundleDisplayMixin._build_scene_bundle`: the single-mirror fold branch now calls
the drop only when `_fold_promoted_mirror_table_row_targets(bundle)` reports it folded a target (the
return value is preserved for the existing RA-mirror coverage guards).

## Verification
`KrakenOS/UI/validate_open3d_folded_duplicate_image_plane.py` (penta **phase 215**):

- **NO DUPLICATE** — on the two-fold after `fov_solve("object","thickness",55,55)` the bundle has
  exactly **one** detector target and **no** stale kind="image" curve (>1 mm) off the folded detector,
  and the detector is genuinely off the +Z axis (a real fold).
- **COINCIDENT KEPT** — a synthetic bundle with a coincident image curve (on the detector) and a
  diverged one (off-beam) → the drop removes only the diverged curve and keeps the coincident one.
- **STILL IMAGES** — rays still reach the single folded detector after the drop.
- **WIRED** — `_build_scene_bundle` calls `_drop_unfolded_superseded_image_curves` and the method is
  defined on the mixin.

The stale curve is a VTK render and can't be pixel-validated headless (llvmpipe SIGSEGV); this guard
checks the bundle geometry the renderer consumes (curve count + detector coincidence). In-app visual
confirm owed (restart the app onto this build, redo the folded solve, confirm a single image plane).
