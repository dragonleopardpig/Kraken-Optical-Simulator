# 0222 — folded FOV ≠ 1X: the RA mirror was modelled as glass (internal), not an external reflection

**Status: FIXED. The promoted RA mirror is an EXTERNAL (first-surface) reflection — the beam bounces
off the coated hypotenuse and never enters the glass — so its glass is optically inert and the
folded 1:1 AZ85 relay now reports magnification 1.0 (was ~1.16–1.40X). The external-vs-internal case
is decided from the GEOMETRY so the model stays in SYNC with the drawing whichever way the prism
sits. Headless-verified (paraxial + ray trace = 1.000). In-app re-eyeball owed: the true focus moved
(the air model is a plate-thickness shorter than the old glass model), so the detector/camera sit a
few mm nearer — cosmetically the cone is unchanged, still sharp on the detector (bugs/0217/0220).**

## The request

`flag_20260704_195234_389`: "detector and camera STEP detached. FOV is not 1X." The detach half was
bugs/0220 (+0217, since confirmed fixed in `flag_20260704_204823_240`: "detector no longer detached
from camera. Rays also sharp focus."). This bug is the **FOV ≠ 1X** half — the AZ85 is a 1:1 relay
(object at 2f, unit magnification), but the folded scene read ~1.16–1.40X.

The user's decisive clarification: *"The glass has no optical function here. The only optical function
is the Reflective Coating on the hypotenuse surface. The rays should only see a 'reflective surface'
and apply reflection law … all the previous snapshots show clearly, the ray never enters the RA
glass, they immediately bounce off as soon as they touch the surface. This is an External Reflection
case."* And the worry that drove the general fix: *"That is to say we clearly see an External
Reflection takes place in the UI, but the underlying code is using Internal Reflection. This kind of
'Out of Sync' situation worry me … if I flip the RA mirror so the hypotenuse faces downwards, will
the ray trace be smart enough to enter the glass first surface, reflect off the second, exit the
third, and correctly take care of the refractive index of glass?"*

## Root cause

The promoted RA mirror is a CAD mesh prism (`OpticalSolidFaces`: a coated Mirror hypotenuse + Transmit
catheti). The 3-D DISPLAY already folds correctly as an EXTERNAL reflection (a rigid mirror-plane
isometry — the drawn rays bounce off the hypotenuse, never entering glass). But the FIRST-ORDER MODEL
that feeds the magnification / distances — the flat-plate straight-equivalent
(`_folded_optical_solid_straight_equivalent_rows`) and the paraxial reference walk
(`_paraxial_reference_rows_for_layout`) — flattened the prism into a **40 mm BK7 plate the rays
transit** (an INTERNAL reflection). That glass plate adds an excess optical path `t·(1 − 1/n)` ≈
13.7 mm, which pulls the object→front-principal distance off 2f and inflates the conjugate
magnification to ~1.16–1.40X. The display said *external*; the model said *internal* — exactly the
out-of-sync the user flagged.

## The fix (general — geometry decides, so a flipped prism is handled too)

- **`_ra_mirror_fold_is_external_reflection(row_index)`** (`services/paraxial_tools.py`): decides the
  case from the GEOMETRY, not a hard-wired assumption. It builds the incoming beam direction (previous
  fold vertex → this mirror centre, or the object at the axis origin for the first fold) and finds the
  ENTRY face by the slab method (the front-facing face — `d·n < −0.05` — the beam reaches last going
  in). If that entry face is the **Mirror** → EXTERNAL (True: the beam strikes the coating directly,
  glass inert). If it is a **Transmit** cathetus → INTERNAL (False: the beam enters glass, refracts,
  reflects off the interior Mirror face, exits — the index matters). None for non-mirror rows.
- **External ⇒ AIR in the first-order model.** In both `_folded_optical_solid_straight_equivalent_rows`
  and `_paraxial_reference_rows_for_layout`, a promoted mirror fold whose detection is `not False`
  (external) has its flattened plate glass forced to `AIR` — a pure fold, matching the drawing. A
  genuine internal-reflection prism (`False`) keeps its glass, so its index still shifts the conjugate.
- **Magnification read at the CONJUGATE, not the prescription Image row** (`_current_finite_paraxial_
  magnification`, `services/layout_scene_bundle_display.py`): on a folded scene the trailing mirror
  pushes the Image row a plate PAST the true focus, so `image_principal/object_principal` measured the
  mag at a DEFOCUSED plane. The Gaussian conjugate `m = f/(s_o − f)` (with `s_o` = object→front-
  principal) reads it at focus. With the external mirrors now air, `s_o = 2f` ⇒ `m = 1.0` exactly.
  **Scoped to folded scenes** (`_scene_folds_for_paraxial_distance()`), so every unfolded scene keeps
  its exact previous magnification.

Because the mirror is now air, the true focus (and the detector/camera that track it, bugs/0217/0220)
moves a plate-thickness nearer than the old glass model — the reconcile truncation
(`_reconcile_folded_image_to_ray_convergence`) was updated to clip the on-axis cone at the waist-plane
crossing anywhere along the ray, so the drawn cone still terminates exactly on the detector.

## Verification

Display-free guard `validate_open3d_ra_mirror_external_reflection` (5/5): (A) the AZ85 RA mirrors are
detected EXTERNAL; (B) magnification 1.0 — paraxial (single + two mirror) AND a ray trace of the
straight-equivalent at the focus (1.000, vs the ~1.16–1.40 a BK7 plate gives); (C) the straight-
equivalent draws the mirror as AIR (in sync); (D) the INTERNAL contrast — a beam redirected to descend
onto a cathetus (Transmit) face is detected `False` (keep the glass), proving the flipped-prism case
the user asked about; (E) wiring. Penta **phase 198**, baseline `pass`. All neighbouring folded guards
(0215–0221 axis/vertex/cone/distance/snap/camera) stay green.

## In-app follow-up owed

Per the memory workflow (visual fixes need an in-app eyeball): confirm the FOV readout now shows 1X
and the detector/camera sit on the (slightly nearer) sharp focus. The optics are unchanged in shape —
only the axial focus position shifted by the removed glass path.
