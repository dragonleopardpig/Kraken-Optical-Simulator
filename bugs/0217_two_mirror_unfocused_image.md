# 0217 — two-mirror folded AZ85 image is unfocused (detector a plate past the true focus)

**Status: FIXED for the 3D view (the `flag_20260703_221640` "still defocus at detector" scene);
the 2D image-plane LINE + a pre-existing single-fold sensor drift remain (see "Remaining"). The
two-mirror optics FOCUS PERFECTLY — the folded display cone converges to a 0.7 µm waist at world
(181.3, 0, −33.8), VERIFIED as the true physical image (reflecting the straight focus (0,0,359.1)
about BOTH real mirror planes by hand lands (181.3,0,−33.8)). The image read "unfocused" because
the DRAWN 3D detector AND the ray hard-stop both sat ~a fold-mirror plate (28 mm) PAST that focus.
`_reconcile_folded_image_to_ray_convergence` (three_d_scene_tools.py, run after
`_apply_folded_display_bend`) snaps the detector target + the rays onto the ray convergence — the
two-arm splitter fold's "detector at the physics focus" pattern generalised to the RA-mirror fold.
Guard `validate_open3d_folded_image_snaps_to_ray_convergence` (penta phase 194) proves the cone
converges ON the detector (0.7 µm) and the single fold / penta are clean no-ops. In-app eyeball on
the 3D two-mirror scene still owed (headless proves detector == waist == ray-stop mechanically).**

## CORRECTION to the earlier note: the detector is at −62.05, NOT −22.05

The first pass reported the detector at z=−22.05. That was a RED HERRING: −22.05 is what
`_surface_reference_world_point(9)` returns (an OVERLAY/dimension anchor helper), which is NOT the
drawn detector. The actual drawn detector — the `is_detector` `SceneTarget3D` in the scene bundle —
is at **z=−62.05**, i.e. it COINCIDES with the ray hard-stop (both = `fold(straight-equivalent
Image row)` = the trailing mirror's flat-plate BACK face). With `folded_detector_policy = "Trace
events"` the detector tracks where the rays land. So the real picture on the harness two-mirror:

```
true focus (ray waist)   z = −33.8   0.7 µm     <- where the light images
detector target + ray-stop z = −62.05  ~0.5 mm   <- 28 mm (= plate back) PAST the focus
```

The rays converge to a sharp point at −33.8 and then DIVERGE back out to −62.05 where the detector
sits — that divergent blob at the detector is the "unfocused image". The bug is that the folded
Image plane is placed a plate past the conjugate, not that the fold breaks the cone.

## What the user flagged

`flag_20260703_145514_224`: *"reflected rays, image plane, detectors are all same direction now.
Note it is still unfocused."* This is the SAME recording that confirmed 0214's fold worked (the
image/detector now fold DOWN with the reflected rays), so the geometry points the right way — the
residual complaint is purely that the image is not sharp at the detector.

## Reproduction (display-free, production bundle)

`bugs/probe_0217_focus.py` (untracked scratch) builds the two-mirror AZ85 editor and calls the
PRODUCTION `editor._build_preview_system_rays_bundle()` (which folds the display rays about BOTH
mirror planes via `_reflect_straight_equivalent_display_rays`), then isolates the OUTGOING −Z leg
(trims each on-axis ray from its max-x mirror-2 corner) and sweeps for the transverse waist.

v1 of the probe was doubly wrong and is superseded: it measured the `_build_two_mirror` harness
bundle (which never applies the mirror-2 display fold — rays overshoot to x≈350) and its `_cross_z`
returned the FIRST z-plane crossing = the INCOMING leg (x≈0), reporting a false object-side focus.

Measured (rays ON, on-axis cone, 361 launched / 196 reach the outgoing leg):

```
drawn detector ref (last row):   z = −22.05   (x≈181.4)
outgoing-leg WAIST (true focus):  z = −33.84   rms = 0.7 µm      <- essentially a point focus
ray hard-stop (endpoints):        z = −62.05   (X,Y) RMS = 488 µm  <- the 0214 twice-folded Image
```

So three planes disagree:
- the **true focus** is at z=−33.84 (the cone is sharp there, 0.7 µm);
- the **drawn detector/image** is 11.79 mm short of it (z=−22.05);
- the **rays terminate** 28.21 mm PAST the focus (z=−62.05), where they have diverged back to
  488 µm — that divergent 488 µm blob at the ray-stop is the "unfocused image" the user sees.

The 11.79 mm ≈ the RA-mirror half-thickness/`desp_z` (~12.5 mm), matching the 0207 class of error
but introduced by the SECOND fold.

Also note the drawn-detector ref (−22.05) disagrees with where the rays actually hard-stop
(−62.05) — a 40 mm inconsistency between two ways of locating the same Image row in the folded
frame (the drawn ref vs the twice-folded detector-plane the 0214 seat put at −62.05). This
secondary inconsistency needs reconciling alongside the defocus.

