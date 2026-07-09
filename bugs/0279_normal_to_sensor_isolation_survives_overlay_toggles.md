# 0279 — "Normal to Sensor" isolation must survive overlay toggles

## Symptom (flag_20260709_150713_387, + follow-up)

A direct follow-up to bugs/0278. The first click of **Overlays ▸ Normal to Sensor** works — a clean
sensor, everything else hidden. But then:

> "First time clicking 'Normal to Sensor' works, clean with only detector. But after enabling
> 'Illumination' overlay, it is blocked again by other elements. Unchecked 'illumination' overlay
> still showing other elements."

And the follow-up direction:

> "Please check all overlays, none of them should re-enable other elements."

## Root cause

`_isolate_scene_to_sensor_plane` (0278) is a **one-shot**: it walks the renderer's *current* actors
and flips their visibility once. Toggling **any** overlay routes through
`_on_scene_visibility_changed → refresh_scene`, and `refresh_scene` (the scene-refresh service)
**rebuilds the actor collection fresh, every actor visible**. The rebuilt actors are brand-new
objects, so:

* the newly-added overlay actors (illum rays, etc.) and the re-created LED plate / lens / rays are
  all visible again — they "block" the sensor;
* `_sensor_isolation_restore` still points at the **old** (now-dead) actors, so unchecking the
  overlay (another rebuild) can't bring back the isolation either — it stays cluttered.

## Fix (`open3d_inspector.py`)

Make the isolation **persistent state** that re-applies after every rebuild while the view is active:

* `_isolate_scene_to_sensor_plane` now records the intent — `self._sensor_isolation_params` =
  `{center, normal, det_row, band}` as plain numbers, so it survives across rebuilt actor objects.
* New `_reapply_sensor_isolation_if_active()`: a no-op unless `_camera_preset == "sensor_normal"` and
  an isolation is recorded; otherwise it re-runs `_isolate_scene_to_sensor_plane` with the stored
  params and renders. Read via `getattr(self, "_camera_preset", …)` so it keys off the real preset.
* `refresh_scene` calls `_reapply_sensor_isolation_if_active()` after the service rebuilds (skipped on
  `reset_camera`, a full reframe = context change, not a toggle). **Every** overlay toggle routes
  through `refresh_scene`, so the fix is overlay-agnostic — Refs / Det / Miss / Clipped / Thickness /
  Focus surf / Distortion / Astigmatism / Spot map / Pixel grid / Illumination / Illum rays / Illum
  emission all preserve the isolation, satisfying "none of them should re-enable other elements."
* `_restore_sensor_isolation` (called at the top of `set_camera_preset`) now **also clears the
  intent**, so leaving the view via any cardinal / iso / nav-cube preset stops the re-apply and
  returns the full scene. Refactored the re-show into `_show_sensor_isolation_hidden` (re-show without
  forgetting the intent) so `_isolate` can clean-slate a re-invoke without dropping persistence.

## Verification

Guard `validate_open3d_normal_to_sensor_isolation` extended (phase **245** updated in place,
display-free stub actors, no renderer/Tk). Adds a **RE-APPLY** block on top of the existing
ISOLATE / RESTORE / RE-INVOKE:

* **REBUILD** — a freshly rebuilt stub scene starts fully visible (models the overlay toggle).
* **REAPPLY** — `_reapply_sensor_isolation_if_active()` re-hides the four off-plane props, keeps the
  detector + two coplanar overlays, and renders.
* **INTENT-CLEAR** — after `_restore_sensor_isolation` a later rebuild + reapply is inert (leaving the
  view really leaves).
* **PRESET-GUARD** — with the params still recorded but the camera preset no longer `sensor_normal`,
  reapply is a no-op (ordinary refreshes in other views are untouched).

Baseline title for 245 updated to "Normal to Sensor isolates the detector and survives overlay
toggles" (still pass).

## Notes

* **In-app eyeball owed.** The headless guard locks the re-apply/clear/guard *logic*; the running
  vendor-STEP scene still owes a visual check that toggling each overlay in the Normal-to-Sensor view
  keeps the sensor alone, and that clicking another view brings the full scene back.
* Sibling flag `flag_20260709_150933_595` ("still seems 4 sided dark edges to me") is the separate
  4-dark question (bugs/0278 note) — the user's pushback on the radial-vignette read; tracked apart,
  needs a real-scene repro, not a display fix.
