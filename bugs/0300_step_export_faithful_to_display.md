# 0300 — 3D STEP export doesn't match what the 3D shows (folded periscope)

User report (2026-07-14), `attachment/machine_vision_AZ85_RA_Mirror.py` (object → RA prism1 (BK7) →
ELS-85 lens group → RA prism2 (BK7) → HR25 camera), see `STEP.png` / `STEP1.png`:

1. the location/orientation of the components is mostly wrong — the exported STEP is useless for production;
2. the exported STEP should be **exactly** what the 3D inspector shows, saved or not;
3. every element shown in the 3D should be exported — the **Object Plane** was missing.

## Root cause

The export takes two paths (`export_3d_step` → `build_system` → if `_has_imported_step_cad()` the
CAD writer `_write_step_with_cad_shapes_and_rays`, else the analytic writer). This scene has vendor
STEP overlays (camera + lens), so it uses the CAD path.

**The two BK7 RA prisms** are optical-solid rows (they carry `Solid_3d_stl`), so they are *not*
revolution-compatible and drop out of the analytic surface phase. They were written by
`_collect_row_native_step_export_shapes`, which read the row's **saved STEP source**
(`_resolve_row_saved_step_source_path`) and placed it with `_row_native_step_alignment_affine`.

The problem: `_resolve_row_saved_step_source_path` returns a **shared** `step_87391.step` *template*
(the same file for both prisms), whose local frame (raw centroid `[0, 5.893, 12.5]`) is a different
frame from each prism's **per-instance STL** (`optical_*.stl`, raw centroids `[±4.167, 0, 4.167]`).
Placing that template with `TRANS_2A`/the runtime pose landed the prism ~11 mm off. Box-ICP against
the runtime mesh is ambiguous on a 6-point symmetric prism (~4 mm error), so fitting is not viable.

Meanwhile the **3D inspector never draws the template** — it draws each prism from its **STL**
tessellation under `_runtime_transform_for_row` (the body render, the assigned-face overlays, the
virtual-plane markers and face picking all use that one transform). So the display and the export
disagreed by construction.

**The vendor camera + lens STEP overlays** had a second, independent placement bug. They are imported
CAD, aligned onto the *straight* +Z axis by `_cad_mesh_aligned_to_optical_axis`; the 3D inspector then
carries them onto the reflected leg with the anchor row's fold transform
(`_transformed_imported_camera_step_mesh` / `…lens…` render them folded). The export, however, fit its
placement affine to the **un-folded** mesh — so the camera and lens floated on the straight axis
instead of the periscope legs. The camera overlay also used `largest_component=True`, which collapses
the vendor assembly to its densest tiny part (a ~6 mm sensor-window cover) and skews the fit; the
display loads the **whole** assembly (`largest_component=False`).

The **Object Plane** was skipped by an explicit `surface in {"Object","Image"}` guard in both writers.

## Fix

Export each optical-solid row the way it is **drawn**: the STL, carried into world by the display
transform, written as one faceted STEP shell — deterministic, no ambiguous fit. Prisms are
flat-faced, so faceting is lossless.

* `occ_shell_shape_from_mesh(mesh)` (`services/cad_step_export.py`) — one `TopoDS_Shell` from a
  world-placed PyVista mesh's triangles.
* `_row_optical_solid_display_world_transform(system, row_index)` — the exact transform the 3D uses.
  Prefers the **live inspector's own** `_runtime_transform_for_row` (so a saved-STEP-native display
  tier is honoured — requirement "saved or not"); headless, it reproduces the runtime tiers:
  output-port override → else `TRANS_2A` with the same off-beam re-decenter the inspector applies.
* `_optical_solid_row_world_step_shell(row, row_index, system)` — builds the same
  `_stl_mesh_with_world_transform` mesh the inspector renders, then tessellates it.
* `_collect_row_native_step_export_shapes` now branches: a **file-backed STL row**
  (`_file_backed_stl_row_at`) exports via the shell above; a genuine **STEP-only** row (no promoted
  STL) keeps the template + placement-affine path unchanged.
* The **vendor camera + lens overlays** now carry the same fold as the display: their export params
  gained a `fold_transform` (the anchor row's `_optical_axis_fold_world_transform_for_row`), applied to
  the aligned mesh before the placement affine is fit, and the camera switched to
  `largest_component=False` — so both land on the folded legs exactly where the 3D shows them.
* The Object/Image skip was removed from both writers (prior step of this bug), so the Object disc
  and folded Image disc are exported as analytic surfaces.

## Result (display-free, `bugs/diag_step_export_prisms.py`)

Per prism row, the exported shell's **world bbox** vs the display mesh's world bbox:

| row | display bbox center | export bbox center | center Δ | extent Δ |
|---|---|---|---|---|
| j=1 (RA prism1) | `[-0.0, 0.0, 50.0]` | `[-0.0, 0.0, 50.0]` | **0.0000 mm** | **0.0000 mm** |
| j=8 (RA prism2) | `[304.19, 0.0, 50.0]` | `[304.19, 0.0, 50.0]` | **0.0000 mm** | **0.0000 mm** |

End-to-end (`bugs/diag_step_export_end_to_end.py`, writes a real STEP and reads it back):

* `cad_shapes = [Lens STEP, Camera STEP, S1 prism, S8 prism]`; writer counts `(8 analytic, 4 CAD, …)`.
* read-back contains the prism shells at `[0,0,50]` and `[304.19,0,50]` (size `25×25×25`), the
  **Object disc** at `[0,0,0]` (size `116×116`), and the folded **Image disc** near `x=304.19`.

## Not baked: the thickness dimension overlay

Requirement 3 also noted "the thickness overlay is not showing." That overlay is an interactive
**dimension annotation** (`ThicknessDimensionWidget` / `Open3DThicknessDimensionService`: leader
lines + text + draggable anchors, toggled by `show_physical_distances_var`), not a physical element.
Baking measurement annotations into a production STEP **solid** model would import as meaningless
floating edges. Deliberately left out; can be added as opt-in leader-line geometry (like the ray
cylinders) if the user wants it. See status table.

## Guard

`KrakenOS/UI/validate_open3d_step_export_matches_display.py` (display-free), penta **phase 264**:

* **A** PRISMS — every file-backed optical-solid row's exported shell bbox equals its display-mesh
  bbox (center + extents within 0.05 mm).
* **B** OBJECT PLANE — the analytic writer emits the Object row (no `{"Object","Image"}` skip).
* **C** SINGLE SOURCE — the export transform equals `_runtime_transform_for_row` (the 3D's own
  transform), so display and export cannot drift apart silently.
