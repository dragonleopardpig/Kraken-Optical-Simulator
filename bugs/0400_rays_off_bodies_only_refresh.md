# 0400 — with Show Rays OFF, a model change must not run the ray trace

**Flag:** `flag_20260722_095136_693` — "… super long time wasted for unnecessary ray tracing.
With Ray Off, there shouldn't be any ray tracing, just add the BS and let user manipulate it
just like a normal CAD software."

## Root cause

Adding/moving a promoted optical solid on the folded AZ85 scene forced a full ~45 s ray trace
**even with Show Rays OFF**. The 3D refresh always retraces when the scene has promoted step
optical-solid rows (`open3d_trace_refresh.py`: `requires_open3d_retrace = ... or
has_promoted_step_optical_solid_rows()`), and the async path (`trace_preview_async`) kicked the
same trace in a worker (`reason: kicked`, `56.7 s`). The build conflated **rebuilding the bodies**
(needed for display) with **tracing the rays** (needed only when they're shown).

## Fix

Separate the two. `_build_preview_system_rays_bundle` gains `trace_rays: bool = True`; when
False it runs `build_system` + `_build_scene_bundle` (the BODIES) but SKIPS
`_trace_preview_rays_folded_aware` (the ~45 s step), keeping an empty raykeeper so the bundle
assembles bodies with no ray polylines. Both refresh paths now gate on Show Rays:

- **Sync** (`build_inspector_refresh`): `trace_rays = physics_requested or show_rays`, threaded
  into the bundle build.
- **Async** (`maybe_begin_inspector_async_trace`): returns `rays_off_bodies_only` when Show Rays
  is off and no live physics, so it falls to the sync bodies-only path instead of kicking the
  background trace.

A bodies-only build marks `_preview_scene_trace_dirty = True`, so
`can_reuse_current_scene_for_show_rays` refuses to reuse the empty-ray cache — turning Show Rays
**on** forces a full rebuild that actually traces. Live physics (Live Mode / Trace Now) always
traces, unchanged.

## Verification (`validate_open3d_rays_off_bodies_only_refresh`, penta phase 328)

On the real AZ85 folded scene:

| | ray_paths | bodies | trace | trace-dirty |
|---|---|---|---|---|
| `trace_rays=False` (rays OFF) | **0** | 2 | **2.1 s** | True |
| `trace_rays=True` (rays ON) | 3249 | 2 | 34.2 s | False |

**16.4× faster** with rays off, bodies present in both. The async gate returns
`began=False` with rays off; `can_reuse_current_scene_for_show_rays` returns False while dirty
(so rays-on retraces). The traced path is byte-for-byte unchanged.

## Files

- `KrakenOS/UI/services/three_d_scene_tools.py` — `trace_rays` gate + trace-dirty on bodies-only.
- `KrakenOS/UI/services/open3d_trace_refresh.py` — thread `trace_rays` from Show Rays.
- `KrakenOS/UI/services/trace_preview_async.py` — skip the async trace when rays are off.
- `KrakenOS/UI/validate_open3d_rays_off_bodies_only_refresh.py` — guard (phase 328).

## Scope / next

This is the first concrete piece of the CAD-smoothness goal. Follow-ups: defer the trace on
drag/move (mouse-up only), and a broader `_apply_model_change` audit so *every* rays-off model
change is geometry-only.

## In-app eyeball still owed

With Show Rays off, add/move a BS — it should appear and be manipulable immediately (no trace
badge, no freeze); turning Show Rays on should then trace once.
