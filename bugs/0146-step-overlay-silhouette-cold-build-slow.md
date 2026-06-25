# 0146 — Heavy STEP overlay silhouette is still seconds-slow to build cold

## Symptom

> *"please fix the super lagging, I can't even use it for anything useful now."*

With the PYRITE camera STEP overlay (591k triangles) in the scene, the first time
each heavy body is drawn — initial load, an unhide, a promote, the first refresh
after a glue — the Open 3D inspector froze for **multiple seconds** on the UI
thread. Bug 0142 had already removed the *per-action* re-walk (a re-placed body
now reuses a cached point-index silhouette), but the **cold first build** of a
heavy body was untouched and still cost several seconds each time a new body
appeared, so the app still felt unusable.

## Root cause

The silhouette of an imported analytic STEP body is its set of analytic-face
boundary edges, selected by `_boundary_edge_index_pairs`
(`KrakenOS/UI/services/open3d_face_index_edges.py`). That selection deduplicates
the body's triangle-edge soup (591k tris × 3 = **1.77 M edges** on the camera) and
groups coincident edges so it can keep the ones shared by ≥2 analytic faces or
lying on an open boundary.

The dedup keyed each edge on its **pair of rounded 3-D coordinates** — a 6-float
row — and ran the grouping with `np.unique(keyc, axis=0, …)` plus a second
`np.unique(np.stack([inv, fids]), axis=0)`. `np.unique(axis=0)` is a full
**lexsort over structured rows**; over 1.77 M six-float rows that is the entire
cost. Profiled on the real vendor meshes:

| body | cells | cold `_boundary_edge_index_pairs` |
|------|------:|----------------------------------:|
| camera `3D_CAD_HR25xCXP` | 591,359 | **≈5.1 s** |
| lens `1072517_00165969_001` | 39,630 | **≈0.31 s** |

That multi-second pass ran on the UI thread for every newly-shown heavy body.

The key observation: an analytic STEP body has *many coincident points with
distinct indices* along shared face seams (the bake is unwelded triangle soup),
so an edge's identity is really its **unordered pair of coordinate-IDs**, not its
raw 6 floats. Resolving each point to a coordinate-ID is one `np.unique` over the
**3-float points** (295k rows on the camera) — far smaller than the 1.77 M
six-float edge rows — after which the canonical edge pair packs into a single
int64 and every dedup pass becomes a cheap **1-D** `np.unique`.

## Fix

`KrakenOS/UI/services/open3d_face_index_edges.py` — rewrote
`_boundary_edge_index_pairs` to use an integer coordinate-id key (and removed the
now-dead `_coord_rows_gt` helper):

- `np.unique(points, axis=0, return_inverse=True)` resolves every point to a
  `coord_id` once (coincident duplicates collapse to one id).
- Each triangle edge becomes `(coord_id[e0], coord_id[e1])`, canonicalised
  `lo ≤ hi` and packed into one int64 `edge_key = lo * stride + hi`.
- `np.unique(edge_key, …)`, a `combo = unique(edge_local * face_stride + fid)`
  to count distinct faces per edge, and `np.bincount` — all **1-D** — reproduce
  the exact same `distinct_faces > 1` / open-boundary selection, returning the
  same `(M, 2)` point-index pairs (the representative index per edge is preserved
  so the result still survives re-placement, per bug 0142).

The selection logic, the per-pose cache (`pose_invariant_feature_edges`), and the
silhouette that bug 0020 deliberately keeps for heavy bodies are all unchanged —
this only swaps the dedup key.

## Verification (`/tmp/cmp_boundary_pairs.py`, same process, real vendor meshes)

Committed-old vs the live integer-key implementation, edge sets compared:

| body | include_open | old | new | speedup | identical |
|------|:------------:|----:|----:|:-------:|:---------:|
| lens 39,630 cells | True | 306.8 ms | 47.7 ms | 6.4× | yes |
| lens 39,630 cells | False | 259.7 ms | 41.2 ms | 6.3× | yes |
| camera 591,359 cells | True | 5139.9 ms | 1176.7 ms | 4.4× | yes |
| camera 591,359 cells | False | 5019.8 ms | 1127.2 ms | 4.5× | yes |

The camera silhouette — the body that dominated the freeze — drops from ≈5.1 s to
≈1.2 s, edge-for-edge identical for both boundary modes.

## Guard

- `KrakenOS/UI/validate_open3d_boundary_pairs_fast.py` (`run_checks`,
  display-free): a synthetic analytic STEP body (unwelded triangle soup with
  coincident duplicate vertices, so the dedup path is genuinely exercised) pins
  that the integer-key selection is edge-for-edge identical to the reference walk
  `face_boundary_edges_from_face_index` for **both** `include_open` flags; that
  `include_open=False` is a subset of `True`; that a clean cube selects exactly
  its 12 geometric edges; that degenerate inputs (no triangles / all face ids
  negative) return an empty `(0, 2)` array; and source markers that the integer
  coordinate-id key is present and the old 6-float `_coord_rows_gt` lexsort is
  gone (so a revert is caught).
- The pose-invariance contract (bug 0142) is still pinned by
  `validate_open3d_pose_invariant_edges.py` / penta phase 131, which re-ran green
  against the rewritten function (same-pose identical to the loop and the old
  cached path, 0-drift re-placement, cube = 12 edges).
- Penta phase **135** (`phase_135_boundary_pairs_fast_int_key`); baseline → 135 =
  pass.

## In-app eyeball still owed

Headless cannot drive the embedded-VTK render, so the *felt* responsiveness on
first-showing the camera body (and that the visible silhouette is unchanged) is
owed an in-app check.