## Snap does NOT cleanly fix it

`editor.snap_detector_to_image_plane()` (the call the single-mirror focus guard uses) only
partially helps: the endpoint (X,Y) RMS drops 488 → 70 µm and the ray-stop moves −62.05 → −29.8,
but it does NOT nail focus (70 µm residual) and it actually DEGRADES the achievable waist
(0.7 µm → 74 µm — snapping moved a gap/row that defocused the system). So the root is the
straight-equivalent image-plane PLACEMENT for two folds, not a missing/again-needed snap.

## Why this is optics-clean

The on-axis cone reaching a 0.7 µm waist proves the twice-folded trace + the two-plane display
reflection compose correctly (the fold does NOT break convergence). Contrast: the single-mirror
scene focuses tightly AT its detector (`validate_open3d_ra_mirror_folded_cone_focus`, endpoint
RMS < 0.05 mm). The difference is purely the axial placement of the image/detector/hard-stop
planes when a SECOND fold is present.

## CONFIRMED root cause (this session)

The earlier "second-fold analog of 0207 in the straight-equivalent flattening" guess was on the
right theme but the wrong mechanism. The precise picture, measured on the `_build_two_mirror`
harness (`bugs/probe_0217_groundtruth.py`):

- **Mirror 2 is FREE-PLACED, not a sequential record.** `fold_promoted_mirror_specs_to_sequential`
  produces only ONE record (mirror 1, row 1); mirror 2 (row 8) keeps its mesh with
  `desp_z=−276.620, desp_x=182.672` (the folded-world drop-point encoding, bugs/0213) and folds via
  the `free_placed_mirror_world_planes` POST-pass — reflecting the already-folded rays about its
  REAL world plane. Measured planes: mirror 1 center (0,0,71.897) n=(0.707,0,−0.707); mirror 2
  center (182.672,−1.532,70.598) n=(−0.707,0,−0.707). Fold is +Z → mirror-1 → +X → mirror-2 → −Z.
- **The display rays are RIGHT.** Both reflection planes are the real drawn hypotenuses, so the
  cone convergence at world (181.3,0,−33.8) is the geometrically-exact reflected image. Verified by
  hand: reflect the straight focus (0,0,359.07) about mirror-1 then mirror-2 → (181.31,0,−33.78).
- **The straight Image ROW sits 28 mm PAST the straight focus.** With the reflection disabled the
  unfolded rays converge at z=359.07 but the Image-row endpoint is at z=387.22 (the AZ85 relay
  images essentially AT mirror-2's front face ~359.72; the flat-plate equivalent then keeps
  mirror-2's 40 mm BK7 plate AFTER the focus, dragging the Image row ~28 mm / one plate-optical-
  length beyond the true conjugate). This mis-placed Image row is what both downstream placements
  fold — two different ways:
  - **ray hard-stop z=−62.05** = the straight Image row (387.22) reflected about mirror-2's plane;
  - **drawn detector z=−22.05** = the SAME Image row placed by `_compute_world_folded_layout_
    geometry_for_rows` (the folded scene geometry / detector disc), which lands it 40 mm (=mirror-2
    thickness) short of the ray hard-stop.
  The true focus (−33.84) sits BETWEEN them; neither downstream placement matches it.

So the single root is: **when the last fold mirror (mirror 2) is immediately before the Image, the
straight-equivalent keeps its full plate thickness after the focus, so the Image row overshoots the
conjugate; the two Image-row fold paths then disagree and neither lands on the true focus.**
Single-mirror works because mirror 1 gets bugs/0207's `_reflected_frame_from_interaction_face`
remaining-thickness correction; free-placed mirror 2 gets no equivalent Image-row correction.

## The PROTOTYPE that worked (headless) — reconcile the display to the ray convergence

There is already a precedent for exactly this: the two-arm beam-splitter fold
(`services/two_arm_display_fold.py`) places each detector at the PHYSICS focus (the ray
convergence), superseding the prescription image plane — its comment even reads *"prescription
595.8 + physics 615.1 collapse to one at the physics focus"*. Following it, a post-pass
`_reconcile_folded_image_to_ray_convergence(scene_bundle)` was prototyped (run after
`_apply_folded_display_bend`, gated to the straight-equivalent fold path):

1. anchor on the `is_detector` target's own plane (normal = outgoing axis);
2. select the AXIAL field (rays launched within 1 mm of the object axis — off-axis fields image
   to their own points, so a mixed bundle has no locatable waist; a collimated cascade like the
   penta launches nothing near the origin, so it is a clean no-op);
3. trim each ray to its OUTGOING leg (trailing +axis-monotonic run) so the object/pre-fold legs
   cannot masquerade as a waist, then sweep the whole leg for the GLOBAL tightest waist;
4. GATE (all required, so single folds / collimated cascades no-op): overshoot ≥ 2 mm AND
   waist RMS ≤ 0.1 mm AND waist RMS ≤ 0.2 × endpoint RMS;
