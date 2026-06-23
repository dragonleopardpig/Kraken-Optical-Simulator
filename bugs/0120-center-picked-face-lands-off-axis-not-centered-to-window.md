# 0120 — "Center Picked Face → Optical Axis" lands off the axis, not centered to the window

## Symptom

`flag_20260623_155107_905` — "after center to axis, it is offset from optical axis,
not centered to the selected window."

The bugs/0119 fix replaced the right-click rotate-snap with a translate-only
"Center Picked Face → Optical Axis". The user right-clicked the LED enclosure's front
window and chose it. The box moved, but came to rest **off** the optical axis instead
of centered on it. `state.json` confirms the command ran
(`step_overlay_poses.led.axis_anchor.source: "feature_center_axis_center"`), but its
recorded target is `axis_anchor.target_point: [-1.1534, -9.8039, 273.0234]` — clearly
**not** on the global axis (which is the dotted guide at x=0, y=0). The LED landed at
`placement_offset_xyz: [45.93, 10.25, -1.38]`, visibly offset in the screenshot.

`ray_actor_count: 0` and `show_rays: false` — there were **no rays drawn** at the
time, which is the tell for the root cause below.

## Root cause

Two compounding bugs in the bugs/0119 centre:

1. **Targeted the nearest traced ray, not the global axis.**
   `center_step_feature_on_optical_axis` resolved its target via
   `_step_optical_axis_frame_near_point`, which calls
   `_nearest_traced_ray_frame_near_point`. That helper reads
   `self._last_scene_bundle.ray_paths` — the **cached** bundle, alive even when rays
   are hidden (`ray_actor_count: 0`, `cached_bundle_mode: "world_cone"`). For an
   off-axis body (the LED, bounds out to x≈101, y≈55) the nearest cached ray is an
   outer marginal ray a few mm off (0, 0), so the face slid onto a *ray*, not onto
   the axis → `target_point: [-1.15, -9.80, 273.02]`. The 0119 guard missed this: its
   fake editor modelled the rays-**off** fallback `(0, 0, z)`, so the guard's target
   was always on-axis and the test passed.

2. **Centred the raw cursor hit, not the face centroid.** The right-click menu passed
   `point` (the `through_pick.point_world` click location) as the feature centre, so
   even with a correct on-axis target the window's **centre** would not land on the
   axis — wherever the cursor happened to hit the face would.

## Fix

1. **Target the GLOBAL optical axis.** New
   `ScenePlacementMixin._global_optical_axis_frame_near_point(reference_point)`
   returns the projection onto the global dotted guide — `(0, 0, z)`, matching how
   `_optical_axis_records_for_3d` builds `axis:global` at x=0/y=0.
   `center_step_feature_on_optical_axis` now uses it (instead of the ray-seeking
   `_step_optical_axis_frame_near_point`) when no explicit `axis_frame` is supplied.
2. **Centre the face centroid.** The right-click menu (`open3d_face_assignment.py`)
   resolves the picked face centroid from the pick
   (`_surface_center_from_face_ray_pick(through_pick)`, falling back to the face
   record's `centroid_world`, then the click point) and binds it into the menu
   command (`picked_center=face_center`). The handler
   `_center_step_face_to_optical_axis_from_context` forwards that centroid.

Net: the window's centroid comes to rest on the global x=0/y=0 axis, z preserved, no
rotation.

## Test

`KrakenOS/UI/validate_open3d_center_picked_face_to_axis.py::run_checks` hardened so it
would have caught this:

- the fake editor now models BOTH frames — `_global_optical_axis_frame_near_point`
  (the correct `(0, 0, z)`) and `_step_optical_axis_frame_near_point` set
  deliberately **off-axis** `(-1.1534, -9.8039, z)` (the failing case);
- behavioural — an off-axis face centre lands on the global axis (x/y zeroed), the
  global frame helper is called and the nearest-ray helper is **not**;
- source contract — the centre resolves `_global_optical_axis_frame_near_point` and
  no longer calls `self._step_optical_axis_frame_near_point`;
- source contract — the right-click menu resolves `_surface_center_from_face_ray_pick`
  and binds `picked_center=face_center`.

Regression-proofed: reverting the call to the nearest-ray helper makes the behavioural
check land at the off-axis sentinel `(-1.15, -9.80)` and trips four source/behaviour
FAILs.

Penta phase 111 runs the full guard; **phase 112** pins the 0120-specific invariant
(off-axis nearest ray present → face still lands on the global axis).

## Note — in-app eyeball owed

Headless Xvfb cannot drive the embedded-VTK right-click face pick, so the menu
click → centre-on-axis is verified in-app. The guard pins the global-axis target, the
centroid wiring, and the translate-only math.
</content>
</invoke>
