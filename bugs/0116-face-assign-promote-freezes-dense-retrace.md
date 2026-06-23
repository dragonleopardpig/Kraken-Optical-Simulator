# 0116 — Right-click direct face assignment freezes the UI (dense forced retrace)

## Symptom

Right-click on an imported STEP face -> "Promote and set `<function>`" (the direct
face-assignment menu) **freezes the whole UI for ~44 s** before the scene comes
back. The same stall hits "many actions" that force a physics retrace, but the
face-assign path is the clearest repro. Reported alongside the more general "is
there a way to free the UI while one task is processing?".

## Timing evidence

From `~/.cache/krakenos/logs/open3d_timing_latest.jsonl`
(`python -m KrakenOS.UI.summarize_open3d_timing`) for a live promotion:

| event                          | max     |
|--------------------------------|---------|
| `refresh_from_editor_done`     | 48.9 s  |
| `preview_system_rays_bundle`   | 43.9 s  | ~90 % of the freeze
| `refresh_scene_timing`         | 10.6 s  | main-thread VTK rebuild
| `render_done` (mean)           | 17 ms   |

The expensive refreshes traced a **3618-ray** fan (`trace_preview_bundle_done`
n=72 = 8 traces x the 9-bundle per-branch cascade). The non-seq branched trace is
the giant; the displayed ray *count* is what makes it 3618 rays instead of a
handful.

## Root cause

The plain "Promote to Optical Element" path
(`open3d_inspector._promote_step_overlay_to_optical_solid_row`) already clamps its
post-promote forced retrace to a **sparse 3-ray fan** (bug 0105):

```python
self.editor._promote_preview_ray_count_override = 3
try:
    self.refresh_from_editor(force_retrace=True)
finally:
    self.editor._promote_preview_ray_count_override = None
```

A promoted optical-solid row makes *every* later refresh force a full branched
physics retrace, so without the clamp a promote stalls ~90 s on a beam-splitter
scene. The clamp lets the promote land in ~1 s; the next explicit Trace restores
full ray density.

The **direct face-assign path**
(`services/open3d_face_assignment.py::_promote_step_and_assign_face_function`) is
*also* a promote of an in-path optical solid (it calls
`promote_imported_step_to_optical_solid_row` then assigns the picked face), but it
called `refresh_from_editor(..., force_retrace=True)` **without** the override. So
the face-assign retrace ran at full `ray_count_var` density (3618 rays) = the
44 s freeze. The clamp was simply missed on this second promote entry point.

## Fix

Wrap the face-assign forced retrace in the same `_promote_preview_ray_count_override
= 3` clamp (set before, cleared in a `finally`), mirroring the plain promote. Only
the displayed ray **count** changes for that one retrace -- the assigned face,
branch detectors and the reconciled prescription are unaffected, and a later
explicit Trace restores full density. `_current_ray_count`
(`trace_preview_sampling.py`) already honours the override, so no sampling change
is needed.

## Test

`KrakenOS/UI/validate_open3d_face_assign_sparse_retrace.py::run_checks` (display-free):

1. source check -- the face-assign method sets the 3-ray override, runs the
   `force_retrace=True` refresh while it is active, and clears it in a `finally`
   (an exception can never leave the scene stuck at 3 rays);
2. behavioural check -- `TracePreviewSamplingMixin._current_ray_count` returns the
   clamped 3 under the override and the live `ray_count_var` once cleared;
3. sanity -- a missing override falls through to the live count without raising
   (the overrides are read via `__dict__.get`, not a recursing `getattr`).

Penta phase 108 runs this guard.

## Note — the residual

The clamp removes the trace (~90 %) from the freeze. The remaining cost is
`refresh_scene` (the main-thread VTK actor rebuild, ~2-7 s), which was itemized in
a separate perf-instrumentation pass (prep / step_overlay / thickness_dim /
detector_overlay / finalize spans). That part is genuine main-thread VTK work and
cannot be moved off-thread; an async-trace offload (worker thread + `after()`
marshalling) remains a possible follow-up for the residual, but is a larger
central-path concurrency change because the trace reads ~13 Tk variables deep in
its call tree and temporarily swaps `self.rows`.