5. truncate every reaching ray onto the waist plane AND move the detector target(s) onto it.

Headless result: the two-mirror AZ85 detector + ray endpoints snap to z=−33.84 at **0.7 µm** (a
tight focus ON the detector); the single-mirror AZ85 is a clean NO-OP (overshoot ~0).

## The entanglement (why the prototype was REVERTED, not shipped)

The detector is NOT one object — it has SEVERAL representations that must stay consistent, and the
post-pass moved only some:

- the scene-bundle `is_detector` `SceneTarget3D` (moved by the post-pass — the drawn disc);
- the OUTPUT-PORT pose override `build_optical_solid_output_port_pose_overrides(...)[image_row]`
  (`_reflected_frame_from_interaction_face`, bugs/0207) — a GEOMETRIC placement that has no ray
  data, so it CANNOT know the optical focus; it stays at the overshot plane;
- the reference-plane override / 2D image-plane curve, and the row actor / dimension anchors.

`validate_open3d_second_mirror_orientation_driven_fold` (a synthetic free-placed 2-mirror scene)
asserts the display ray endpoint COINCIDES with the output-port override image center. That scene
has the SAME overshoot (waist z=−4.49, endpoint/override z=−32.72, ~28 mm), so the post-pass
CORRECTLY fires and moves the rays to −4.49 — but the override stays at −32.72, so the guard's
"rays == detector" coincidence breaks. This is not a false positive; it shows the overshoot is
SYSTEMIC (single-mirror end-to-end, the orientation-driven scene, and the main flag all exhibit
it), and that several existing guards ENCODE the overshot behaviour (rays == overshot detector).

Also note: `validate_open3d_ra_mirror_folded_sequential_trace` already FAILS on clean `main`
(single-mirror cone at X=275.32 vs the guard's `_SENSOR_X=287.82`) — a pre-existing 12.5 mm
(=mirror desp_z) discrepancy, independent evidence that even the SINGLE fold's drawn sensor sits a
half-plate past where the cone lands. Fixture/guard drift, not this bug, but same family.

## SHIPPED (Stage 1 — the 3D view, `flag_20260703_221640`)

`_reconcile_folded_image_to_ray_convergence(scene_bundle)` runs after `_apply_folded_display_bend`,
gated to the straight-equivalent fold path. It anchors on the `is_detector` target's own plane,
selects the AXIAL field (launch within 1 mm of the object axis), trims each ray to its OUTGOING leg
(so the object/pre-fold legs can't masquerade as a waist), sweeps the whole leg for the GLOBAL
tightest waist, and — only on a real overshoot (waist ≥ 2 mm upstream AND ≤ 0.1 mm AND ≤ 0.2×
endpoint RMS) — truncates every reaching ray onto the waist plane and moves the detector target(s)
onto it. On the two-mirror AZ85 the detector + rays snap from z=−62.05 to z=−33.84 at **0.7 µm**
(the cone now focuses ON the detector). Clean NO-OP on the single fold (overshoot ~0) and the penta
(collimated, no axial cone → <8 axial rays). `validate_open3d_second_mirror_orientation_driven_fold`
was updated (it asserted rays == the RAW output-port override `image_center`, the plate-back; it now
asserts rays == the reconciled `detector_target`, both at the physics focus — the override is the
superseded geometric placement). Guard `validate_open3d_folded_image_snaps_to_ray_convergence` =
penta phase 194. All 9 folded guards green. In-app eyeball on the 3D scene still owed.

## Remaining (owed)

1. **The 2D image-plane LINE.** The `surface_curves` role="image" curve sits at z=−22.05 (the
   `_optical_solid_image_plane_overrides` / output-port geometric value — a THIRD representation,
   already inconsistent with the −62.05 disc BEFORE this fix). Stage 1 moves the 3D disc + rays but
   NOT this 2D curve (it lives in a different/projected frame). The 2D layout view will still draw
   the image line off the focus — the `flag_20260703_145514` "image plane … wrong direction" 2D
   complaint. Stage 2: move the 2D image curve (and any row/dimension anchor) onto the convergence
   too. The geometric output-port override cannot know the optical focus, so this must also be a
   display reconciliation keyed off the ray convergence.
2. **Pre-existing single-fold sensor drift.** `validate_open3d_ra_mirror_folded_sequential_trace`
   FAILS on clean `main` (single-mirror end-to-end cone at X=275.32 vs its `_SENSOR_X=287.82`, a
   12.5 mm = mirror desp_z gap). Same family, but a separate fixture/guard-drift issue — the
   single-fold reconcile is a NO-OP (its display cone already waists at its own endpoint 275.3), so
   0217 neither fixes nor worsens it. Left for a dedicated pass.

Scratch (untracked): `bugs/probe_0217_{focus,groundtruth,dissect,flagpose,airplate,postpass,
reconcile_prototype}.py` carry every measurement + a standalone copy of the shipped post-pass.
