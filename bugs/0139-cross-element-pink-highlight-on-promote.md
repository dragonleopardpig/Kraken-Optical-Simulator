# 0139 — Promoting a STEP solid flashes a distant element's datum pink

## Symptom

> *"I promote the Cube Beam Splitter, and there is another Imaging Lens surrogate
> 150 mm focal length a distance away from the BS. However, I promote the BS, the
> lens surrogate front datum highlight pink as well during BS promotion. Shouldn't
> they are independent elements? Why there is a link?"*

Right-clicking a face on an imported STEP overlay (e.g. the beam-splitter cube) and
assigning an optical role promotes the overlay to an optical-solid row. **During**
that promotion a completely separate, upstream element — the imaging lens's
**Lens Front Datum** — briefly turns pink (the app-wide "selected" highlight), even
though the two elements share no data or optical link. The pink clears once the
promotion finishes.

## Root cause

Pink fill `(1.0, 0.45, 0.65)` + red edges means exactly one thing — *this row is
selected* (`open3d_inspector.py::_set_row_actor_selected`, the `selected` branch). A
row highlight pinks every actor whose `_actor_row_map[key]` equals the selected row
index (`open3d_selection_representation.py::apply_row_selection`).

The promote-and-assign runs in this order (`open3d_face_assignment.py`):

1. `promote_imported_step_to_optical_solid_row(..., refresh_open_3d=False)` inserts
   the new solid as a row at `resolved_insert_at` and selects it **in the table**,
   but deliberately does **not** rebuild the 3-D scene → the 3-D `_actor_row_map` is
   now **stale** (it still describes the pre-promote scene).
2. `self.editor._select_table_row(row_index)` — and `_select_table_row`
   *synchronously* calls `_sync_surface_selection` →
   `self._three_d_inspector.highlight_row(row_index)`
   (`layout_table_workbench.py`). That highlight runs against the **stale** map.
3. `refresh_from_editor(...)` finally rebuilds the scene and re-applies the selection
   against the **fresh** map (`open3d_scene_refresh.py`); a trailing
   `highlight_row(row_index)` does the same.

The bug is the step-2 highlight. In the stale (pre-promote) map, index
`resolved_insert_at` belonged to whatever row sat there **before** the new solid
displaced it. An in-path solid is inserted into the gap that *leads into* the lens,
so `resolved_insert_at` is exactly the **Lens Front Datum**'s old index — and
`highlight_row` paints that datum pink. The rebuild in step 3 destroys those actors
and repaints the real solid, so it is a transient flash that is most visible while
the post-promote retrace runs.

So the elements are genuinely independent; the pink is a stale-actor-map artifact of
highlighting before the scene is rebuilt — not a real coupling.

## Fix

Select the new solid in the table **without** the synchronous stale-map 3-D
highlight (`open3d_face_assignment.py`):

```python
# was: self.editor._select_table_row(row_index)
self.editor._select_table_indices([row_index], focus_index=row_index)
```

`_select_table_indices` sets the identical table selection (so the rebuild and the
trailing `highlight_row` still paint the real solid against the FRESH map) but does
not call `_sync_surface_selection`, so nothing is highlighted against the stale map.
The deferred `<<TreeviewSelect>>`-style sync the table schedules via `after_idle`
runs only after the rebuild, against fresh actors. This mirrors what the promote
method itself (`step_overlay_promotion.py`) and the sibling row-action menu path
already use.

## Test

- `KrakenOS/UI/validate_open3d_promote_no_stale_highlight.py::run_checks` —
  display-free, source-contract:
  - the promote-and-assign path selects the new row via `_select_table_indices`
    (the quiet selector), not `_select_table_row` (which eagerly syncs 3-D).
  - `_select_table_row` still carries its synchronous `_sync_surface_selection`
    (so the guard is pinning the *caller's* choice, not a coincidence), while
    `_select_table_indices` does **not** sync 3-D.
- Penta phase **129**.

## Status

Fixed; guard green standalone and in the penta harness (phase 129, display-free).
In-app eyeball owed — headless cannot drive the embedded-VTK promote + rebuild
timing. The user should confirm that promoting a STEP solid no longer flashes any
distant, unrelated element (the imaging lens's Front Datum) pink during promotion,
while the promoted solid itself still ends up correctly highlighted.
