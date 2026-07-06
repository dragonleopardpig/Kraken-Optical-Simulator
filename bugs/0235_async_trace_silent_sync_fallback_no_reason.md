# 0235 — Off-thread preview trace silently falls back to the 41s sync trace with no recorded reason

## Symptom
flag_20260706_070708_237 ("tracing 6939 rays take 41 seconds"): on the promoted two-fold AZ85
periscope **with imported-STEP decoration overlays (lens + camera)**, Show-Rays spent ~41 s on the
Tk main thread. The off-thread preview trace (bugs/0223) was supposed to move exactly this slow
per-ray scalar folded trace into a worker process, yet the scene ran it synchronously anyway.

The recording could not say *why*. `sampling_diagnostics` showed only
`actual_trace_backend == "Scalar TraceLoop"` and `folded_sequential_engaged == true` — i.e. the sync
path ran. It did **not** record whether the async kick was refused at an eligibility gate, or whether
a worker was kicked and then failed on rebuild and fell back. Those are different bugs with different
fixes, and the recording collapsed them into one indistinguishable "it was slow."

## Root cause (of the diagnostic gap)
`maybe_begin_inspector_async_trace` returns `False` (→ synchronous fallback) at ~13 different
eligibility gates, and `_poll_inspector_async_trace` can complete a worker that *failed* and then
call `_fallback_sync_refresh`. Both roads end at the same synchronous `Scalar TraceLoop`, and nothing
recorded which road was taken.

The leading suspect for the flag scene is the **worker rebuild gap**: the worker rebuilds the scene
from row specs only (`_snapshot_editor(rows, settings)`) and never re-imports STEP overlays. A
promoted periscope carrying imported-STEP lens/camera overlays would kick a worker that raises on
rebuild → `worker_failed` → sync fallback. But "leading suspect" is exactly the problem — the async
equivalence guard (bugs/0223) never exercised an imported-STEP scene, so this branch was untested and
unobserved. Without a recorded reason we were guessing.

## Fix (this increment: diagnostics, not the perf fix)
Record WHY at every decision point so the *next* recording is conclusive:

- `maybe_begin_inspector_async_trace` sets `editor._last_async_trace_decision` (`{began, reason}`) at
  **every** return. Refusals name the exact gate — `kill_switch_off`, `not_interactive_opt_in`,
  `fallback_latched`, `force_retrace`, `placement_drag`, `traceable_step_overlay`,
  `no_promoted_step_rows`, `settings_error`, `capture_error`, `capture_none`, `spawn_failed`. Begins
  name their reason — `coalesced_inflight` or `kicked`.
- `_poll_inspector_async_trace` sets `editor._last_async_trace_worker_outcome` (`{reason, detail}`)
  for a completed worker — `worker_failed` (+ error and log tail), `stale_rekick_exhausted`,
  `apply_failed`, or `applied` (+ elapsed). The `worker_failed` outcome **survives the sync
  fallback's re-entrant kick check**, so the flag case (kicked-then-failed) is not overwritten by the
  fallback's own decision.
- The bug recorder surfaces both fields in `sampling_diagnostics` as `async_trace_decision` and
  `async_trace_worker_outcome`.

So a future flag_ recording of the same scene will show, e.g., `async_trace_decision =
{began: True, reason: "kicked"}` **and** `async_trace_worker_outcome = {reason: "worker_failed",
detail: "…KeyError('optical')… | log: could not re-import imported-STEP overlay"}` — confirming the
rebuild gap — or instead a specific gate that refused the kick.

## Deferred (the actual perf fix)
Making the off-thread worker rebuild imported-STEP scenes (re-import the STEP overlays in the worker,
or trace only the promoted rows, or cut the folded ray count) is a display-entangled increment,
deferred until the next recording confirms which branch trips in-app. `_async_trace_fallback_sync`
is transient (reset in its `finally`), so every refresh re-attempts async — this diagnostic ships
with no behavior change to the trace itself.

## Verification
`KrakenOS/UI/validate_open3d_async_trace_fallback_reason.py` (penta phase 212):
- **GATE REASONS** — a refused kick records the exact gate (`force_retrace`, `not_interactive_opt_in`).
- **BEGAN REASON** — a coalesced begin records `{began: True, reason: "coalesced_inflight"}`.
- **WORKER-FAILED** (the flag case) — a kicked-but-failed worker, driven through the real
  `_poll_inspector_async_trace` with a finished-proc + error result, records
  `{reason: "worker_failed"}` with the error and log tail in `detail`, then falls back to sync
  without the fallback overwriting the outcome.
- **WIRED** — the reason literals are in the async source and both fields are read by the recorder.

The bugs/0223 async equivalence guard (`validate_open3d_async_trace_equivalence`, 13 checks) still
passes after the instrumentation — the recorded reasons are additive and do not change the traced
result. In-app confirm owed on the next recording of the flag scene (the app must be restarted onto
this build for the new fields to populate).
