# 0217 — two-mirror folded AZ85 image is unfocused (detector ~12 mm off the true focus)

**Status: ROOT-CAUSED (fix not yet implemented; user greenlit the root fix, then asked to pause).
The two-mirror optics FOCUS PERFECTLY — the folded display cone converges to a 0.7 µm waist at
world (181.3, 0, −33.8). That point is VERIFIED to be the true physical image: reflecting the
straight-equivalent focus (0,0,359.07) about BOTH real mirror hypotenuse planes by hand lands at
(181.31, 0, −33.78), matching the display waist. So the display-ray fold is CORRECT. The image
reads "unfocused" only because the drawn detector (z=−22.05) and the ray hard-stop (z=−62.05) are
BOTH placed off that focus. This is a two-mirror Image-ROW PLACEMENT bug, not an optical/fold bug.
The fix touches the delicate straight-equivalent focus machinery (0197/0205/0207/0208) and its
success is VISUAL (rays must terminate ON the detector at focus), which headless cannot confirm.**

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

## Next step (owed to the user)

Root fix (greenlit): make the Image ROW land at the true focus for a trailing fold mirror, so BOTH
the drawn detector AND the ray hard-stop reconcile to z=−33.84. Candidate sites — the free-placed
mirror's missing analog of `_reflected_frame_from_interaction_face` (nonseq_output_ports.py:1116)
for the Image-row/exit-frame, and/or the flat-plate track in
`_folded_optical_solid_straight_equivalent_rows` (paraxial_tools.py:358) not carrying a
post-focus fold mirror's plate. Then: display-free guard (extend the
`validate_open3d_ra_mirror_folded_cone_focus` pattern to the two-mirror scene, asserting endpoint
RMS small AND the detector ref == the waist) + penta phase + baseline + commit + push, then in-app
eyeball (stacked with 0214/0215/0218). Re-run the folded-scene guard suite — the single-mirror
control (`validate_open3d_ra_mirror_folded_cone_focus`) must stay byte-identical.
