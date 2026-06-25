# 0142 — Heavy STEP overlay rebuilds its silhouette edges cold on every action

## Symptom

> *"Open 3D seems takes longer … and it is live now, still very lag."*
> *"I think slow down after the BS is promoted and overlayed to the LED?"*

With a heavy imported camera STEP (591k triangles) plus the LED plate and a
beam-splitter overlay in the scene, every editing action — dragging an element,
rotating, resizing, unhiding, or just nudging a glued body — stalled the Open 3D
inspector for **3–7 s**. The lag scaled with the number of overlays present: the
timing log showed the per-action spike roughly **double** (≈3.4 s → 5.8–7.2 s) the
moment the beam-splitter ("optical") overlay appeared alongside the camera and LED.

## Root cause

Each imported-CAD overlay is drawn as a semi-transparent mesh plus a **silhouette**
of analytic-face boundary edges. Those edges come from
`face_boundary_edges_from_face_index` — a per-triangle Python walk
(`_edge_records`) that, for every one of the body's triangle-edges (591k tris × 3 =
1.77M iterations on the camera), groups coincident edges and selects the ones shared
by ≥2 analytic faces or lying on an open boundary. Cold, that walk costs **≈31 s on
the camera** and **≈3 s on the LED**.

It was memoised, but only by **`id(mesh)`** (`cached_display_feature_edges`,
`_DISPLAY_EDGE_CACHE`). A re-placement builds a **brand-new mesh object**:
`_cached_transformed_step_overlay` re-bakes the display mesh whenever its placement
signature changes (`layout_polyline_display.py`), and the camera additionally tracks
the image plane (`camera_front_z = image_plane_z − front_to_sensor`). So a glued LED
following its partner, the camera following the image plane, or any drag/rotate/resize
produced a new object whose `id()` **missed** the cache and re-ran the full walk cold —
paid on essentially every action, summed over every overlay present, and amplified
when "show physical distances" is on (16 dims force the slow full-refresh path).

The key observation: `_cad_mesh_aligned_to_optical_axis` deep-copies the body and then
reassigns **only `mesh.points`** — the triangle connectivity and the per-cell
`kraken_step_face_index` are preserved. So the boundary-edge **selection** (which
point-index pairs are silhouette edges) is **invariant** under any rigid/uniform
re-placement; only the coordinates move. The id-keyed cache threw that invariant away
on every move.

## Fix

`KrakenOS/UI/services/open3d_face_index_edges.py` — new `pose_invariant_feature_edges`
(plus `_boundary_edge_index_pairs`, `_line_polydata_from_index_pairs`,
`_mesh_is_analytic_step`):

- Scoped to analytic STEP display meshes (`field_data["kraken_step_analytic"]`, the
  only meshes whose connectivity is a fixed CAD tessellation that re-placement never
  re-meshes). Everything else (row glass, computed surfaces) falls through to
  `cached_display_feature_edges` unchanged.
- Compute the boundary selection **once** as `(M, 2)` **point-index pairs** (a
  vectorised `np.unique`/`np.bincount` equivalent of the `_edge_records` loop —
  verified edge-for-edge identical at the `_point_key` 8-decimal precision), and cache
  it under the body's **intrinsic identity** `(hash(face_index.tobytes()), n_points,
  n_cells, include_open)` rather than `id(mesh)`.
- On a re-placement the new object hits that content key and rebuilds the silhouette
  with a vectorised coordinate gather `surface.points[pairs]` — **no boundary walk**.

`KrakenOS/UI/open3d_inspector.py` — `Kraken3DInspector._display_feature_edges`
(the single staticmethod behind all 7 silhouette call sites) now routes to
`pose_invariant_feature_edges`.

## Verification (`/tmp/verify_0142_fix.py`, cached camera display mesh)

- **Same pose:** `matches_current = True` — the index-pair silhouette is edge-for-edge
  identical to the production loop and to the old `cached_display_feature_edges` output
  (**0-edge drift**), so no visual change.
- **Re-placement (new mesh object, id caches all miss, content key HITs):**
  **76.6 ms** vs the **~31,000 ms** cold walk it replaces — the per-action cost the
  user felt. `drift vs loop re-run at the moved pose = 0 edges`.
- **Cold build** (first time a body is seen) is the vectorised pass: **~6.8 s** on the
  camera vs ~31 s for the Python loop (a ~5x bonus), paid once per body.
- **Non-analytic fallback** still produces edges via the unchanged path.

## Guard

- `KrakenOS/UI/validate_open3d_pose_invariant_edges.py` (`run_checks`, display-free):
  builds a synthetic analytic STEP mesh (unwelded triangle soup + per-cell
  `kraken_step_face_index` + the analytic flag, mirroring the real bake) and pins:
  same-pose faithfulness to the loop **and** to the old cached path; a clean cube
  selects exactly its 12 geometric edges (face-internal diagonals excluded); a rigid
  re-placement **hits the cache without re-running the boundary walk** (a call counter
  on `_boundary_edge_index_pairs`) and the gathered edges equal both the loop re-run at
  the moved pose and the original silhouette carried through the same transform; the
  non-analytic fallback never touches the index cache; and the inspector wiring.
- Penta phase **131** (`phase_131_pose_invariant_step_edges`); baseline → 131 = pass.

## In-app eyeball still owed

Headless cannot drive the embedded-VTK render, so the *visible* silhouette + the felt
responsiveness after a glue-follow / image-plane-track / drag are owed an in-app check.
