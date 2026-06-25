# 0148 — STEP face hover/pick outline re-walks the whole body every mouse-move

## Symptom

> *"confirm super lag, please look into it now."* … *"it is freezing, I
> actually can't click anything."*

Hovering (or clicking) a face of a heavy imported vendor STEP body froze the GUI
for **tens of seconds per mouse-move** — the window stopped repainting and
swallowed clicks. The user also noted the puzzle that pinned the cause:

> *"150mm machine vision lens don't have this problem, 85mm has, that make me
> puzzled."*

The 85mm PYRITE vendor STEP (`1072517`) tessellates to **~55k triangles** at the
display deflection (0.2 mm); the 150mm (`15056`) to **~23k** — about 2.4× lighter.
A vendor camera body is heavier still (~591k cells, the bug 0146 case). The freeze
tracks **triangle count, not focal length** — which is exactly what an O(triangles)
per-hover cost looks like.

## Root cause

`face_outline_from_face_indices`
(`KrakenOS/UI/services/open3d_face_index_edges.py`) drives the hover/pick
face-outline highlight (`_hover_overlay_for_step_face_impl` →
`open3d_inspector.py`). On **every** mouse-move it rebuilt the body's entire
triangle-edge dictionary from scratch:

```python
for records in _edge_records(triangles, face_index).values():
    ...
```

`_edge_records` walks all `3T` triangle-edges and keys each by
`_edge_key` → `_point_key`, which calls scalar `np.round(coord, 8)` **per
coordinate** to unify coincident-but-distinct STEP seam vertices. For the 591k
camera that is ~10.6 M scalar rounds plus ~1.77 M Python dict inserts **per
hover**, on the Tk main thread — 30–56 s of dead GUI. py-spy (`record -f raw`,
4194 samples while the user confirmed the freeze) caught the main thread 94.7 % in
`face_outline_from_face_indices` → `_edge_records`/`_point_key`, ~34 % leaf in
`numpy.round`, reached from both `_on_mouse_move` (38.9 %) and the click handlers
(61.1 %).

The topology this computes — *which triangle-edges share a rounded-coordinate
vertex, each edge's face id, its point-index pair* — is **target-independent and
pose-stable**: it does not change as the cursor moves across faces of the same
body. Bug 0146 already gave the *silhouette* path
(`_boundary_edge_index_pairs`) a vectorised, cached, integer-coord-id treatment;
the hover/pick *outline* path never got it and kept doing the full scalar walk
each time.

## Fix

Compute the edge topology **once per body** (vectorised) and cache it; each hover
then selects one face group's outline with a boolean mask. Three new helpers
mirror bug 0146's coordinate-id + packed-int64 edge key:

- `_face_outline_edge_topology(surface, face_index)` — `np.unique(points, axis=0)`
  → per-point coordinate id (coincident seam duplicates collapse), canonical
  `lo*stride+hi` int64 edge key, then one 1-D `np.unique` → `(inv, counts, fids,
  rep0, rep1, n_uniq)`. Returns `None` (→ scalar fallback) for any non-triangle /
  malformed mesh.
- `_cached_face_outline_edge_topology(mesh, surface, face_index)` — memoised on
  `id(mesh)` + `_mesh_cache_token(mesh)` (`n_points, n_cells, GetMTime()`), LRU of
  8. `mesh is None` bypasses the cache (used by the guard).
- `_face_group_outline_pairs_from_topology(topo, targets)` — the selection
  `(target_per_edge > 0) & ((counts == 1) | (target_per_edge < counts))`, i.e.
  *touches a target face AND is not fully interior to the group*. The
  representative point-pair is the **first** target triangle-edge in cell-major,
  edge-(0,1)/(1,2)/(2,0) order — byte-for-byte the scalar walk's choice.

`face_outline_from_face_indices` tries the cached topology first and falls back to
the unchanged scalar walk on `None` or any mismatch:

```python
topo = _cached_face_outline_edge_topology(mesh, surface, face_index)
if topo is not None:
    pairs = _face_group_outline_pairs_from_topology(topo, targets)
    if pairs is not None:
        return None if pairs.shape[0] == 0 else _line_polydata_from_index_pairs(surface.points, pairs)
# ... scalar _edge_records walk (fallback) ...
```

The per-hover cost collapses from a full O(triangles) walk to a cache hit + a few
boolean masks; the heavy `np.unique` runs once per body (and is shared with no
other path). Edge selection is **edge-for-edge identical** to the old walk.

## Verification

- `KrakenOS/UI/validate_open3d_face_outline_fast.py` (`run_checks`, display-free) —
  10/10 PASS on a synthetic two-quad mesh whose shared seam vertices are
  **duplicated with coincident coordinates** (the analytic STEP seam the rounding
  unifies): vectorised == scalar for `{0}`, `{1}`, `{0,1}`; the seam is on each
  single-face outline but DROPPED from the two-face group; outer edges kept,
  interior diagonals never drawn; topology builds with `mesh=None`; and a source
  marker that `face_outline_from_face_indices` consults
  `_cached_face_outline_edge_topology`.
- Full penta-telescope suite green except the **pre-existing**
  `validate_open3d_lens_step_face_pick` failure (branch debt — see Guard note);
  proven unrelated by stashing this edit and reproducing the same failure.

## Guard

- `KrakenOS/UI/validate_open3d_face_outline_fast.py` as above.
- Penta phase **137** (`phase_137_face_outline_fast`); baseline → 137 = pass
  (138 phases, 0–137).
- The source marker means a revert to the pure scalar walk (the 30–56 s freeze) is
  caught.

## Pre-existing failure (NOT caused by this fix)

`validate_open3d_lens_step_face_pick` fails on this branch independently of 0148:
its source-marker check looks for `_display_feature_edges_mesh` inside
`inspect.getsource(Kraken3DInspector)` (the class body), but that symbol is a
**module-level import alias** (`open3d_inspector.py:39`), so it is never in the
class source. Stashing the 0148 edit reproduces the identical failure. Left as
branch debt; documented here so it is not mistaken for a 0148 regression.

## In-app eyeball still owed

Headless cannot drive the embedded-VTK hover/pick, so the *felt* result — hover
the 85mm (and the heavier camera) body and confirm the outline highlight is
instant with no GUI freeze — is owed an in-app check.
