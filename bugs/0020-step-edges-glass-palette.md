# 0020 — Imported CAD optical solids drew a heavy black wireframe; the vendor camera body had no outline at all

**Status:** Fixed (2026-06-05).
**Component:** Open 3D scene refresh — the STEP/STL edge palette in
`KrakenOS/UI/services/open3d_scene_refresh.py` (file-backed rows + overlay
rebuild), `KrakenOS/UI/services/open3d_step_overlay_refresh.py` (targeted
single-overlay redraw), and feature-edge extraction in
`KrakenOS/UI/services/open3d_face_index_edges.py`.
**Reported via:** in-app recorder (latest flagged recording). **Repro bundles
are gitignored**, so the evidence is transcribed here. Saved repro prescription:
`attachment/machine_vision_150mm_measured_test.py` (8 surfaces; S6 is a promoted
beam-splitter **cube**, BK7, promotion display label `"led"`, mesh z≈200–225;
`SETTINGS` also loads two transient STEP overlays — the imaging lens
`attachment/Lens/15056/15056.STEP` and the vendor camera
`attachment/Cameras/3D_CAD_HR25xCXP.STEP`). These vendor CAD files are not
checked into git.

## Symptoms (user's words)

The optical/STEP element edges rendered as a thick **black wireframe cage**
instead of the nice teal "glass" outline the analytic lenses use; the imaging
lens STEP wanted that nicer palette too; and the camera STEP had **no outline at
all** — a flat translucent slab. The user also asked, pointedly:

> why do we need "mesh" in camera? Can't we just import as it is? It is just for
> illustration purpose.

(Answer, for the record: a STEP file is B-Rep — analytic trimmed surfaces. VTK
only draws triangles, so *any* on-screen display requires tessellation; there is
no "show the B-Rep as-is" path. The camera is purely an illustration prop, so the
right fix is the cheap one — give it the same teal outline as everything else,
computed once, not a bespoke renderer.)

## Root cause

Two independent gates kept imported CAD solids off the glass palette.

**Facet 1 — the edge palette was gated on the display label `"optical"`.**
Analytic lenses and overlays tagged `"optical"` got the teal glass palette
(`_OPTICAL_STEP_EDGE_COLOR` `(0.026,0.512,0.528)` / `_OPTICAL_STEP_SILHOUETTE_COLOR`
`(0.014,0.279,0.288)` at `_GLASS_EDGE_LINE_WIDTH` 2.0 / `_GLASS_EDGE_SILHOUETTE_WIDTH`
2.8). Every other imported solid fell through to a legacy heavy black wireframe:
`_solid_silhouette_edge_color()` returned `(0.005,0.007,0.014)` drawn at width
**5.0**, plus `_solid_edge_color_from_body()` (the body colour darkened to ~16%)
at width **3.2**. The beam-splitter cube's promotion label is `"led"`, and the
imaging-lens overlay's label is `"lens"` — neither is `"optical"`, so both wore
the black cage.

**Facet 2 — heavy meshes skipped edge extraction entirely.** Both the overlay
rebuild and the targeted overlay redraw guarded edge extraction behind
`heavy_cad_mesh = n_cells > 50000`. The vendor camera body is **113,972 cells**,
so it tripped the guard and drew with *no* feature edges — the "no outline at
all" the user saw. (The guard existed because the camera's clean face-index
boundary path can't resolve it — 113,972 cells vs 113,952 polygon triangles, 20
stray line cells — so it falls back to geometric `extract_feature_edges`, ~450 ms
and ~52k segments. That was deemed too slow to run every frame.)

## Fix

Make the palette uniform and make the heavy-mesh extraction cheap enough that the
skip is unnecessary.

* **`open3d_scene_refresh.py`** — the file-backed edge colour/width are now
  unconditionally the glass palette (`file_backed_edge_color`,
  `file_backed_silhouette_color`, widths 2.0 / 2.8); the `row_step_label ==
  "optical"` branch that downgraded everything else to black is gone. The overlay
  edge block always extracts edges and paints them glass; the `heavy_cad_mesh`
  >50k skip is removed.
* **`open3d_step_overlay_refresh.py`** — the targeted single-overlay redraw now
  mirrors the same policy (glass palette, no skip), so a partial refresh of one
  overlay matches a full rebuild.
* **`open3d_face_index_edges.py`** — new `cached_display_feature_edges`
  memoises `display_feature_edges` keyed on mesh identity + a content token
  (VTK MTime), mirroring the existing surface-triangle cache. Overlay meshes are
  already memoised one stable object per layout pose, so the camera's geometric
  edges are computed **once per pose**, not per frame — the reason the >50k skip
  could be dropped safely.
* **`open3d_inspector.py`** — `_display_feature_edges` is rewired to the cached
  wrapper for every caller, and the now-unused `_solid_edge_color_from_body` /
  `_solid_silhouette_edge_color` static helpers are deleted.

After the fix the cube, the imaging-lens overlay, and the camera overlay all wear
exactly one teal glass edge palette; the camera body is outlined like the lens.

## Tests

* **Source-invariant contract** — `validate_3d_interaction_contract.py`'s
  promoted-optical-solid display contract now asserts the uniform glass palette
  and pins the legacy black silhouette `(0.005,0.007,0.014)`, the
  `_solid_edge_color_from_body` helper, and the 5.0 / 3.2 widths as **absent**
  from the refresh path. Fixture-free, so it runs on a clean checkout.
* **Render guard** —
  `KrakenOS/UI/validate_open3d_step_edges_glass_palette.py`
  (`python -m KrakenOS.UI.validate_open3d_step_edges_glass_palette`). Boots a
  private Xvfb, loads the repro cube+lens+camera scene, and asserts: the
  file-backed cube (row 6, label `"led"`) carries both glass edge actors
  (silhouette @ 2.8, edge @ 2.0) with **no** actor using the legacy black colour
  or the 5.0 / 3.2 widths; the camera and lens overlays each gain ≥2 glass edge
  actors (the >50k skip is gone); and a render framed on the cube shows teal edge
  pixels with the black cage absent. Each element whose vendor STEP / CAD cache is
  missing is a SKIP, not a failure. Verified fail-before / pass-after by stashing
  the fix:

  | signal | pre-fix | post-fix |
  |---|---|---|
  | cube edge actors | legacy black `(0.005,0.007,0.014)` @ 5.0 + darkened @ 3.2 | glass `(0.014,0.279,0.288)` @ 2.8 + `(0.026,0.512,0.528)` @ 2.0 |
  | camera overlay glass edge actors | **0** (>50k skip) | **≥2** |
  | lens overlay glass edge actors | **0** | **≥2** |
  | cube render near-black edge pixels | **603** | **9** (axis gnomon) |
  | cube render teal pixels | 7,703 (bodies only) | 18,428 |

* **Regression / end-to-end** — `Phase 28`
  (`phase_28_step_edges_glass_palette`) in
  `validate_open3d_penta_telescope_comprehensive.py` wraps `run_checks()`. Gate
  baseline regenerated (`tools/penta_validator_baseline.json`).
* **Visual** — the repro scene was rendered off-screen under Xvfb on 2026-06-05,
  framed on each element in turn and inspected by eye: the beam-splitter cube
  shows a clean teal-edged glass box with its 45° splitter face visible inside;
  the imaging-lens overlay shows the lens groups in the teal glass palette; and
  the 113,972-cell camera body now carries a coherent teal feature-edge outline
  (panel seams, mount circles, screw holes) instead of an edge-less slab — busy
  because the vendor body genuinely has that much structure, but reading as a CAD
  prop, not noise.
