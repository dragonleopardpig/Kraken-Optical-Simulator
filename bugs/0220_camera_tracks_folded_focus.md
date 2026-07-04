# 0220 — camera STEP detached from the detector on a folded overshoot

**Status: PARTIAL FIX SHIPPED (the CAMERA). On the two-mirror folded AZ85 the camera STEP followed
the prescription Image-row plane (z=387) while the bugs/0217 reconcile parks the detector at the
true optical focus (z=355) — so they sat a mirror-plate (~32 mm) apart ("detector and camera STEP
detached", `flag_20260704_195234`). `_camera_track_image_plane_z` now tracks the paraxial focus when
the trailing mirror overshoots the conjugate, so the camera STAYS ON the detector. Still owed: the
row-9 image-plane DISC actor + the 2D image-plane LINE may be separate representations that also need
reconciling — an in-app eyeball is required to see which of these the user perceives as "the
detector". FOV≠1X is a separate pre-existing magnification bug, untouched.**

## The bug

The camera front is placed at `_current_image_plane_z() - _current_camera_front_to_sensor_mm()`
(`layout_polyline_display.py`, `optical_solid_workflow.py`, `scene_placement_commands.py`).
`_current_image_plane_z()` is the PRESCRIPTION Image-row cumulative-z. On the two-mirror AZ85 the
trailing mirror-2 BK7 plate pushes that row ~32 mm PAST the true optical conjugate
(`_current_image_plane_z` = 387.22 vs `_paraxial_image_plane_z` = 354.97). bugs/0217 already snaps
the detector + rays onto the focus (355), but the camera kept following the row (387) → the camera
body floated a plate behind the detector.

## The fix (camera)

`_camera_track_image_plane_z()` (`layout_polyline_display.py`): tracks `_paraxial_image_plane_z`
(the focus) when it is meaningfully BEFORE the prescription row — the trailing-mirror overshoot,
which is EXACTLY the condition bugs/0217 fires on. Otherwise it keeps the prescription row. That
"only when the focus is before the row" rule is load-bearing:

```
                prescription   paraxial focus   camera tracks
TWO-MIRROR      387.22         354.97 (before)  354.97  -> the FOCUS (attaches to the 0217 detector)
SINGLE-MIRROR   347.22         354.97 (past)    347.22  -> the ROW (unchanged)
```

For the single fold the focus is 8 mm PAST the row: the rays stop at the row before reaching it
(0217 is a no-op there, detector on the row), so tracking the focus would detach the camera the
OTHER way. Unfolded scenes (`_scene_folds_for_paraxial_distance` False) always keep the row.

Wired at all four camera-placement sites; the other `_current_image_plane_z` consumers (the 2D
image-line, results, the detector-coverage GAP overlay that deliberately compares row-vs-focus) are
left untouched.

## Verification

Display-free guard `validate_open3d_camera_tracks_folded_focus` (4/4): two-mirror tracks the focus,
single fold keeps the row, a causal contrast (the camera did NOT follow the 32 mm-overshot row), and
wiring. Penta **phase 196**, baseline `pass`. `validate_open3d_camera_overlay_hover_alignment` kept
green (its `_FakeEditor` gained a `_camera_track_image_plane_z` returning the prescription, since it
is unfolded). `validate_open3d_folded_image_snaps_to_ray_convergence` (0217) + the folded-distance
guard (0219) unaffected.

## In-app eyeball — OWED (the visual part of the "detached" flag)

Headless proves the camera-track z now equals the focus (== where 0217 puts the detector). But which
element the user sees as "the detector" — the 0217 `is_detector` target, the row-9 disc actor
(`row_actor_bounds[9]`), or the 2D image line — is a rendering detail this fix does not touch for the
disc/2D-line. The user should confirm in-app whether the camera + detector now coincide, and flag any
residual (a floating row-9 disc / a 2D image line off the focus) so the remaining representations can
be reconciled the same way.
