# 0607 — A swap performed INSIDE Normal-to-Sensor left a stale isolation (FIXED)

Found while verifying the three confirmation flags of 2026-08-11
(`flag_20260811_125250` rotation/zoom, `125350` Nav-Cube exit, `125507` *"swapped lens
auto turn off Normal to sensor: is working"*), build 4212d10c.

## Two defects, one sequence

**1. The 0606 exit wiped the caller's camera preset (regression, shipped 4212d10c).**
`_restore_sensor_isolation` cleared `_camera_preset` so its leaving redraw would not
re-filter. But `set_camera_preset` assigns the NEW preset **before** it calls the
restore, so every preset button / nav-cube snap that left the view ended with
`_camera_preset = None` instead of the view it had just selected. The redraw now
suppresses the FILTER for its duration (`_sensor_view_ray_filter_suppressed`) and never
touches the preset. Measured after the fix: leaving to `-xz` keeps `-xz` and restores
all 558 rays.

**2. A swap inside the view kept the stale isolation.** Measured headlessly (swap
PYRITE_56_100 while in the sensor view): `preset=sensor_normal`, isolation params still
set, **3 actors visible, 175 rays (still filtered)** — the incoming lens sits off the
OLD sensor plane, so the swap's own result is invisible. The user's flag reports the
opposite behaviour in-app (their post-swap capture shows full-scene bounds), i.e. it
depended on whether that rebuild happened to skip the re-isolation. Behaviour that
matters should not be incidental.

## Fix

`Kraken3DInspector.leave_sensor_view_for_scene_change()`: when the view is active,
restore the isolation (which also restores the full ray set) and clear the view MODE,
leaving the camera POSE exactly where the user put it — no reframe surprise. Called from
`_switch_off_analysis_overlays_for_swap`, the helper BOTH swap paths (lens + camera)
already share, and reported in the swap message ("Left the Normal to Sensor view so the
swapped optics are visible"). A no-op outside the view.

Guard: phase 459 extended — D (no preset wipe; suppression beats the preset;
set_camera_preset still records its preset) and E (the scene-change exit exists,
restores + clears the mode, no-ops outside the view, and both swap paths call it).
