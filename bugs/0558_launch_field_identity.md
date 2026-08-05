# 0558 — a ray's field identity comes from the launch, not from division

**Flags:** `flag_20260805_121454_688` ("fresh load .py file, 2 ray colors only: green and blue")
and `flag_20260805_121547_451` ("after clicking Trace now: rays color become normal"), both on
build `328ae1a7` — i.e. **with bugs/0555 already in**.

## The evidence

The two flags are identical in every recorded respect:

| | fresh load | after Trace Now |
|---|---|---|
| traced paths | 558 | 558 |
| census | 375 / 93 / 87 / 3 | 375 / 93 / 87 / 3 |
| `ray_count` | 31 | 31 |
| trace backend | `NsTraceLoop` | `NsTraceLoop` |
| **ray actors** | **2** | **8** |

Ray actors merge per style, so the count IS the number of distinct colours. The trace never
differed; only the colouring did.

## Why bugs/0555 only got halfway

0555 removed the CLAMP (`min(..., field_count - 1)`) that folded every ray onto field 0, taking
the fresh-load case from 1 colour to 2. But the grouping still RECONSTRUCTED a ray's field as
`source_ray_index // ray_count_per_field`, and that division is wrong twice over:

1. **It needs a display-side number.** `ray_count_per_field` comes from
   `_preview_field_ray_count`, which `layout_editor` initialises to 1 while `saved_layout_plot`
   seeds it from the saved settings' `ray_count`. A fresh `.py` load and an explicit re-trace
   therefore disagree — exactly the two flags. With 31 source rays, 2 groups implies
   `ray_count_per_field ≈ 16` and 8 groups implies `≈ 4`.
2. **It assumes uniform rays per field.** The launch appends corner probes to some fields
   (`field_launches` gains extra entries), so rays-per-field is RAGGED. No value of the count
   reconstructs a ragged grouping — the division is wrong even when perfectly fresh.

## Fix

The launch already knows the answer and was discarding it: `_build_world_envelope_bundles` and
friends build **one bundle per field**, and `_trace_preview_bundles` — documented as the choke
point *"EVERY preview sampling path funnels its launch bundles through this method"* — flattens
them. It now records the real mapping:

```python
field_by_source_ray = []
for bundle_index, length in enumerate(bundle_lengths):
    field_by_source_ray.extend([bundle_index] * length)
self.editor._preview_field_index_by_source_ray = field_by_source_ray
```

`build_scene_bundle` takes it as `field_index_by_source_ray` and `_launch_field_group` prefers it,
keeping the old division only as a fallback for callers that never went through that path. It is
recorded AFTER the async replay substitution, so a worker-traced bundle maps its own rays.

Exact for ragged fields, and it cannot go stale: it is produced by the same call that traces the
rays it describes.

## Guard

Extended `validate_open3d_0555_ray_colors_follow_fields` (penta phase 437): on a ragged 3/5/3
fixture the mapping reproduces the true grouping while the division misassigns ray 3; the
division fallback is unchanged for uniform fields; an out-of-range index falls back safely; and
`_trace_preview_bundles` is asserted to record the mapping.

Non-vacuity: forcing division-only fails it with the exact ragged mismatch.

## Note

This supersedes bugs/0555's remedy. 0555's diagnosis (the clamp plus a green default) was right
and its removal stands; 0558 removes the division that remained underneath it.
