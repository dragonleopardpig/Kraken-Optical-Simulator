# 0003 — Aspheric achromat: "so many faces", snapshot key dead in face editor, InvalidMeshWarning

**Status:** Partially fixed — snapshot hotkey + InvalidMeshWarning fixed; the
all-red selection render and face-count reduction are analysed and deferred to
the offscreen-render environment (see below).
**Component:** Open 3D inspector — STEP promotion + face editor + selection render
**Reported via:** in-app recorder, `attachment/recorded_bug_repros/flag_20260602_205444_993/`
plus the `InvalidMeshWarning`s printed by `python -m KrakenOS.UI.layout_editor`.

## Symptoms (user's words)

> "why a simple aspheric achromatic lens has so many faces" … "I see there are
> 160 faces." … "trying to press 's' to snapshot the pop up face editor, but
> seems 's' is not functioning in the pop up."

Plus, on startup with the aspheric achromat loaded, `step_overlay_promotion.py`
emitted repeated `InvalidMeshWarning`: *"Mesh has 5 cell arrays with incorrect
length (length must be 1115). Invalid arrays: 'kraken_step_face_index' (2227),
…"*.

Fixture: `attachment/Lens/Aspherized_Achromatic_Lenses/step_49665.step`.

## Issue 1 — `s` snapshot key dead in the face editor (FIXED)

### Root cause
The `s` bug-flag / scene-snapshot hotkey is bound only on the inspector window
and its VTK widget (`open3d_inspector.py:624-627`). The face editor is a
separate `tk.Toplevel` (`panels/main_optical_solid_face_roles_dialog.py:51`), so
while it held focus the key went nowhere.

### Fix
Bind `<KeyPress-s>` / `<KeyPress-S>` on the face-editor Toplevel and forward to
the inspector's `_flag_bug_event` (which already no-ops while typing in an
entry/combobox). `panels/main_optical_solid_face_roles_dialog.py`.

## Issue 2 — `InvalidMeshWarning` during STEP promotion (FIXED)

### Root cause
`_mesh_from_step_analytic_document` attaches per-triangle face-index cell arrays
(`kraken_step_face_index`, `kraken_step_selection_face_index`,
`kraken_step_source_face_index`, `kraken_step_solid_index`) sized to the source
tessellation (`layout_polyline_display.py:413-446`). The promotion path then runs
`mesh.extract_surface(algorithm="dataset_surface").triangulate()`
(`step_overlay_promotion.py`, two sites) and saves an STL. That topology change
alters the cell count, leaving the custom arrays stale (e.g. length 2227 on the
collapsed 1115-cell outer surface of the cemented doublet), which pyvista flags
on the triangulate / save.

### Fix
`step_overlay_promotion._mesh_without_cell_data(mesh)` returns a deep copy with
cell-data cleared; it is applied before both `extract_surface().triangulate()`
chains. Root-cause and safe: the promotion output is an STL (stores no cell
data) and face metadata is recovered separately via `_step_overlay_face_metadata`,
so the arrays are not needed past this point.

### Test
`validate_open3d_step_promotion_mesh_warning_free` (display-free): injects a
length-mismatched `kraken_step_face_index` cell array at the VTK layer, confirms
the raw chain warns, then confirms `_mesh_without_cell_data` clears it and the
chain (`extract_surface(...).triangulate().save(stl)`) is warning-free, and that
the input mesh is left untouched (helper copies).

## Issue 3 — "160 faces" (explained; reduction deferred)

The face editor lists planar face *candidates* (`_step_overlay_face_metadata` →
planar clustering of the STL). An aspheric surface is curved, so it cannot be a
single planar face: clustering fragments it into ~160 small planar patches.
Spherical lenses are handled by the analytic sphere-fit promote path, but an
asphere has no clean sphere fit, so it stays a file-backed CAD solid whose curved
faces fragment. This is a known limitation, not a data error. A future
enhancement could cluster co-axial/curved patches into one logical optical face
(or fit an even-asphere surface). **Deferred** — needs design + the offscreen
render to verify.

## Issue 4 — selected lens renders all-red ("so many faces" as red triangles) (DEFERRED)

When selected, the lens fills the screen with dense red triangle edges instead of
the pink translucent fill. In `_set_row_actor_selected`
(`open3d_inspector.py:3322`) `suppress_select_edges = is_file_backed_body or
is_glassy_lens_body`; the aspheric lens's body actor carries neither flag, so per-
triangle red edges are drawn (same family as 0001/0002). The exact reason the flag
is unset on this actor, and any fix, **require the offscreen renderer** to
reproduce and visually verify per this workflow — and offscreen rendering is
currently producing blank frames on this machine (an Xvfb/GL environment issue,
tracked separately). **Deferred** until rendering works so the image-snapshot
test + Phase-10 check can be authored honestly.
