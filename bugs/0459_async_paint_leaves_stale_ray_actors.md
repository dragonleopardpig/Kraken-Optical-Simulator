# 0459 — the async refresh leaves STALE ray actors, so the drawn beam stops short

`flag_20260728_160708` ("still the same.", build `ee21598b` — i.e. WITH the 0457 fix). The user
reopened `machine_vision_AZ85_RA_Mirror_BS.py` and the beam still visibly dies just past the lens,
never crossing to the fold mirror or the sensor.

## What is already correct (0457 shipped and works)

* the flag's own state shows **row 8 (Image) at (228.7, 0.0, 2.7)** — coincident with the camera
  body and the reached-image detector. Before the fix it was **−48.8**.
* the app HAD the fix: process started 16:04:44, commit `ee21598b` landed 15:13:16.
* headless, in BOTH sampling modes, every drawn ray record reaches the mirror:

    | sampling mode | display records | max-x median | reach past x=200 | statuses |
    |---|---|---|---|---|
    | `world_envelope` | 174 | 229.2 | **174/174** | 167 hit_detector, 7 escaped |
    | `world_cone` | 2449 | 228.7 | **2449/2449** | 2381 hit_detector, 68 escaped |

So the physics and the synchronous display are both right. What the user sees is not.

## The defect

Driving the LIVE path (`open_3d_view` → `refresh_from_editor()` **without** `force_retrace`, i.e.
async-eligible, then pumping Tk) reproduces the flag exactly:

    actor_ray_map = 12        <- the flag reports ray_actor_count = 12
    actor_by_key  = 82
    every one of the 12 ray-actor keys: NOT in actor_by_key

The ray-actor registry still holds **12 keys from a previous build**, none of which resolve to a
live actor. The synchronous path produces 174. So after the async kick, `_actor_ray_map` is not
rebuilt in step with `_actor_by_key`, and the rays left on screen are the ones painted before the
worker's result arrived — bugs/0450 records that the async kick deliberately paints BODIES
synchronously and lets "the worker's rays replace this scene when they arrive". Here that
replacement leaves the map pointing at dead actors.

Same invariant as the 0248/0296/0298 "2-D is stale" family and the 0451 actor work: **no actor (or
actor key) may outlive the geometry that justified it.**

## Repro

`/tmp/.../async_rays.py`: load the BS scene, `open_3d_view()`, `refresh_from_editor()` (async
path — NOT `force_retrace=True`, which is synchronous and healthy), pump Tk, then resolve every
`_actor_ray_map` key against `_actor_by_key`. All 12 fail to resolve.

Contrast: `refresh_from_editor(force_retrace=True, geometry_changed=True)` yields 174 ray records
that all reach the sensor.

## Fix shape (not yet attempted)

Rebuild — or clear — `_actor_ray_map` / `_ray_actor_map` whenever the actor set is replaced, so a
stale key can never be resolved or counted. Then confirm the async path paints the same 174 rays
the synchronous path does.

**Acceptance test:** after an ASYNC refresh, every `_actor_ray_map` key resolves in
`_actor_by_key`, and the visible ray actors reach x > 200 (the fold mirror at 228.7) — matching the
synchronous path.

**User-visible check meanwhile:** toggling Show Rays off/on forces a synchronous repaint, which
should draw the full beam to the sensor. If it does, that confirms this diagnosis from the UI side.
