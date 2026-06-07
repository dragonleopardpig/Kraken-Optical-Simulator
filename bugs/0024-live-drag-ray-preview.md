# 0024 — Live ray preview while dragging an element (Live Mode)

**Status:** Implemented (2026-06-07). Enhancement, not a defect fix.
**Component:** Open 3D placement drag + Live Mode trace
(`KrakenOS/UI/open3d_inspector.py`,
`KrakenOS/UI/services/open3d_scene_refresh.py`,
`KrakenOS/UI/services/trace_preview_sampling.py`).
**Reported via:** the user — "when I start dragging the beam splitter, can I see in
Live the ray reaction immediately?"

## Background

The placement-move drag (bugs/0012) moves the body + handles with a cheap actor
transform (no retrace) and defers the ray trace to release, because a full
retrace on the heavy machine-vision scene is ~8 s. So dragging an element showed
the body slide but the rays only updated on release. The user wanted the rays to
react *during* the drag.

A full live retrace per step is ~8 s — unusable. Two profiled facts shaped the
fix: the cost is **~6 s trace (558 rays) + ~2 s scene rebuild**; and an
incremental "only retrace the rays the element touches" approach does not help
the common case (an element *in* the beam touches every ray — measured 100%), so
the lever is fewer rays + skipping the body rebuild.

## Implementation

Gated entirely on **Live Mode** (opt-in; off by default keeps the bugs/0012
deferred behaviour):

* **Sparse fan during the drag** — `_current_ray_count` honours a new
  `_drag_preview_ray_count_override` (3) that the drag sets, so the live trace
  uses a sparse fan instead of the full 558-ray bundle. `_finish_placement_drag`
  clears it so the on-release commit retraces full fidelity.
* **Schedule a debounced live trace** — `_apply_placement_drag_motion` calls
  `schedule_live_refresh("placement drag")` (the existing ~180 ms debounce) when
  Live Mode is on.
* **Flush the drag into the model** — `_refresh_live_preview_scene` first calls
  `_flush_pending_placement_drag_for_live`, committing the accumulated drag offset
  (model-only) so the trace reflects the dragged pose; the body already sits there
  via the cheap transform.
* **Rays-only refresh** — during an active drag, `_refresh_live_preview_scene`
  calls the new `_refresh_rays_only` instead of `refresh_scene`: it removes and
  redraws only the ray actors, leaving every body / handle / overlay actor in
  place (they don't change). This skips the ~2 s scene rebuild.

## Result

Measured on machine-vision: the live drag preview went from **~8 s to ~1.2 s per
update (~0.8/sec)** — a ~6.5× improvement. The body slides smoothly via the cheap
transform; the rays catch up about once a second; the full 558-ray bundle is
restored on release.

The remaining ~1.2 s is `build_live_preview` **rebuilding the KrakenOS optical
system from the rows every step (~0.7 s)** plus the model-commit flush (~0.3 s).
Reaching truly-immediate (~3/sec) would require an **incremental system update**
(updating only the dragged surface's transform in the existing system rather than
reconstructing it) — a deeper change into Prerequisites3D, deferred as a separate
effort.

## Tests

`KrakenOS/UI/validate_open3d_live_drag_ray_preview.py` — source contracts (the ray
count honours the drag override; the drag sets the override + schedules a live
refresh; the live preview flushes the drag and uses the rays-only path; release
clears the override) plus a render check (SKIP without the cube's source STEP):
with Live Mode on and a pending drag, the live preview moves the model, traces a
sparse fan, and refreshes **only** the ray actors — leaving the body actors in
place. Wired into the comprehensive harness as `Phase 33`.
