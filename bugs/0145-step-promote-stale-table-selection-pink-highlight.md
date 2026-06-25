# 0145 — Promoting the beam splitter pinks the imaging-lens "Lens Front Datum" mid-promote

## Symptom

> *"the highlight pink for imaging lens surrogate while promoting BS"*
> (the user could not flag it: the promote is synchronous, so the in-app flag key
> cannot fire mid-promote — the only artifact is the felt pink flash during the
> ~13-second frozen beam-splitter promote, flag `flag_20260625_120811_451` was an
> unrelated post-promote idle capture).

With the camera + LED + beam-splitter + imaging-lens overlays loaded, right-clicking
the beam splitter and choosing **Promote to Optical Element** freezes the app for the
duration of the retrace+rebuild. For that whole frozen window the *upstream* imaging
lens's surrogate **"Lens Front Datum"** flashes pink (row-selection highlight), even
though nothing selected the lens — it clears only when the rebuild finishes and the
authoritative highlight repaints the real selection.

## Root cause

The Open 3D row highlight (`open3d_selection_representation.apply_row_selection`) pinks
**every actor whose `_actor_row_map[key]` equals the selected row index**
(`_set_row_actor_selected` → `SetColor(1.0, 0.45, 0.65)` + red edges). It iterates the
renderer's *current* actors and keys them through `_actor_row_map`.

`refresh_from_editor` runs the **retrace first**, then the **scene rebuild** that
repopulates `_actor_row_map`. So there is a window — the whole promote — where
`_actor_row_map` is **stale**: it still describes the *pre-promote* scene. The in-path
solid is inserted at the row index that, before the promote, belonged to the imaging
lens's **Lens Front Datum**. A `highlight_row(new_index)` fired against that stale map
therefore pinks **old-row-N = the lens datum**.

Two classes of trigger reach `highlight_row`:

- **DIRECT** — `inspector.highlight_row(...)` called by the scene-rebuild's end-of-rebuild
  re-apply (`open3d_scene_refresh.py`) and the inner promote's explicit post-refresh
  highlight (`open3d_face_assignment.py:877`). These run **after** the rebuild, against
  the **fresh** map — correct.
- **TABLE-EVENT** — `_sync_surface_selection → _three_d_inspector.highlight_row`
  (`layout_table_workbench.py`), driven by the monkey-patched
  `table.selection_set` / `_sync_table`'s `delete(*get_children())`, both of which
  schedule a **deferred `<<TreeviewSelect>>`** sync via `after_idle`. On the slow
  beam-splitter promote that deferred sync **lands while the map is stale** → the lens
  datum flashes pink.

Bug **0139** removed the *synchronous* `_select_table_row` trigger from the
promote-and-assign caller, but its premise ("the deferred sync runs only after the
rebuild") is false on the long BS promote: `_select_table_indices` / `_sync_table` still
schedule the deferred `<<TreeviewSelect>>` sync, and it fires mid-rebuild.

## Fix

A new flag `_suppress_3d_row_selection_sync` gates **only** the table-event 3-D highlight:

- `KrakenOS/UI/services/layout_table_workbench.py` — `_sync_surface_selection` skips the
  `_three_d_inspector.highlight_row` call when
  `getattr(self, "_suppress_3d_row_selection_sync", False)` is set. The 2-D layout
  overlay (`_update_layout_selection_overlay`) and the status-bar text are **untouched** —
  the suppression is surgical to the 3-D pink.
- `KrakenOS/UI/services/open3d_face_assignment.py` —
  `_promote_step_and_assign_face_function` is now a thin wrapper that sets the flag
  `True`, calls the renamed `_promote_step_and_assign_face_function_inner`, and clears the
  flag in a `finally`. The flag is held across the whole promote+refresh, so any deferred
  `<<TreeviewSelect>>` sync that lands in the stale-map window is dropped.

The promote still does its **own** authoritative highlight against the **fresh** map — the
scene rebuild's re-apply plus the inner body's explicit `self.highlight_row(row_index)` —
both **direct** `inspector.highlight_row` calls that bypass `_sync_surface_selection`, so
only the stale flash is suppressed. `finally` guarantees the flag is cleared on every exit
path; a stuck flag would mute **all** later selection highlighting.

## Verification (`KrakenOS/UI/validate_open3d_promote_suppresses_table_selection_sync.py`)

A display-free harness drives the **real** `LayoutTableWorkbenchMixin._sync_surface_selection`
and `Open3DFaceAssignmentService._promote_step_and_assign_face_function` with fake selves
(`_FakeWorkbench` carrying the leaf state the sync reads/writes, `_FakeInspector3D` recording
`highlight_row` calls, `_FakeFaceService` recording the flag seen INSIDE the inner body):

- **BUG PATH** — flag unset, a table-selection sync DOES call `highlight_row` (the path that,
  mid-promote, pinks the lens).
- **FIX** — flag set, the same sync does NOT call `highlight_row`.
- **SURGICAL** — flag set, the 2-D layout-selection overlay + status are STILL updated.
- **WRAPPER (normal)** — the real wrapper sets the flag `True` for the inner body's duration
  and clears it to `False` after.
- **WRAPPER (finally)** — a raising inner body still clears the flag.
- **SOURCE WIRING** — the gate + the set/finally-clear + the inner-delegation exist in source.

All 6 checks pass. Removing the `not suppress_3d_sync` gate flips the FIX check to FAIL
(`highlight_calls=[1]` — the lens is pinked) and the SOURCE-WIRING check to FAIL, confirming
the guard reproduces the bug rather than passing vacuously.

## Guard

- `KrakenOS/UI/validate_open3d_promote_suppresses_table_selection_sync.py` (`run_checks`,
  display-free): the six pins above.
- Penta phase **134** (`phase_134_promote_suppresses_table_selection_sync`);
  baseline → 134 = pass.

## In-app eyeball still owed

Headless cannot drive the embedded-VTK promote that pumps the deferred `<<TreeviewSelect>>`
event during the frozen rebuild, so the *felt* fix — the imaging-lens datum **not** flashing
pink while the beam splitter is promoted — is owed an in-app check alongside the
0142 / 0143 / 0144 eyeballs.
