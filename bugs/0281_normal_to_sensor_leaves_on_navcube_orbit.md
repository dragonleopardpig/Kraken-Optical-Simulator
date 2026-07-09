# 0281 — leaving "Normal to Sensor" via the nav cube / mouse orbit must restore the full scene

## Symptom (flag_20260709_162334_323)

> "ISO view, all elements missing (except detector)."

A direct follow-up to bugs/0278 + bugs/0279. **Overlays ▸ Normal to Sensor** correctly isolates the
detector (0278) and holds through overlay toggles (0279). But when the user leaves that view by
**dragging the nav cube to an ISO corner** (or by a free **mouse orbit**) instead of clicking a
cardinal / ISO **preset button**, the scene comes back with *only the detector* — the LED plate, the
lens bodies, the ray polylines and the optical-axis guide all stay hidden.

## Root cause (`open3d_inspector.py`)

`_restore_sensor_isolation()` — the one call that re-shows the hidden props **and** clears the
isolation intent — was invoked from exactly one place: the top of `set_camera_preset`. So only the
cardinal / ISO **preset buttons** left the view cleanly.

The nav-cube snap (`_apply_navigation_cube_orientation` / `_apply_navigation_cube_step` →
`_on_navigation_cube_snap`) and a free mouse orbit both move the camera **without** going through
`set_camera_preset`; they funnel through `_on_camera_interaction`. Neither restored the isolation nor
reset `_camera_preset`. So after a nav-cube/orbit exit:

* the props stayed hidden (nobody re-showed them), and
* `_camera_preset` was still `"sensor_normal"` with `_sensor_isolation_params` still recorded, so
  bugs/0279's `_reapply_sensor_isolation_if_active` **re-hid** them on the very next refresh — the
  isolation was effectively sticky until a preset button was pressed.

## Fix

`_on_camera_interaction` is the single universal hook every free-camera gesture lands on — the mouse
orbit binds it to `InteractionEvent` / `EndInteractionEvent`, and `_on_navigation_cube_snap` calls it
explicitly after a cube pick. Add a leave-check there:

* New `_leave_sensor_normal_on_gesture(view_dir) -> bool`: when `_camera_preset == "sensor_normal"`
  and an isolation is recorded, and the sight line has **turned off** the sensor normal
  (`|cos(view_dir, normal)| < 0.999`), call `_restore_sensor_isolation()` and drop `_camera_preset` to
  `None` — exactly what a preset button already does. Returns `True` iff it left.
* `_on_camera_interaction` calls it first (using the live camera's `GetDirectionOfProjection()`), OR-ing
  the result into its existing `moved` flag so the scene re-renders with the props back.

The off-normal **gate** is what makes this safe:

* `view_normal_to_sensor` enters the view by setting the camera straight **down** the sensor normal and
  calling `render()` only (it does *not* fire `_on_camera_interaction`), so entry never self-cancels;
  and even a spurious face-on fire is inert (`|cos| ≈ 1 ≥ 0.999`).
* A **pure zoom** that stays face-on keeps the isolation — you only leave when you actually orbit away.
* It's one-shot: `_restore_sensor_isolation` nulls the intent, so later per-frame fires no-op.

Because the leave routes through `_on_camera_interaction` (not `refresh_scene`), it does **not** touch
the 0279 overlay-toggle path — toggles still re-apply the isolation while the view is active.

## Verification

New display-free guard `validate_open3d_normal_to_sensor_gesture_leave` (penta phase **247**), stub
actors, no renderer / Tk. Binds the real `_leave_sensor_normal_on_gesture` / `_isolate` / `_restore`
against the coaxial MV-150 stub scene (detector + 2 coplanar overlays at z=657 + 4 off-plane props):

* **TURN-AWAY** — an off-normal ISO sight line `(1,1,1)` leaves: the 4 props re-show, the intent is
  nulled, `_camera_preset` drops to `None`, returns `True`; a second call is a no-op (one-shot).
* **STAY** — a face-on pure zoom `(0,0,-1)` keeps the isolation: returns `False`, props stay hidden,
  intent + preset intact (why entering the view never self-cancels).
* **PRESET-GUARD** — inert when the camera is no longer on the `sensor_normal` preset.
* **NO-PARAMS** — inert on the `sensor_normal` preset with no isolation recorded.

The bugs/0279 guard (`validate_open3d_normal_to_sensor_isolation`, phase 245) still passes — the
overlay-toggle re-apply is unchanged. Baseline: phase/title **247** added (pass).

## Notes

* **In-app eyeball owed.** The headless guard locks the leave/stay/guard *logic*; the running
  vendor-STEP scene still owes a visual check — enter Normal-to-Sensor, drag the nav cube to ISO (and
  separately mouse-orbit away), confirm the LED / lens / rays / axis all return, and that a pure zoom
  while face-on still isolates.
