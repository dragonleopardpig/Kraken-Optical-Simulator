# 0646 — Slow .py load: rays and the 0625 re-measure deferred to "Trace Now" / first consumer

**User (2026-08-24):** "the loading of a .py file take super long time, can't you just
freeze the ray first, or don't trace the ray upon startup? Let the user click Trace Now
for actual ray tracing after loading."

## Measured (bugs/probe_0646_load_time_breakdown.py, one app per process)

ELS85 / Apo75: **24.6 s** total load —

| stage | cost |
|---|---|
| `refresh_plot(suppress_analysis=True)` | **18.0 s** |
| `_relearn_folded_m_correction_after_swap` (the bugs/0625 load-time re-measure) | **6.5 s** |
| everything else (rows, heal, caches, table) | ~0.2 s |

cProfile inside the refresh: `_trace_preview_rays_folded_aware` (the non-sequential
preview trace) plus the ray-derived analysis records are essentially the whole cost; the
matplotlib draw and the system build are minor. The user's instinct was exactly right.

Two hidden side channels kept the first fix at 16.8 s: with only the main preview trace
skipped, `_update_results` → `_traced_image_diameter_value` → `_build_temporary_preview_trace`
rebuilt a FULL trace for a results-table label, and the field-metrics chain's
`folded_m_correction()` read consumed the deferred re-measure mid-load.

## Fix — both doctrines kept, only the timing moves

- **Loaders** (`load_layout_by_name`, `open_layout`, the Zemax loader) call
  `_defer_folded_m_relearn_on_load()`: sets `_folded_m_relearn_pending` (the 0625
  re-measure will run) and `_preview_trace_deferred_until_requested` (the FAST-LOAD
  state), then `refresh_plot(defer_trace=True)` draws **geometry only** (rays=None is a
  documented `build_scene_bundle` input) and leaves the preview trace DIRTY.
- **While the fast-load state is set**: `folded_m_correction()` returns raw 1.0 WITHOUT
  consuming the pending marker (labels may read it), and `_traced_image_diameter_value`
  returns None instead of building a temporary trace.
- **Real trace requests clear the state FIRST** — `refresh_plot`'s trace branch, the 3D
  `_build_preview_system_rays_bundle` (trace_rays=True), and `fov_solve` — so the very
  next correction read re-measures the deferred 0625 state before any ray or booking
  uses it. An eager relearn (swap) also satisfies the pending marker (no double run).
- **Trace Now** button (2D toolbar, next to Update): `_trace_now` →
  `refresh_plot(suppress_analysis=True)` — rays without the analysis panels. Load status:
  "Loaded X (rays not traced -- fast load). Click Trace Now for rays, Update for analysis."
- The bugs/0319 mixin-wrapper rule struck again: `defer_trace` had to thread through
  `LayoutAnalysisDisplayMixin.refresh_plot` (the editor facade over PlotRefreshService).

## Verified

- ELS85 load: **24.6 s → 1.16 s** (21×). After load: pending=True, state=None, dirty=True.
- First 3D trace (2.5 s): consumes the deferral — correction 0.9233 and field centre
  (0.379, ~0) byte-identical to the eager-load values; census 247 landed (healthy).
- Solve-straight-after-load (no trace between): re-measures before booking (the
  0602/0621 raw-first-order regression class is closed by the `fov_solve` clear point).
- Guard: `validate_open3d_0646_deferred_load_trace` = penta **phase 484** (A loaders
  defer, B consume-with-reentrancy-order, C eager satisfies pending, D defer branch
  stays dirty, E functional stub incl. the held state, F Trace Now wiring, G fast-load
  state set/honored/cleared incl. fov_solve). The 0625 guard's check E now accepts
  eager OR deferred re-measure.

## Open note (pre-existing, surfaced by this work)

A `fov_solve` run headless with NO inspector ever opened crawls inside numpy's
array-print formatter (faulthandler stack: `arrayprint.fillFormat` — some debug line
formats a huge ray array). Unreachable from the GUI (the FOV popup lives in the 3D
inspector, whose open traces first) and the sweep workers open the inspector; noted for
a future probe. Two probe scars while chasing it: a headless script that drives a solve
MUST have an `if __name__ == "__main__":` guard (the solve's multiprocessing spawns
re-execute an unguarded script — looks exactly like a hang), and `pgrep -f xvfb` matches
your own compound shell command (exit 144, the pkill scar again).
