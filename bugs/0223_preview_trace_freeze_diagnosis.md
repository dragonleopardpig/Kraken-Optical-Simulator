# 0223 — STEP import / preview-trace "long duration" freeze: diagnosis + fix plan

**Status: DIAGNOSED, not yet fixed.** Root cause pinned with measured timings. The *correct* fix
(move the trace off the Tk main thread) keeps behaviour identical and only needs in-app verification;
it is NOT applied here because the freeze-gone can't be proven headless (the validator SIGSEGVs on
llvmpipe) and the tempting shortcut (reuse the cache for promoted solids) reverses a **deliberate
correctness guard** — see "Why the easy cache fix is unsafe" below. This doc makes the fix a small,
safe, in-app-verifiable job.

## The request

`flag_20260703_145107_735`: "it still take long duration to import and placed." The recorded bundle
logged `elapsed_ms ≈ 93,660` (**93.6 s**) for an import + place. Tracked as task #78 ("preview-trace
freeze, off-UI-thread / cache").

## Diagnosis (measured, not guessed)

The STEP *tessellation* is NOT the bottleneck — it is disk-cached (`load_step_mesh_done` avg **85.6
ms**, analytic-disk-cache hit). The cost is a **synchronous full non-sequential ray re-trace + full
VTK scene rebuild that runs on the Tk main thread on every refresh**, repeated several times.

Call chain (import → placed actor):
- `services/step_overlay_import.py:153` `import_optical_step` → `_invalidate_preview_scene_trace()`
  (:186) → `_refresh_open_3d_views(step_label="optical")` (:196).
- Placement/drag (debounced 180 ms, `services/open3d_live_refresh.py:8-11,60`) → `inspector.after(…)`
  → `_refresh_live_preview_scene` → `refresh_from_editor` (`open3d_inspector.py:13061`).
- `refresh_from_editor` → `build_inspector_refresh` (`services/open3d_trace_refresh.py:266`) →
  **cache gate at :281-288** → `_build_preview_system_rays_bundle`
  (`services/three_d_scene_tools.py:482`) → `_trace_preview_rays_folded_aware` → `Kos.NsTraceLoop`
  (`services/trace_preview.py:463`) → `_build_scene_bundle`.
- Result applied on the main thread: `refresh_scene` (VTK `RemoveAllViewProps` + rebuild every ray
  actor), `services/open3d_scene_refresh.py:1203`.

Measured (from `~/.cache/krakenos/logs/open3d_timing_latest.jsonl`, a real run of this exact scenario):
one `refresh_from_editor` = **11,033 ms**:
- `build_inspector_refresh` **7,015 ms** → `_build_preview_system_rays_bundle` **7,001 ms**:
  - `preview_trace_rays` **3,241 ms** (`trace_preview_bundles` **3,135 ms** = the `NsTraceLoop` mesh
    trace, 9 bundles ~335 ms each)
  - `preview_build_scene_bundle` **1,816 ms**
  - `preview_saved_step_native_rows` **995 ms** + step-overlay bake ~**1,000 ms**
- `refresh_scene` (VTK actor rebuild, **3,249 ray actors**) ≈ **3,970 ms**.

That single refresh is followed by **4 more full VTK rebuilds** (`refresh_scene_timing` n=5, total
**16,710 ms**) and **2,673 `render_done` = 68,793 ms cumulative** (~25 ms each because the scene
carries 3,249 individual ray actors). All on the UI thread → the "freeze"/"long duration".

**Why every refresh re-traces:** `open3d_trace_refresh.py:281` sets
`requires_open3d_retrace = include_live_step_overlays or has_promoted_step_optical_solid_rows()`, and
:284 consults the trace-result cache (`_current_preview_scene_trace()`) only when
`not requires_open3d_retrace`. The bug scene has a promoted BK7 solid **and** a live optical overlay
with `show_rays:true` → the cache is never consulted → every selection / highlight / camera / show-rays
refresh re-runs the full ~7 s trace + rebuild. (`current_or_rebuild_scene` at :351-381 has the same
bypass.)

## Why the easy cache fix is unsafe (the trap)

