# 0278 — "Normal to Sensor" should show only the sensor, hide everything else

## Symptom (flag_20260709_125338_765)

A direct follow-up to bugs/0277's **Normal to Sensor** view. The face-on snap works, but the whole
scene stays drawn — the big coaxial LED plate, the imaging-lens bodies, the ray polylines and the
optical-axis guide all sit in front of / around the sensor, so the on-detector illumination heatmap
is still cluttered and hard to read:

> "Overlay --> Normal to Sensor should only show the sensor, hide all others."

## Root cause

`Kraken3DInspector.view_normal_to_sensor` (bugs/0277) only moved the *camera*; it never changed actor
**visibility**. Every scene actor stayed on screen, so looking down the sensor normal you see the
detector through/around the rest of the system rather than in isolation.

## Fix (`open3d_inspector.py`)

Add `_isolate_scene_to_sensor_plane(center, normal, det_row_index, *, band)`, called at the end of
`view_normal_to_sensor`, and its partner `_restore_sensor_isolation`:

* **Keep visible:** the detector row's own actors (looked up in `_row_actor_map`, whatever their
  depth) **plus** any actor whose whole extent lies within `band` mm of the sensor plane along the
  normal — the heatmap quad and the orange sensor square, which are drawn coplanar with the detector.
  `band = max(3.0, 0.1 * max(width, height))` (≈3 mm for the 23×23 sensor).
* **Hide:** everything else — the LED plate, lens bodies, ray polylines, the optical-axis guide. In
  the coaxial scene the nearest of these is ~200 mm off the sensor plane (row 7 lens at z≈446 vs the
  detector at z≈657), so the proximity test has a huge margin and never mis-hides an on-plane overlay.
* **Restore:** the hidden actors are recorded on `self._sensor_isolation_restore`; `set_camera_preset`
  calls `_restore_sensor_isolation()` at the top, so switching to *any* other view (iso / cardinal /
  nav-cube) brings the full scene back. A re-invoke restores first, so it never double-hides.

The nav cube and gizmo handles live in a **separate** overlay renderer (`_gizmo_overlay_renderer`),
so they are never touched — the user can still navigate back out.

## Verification

New guard `validate_open3d_normal_to_sensor_isolation` (phase **245**), display-free: it drives the
real `_isolate_scene_to_sensor_plane` / `_restore_sensor_isolation` against **stub** VTK actors (no
renderer, no Tk, no llvmpipe segfault risk). The stub scene mirrors the coaxial layout — a detector +
two coplanar overlays at z=657, and four off-plane props (lens 211 mm away, LED cube, scene-spanning
axis, a ray). Asserts:

* **ISOLATE** — detector body (row map) + the two on-plane overlays (proximity) stay visible; the four
  off-plane props hide (hidden count == 4).
* **RESTORE** — every hidden prop re-shows and the restore list clears.
* **RE-INVOKE** — a second isolate is idempotent (restores first), so the restore list holds the four
  props once, not stale duplicates.

Baseline updated in place (245 new, pass).

## Notes

* **In-app eyeball owed.** The headless guard locks the hide/keep/restore *logic*, but the running
  vendor-STEP scene still owes a visual check that Overlays ▸ Normal to Sensor now shows a clean
  sensor + heatmap with the LED/lens/rays gone, and that clicking any other view restores them.
* Sibling flag `flag_20260709_125602_415` ("I see 4 edges dark") is a separate matter — it is the
  radial illumination falloff on the real **23×23** sensor (its corners reach the Ø32.6 image-circle
  edge, so they vignette), not the 2-dark fold pattern, which is geometrically off-sensor at that
  size (the fold darkening lives at ±15–19.5 mm; a 23×23 sensor only reaches ±11.5 mm). Tracked
  separately; not a display bug.
