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


## Refinement: the async COMPLETION path is not the bug -- the delivery is

`_poll_inspector_async_trace` applies its result through
`inspector.refresh_scene(system, rays, row_names, scene_bundle=..., reset_camera=False)` -- the
SAME full path that clears `_actor_ray_map` / `_ray_actor_map` / `_actor_by_key`. So if the worker
delivers, the maps are rebuilt correctly and there is nothing stale.

The stale 12 keys therefore mean the worker had **not delivered** at the moment of measurement --
the scene on screen is still the pre-worker paint (bugs/0450 has the async kick paint BODIES
synchronously so a geometry change is visible immediately, and lets the worker's rays replace the
scene when they arrive).

A follow-up probe that waits up to 400 s for delivery produced **no output at all** and was killed
by its timeout, i.e. `refresh_from_editor()` (async-eligible) blocked and never returned control to
the poll loop. For contrast, a SYNCHRONOUS trace of this same scene completes comfortably inside a
minute (every measurement in bugs/0457 used it).

So the question for 0459 is no longer "why is the map stale" but:

**why does the async path for this scene never deliver (or block on kick), when the synchronous
trace of the same scene is fast?**

Look at, in order:
1. `maybe_begin_inspector_async_trace` -- the capture step runs the sampling on the main thread
   (`_preview_trace_bundle_capture`); if capture itself is heavy or re-enters, the kick blocks.
2. the worker subprocess: does it start, and does it ever post a result? `_record_async_worker_outcome`
   records `applied` / `stale_rekick_exhausted` / failures -- capture that string.
3. the `stale` + `rekicks` loop above the apply: two rekicks then `_fallback_sync_refresh`; if the
   BS scene keeps looking stale, it could rekick indefinitely without ever painting rays.

**User-visible workaround stands:** toggling Show Rays off/on forces the synchronous repaint, which
draws the full beam (174 records reaching the sensor headless).


## Round 2 evidence (6-flag walkthrough, build `6e0efacd`) -- staleness is NOT the whole story

The user rebuilt the entire workflow on the fixed build and flagged each step:
`original` -> `1st RA mirror deleted` -> `BS plate added, resized, repositioned` ->
`rubberband select + Optical axis snapping of Imaging Lens, 2nd RA mirror and Camera` ->
`STEP hidden` -> `Rays ON`.

**The 0457 fix holds through all of it.** Final state:

    row 8 (Image)  [228.5, 0.0, 2.3]
    detector 100000 (reached_image) [228.5, 0.0, 2.3]      <- coincident
    camera body     [228.5, 0.0, 2.3]                      <- coincident
    rows 1-7 along +X at z = 53.8

No trace of the -48.77 error anywhere in the walkthrough.

**But the drawn beam still stops at the last lens element** (screenshot of `Rays ON`): it folds at
the BS, crosses all four lens elements, and ends there -- never reaching the fold mirror at
x = 228.5 or the sensor.

Crucially, that flag is titled **"Rays ON"** -- a FRESH toggle, i.e. the synchronous repaint this
document proposed as the workaround. It still truncates. So the "stale pre-worker paint" theory
above does NOT explain the live behaviour on its own, and the workaround does not work.

Yet headless, the same scene draws to the sensor in both sampling modes
(`world_envelope` 174/174 reaching past x=200, `world_cone` 2449/2449). So the divergence is
LIVE-ONLY and survives a synchronous repaint.

**What that leaves:** something in the live inspector's ray-display path truncates polylines that
the editor-level bundle carries in full. Next probe should compare, IN ONE live session, the
polylines in `inspector._current_scene_bundle.ray_paths` against the vertices actually handed to
the ray actors -- i.e. instrument the ray-actor construction the way `_add_mesh_actor` was
instrumented for bugs/0457, and find where the tail vertices are dropped. Do NOT theorise about
async vs sync again; measure the polyline going into the actor.

Also visible in the same screenshot and worth deciding: THREE "Sensor 23.0x23.0 / Image circle"
label pairs -- the real sensor plus the two mid-scene branch arms at (74.3, 31.3) and
(-0.5, 68.4). Per the agreed rule (sensor iconography follows CAMERA REGISTRATION, not leaf count)
only the arm carrying the camera should draw sensor dimensions; the others should draw at most a
neutral plane.
