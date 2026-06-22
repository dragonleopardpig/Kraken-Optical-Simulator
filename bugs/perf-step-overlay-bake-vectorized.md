# perf — Vectorise the STEP-overlay face-metadata bake ("Open 3D takes a while")

**Report (live, 2026-06-23):** "Open 3D takes quite a while."

The always-on timing log named it immediately — a single cold **camera STEP
face-metadata bake = 50.5 s**, the LED baked twice (~10.5 s), plus the
import overheads:

```
step_overlay_face_metadata_done   50560 ms   (camera)
step_overlay_face_metadata_done    5405 ms   (led)
step_overlay_face_metadata_done    5141 ms   (led)
import_optical_step_overlay_done  13305 ms
import_step_overlay_done           9551 ms
```

bug 0111 already caps this bake to **once per session** (pose-blind cache), but
the first bake on every fresh launch / first STEP selection still pays the full
cost — so it reads as "Open 3D takes quite a while".

## Diagnosis

`cProfile` of `cluster_optical_solid_planar_faces` on the camera snap STL
(591,272 triangles) = **91 s**, entirely a **per-triangle Python loop**:
`np.cross` 34 s, `_canonical_optical_solid_plane` (incl. `unit_vector_tuple`)
15.7 s, `np.round` 9 s, `np.linalg.norm` 7.7 s, plus 18.5 s of loop body — one
numpy call *per triangle* over 0.6 M triangles. A second, smaller per-triangle
loop in the binary STL reader cost ~1 s.

## Fix

Both per-triangle Python loops are replaced by numpy batch ops:

- **`cluster_optical_solid_planar_faces`** (`optical_solid_geometry.py`): cross /
  norm / area / centroid / canonical-plane are computed across all triangles at
  once; triangles are grouped with `np.unique` on the rounded canonical plane;
  the area-weighted normal / centroid / plane-offset sums are accumulated with
  `np.bincount`; faces are ranked by area with `np.lexsort` so the F-number
  tie-break among **equal-area** faces still follows the original first-appearance
  order. Result: **91 s → 2.9 s (~31×)**.
- **`read_stl_triangle_vertices`** (`stl_geometry.py`): the binary path reads the
  whole triangle block in one structured `np.frombuffer` instead of a
  per-triangle `frombuffer` loop. **1.0 s → 0.034 s (~29×)**, byte-identical.

Full post-read metadata pipeline (cluster + role assign + normalise):
**~92 s → ~3 s**. The cold camera bake drops from ~50 s to a few seconds.

## Lossless verification

Bit-identical, not merely close: the grouping key (rounded canonical plane) is
unchanged, and the per-group area-weighted sums accumulate in **ascending
triangle-index order** in both implementations (`np.bincount` walks the input in
order), so the float reductions match. Verified against the real camera STL:
all 160 face candidates match face-for-face (id, normal to 1e-9, centroid/area
to 1e-6, plane offset, triangle count, and the per-face triangle-index list).
The STL reader is byte-for-byte identical.

## Tests

- `python -m KrakenOS.UI.validate_open3d_step_overlay_bake_vectorized` —
  display-free; reimplements the original loop as an independent brute-force
  reference and asserts the vectorised clustering matches face-for-face
  (including a cube's six equal-area tie-break), the binary STL reader is
  byte-identical, a plain cube clusters to 6 axis-aligned faces, and the source
  carries no per-triangle Python loop. Penta **phase 101** (baseline → 102).
- Face-clustering regressions still pass (`validate_open3d_optical_solid_face_grouping`,
  `validate_optical_solid_face_fit`, `validate_optical_solid_path_fit`); the three
  NS-trace perf validators still pass.

## Follow-up (not done here)

The snap STLs accumulate one ~29.5 MB file per distinct transformed pose under
`attachment/cad_cache/step_overlay_face_snap/` (≈16 camera copies = ~470 MB
observed). A small LRU/prune of that dir would reclaim disk; out of scope for
this latency fix.
