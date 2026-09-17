# 0810 -- a cache is a recipe

User: "I sometimes see errors when you run validation but ignore them (previous known errors). Can you fix
them all?"

## Census

Running every penta phase on its own (one app per process, scratchpad `census.py`) found phases that
never finish (449-452) and a group that fail with "file not found" or "0 folded rays" (169, 170,
181-194). They had one cause.

## Measured

23 derived files under `attachment/cad_cache` were gone -- Filen had moved them to its trash -- and 15
saved scenes referenced them 132 times. Two kinds:

* **overlay-promoted optical-solid bodies** (`Solid_3d_stl`, `StepOverlayPromotion.mesh_coordinates =
  local_centered_from_open3d_overlay...`);
* **generated beam-splitter template STEPs** (`beam_splitter_templates/bs_<kind>_<sha1>.step`).

The load path could rebuild only bugs/0021's kind: a file-backed solid, re-meshed from
`OpticalSolidSourcePath`. What happened to the rest:

* **Loading hung.** The load opened the missing-assets dialog **modally** (`grab_set` + `wait_window`).
  Phases 449-452 load such scenes, so they waited for their whole deadline: the gate's "hangs".
* **Guards lost their bodies.** Guards that build rows without the load path got a body neutralised
  at system build, so an RA-mirror scene lost its mirror: "0 rays folded" (181-194).
* **bugs/0021 rebuilt overlay bodies WRONG.** It meshes the STEP in its native frame and repoints the
  row at the new file. On ELS85, face S001/F001's centroid came out at x -8.84 where the scene records
  +12.5, so the optical roles were on the wrong triangles.

## The scene already records each recipe

* **Beam-splitter template.** The file name is `bs_<kind>_<sha1(kind|params)[:16]>.step` and the row
  carries `beam_splitter_params`. The recorded parameters are used only if they hash to the name the
  scene asks for.
* **Overlay-promoted body.** It is `step_overlay_promotion`'s own steps: the source STEP through
  `_cad_mesh_aligned_to_optical_axis` (source axis z, front face min, the recorded x/y/roll rotations),
  `_clean_surface_triangulate`, then centred on its bounding box. A resize done before promotion is not
  recorded as a spec, but its result is (`bounds_min_world` / `bounds_max_world`), so a resized
  candidate is tried as well.
* **The proof.** `OpticalSolidFaces` records every face's triangle indices with its area-weighted
  centroid, area and summed normal. A rebuilt body is written only if every recorded face comes out of
  its own triangles again. Measured on the originals: centroid 2e-6 mm, area 4e-6 relative, normal
  exact; accepted within 1e-3 mm, 1e-4 relative and 1e-6.

Checked against the originals recovered from the Filen trash: the overlay bodies come back
**bit-identical** (same triangles, 0.0 vertex deviation) and the template geometry is identical.

## Fix

* `services/cad_cache_recipes.py`:
  * `face_table_mismatch`, the proof;
  * `rebuild_beam_splitter_template`, hash-checked;
  * `rebuild_overlay_promoted_body`, which rebuilds the template first if the source is a missing
    template and writes only a body that passes the face check.
* `layout_import_export._regenerate_missing_optical_solid_caches`: per row, the missing templates, then
  `_rebuild_row_body_cache` for `Solid_3d_stl` and `StepAnalyticBodyStlPath`.
  * An overlay body is rebuilt by its recipe at the **recorded** path, and the row is not repointed.
  * Any other body goes through the bugs/0021 re-mesh, and for `Solid_3d_stl` it must also pass the
    face check.
  * Notes go to `_cad_cache_rebuild_notes` and the debug log.
* `missing_assets_dialog`: relocating a source takes the same `_rebuild_row_body_cache` route.
* **The load no longer waits on the dialog**: `run(..., modal=False, on_resolve=...)`. When it closes,
  `_after_missing_assets_dialog` rebuilds what the relocations made possible and redraws.
* `tools/rebuild_cad_caches.py` rebuilds every scene's caches without loading them. On this machine:
  **rebuilt 21, refused 0, still missing 0**. Scene files are never rewritten.

## Verified

* Guard `validate_open3d_0810_a_cache_is_a_recipe` (penta phase 593), standalone:
  * A: the face table catches a 10 um shift and a re-posed body;
  * B: the template hash, where parameters that hash elsewhere are refused;
  * C: ELS85 (as posed) and 150mm_GN (resized) rebuild identical to the cache, and a tampered face
    table is refused with nothing written;
  * D: the load path rebuilds at the recorded path without repointing;
  * E: the dialog is non-modal and returns at once;
  * F: loading the ELS85 scene with its body moved aside rebuilds it identical.
* Penta phases 447, 449, 450, 451 and 452 pass (470 s; 449-452 had hung).
* One penta run of 16 phases (170 s):
  * **pass**: 169, 170, 183, 185, 186 and 189 (all failed on the missing files before), plus the related
    guards 26 (beam-splitter transmit), 29 (missing solid cache regenerates), 31 (moved element rays),
    495 (0661), 497 (0664), 502 (0669), 506 (0674) and 507 (0680);
  * **still fail, on their own assertions**, which the missing files had hidden:
    * 181: `#2 density: production world_cone on-axis rays too few (65 < 100)`;
    * 194: `two-mirror: after the paraxial snap ... no sensor-reaching on-axis rays`.

    Both are recorded `fail` in `tools/penta_validator_baseline.json`, and 194 flipped on 2026-08-09,
    before this bug. They are the census's next items, not this fix.
