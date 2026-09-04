# 0718 — "the program seems freezing" after a forced FOV solve

Flag: `attachment/after_crash_solve.png` (flag 161212, second form). After Force FOV
(0717) applied the rigid lens-into-mirror move correctly — the banner read
"30.44 mm clearance to RA mirror 1", vendor hardware intact — the app **hung**: the
user could not even flag it live.

## Root cause

The freeze is a **preview ray trace on the deliberately-crashed geometry that never
returns**, blocking the Tk UI thread. Diagnosed with a `faulthandler` watchdog +
durable per-step log; the definitive stuck main-thread leaf on the om05a (folded,
non-sequential) scene is:

```
solve_fov_to_inspection_face(force=True)
 -> refresh_plot(defer_trace=True)
   -> plot_refresh.py:251 _refresh_3d_inspector_if_open        # called UNCONDITIONALLY
     -> open3d_trace_refresh.current_or_rebuild_scene
       -> _build_preview_system_rays_bundle(trace_rays=True)   # <-- traces anyway
         -> _trace_preview_rays_folded_aware -> _trace_preview_bundles
           -> NsTraceLoop -> NsTrace -> InterNormal -> mesh_cell_normals   # WEDGED
```

The key mechanism: `refresh_plot(defer_trace=True)` correctly defers the **2D** trace
(sets `rays=None`), but then hands `system` + `rays=None` to
`_refresh_3d_inspector_if_open`. In `current_or_rebuild_scene`, `rays is None` is read
as "no products supplied — rebuild FRESH", so it calls
`_build_preview_system_rays_bundle()` with the default `trace_rays=True` and runs a
full trace. On the forced collision (lens *inside* the RA mirror) the **in-process,
non-sequential** `NsTraceLoop` wedges in the mesh ray loop and never returns. `defer_trace`
never reached the 3D path.

Two aggravating triggers on the same geometry, also removed: the force short-circuit
called `snap_detector_to_image_plane()` (a best-focus trace), and `_sync_table`'s
auto image-diameter fires its own temporary trace.

Note on the executor: a folded / non-sequential scene traces **in-process**
(`NsTraceLoop`), NOT through the `ProcessPoolExecutor`, so a `.result()` timeout cannot
save it — a C-level trace cannot be interrupted. The executor timeout below is a
complementary net for the *sequential* parallel path; the DEFER gate is what protects
the folded/NS path.

### A test-harness red herring, recorded so it is not re-hit

The analysis executor uses `mp_context("spawn")`. A headless repro script WITHOUT an
`if __name__ == "__main__":` guard makes every spawned worker re-import `__main__`
and **re-run the whole script**, recursively spawning more workers — a fork-bomb that
*looks* like the freeze but is the harness, not the app. Every 0718 headless test
MUST carry the `__main__` guard. The real GUI never hits this (its workers re-import
KrakenOS, not a throwaway script).

## Fix

Belt and suspenders, because the force exists to SHOW a geometric collision, not to
produce a valid trace ([[feedback_no_silent_solve_failure]]):

1. **Defer the trace on force** (targeted — the trace never even starts).
   - `quick_estimation.py` force short-circuit: drop `snap_detector_to_image_plane()`;
     set `editor._preview_trace_deferred_until_requested = True` +
     `_invalidate_preview_scene_trace()`. The fast-load gate (bugs/0646) then makes
     `_traced_image_diameter_value` return None (no temporary trace) and the auto
     diameter falls back to the analytic estimate.
   - `layout_table_workbench.solve_fov_to_inspection_face`: the post-solve redraw is
     `refresh_plot(defer_trace=bool(force and ok))` — bodies only on a forced solve.
   - **`open3d_trace_refresh.current_or_rebuild_scene` (the fix that actually stopped
     the freeze):** when the fast-load gate is set, rebuild the 3D scene BODIES ONLY
     (`_build_preview_system_rays_bundle(trace_rays=not deferred)`). This is what makes
     `defer_trace` reach the 3D inspector; without it the 3D rebuild traced regardless.
   The user presses **Trace Now** to trace the valid geometry deliberately (which
   clears the gate first, per bugs/0646).

2. **Bound every parallel preview trace** (general safety net — ANY runaway trace,
   from any entry point, recovers). `trace_preview._trace_preview_bundles` now waits
   on `future.result(timeout=…)` against a shared 90 s deadline
   (`_PREVIEW_TRACE_RESULT_BUDGET_SECONDS`). On timeout it abandons the remaining
   chunks (same bad system), the `finally` calls `_shutdown_analysis_executor()`
   which force-terminates/kills the wedged workers, and the preview degrades to
   "no rays" with a logged note. 90 s never trips on a legitimate preview slice
   (seconds, even with cold spawn workers); a timeout only ever means a hang.

The serial in-process backends (`Kos.TraceLoop` / `BatchTraceLoop`) cannot be
timed out (a C call cannot be interrupted without killing the process), so the
DEFER gate is what protects them; the executor timeout protects the parallel path.

## Verify

`freeze_valid.py` (`__main__`-guarded): load om05a_folded_80mm, resize device to
15×15×1 (far off-conjugate), open 3D, `solve_fov_to_inspection_face(fov=21, force=True)`,
then the 2D + 3D refreshes that froze — must COMPLETE in bounded time, not hang.

Penta phase 517 (`validate_open3d_0718_force_solve_freeze.py`): pins the timeout
constant + `future.result(timeout=` + `_futures.TimeoutError` handling +
`_shutdown_analysis_executor` teardown, the force-path defer edits, and the
`__main__`-guard lesson.
