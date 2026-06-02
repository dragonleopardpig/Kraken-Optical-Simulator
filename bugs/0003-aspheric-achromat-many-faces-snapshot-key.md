# 0003 — Aspheric achromat: "so many faces", snapshot key dead in face editor, InvalidMeshWarning

**Status:** All four issues fixed — snapshot hotkey, InvalidMeshWarning, all-red
selection render, and the "160 faces" (via display-only grouping in the face
editor). The earlier "blank offscreen render" turned out to be transient
(offscreen VTK rendering works; the comprehensive validator passes Phase 10).
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
A plain `window.bind('<KeyPress-s>')` on the Toplevel was **not** enough — the
face editor's `ttk.Treeview` swallows `s` (its class binding) before a
Toplevel-level binding fires (verified: a Toplevel binding fires for combobox
focus but not Treeview focus). So instead use an application-wide
`self.editor.bind_all('<KeyPress-s>' / '<KeyPress-S>')`, scoped by focused-toplevel
to the face-editor window (so it never double-fires with the inspector's own `s`
binding), forwarding to the inspector's `_flag_bug_event` (which itself no-ops
while typing in an entry/combobox), and torn down on the window's `<Destroy>`.
`panels/main_optical_solid_face_roles_dialog.py`. Note: `_flag_bug_event` →
`flag_bug` captures the **3-D scene** screenshot (the inspector render window),
not the face-editor dialog pixels; capturing the dialog window itself would be a
separate enhancement.

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
Clearing only the *input* was insufficient: `extract_surface` itself adds a
`vtkOriginalCellIds` cell array sized to its output, and `triangulate` then
changes the cell count again (the 2227 → 1115 collapse), leaving *that* array
stale — so after the first fix the warning re-appeared as
`vtkOriginalCellIds (2227)`. The complete fix is
`step_overlay_promotion._clean_surface_triangulate(mesh)`: it drops cell data
before extract_surface, again before triangulate, and once more on the result,
and is applied at both promote sites. Safe because the promotion output is an STL
(stores no cell data) and face metadata is recovered separately via
`_step_overlay_face_metadata`.

### Test
`validate_open3d_step_promotion_mesh_warning_free` (display-free): a
length-mismatched cell array makes the raw chain warn; `_clean_surface_triangulate`
clears it and is warning-free (incl. STL save) with the input left untouched. When
a cached analytic `.vtp` is present it also reproduces the real `vtkOriginalCellIds`
case — confirming clear-input-only still warns while `_clean_surface_triangulate`
does not.

## Issue 3 — "160 faces" (FIXED via display-only grouping)

The face editor lists planar face *candidates* from
`cluster_optical_solid_planar_faces`, which groups STL triangles by **plane**
(rounded normal + offset). A flat face → 1 cluster; a *curved* aspheric surface →
one micro-cluster per triangle → capped at `max_faces=160`. So the 160 are the
curved front/back surfaces fragmented, not real optical faces.

**Fix (display-only, chosen over a clustering rewrite to avoid disturbing the
planar snapping/role system):** `group_optical_solid_face_candidates`
(`optical_solid_geometry.py`) region-grows the STL by mesh connectivity + normal
continuity (edge-adjacent triangles within ~35° = same surface; sharp dihedral =
boundary) and returns a group id per candidate. The candidates and their planar
fits are **unchanged**. The face editor (`main_optical_solid_face_roles_dialog.py`)
shows a **Group** column when grouping consolidates (>1 fewer groups than
candidates) and a right-click **"Select all N faces in group G…"**, so the
existing multi-select bulk-apply lets the user role-assign a whole curved surface
at once. Verified: the aspheric achromat collapses 160 → **3 groups**
(front/back/edge); a penta prism stays **7 → 7** (flat faces untouched, so the
Group column does not even appear). Guarded by
`validate_open3d_optical_solid_face_grouping`.

## Issue 4 — selected lens renders all-red ("so many faces" as red triangles) (FIXED)

When selected, the lens filled the screen with dense red triangle edges instead
of the pink translucent fill. Root cause confirmed by promoting the aspheric
achromat to a file-backed optical-solid row and dumping its row-1 actors: the
body actor has `_kraken_file_backed_row_body=False` and
`_kraken_glassy_lens_body=False` (it is rendered through the glassy analytic path
but, being file-backed-with-an-on-disk-STL, misses both flags), so
`_set_row_actor_selected`'s `suppress_select_edges = is_file_backed_body or
is_glassy_lens_body` was False and per-triangle red edges were painted (same
family as 0001/0002). The body actor *does* carry `_kraken_round_lens_like_step_body
=True`. **Fix:** include that flag in `suppress_select_edges`
(`open3d_inspector.py`) — a round-lens-like dense body should never show a red
per-triangle wireframe on selection; its separate rim/feature-edge actor still
outlines it. Verified the existing DCV glassy-selection snapshot still passes
(pink fill, negligible red). The offscreen render was confirmed working (the
earlier "blank" was transient), so the bug-0002 snapshot check guards the
glassy case end-to-end.
