# 0606 — Normal-to-Sensor hides rays that don't land on the sensor (FEATURE)

From the flag_20260810_204240 discussion: after bugs/0605 every ray ending on the
sensor is genuine (143 target_termination arrivals forming the 3×3 field grid), but
**415 polylines still CROSS the sensor plane beside the glass** — the BS other-arm
light and the per-field misses flying visibly past. In a face-on sensor view those
strands visually overlap the square and read as strays. The user accepted the physics
("I will take it as it is") and opted into the offered polish: while in the sensor
view, show only the light that actually lands.

## Behaviour

- **In Normal-to-Sensor**: any ray draw (the Rays toggle inside the view, an overlay
  rebuild, the async trace) keeps ONLY rays whose terminal status is `hit_detector` —
  the landing set. Crossers, misses, escapes and vignette stubs are not drawn.
- **Every other view**: unchanged — misses still fly visibly past (the 0605 doctrine
  holds where the 3D geometry can be seen).

## Design

- The filter derives from `_camera_preset == "sensor_normal"`
  (`_sensor_view_hides_non_landing_rays()`) — the single source of truth for being in
  the view, so every draw path inherits it with no separate lifecycle flag to desync.
- Both draw loops in `open3d_scene_refresh.py` (`_refresh_rays_only` + `refresh_scene`)
  apply it and mark `_sensor_view_ray_filter_applied` when they actually skipped rays
  (debug trace `sensor_view_non_landing_rays_hidden`).
- **Leaving the view redraws the rays**: filtered rays are ABSENT, not hidden, so
  `_restore_sensor_isolation` (the set_camera_preset / Nav-Cube exit funnel) triggers a
  rays-only redraw when the marker is set — the full ray set returns with the scene.

Guard: phase 459 (`validate_open3d_0606_sensor_view_landing_rays_only`). Verified by
sequence replay with rendered snapshots: enter view → rays ON → only the 9 field
pencils; Nav-Cube exit → full ray set restored.

## Follow-up (bugs/0607)

The first cut of the leaving redraw cleared `_camera_preset` so it would not re-filter —
but `set_camera_preset` assigns the NEW preset BEFORE calling the restore, so that wiped
the caller's own preset on every exit. The redraw now suppresses the FILTER for its
duration (`_sensor_view_ray_filter_suppressed`) and never touches the preset. See
bugs/0607, which also makes a swap leave the view explicitly.
