# 0419 — Accept-cone crease must REFLECT about the mirror plane, not rotate (0418 fix)

**Flag `flag_20260723_092135_318`** (AZ85 RA-mirror scene, build `ce6b2422` — which has 0418):
> "Acceptance cone go[es] he[y]wire[d]."

## Why 0418 twisted the surface

0418 creased the cone by (a) splitting its points at a **horizontal** plane `z > hinge_z` and (b) applying
the rigid fold **rotation** `R·p + t` to the downstream half. Two problems:

1. The split boundary (a horizontal plane) is **not** the mirror plane (a 45° tilted plane), so points
   near the fold were mis-classified.
2. A rigid rotation about the hinge is **discontinuous** across that split and reorients the ring
   abruptly — so the loft between the object-leg ring and the rotated lens-leg ring became a twisted,
   self-intersecting surface. "Haywire."

## Fix — reflect about the mirror plane (the proven BS-fold trick)

`two_arm_display_fold.fold_points` folds the beam splitter's rays by **reflecting** the past-plane portion
about the tilted splitter plane — a **continuous isometry** (identity ON the plane), which is exactly why
it doesn't twist. `_crease_overlay_mesh_at_fold` now does the same, with the mirror plane **derived from
the fold transform**:

- incoming axis `= +Z` (the straight sequential axis); outgoing `= R·(+Z)` (the folded leg direction);
- mirror-plane normal `= incoming − outgoing` (the bisector), through the fold's fixed point `(I−R)a = t`;
- points on the downstream side reflect about it: `p − 2·((p−a)·n̂)·n̂`; the rest stay.

Because a reflection is an isometry, the cone's cross-section is **preserved** as it crosses the fold —
the ring reorients smoothly from the object leg's transverse plane to the lens leg's, no twist. The FOV
ring (upstream) stays up the object leg; the pupil end lands on the lens leg. `None`/identity transform
(unfolded scene) → unchanged.

## Verification (`validate_open3d_accept_cone_fold_aware`, penta phase 339)

Display-free, on a real cone straddling a Z→X fold (hinge z=53, mirror plane `z = 53 + x`):

| check | asserts |
|---|---|
| MECHANISM | the crease REFLECTS (`2.0 * signed … normal`), not the old `@ rotation.T + translation` |
| CREASE-MATH — fold | the downstream pupil ring reflects onto the leg, centre (0,0,100) → (47,0,53) |
| CREASE-MATH — **isometry** | the reflected pupil ring **keeps its radius** (the no-twist guarantee) |
| CREASE-MATH — continuity | a point on the mirror plane `z = 53 + x` is a fixed point |
| CREASE-MATH — unfolded | a `None` transform is a no-op |

5/5 pass. Baseline phase 339 = pass. This reuses the same reflection math as the shipped BS two-arm fold,
so the geometry is on firmer ground than the two prior attempts.

## Files

- `KrakenOS/UI/open3d_inspector.py` — `_crease_overlay_mesh_at_fold` reflects about the derived mirror plane.
- `KrakenOS/UI/validate_open3d_accept_cone_fold_aware.py` — guard: reflection + isometry + continuity.

## In-app eyeball still owed

Folded geometry is headless-untestable. On the AZ85 scene, **Accept cone** should now be a clean cone up
the object leg that bends smoothly onto the lens leg at the RA mirror — no twist, no flat sheet, not
straight down. This is the third iteration; if it's still off, a fresh flag pins the next correction.
