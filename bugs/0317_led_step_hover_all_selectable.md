# 0317 — Imported-LED STEP hover: "only a few can be selected as highlight" + wrong edge

## Flag
`attachment/recorded_bug_repros/flag_20260715_133849_947/`:

> *"mouse hover imported LED STEP: is not intuitive, the highlight is not the nearest edge, and only a
> few can be selected as highlight."*

The user elaborated they need the hover to *"select surface or edges, especially when I want to align it
to the optical axis."* Two distinct defects: (1) most of the LED body would not highlight at all on
hover, and (2) when a highlight did appear it lit the whole clustered face, never the edge nearest the
cursor — so an edge-to-axis alignment gesture had nothing to grab.

## Root cause — the pick crossed two different meshes, and only 21.4% of cells lined up
A vendor LED is drawn as an **analytic** STEP body (`_mesh_from_step_analytic_document`): every triangle
carries a per-cell `kraken_step_selection_face_index`. On the real LED (`OPT-CO90-X-V1.6.2-H.STEP`) that
is **60138 cells over 714 analytic faces, 100% indexed**. So the geometry to highlight any patch was
already present on the display mesh.

But the hover PICK did not read that per-cell index directly. `face_pick_from_display_cell` resolved a
picked cell to a highlight **only when the cell's face index mapped to a METADATA record**, and those
records come from planar **clustering capped at 160 faces** (`cluster_optical_solid_planar_faces`), built
on a **separately re-triangulated / re-saved STL** (`_step_overlay_face_metadata_compute` strips the cell
data, `extract_surface` → triangulate → saves a NEW STL). The two meshes don't share indices, so the
cross-mesh mapping only aligned for **165 of 714 faces → 12870/60138 cells (21.4%)**. Roughly four-fifths
of the body returned `None` on hover — exactly *"only a few can be selected as highlight."*

Measured on the real LED analytic cache (decisive):

| | cells with a face index | faces referenced by a record | cells that could highlight |
|---|---|---|---|
| **OLD** (metadata-record path) | 60138/60138 (100%) | 165/714 | **12870/60138 (21.4%)** |
| **NEW** (raw per-cell fallback) | 60138/60138 (100%) | n/a | **60138/60138 (100%)** |

## Fix — highlight the cell's OWN face group, then refine to the nearest edge
`KrakenOS/UI/services/open3d_face_index_edges.py` (all-selectable) +
`KrakenOS/UI/services/open3d_round_lens_pick.py` (edge refinement):

1. **`raw_face_feature_for_display_cell(mesh, cell_id)`** — an all-selectable fallback that needs **no
   metadata record**. It reads the picked cell's own `kraken_step_selection_face_index`, groups every
   triangle sharing that index (`triangles_for_face_indices`), builds the group's boundary outline
   (`face_outline_from_face_indices`), and returns an area-weighted centroid + summed-cross normal.
   Coverage **21.4% → 100%**. Wired into `step_feature_pick_for_display_xy` **after** the metadata
   cell-pick returns `None` and **before** the coarse-ray fallback, so records still win when present
   (nothing regresses) and the raw group catches everything else.

2. **`nearest_display_edge` + `_edge_refined_feature`** — when the cursor is within a pixel tolerance
   (14 px) of a projected outline segment, refine the whole-face highlight to that **single nearest
   edge** (midpoint feature point, single-segment overlay), keeping the face normal. This is the
   *"highlight the nearest edge"* half and gives an edge-to-axis alignment something to grab.

   The hover dedup keys on `face_id` (`_set_step_hover_outline` early-returns when the key is unchanged),
   so a per-edge highlight must vary the key or it never updates. The refined feature therefore tags the
   `face_id` as `f"{base}e{ordinal}"`. Safe because `face_id` is a display/annotation string only —
   `selected_feature_action` matches on label + pick_point/normal and **never re-looks-up by face_id** —
   so the suffix cannot break click alignment.

3. **Latent PyVista bug fixed in passing** — the OLD face-pick's centroid/normal fallback called
   `pv.wrap(mesh).cell_points(cell_id)`, removed in PyVista 0.44+ (this box runs 0.48). Every call raised
   `AttributeError` and was swallowed; it was masked in production only because a VTK `pick_point` and a
   record `normal_world` normally stand in. New `_display_cell_point_array` prefers `get_cell().points`
   and falls back to the legacy name.

Per *"guard the invariant, not the instance"*: the invariant is **every patch the LED body draws must be
hoverable straight from its own per-cell face index — never gated on a lossy second mesh.**

## Verified (display-free)
`KrakenOS/UI/validate_open3d_led_step_hover_all_selectable.py` — **PASS**:
- **A** all-selectable delta: on a synthetic analytic mesh whose face 0 has **no** record, the OLD path
  returns `None` for face 0 while `raw_face_feature_for_display_cell` returns a finite feature; a face
  **with** a record stays selectable both ways.
- **B** raw-feature shape: real boundary outline (≥4 edges for a square), centroid `(2,2,0)`, unit
  axis-aligned normal.
- **C** pure nearest-edge: catches the segment nearest a fake cursor, `None` beyond tolerance, `None`
  when the projector fails, stable ordinal; `line_segment_pairs` / `single_edge_polydata` round-trip.
- **D** edge-refine contract: whole-face feature far from any edge, single-edge feature + suffixed
  `face_id` near one, preserving the `(point[3], overlay, normal[3])` tuple.
- **E** source wiring: `step_feature_pick_for_display_xy` funnels through both the raw-face fallback and
  `_edge_refined_feature`.
- **F** real-LED bonus (cache is gitignored → skips cleanly when absent): raw-fallback covers **401/401
  = 100%** of sampled cells.

Penta **phase 279** (`phase_279_led_step_hover_all_selectable`) delegates to the guard; baseline updated
(`"279": "pass"`).

## Files
- `KrakenOS/UI/services/open3d_face_index_edges.py` — `raw_face_feature_for_display_cell`,
  `line_segment_pairs`, `_point_segment_distance_2d`, `nearest_display_edge`, `single_edge_polydata`;
  `_display_cell_point_array` (PyVista-version-robust cell vertices) behind `_display_cell_centroid` +
  the face-pick normal fallback.
- `KrakenOS/UI/services/open3d_round_lens_pick.py` — `_edge_refined_feature` + raw-face fallback wired
  into `step_feature_pick_for_display_xy`.
- `KrakenOS/UI/validate_open3d_led_step_hover_all_selectable.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_279`.
- `tools/penta_validator_baseline.json` — phase 279 baseline + title.

## Notes / remaining
- General across lens/camera/LED: the fallback keys only on the display mesh's own per-cell face index,
  not on anything LED-specific, so any analytic STEP body (round lens, box camera) gets full coverage.
- The LED STEP and its analytic cache are **gitignored**, so a fresh clone can't run check **F**; the
  synthetic core carries the guarantee and F is a dev-box bonus.
- In-app eyeball owed (needs a GLX display): import the LED STEP, sweep the cursor over the body and
  confirm every patch highlights, and that hovering near an edge lights the nearest edge (not the whole
  face) — the target gesture for aligning an edge to the optical axis.
