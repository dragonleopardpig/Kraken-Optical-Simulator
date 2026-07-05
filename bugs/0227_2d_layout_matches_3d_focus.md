# 0227 — the 2D layout defocused at the detector while the 3D was sharp

**Status: FIXED. The 2D layout plot now shows exactly what the 3D inspector shows on a folded
scene: the rays converge ON the sensor line (detector parity to 0.004 mm, on-axis gap 0.000 mm).
In-app confirm owed (re-open the 2D plot on the AZ85 scene).**

## The report

`attachment/2D.png` ("YZ full 3D" figure): "not matching with the 3D (rays defocus at the
detector)" — the field bundles arrive at the Image/Sensor line still broad, converging somewhere
short of it, while the 3D inspector shows the cone sharp on the detector.

## Root cause

The 3D pipeline (`_build_preview_system_rays_bundle`) follows the folded display bend with the
bugs/0217 reconcile: when the trailing fold mirror's plate pushes the prescription Image row PAST
the true conjugate, the detector target and the on-axis ray hard-stops snap onto the cone's real
waist. The 2D pipeline (`refresh_plot`, `services/plot_refresh.py`) ran the SAME trace and the SAME
bend — but stopped there. Its bundle kept the detector at the overshot `fold(prescription)` and the
rays running a full plate past their focus to that line: measured on the two-mirror AZ85, the
bend-only detector sits at (181.4, 0, −62.05) — **48.5 mm past the waist** at (181.4, 0, −13.55).
The user saw precisely that: sharp in 3D (reconciled), defocused in 2D (not).

## The fix

`refresh_plot` now mirrors the 3D pipeline exactly — after `_apply_folded_display_bend`, when a
straight-equivalent fold transform is present, it calls
`_reconcile_folded_image_to_ray_convergence(bundle)`. Unfolded scenes and the sequential-Mirror
fallback (no transform) are untouched, matching the 3D gates.

## Verification

`validate_open3d_2d_layout_matches_3d_focus` (4/4, penta **phase 202**): 2D/3D detector parity
(both on the waist), the 2D on-axis cluster converges ON the 2D detector (0.000 mm), the CAUSAL
bend-only contrast (48.5 mm overshoot — the flagged defocus), and the wiring order in refresh_plot.
Regression: `validate_folded_mirror_projection_parity` + `folded_image_snaps_to_ray_convergence`
stay green.
