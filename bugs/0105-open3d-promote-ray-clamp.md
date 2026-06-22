# 0105 — Promoting a STEP overlay stalls ~90s on the forced retrace

**Reported:** 2026-06-22. *"Can we speed up the promotion process?"* — after
gluing the beam-splitter cube to the LED and promoting it, the Open 3D view
freezes for ~90s before the promoted solid + rays appear.

## Why promotion is tied to ray tracing

Promoting a STEP overlay to an optical-solid row ends with a forced full
retrace:

```python
# open3d_inspector.py, _promote_step_overlay_to_optical_solid_row (~:5878)
self.refresh_from_editor(force_retrace=True)
```

That is not optional polish. Once any promoted optical-solid row exists,
`build_inspector_refresh` (services/open3d_trace_refresh.py) sets

```python
requires_open3d_retrace = include_live_step_overlays or self.has_promoted_step_optical_solid_rows()
```

permanently True, so the cached trace can never be reused and the branch
detectors (`derive_branch_detectors`) are derived from the *traced* ray tree —
the scene bundle build is coupled to the trace.

It is **not** the "Ray On" checkbox: `show_rays_var` only gates whether ray
**actors** are drawn; the trace still runs to place the branch detectors.

## Where the time goes (measured)

`python -m KrakenOS.UI.summarize_open3d_timing` against a live promote log:

- `preview_trace_rays_done`: one trace peaked **96,838 ms** (~97 s).
- `build_system_from_specs`: total 769 ms, the heavy `build=1`
  Prerequisites3D mesh path ran **once** (483 ms) — the shipped
  `_cached_stl_read` (42×) already flattened mesh cost.

So the chokepoint is the **branched physics trace**, not mesh building. A
beam-splitter scene explodes each root ray into transmit+reflect subtrees to
`max_branch_depth=8`, so cost scales ~linearly with the **root-ray count**
(fields × pupil samples per field, ~31/field for a doublet). The reconcile is
closed-form (`_inpath_plate_focus_shift` = t(1−1/n)), so promote traces exactly
once — there is no redundant double-trace to remove.

## Fix — clamp the forced retrace to a sparse 3-ray fan

Reuse the bugs/0024 drag-preview mechanism: `_current_ray_count`
(services/trace_preview_sampling.py) honours a temporary override, so the
trace samples a sparse pupil fan during a snappy interaction and restores full
density afterwards. Add a sibling override for the promote:

```python
# trace_preview_sampling.py, _current_ray_count
override = self.__dict__.get("_promote_preview_ray_count_override")
if override is None:
    override = self.__dict__.get("_drag_preview_ray_count_override")
```

```python
# open3d_inspector.py, _promote_step_overlay_to_optical_solid_row (~:5878)
self.editor._promote_preview_ray_count_override = 3
try:
    self.refresh_from_editor(force_retrace=True)
finally:
    self.editor._promote_preview_ray_count_override = None
```

The promote's own forced retrace now traces ~3 rays/field (≈10× fewer root
rays → ≈10× fewer branch subtrees on a splitter scene). The override is cleared
in a `finally` so a failing retrace can't leak the clamp, and so the **next
explicit trace restores full ray density**. Only the *displayed ray count* is
reduced for that one retrace — geometry, the branch detectors and the
reconciled prescription are unaffected.

## Tradeoff (accepted by the user)

Immediately after a promote the rays show as a coarse 3-ray fan. The detectors
and geometry are correct; pressing Trace (or any later refresh) re-traces at
full density.

## Repro / test

`.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_promote_ray_clamp`
— display-free guard (the machine-vision render SIGSEGVs headless). Checks:
(A) `_current_ray_count` honours `_promote_preview_ray_count_override`;
(B) the promote site sets it to 3 and clears it (`= None`) in a `finally`
around the forced `refresh_from_editor(force_retrace=True)`;
(C) functional — with the override set `_current_ray_count` returns 3, cleared
it falls back to the ray-count var, and the drag override still works. Penta
phase 91.

## Owed

In-app eyeball: the actual wall-time drop on a real cube promote still wants a
user confirm (headless can't render the machine-vision scene to time it end to
end).
