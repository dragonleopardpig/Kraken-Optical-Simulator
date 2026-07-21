# 0386 — lens swap freeze: remove the redundant double trace (perf, pass 1)

**Flags:** the AZ85 swap "still takes super long / freeze" thread. The swap correctness is fixed
(0381–0385); this is the first perf pass on the freeze.

## Profile (headless capture, warm caches)

The swap's display rebuild is dominated by the preview trace's **system build**:

```
capture_async_trace_payload           5.2 s
  _trace_preview_rays                  5.0 s
    _build_system_from_specs  x19      3.4 s   <- 19 system builds per trace
      Prerequisites3DSolids   x3       3.3 s   <- 3D solids rebuilt 3x (the pupil first-order
      Face3D / GeometricRotatAndTran           reference, bugs/0094 per-branch)
```

Two independent costs:
1. **The swap runs the trace TWICE.** The editor `swap_imaging_lens_from_folder` ends with
   `refresh_plot(suppress_analysis=True)` — a full 2D system build + trace (~5 s on this folded
   multi-STEP scene). The inspector wrapper then calls `_apply_model_change()`, which retraces the 3D
   AND marks the 2D stale for a later redraw. So the editor's 2D trace is **pure redundant work that
   doubles the freeze**.
2. Within one trace, the pupil first-order reference rebuilds the 3D solids 3× (~3.3 s). Deeper caching
   effort — pass 2.

## Fix (pass 1)

`swap_imaging_lens_from_folder` takes a `refresh: bool = True` and gates the `refresh_plot` call on it.
The Open-3D inspector wrapper passes `refresh=False` (its `_apply_model_change` already retraces the 3D
and marks the 2D stale, so the 2D redraws on demand). The 2D-UI callers keep `refresh=True`. Net: the
swap-from-3D freeze drops one full folded-scene build+trace (~half).

## Verification

- MV-150 swap still completes; the 2D stays correct (marked stale → redraws when viewed).
- Guard (phase 322) wiring check: editor swap accepts+gates `refresh`, inspector passes `refresh=False`.

## Not done (pass 2)

- Cache/reuse the pupil first-order reference system build (the 3× `Prerequisites3DSolids`, ~3.3 s) so a
  folded scene's geometry is constructed once per trace.
- Skip `import_lens_folder` re-parse (~1.5 s) when the surrogate `.py` already exists.

## Files

- `KrakenOS/UI/services/layout_table_workbench.py` — `refresh` flag on `swap_imaging_lens_from_folder`.
- `KrakenOS/UI/open3d_inspector.py` — wrapper passes `refresh=False`.
- `KrakenOS/UI/validate_open3d_lens_swap_block_safety.py` — wiring check (phase 322).
