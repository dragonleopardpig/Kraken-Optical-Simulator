# 0370 — Measure E/E overhaul: CAD-style entity picks off the picked cell

**Flag:** 20260720_130210_274 (build 1800eb3e) — "Measure E/E can't hover highlight, click edge no
function." User: "we really need to overhaul the Measure Edge-Edge. I need it to behave like common
CAD software click and measure." **Status:** SHIPPED 2026-07-20 (guard rewritten, penta phase 306).

## Why the old architecture could never work (forensics from the recording)

Nine clean clicks (≤3 px) in 20 s — every one resolved to NOTHING. The chain was
`_measure_resolve_snap` (9 px magnetism) → recognised-component GATE → step-label recovery →
`_step_component_edge_outline` (the sparse DRAWN edge actors) → 14 px screen test: five independent
None-exits, and on the user's scene (camera+lens HIDDEN → non-pickable per 0351, zoomed inside the
hollow CO90) every click died in the ladder; the 0367/0369 point fallback itself returned empty
through a blanket except. The two failure statuses were then OVERWRITTEN by the hover's
unconditional per-move status writes — so the tool looked completely dead. The hover highlight was
absent BY DESIGN since 0369. And the deepest bug of all, masked since 0353 by a stubbed test fake:
**the arm sequence set `_measure_pending_edge` then called `_show_measure_pending_edge`, whose first
line `_clear_measure_pending_edge()` NULLED the freshly armed state — edge+edge never completed
in-app, ever.**

## The overhaul

- **One resolver, `_measure_resolve_entity(x, y)`:** `vtkCellPicker.Pick` → actor + world +
  cell_id; the entity resolves on the picked actor's OWN mapper-input mesh (the cell id is aligned
  with it by definition). Face via `kraken_step_face_index` cell data → cached
  `face_outline_from_face_indices` (topology walks once per mesh, per-face masks ~ms); no-face-index
  meshes (promoted STL bodies, analytic discs) → `cached_display_feature_edges`. Nearest boundary
  segment within 18 px (front-depth ranked) → **EDGE** (collinear run); else **FACE** (boundary
  segment set); else **POINT**. No recognised gate, no drawn actors: what you can see, you measure.
  Pick failures leave an `append_debug` breadcrumb, never a silent None.
- **Entities as segment sets:** `services/measure_edge_pick` gained
  `outline_pairs_to_segments` / `polyline_to_segments` / `closest_point_on_segments` /
  `closest_points_between_segment_sets` / `reduce_measure_entities` — edge+edge and face+face give
  the closest pair (opening width, plate gap), anything+point projects. All reduce to two world
  points, so the segment/label/offset/persistence/export pipeline is untouched.
- **Click flow:** first pick ARMS with a persistent orange highlight (show helper clears ACTORS
  ONLY — state lifecycle belongs to the callers) + status; second pick completes (pending cleared
  before the reduce, strand-proof); reanchor and plain-measure p0 interop preserved; a click on
  nothing says so explicitly. Entity mode ends with the measurement (zombie flag fixed).
- **Hover:** real highlight again — one cell pick + cached outline per move, CHANGE-GATED on the
  hover entity key: unchanged entity = no actor work, no render, NO status write (click results
  survive). Cursor signals pickability.

## Guard lesson institutionalised

The integration fakes now bind the REAL `_show_measure_pending_entity` (only renderer plumbing
stubbed) — a stubbed draw helper is how the state-nulling bug stayed green for five iterations.
Needles: resolver must use GetCellId/face-index/feature-edges and must NOT reference the old
gate/drawn-actor chain; show helper must not call the state-clearing helper; arm draws before
assigning state; hover change-gated; every-click-visible string present.
