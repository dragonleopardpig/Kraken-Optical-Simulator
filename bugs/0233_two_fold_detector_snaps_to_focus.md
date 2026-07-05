# 0233 — two-fold periscope: the detector stayed at the overshot image plane (defocus)

**Status: FIXED. On a two-mirror periscope whose image row overshoots the focus, the detector now
snaps onto the ray waist (where the camera STEP already sits). In-app confirm owed.**

## The report

flag_20260705_180738 (re-saved Pyrite periscope, AFTER the 0232 fix put the 2nd mirror at the end
so it correctly folds only the camera): "Camera STEP and detector detached. Camera STEP at correct
focus position. Detector and image plane in defocus location." Measured on the exact scene: the
camera-track focus (where the camera STEP sits) = (0, 184.7, **23.5**); the detector/image plane =
(0, 184.7, **−77**) — 100.6 mm apart, and the rays trace all the way to the −77 image row, so they
arrive DEFOCUSED there while the true waist is at 23.5.

## Root cause

The bugs/0217 reconcile (`_reconcile_folded_image_to_ray_convergence`) that snaps a folded detector
onto the ray convergence **no-opped**. It orients its analysis axis along the beam, then walks each
ray's OUTGOING leg (the trailing run where the projection increases toward the endpoint) to find
the waist. The orientation used `mean((ends − ref) @ axis)` — but a periscope images a full plate
PAST the focus, so the ray endpoints land **ON the detector plane**, making that projection ≈ 0.
Its sign is then float noise; here it came out slightly negative and **flipped the axis against the
beam**. With the axis reversed, the projection DECREASES toward the endpoint, so the outgoing-leg
walk captured nothing (`legs == 0`) and the reconcile bailed — leaving the detector at the 100 mm
overshoot while the camera-track focus sat on the waist. (A single-fold AZ85 images at its
endpoints, overshoot ≈ 0, so it legitimately no-ops — the bug only bites when there's a real
overshoot AND the endpoints are on the plane, i.e. the two-fold periscope.)

## The fix

Orient the axis by the beam's **final-segment direction** (`mean(pw[-1] − pw[-2])`) instead of the
endpoint-vs-ref projection. The last segment always points along the propagation into the detector,
regardless of where the endpoints land, so the outgoing-leg walk finds the waist and the reconcile
snaps the detector (and truncates the rays) onto it. On the Pyrite periscope the detector now lands
at (0, 184.7, 23.5) = the camera focus (gap 0.0 mm), with the axial cone converging on it (RMS 0.0).

## Verification

`validate_open3d_two_fold_detector_snaps_to_focus` (display-free, penta phase 206): the
endpoint-vs-ref projection is ≈0 (the old unreliable orient) while the final-segment direction is
clearly signed; a synthetic overshoot bundle (waist 50 mm before endpoints, endpoints on the plane,
normal along the beam) is now moved onto the waist by the real reconcile (it no-ops without the
fix); the two-mirror AZ85 detector is NOT spuriously moved (stays on its known folded focus).
Regression: folded_image_snaps_to_ray_convergence (0217), 2d_layout_matches_3d_focus (0227), offbeam
(0224/0226), retroreflect-dive, carryover, periscope (0230), trailing-fold (0232) all green.
