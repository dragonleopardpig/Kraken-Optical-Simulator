# 0003 — Aspheric achromat: "so many faces", snapshot key dead in face editor, InvalidMeshWarning

**Status:** All four issues fixed — snapshot hotkey, InvalidMeshWarning, all-red
selection render, and the "160 faces". The "160 faces" first got a display-only
grouping fallback, then a **root-cause fix**: STEP optical solids are now meshed
by their OpenCascade B-Rep faces (the achromat shows 7 real faces, not 160),
behind `KRAKENOS_BREP_OPTICAL_SOLID` with a gmsh fallback — see the Issue 3
root-cause section below. The earlier "blank offscreen render" turned out to be
transient (offscreen VTK rendering works; the comprehensive validator passes
Phase 10).
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
`panels/main_optical_solid_face_roles_dialog.py`.

### Follow-up — capture the dialog pixels, not the 3-D scene (FIXED 2026-06-03)
Originally `_flag_bug_event` → `flag_bug` only screenshotted the **3-D scene**
(the VTK render window), so pressing `s` in the face editor saved the scene
*behind* the dialog, never the face list the user was looking at (confirmed from
the in-app flag `flag_20260603_072730_717` "still 160 faces": the saved PNG is
the 3-D scene). `flag_bug` now detects whether a popup Toplevel is the focused
window (`_focused_foreign_toplevel`, built on the pure, unit-tested
`_classify_dialog_toplevel`); if so it saves the **dialog's own pixels** as
`screenshot.png` and keeps the 3-D render as `scene_3d.png` (the cursor
crosshair stays on the 3-D image; `state.json` records `screenshot_kind`). With
no popup focused the behaviour is unchanged (3-D render → `screenshot.png`, no
`scene_3d.png`). Capture is universal via the `@staticmethod`
`_capture_toplevel_png`, first success wins: ImageMagick `import -window <xid>`
(Linux X11/XWayland), PIL `ImageGrab` over the window rect (native on
macOS/Windows; Linux with a backend), then `grim -g` (Wayland). If no backend
works the 3-D render is promoted to `screenshot.png` so the bundle always has
one. Note: ImageMagick's X11 grab does **not** work under XWayland, so on a
Wayland/Hyprland session `import` fails fast (rc≠0, no file) and capture falls
through to `grim`.

### Test (follow-up)
`validate_open3d_flag_dialog_capture` (display-free seam): forces a private
Xvfb and masks Wayland, checks `_classify_dialog_toplevel` routes a focused
popup to a dialog grab (and the inspector/root windows to the 3-D scene), and
asserts a solid-red Toplevel comes back from `_capture_toplevel_png` as a
mostly-red PNG of the right size (exercises the `import -window <xid>` X11 path).
No penta phase: the face editor is not part of the penta cascade, so the
standalone validator guards it.

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

## Issue 3 — "160 faces" (FIXED — display-only grouping first, then root-cause B-Rep import)

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

### Root-cause fix — mesh STEP optical solids by their OCC B-Rep faces (2026-06-03)

The 160 were an artifact of the *import path*, not the lens: the optical-solid
import went STEP → gmsh → STL → re-cluster-triangles-by-plane, which discards
the B-Rep topology OpenCascade already computes. The aspheric achromat is **7
outer faces** (4 cylinder + 1 sphere + 2 bspline; 2 coincident cemented-interface
spheres dropped as interior duplicates), not 160. The grouping above is a good
*display* fallback but still operates on the shattered clusters.

**Fix:** a new service `KrakenOS/UI/services/step_optical_solid_brep.py` meshes
the STEP **in process** via `load_step_analytic_document` and emits two aligned
artifacts:

* the displayed binary STL, written from `doc.triangles` **in order**
  (`write_triangles_binary_stl`), so every existing triangle-index-based picker /
  highlighter — which indexes into the displayed STL — stays aligned with the
  face metadata with **no rewrite**; and
* a sidecar `*.kraken_brep_faces.json` of the per-face metadata
  (`surface_type` + `triangle_indices`) from the **same** document.

Because both come from one tessellation, the displayed mesh and the metadata
share triangle indices. Wiring (all behind `KRAKENOS_BREP_OPTICAL_SOLID`, default
on; set `0`/`false`/`no`/`off` to fall back to gmsh):

* `cad_import_service.optical_solid_mesh_path_from_source` routes `.step`/`.stp`
  through `build_step_optical_solid_mesh` (`_build_optical_solid_cad_mesh`),
  falling back to `convert_step_to_stl` (gmsh) on any failure — and removing a
  stale sidecar first so a fallback STL is never mis-read as B-Rep-backed. IGES
  still uses gmsh.
* `optical_solid_workflow._default_uncoated_optical_solid_face_metadata` seeds
  the row's face metadata from the sidecar (`load_face_sidecar`) when present,
  applying the same uncoated-transmit defaults, instead of clustering.
* `optical_solid_geometry` gains `optical_solid_metadata_is_brep` (a face with a
  `surface_type` is the durable B-Rep marker — it survives normalization, and
  clusters never set it) and `optical_solid_face_record_triangles` (pull a
  record's triangles by `triangle_indices`); both exported onto `le`.
* `main_optical_solid_face_roles_dialog._open_optical_solid_faces_for_row`
  branches on `brep_backed`: when B-Rep it lists the saved faces verbatim (no
  cluster, no grouping) and `candidate_mesh` / the matplotlib preview pull
  triangles via `optical_solid_face_record_triangles`. The flat-STL path is
  byte-for-byte unchanged.

The face editor now shows the achromat's **7 real optical faces**, and selection
/ picking / highlight keep working because the indices still address the same
displayed STL.

### Tests (root-cause fix)
* `validate_open3d_brep_optical_solid_faces` (display-free): the achromat meshes
  to 7 B-Rep faces (sphere/cylinder/bspline); the STL is written in
  `doc.triangles` order (max vertex error ~1e-6, float32); every face's
  `triangle_indices` are in range and together cover all 1115 triangles;
  `optical_solid_metadata_is_brep` accepts the result and rejects cluster-shaped
  metadata; `optical_solid_face_record_triangles` returns exactly the STL rows at
  a face's indices; and the import-time default metadata is those 7 B-Rep faces,
  not 160 clusters. The `KRAKENOS_BREP_OPTICAL_SOLID` flag is exercised.
* `validate_open3d_brep_optical_solid_faces_snapshot` (image): renders the
  **written STL colored by the sidecar's `triangle_indices`** (the real
  round-trip) off-screen and asserts several large single-color regions
  (6/7 faces visible in one iso view, 7th occluded), not a fragmented soup —
  opened and confirmed by eye.

Note: an already-cached gmsh STL (no sidecar, e.g. imported before this change)
keeps clustering until the source is re-imported or the CAD cache is cleared;
fresh imports take the OCC path.

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