The obvious fix — "a promoted solid's pose is in the signature, so consult the cache anyway" — reverses
a **deliberate** contract. `validate_3d_interaction_contract.py` pins a check literally titled **"Open
3D initial refresh retraces promoted STEP optical solids"** (asserting the `requires_open3d_retrace =
… or has_promoted_step_optical_solid_rows()` structure in both gates). The forced retrace exists so a
change the trace *signature may not fully capture* — the promotion itself, a face-assignment, a coating
edit on the promoted solid — cannot serve a **stale** cached scene. Direct testing confirms the cache
reader `_current_preview_scene_trace()` correctly invalidates on `_preview_scene_trace_dirty` and on a
thickness edit (signature change) — but I cannot prove headless that *every* promoted-solid mutation
flips one of those, and the guard's existence says someone hit a case where it didn't. So reversing the
retrace is a real stale-scene risk that is unverifiable headless. **Do not take the cache shortcut
without auditing signature-completeness for promoted-solid edits in-app.**

## Recommended fix (safe, keeps correctness)

**Fix A — move the trace off the Tk main thread (the task's "off-UI-thread").** This keeps the retrace
(so the correctness contract above is untouched) and only removes the *freeze*. Run the pure-compute
core of `_build_preview_system_rays_bundle` (`three_d_scene_tools.py:507-572`: `build_system` +
`NsTraceLoop` + `_build_scene_bundle`) in a worker thread on a **snapshot** of `self.rows`, then marshal
`(system, rays, scene_bundle)` back via `inspector.after(0, apply)` to do the VTK `refresh_scene` on the
main thread. Established precedent to copy: the async STEP-display cache warm-up
`_start_open3d_step_cache_warmup` / `_poll_open3d_step_cache_warmup` (`three_d_scene_tools.py:282,356`).
Keep `append_debug` (:612) and the state writes (:613-619) on the main thread. Show a "Tracing…" badge
while it runs. Risk: medium (must snapshot rows [mutated at :523-525]); Impact: converts the 11 s freeze
into a responsive background job. **Needs in-app verification** (the freeze-gone + no display tearing).

**Fix B — reduce the ray-actor count.** 3,249 individual ray actors cost ~68 s of cumulative
re-rendering (25 ms × 2,673 renders). Consolidating the on-axis/field rays into a few `vtkPolyData`
line actors (one per field or per branch) instead of one actor per ray would cut per-render cost by
~100×, helping every subsequent camera move / interaction — independent of the trace. Risk: medium
(picking/highlighting currently keys off per-ray actors — check `_actor_ray_map`); verify ray-select
still works.

**Fix C — cache the live-overlay trace (only for the exact flagged scene).** `three_d_scene_tools.py:613`
refuses to cache when `include_live_step_overlays=True`, so re-placing the same overlay at the same pose
re-traces the full 7 s. Cache it keyed on `(label, pose-offset, _preview_trace_signature)`, invalidated
where `_live_step_overlay_trace_plan_cache` already resets (`step_overlay_import.py:91,185,229,269`).
Risk: medium (correct invalidation on every pose/rotation nudge). This one, unlike the promoted-solid
cache, is lower-correctness-risk because the overlay pose is the only variable.

Recommended order: **A first** (kills the freeze without correctness risk), then **B** (cheap, broad
win), then **C** if placement fiddling is still slow.

## Implementation findings (2026-07-05) — a naive thread will NOT work; the safe win is Fix B

Attempting Fix A surfaced obstacles the initial plan missed (all verified headless):

- **The trace is a per-ray PYTHON loop** (`TraceLoopTool.py:107` `for i in range(0, len(x)): System.Trace(...)`),
  not a vectorised numpy batch. A Python **thread** holds the GIL through that loop, so it would NOT
  free the Tk main loop — the freeze would remain. Only a **subprocess** (separate interpreter/GIL)
  truly offloads it. (This is exactly why the existing precedent `warm_open3d_step_cache` is a
  subprocess, not a thread.)
- **A subprocess can't return the result cleanly.** The `system` object does **not** pickle
  (`_install_build_hook.<locals>.build_with_output_ports` — a local closure), yet `refresh_scene`
  needs `system`. And the picklable parts are **huge**: `scene_bundle` ≈ 49 MB + `rays` ≈ 72 MB ≈
  **121 MB** to serialise across the process boundary per trace (~1-2 s of pickle/IPC, eating into the
  saving). A subprocess path therefore also has to **rebuild `system` on the main thread** (a small
  residual freeze) after receiving the trace.
- **Good news for isolation:** two independent editors tracing the same scene produce a **byte-identical
  bundle** (detector + all 3,249 ray endpoints match), and the only KrakenOS module global on the trace
  path is the read-only `fraunhofer` constant — so running the trace on a snapshot editor is
  deterministic and free of shared mutable state (whichever offload mechanism is used).

**Revised recommendation.** Do **Fix B first** (consolidate the 3,249 per-ray actors → a few polyline
actors). It is a pure display change — no threading, no GIL, no serialisation — removes the ~4 s VTK
rebuild and the dominant ~68 s cumulative render cost, and is headless-verifiable (actor count + a
render snapshot). It is the biggest safe win. The off-thread trace, if still wanted after Fix B, should
be the **subprocess** variant (trace in a child → return `rays` + `scene_bundle` → rebuild `system` +
`refresh_scene` on the main thread), accepting the ~121 MB serialisation; a thread is not worth building
because the GIL negates it.

## Fix B IMPLEMENTED (2026-07-05) — ray-actor consolidation

Shipped the ray-actor merge. `_add_ray_actor` now DEFERS each pickable ray into `_pending_ray_specs`;
`_flush_merged_ray_actors()` (called once after each ray-build loop in `open3d_scene_refresh.py`) groups
them by `(color, opacity, line_width)` and builds ONE `vtkPolyData` actor per style via
`vtkAppendPolyData`. Picking a merged actor resolves the ray from the picked cell
(`_merged_ray_cell_index[actor_key][cell_id]`, via the new `_ray_index_for_actor` used by the three pick
consumers — `interaction_event`, `interaction`, `debug_tools`). The selection highlight is now a bright
OVERLAY actor (`_apply_ray_highlight_overlay`, `apply_ray_selection` rewritten) because a merged actor
can't recolour one of its rays. `_ray_actor_map` stays keyed by ray_index (so ray-count/"still visible"
checks are unchanged); `_clear_merged_ray_state()` drops the new maps + overlay on every rebuild.

Headless-verified: on the two-mirror AZ85 cone the scene drops from **3,249 ray actors to 8** (one per
field colour), every ray stays cell-pickable (cell0→ray0, mid→ray2888 resolve correctly), all 3,249
rays keep display points for the overlay, and an offscreen render shows the folded П-path intact in all
8 colours. Unit test: 5 rays / 2 styles → 2 actors, cell→ray exact, out-of-range + non-ray → None.

**In-app verification still owed** for the INTERACTIVE paths (only observable in the app): (a) click a
ray → it selects + the bright overlay draws on the right ray; (b) hover a ray; (c) the ray-inspector /
debug pick reports the correct ray_index; (d) show-rays toggle + a live placement drag still render
rays; (e) the freeze is visibly reduced. If cell-pick feels off, the likely culprit is a stale picker
cell in `_ray_index_for_actor` (it falls back to the live `self._picker.GetCellId()`); pass `cell_id`
explicitly at that call site.

## Fix A (subprocess off-thread trace) — findings + remaining friction (2026-07-05)

Prototyped the subprocess path headlessly. It is VIABLE but larger + more fragile than hoped; net win
is partial. Findings:

- **The trace IS reproducible from a serialized scene.** Pickling `{specs, settings}` → rebuilding rows
  (`_row_from_layout_item`) → `_snapshot_editor` → `_build_preview_system_rays_bundle` reproduces the
  bundle deterministically (two independent editors already trace byte-identical). So a worker process
  can trace from a serialized scene.
- **Friction 1 — the snapshot editor recurses on lazy caches.** `_snapshot_editor` builds via `__new__`
  (no `self.tk`), so the trace path's `getattr(self, "_saved_step_native_trace_plan_cache", {})` (and
  likely other lazy caches) hits tkinter's `__getattr__` → `RecursionError` — the SAME class as the
  Phase 92 bug (`_optical_led_glued`). The worker must seed every lazy cache the trace reads (or the
  trace path must stop deriving them from a Tk-widget editor). Whack-a-mole risk.
- **Friction 2 — `system` is unpicklable** (a local closure build-hook) yet `refresh_scene` needs it →
  the worker returns `rays` + `scene_bundle` (both pickle) and the MAIN thread rebuilds `system` from
  specs (`build_system` ≈ 0.4 s — cheap).
- **Friction 3 — ~121 MB result** (`scene_bundle` 49 MB + `rays` 72 MB) to serialise back per trace
  (~1–2 s pickle/IPC).
- **Net win is partial.** Session log: refresh = ~10 s = ~6.7 s trace (`preview_trace_rays` 4.3 s +
  `preview_build_scene_bundle` 2.3 s) + ~3.3 s apply (`refresh_scene` 2.3 s + `ray_actor_ms` 1.3 s ray
  MESH construction, which stays on the main thread). Off-threading the 6.7 s trace + ~2 s deserialise
  leaves a ~3.5 s main-thread apply. So the freeze drops ~10 s → ~3.5 s — real, but not gone. (Fix B
  cuts the per-frame render, not this apply-time mesh build.)

### Session-2 progress (2026-07-05) — recursion ROOT-FIXED; a cleaner architecture found

- **DONE, committed (`2c426776`): the `__new__` snapshot-editor recursion is root-fixed** — `_snapshot_editor`
  now sets `editor.tk = object()`, so tkinter's `__getattr__` raises `AttributeError` (→ getattr default)
  instead of recursing on ANY missing attribute. No more per-cache whack-a-mole; a headless worker can
  now trace a promoted-STEP folded scene. All snapshot-editor guards stay green.
- **Verified: a serialized scene traces in a rebuilt editor** — `{specs}` → `_row_from_layout_item` →
  `_snapshot_editor` → `_build_preview_system_rays_bundle` runs without error and lands the detector at
  the right place.
- **BUT — fidelity gap.** The rebuilt editor did NOT reproduce the same ray COUNT (33 sparse rays vs the
  real 3,249-ray cone), because the sampling density lives in editor state that `{specs, sampling_mode,
  wavelength}` doesn't fully carry. Replicating an editor faithfully enough to reproduce the exact trace
  is fragile.

**Revised architecture (do this instead of replicating the editor): off-thread only the `NsTraceLoop`,
passing EXPLICIT launch rays.** The main thread already owns the exact sampling; split the trace so:
1. Main: `build_system` (~0.4 s) + compute the launch-ray arrays (the pupil/field sampling — fast,
   deterministic, no fidelity question). This needs a small refactor of `_trace_preview_rays` /
   `_trace_preview_rays_folded_aware` (`three_d_scene_tools.py:622`) to expose the launch arrays instead
   of computing-and-tracing in one call.
2. Worker: rebuild `system` from specs (unpicklable, so rebuilt not shipped) + run `NsTraceLoop` on the
   passed launch arrays [+ optionally `_build_scene_bundle`] → return the traced ray arrays.
3. Transfer via **shared memory** (`multiprocessing.shared_memory` + numpy views) — the launch arrays in,
   the traced arrays out, **zero-copy**, no 121 MB pickle. (A database is the wrong tool for these bulk
   numeric arrays; shared memory is the right "fast data" layer — see the design discussion.)
4. Main: `_build_scene_bundle` (or use the worker's) + `refresh_scene`, with a trace-signature re-check
   to discard a result whose scene changed mid-trace, and a "Tracing…" badge meanwhile.

This sidesteps the editor-fidelity problem entirely (the exact rays are specified by the caller) and
moves the ~4.3 s `NsTraceLoop` off the UI thread. **Remaining work** (focused session, task #78): the
sampling/trace split refactor, the shared-memory channel, and the main-thread orchestration. Net freeze
target: ~10 s → ~3–4 s (the VTK apply stays on main; Fix B already trims its render).

## Verification owed (in-app)

Per task #78 and the validator SIGSEGV, the freeze-gone can only be confirmed in-app: import + place a
STEP on the `attachment/machine_vision_150mm_test.py`-style scene with Show Rays on, confirm the UI stays
responsive (no multi-second lock), the displayed rays/scene are correct after each nudge, and the
`open3d_timing_latest.jsonl` `refresh_from_editor` wall-time drops. A headless guard can assert the trace
core is callable off-thread on a rows snapshot and returns the same bundle as the inline path, but not
the freeze itself.

## Related

- The 2D-analysis-vs-Open3D cache machinery is sound (`_current_preview_scene_trace` +
  `preview_trace_signature_matches` + `_preview_scene_trace_dirty`); the issue is purely that the
  promoted/overlay scenes bypass it AND that the trace is synchronous.
- Existing perf guards: `validate_open3d_action_timing` (STEP *display* warm-up is async + hidden-ray
  drop doesn't retrace), `validate_open3d_live_performance_budget` (debounce delays only),
  `validate_nonseq_decimated_trace_proxy` (planar-solid trace proxy — a curved imported lens can't be
  decimated, so it pays the full ~3.1 s trace). None asserts an off-thread trace or a wall-time budget
  on `refresh_from_editor` — add one alongside Fix A.
