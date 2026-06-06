# 0022 — Shifting the beam-splitter cube off-axis blanked the whole trace

**Status:** Fixed (2026-06-06).
**Component:** Open 3D ray display filter — `_iter_3d_scene_ray_records`
in `KrakenOS/UI/services/three_d_scene_tools.py`.
**Reported via:** in-app recorder, a before/after pair:
`attachment/recorded_bug_repros/flag_20260606_220851_549` ("beam spliter in
place", 558 ray actors) and `flag_20260606_220946_729` ("beam splitter shifted
out", **0** ray actors).

## Symptoms (user's words)

> beam splitter shifted out.

The user moved the promoted beam-splitter **cube** (row S6) sideways off the
optical axis with its placement handle — cube centre `[0,0,212.5]` →
`[-55,0,212.5]` (−55 mm in X) — and **every traced ray vanished** from the 3D
view (558 → 0 rendered), leaving only the dotted optical-axis guide. Rays must
not disappear when an element is repositioned.

## Root cause

"Show Clipped Rays" was OFF. The 3D ray filter
(`ray_path_visible_without_clipping_from_events`) shows a ray that reached a
surface, and — per bug 0018 — an *escaped* ray that underwent a reflective fold
(it has non-refractive steering), but hides an escaped ray that was merely
vignetted (bug 0016).

With the cube **in place**, the beam hit it: of 558 paths, 155 reached the
detector, 124 missed the detector (both shown), and 279 **reflected off the
cube** — escaped *with* steering, so bug 0018 kept them visible. All 558 rendered.

With the cube **shifted off-axis**, nothing hits it. The reflected branch is gone,
and because the cube's output port had been positioning the detector, the on-axis
transmit beam now misses it too. Every remaining path (279) escaped *without*
steering, so the filter hid **all of them** — `_iter_3d_scene_ray_records`
replaced `scene_paths` with an empty list and the trace rendered nothing. Hiding
individual vignetted strays is correct (bug 0016); hiding *every* ray is not — it
blanks the trace and breaks the invariant that rays survive an element move.

## Fix

`_iter_3d_scene_ray_records` now only suppresses clipped rays when **at least one
ray survives** the filter. If the filter would hide every path, it keeps the
unclipped `scene_paths` so the beam stays visible:

```python
visible_paths = [p for p in scene_paths if ray_path_visible_without_clipping_from_events(p)]
scene_paths = visible_paths if visible_paths else scene_paths
```

This preserves bug 0016 (the mixed case — some rays land, hide the vignetted
strays among them) and bug 0018 (folded branches stay visible), while ensuring a
moved element can never blank the whole trace.

## Tests

`KrakenOS/UI/validate_open3d_moved_element_rays_stay_visible.py`
(`python -m KrakenOS.UI.validate_open3d_moved_element_rays_stay_visible`):

* **A — source (fixture-free):** `_iter_3d_scene_ray_records` keeps the all-hidden
  fallback (`visible_paths if visible_paths else scene_paths`).
* **B — render (needs the cube's source STEP + a display; SKIP otherwise):** load
  the machine-vision prescription with Show Clipped Rays OFF, shift the cube
  −55 mm in X via its placement handle, and assert the trace still renders ray
  actors. Verified fail-before / pass-after: pre-fix the render blanks
  (558 → 0); post-fix the beam stays visible (558 → 279).

Wired into the comprehensive harness as `Phase 31`; pass/fail of every phase is
unchanged, so the gate baseline is untouched.
