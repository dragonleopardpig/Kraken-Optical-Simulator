# perf — Non-sequential mesh trace recomputed solid cell normals per hit

**Symptom:** a post-edit refresh in Open 3D took **seconds to minutes** once the
scene contained a promoted **STL optical solid** (e.g. a beam-splitter cube). The
always-on timing log showed `refresh_from_editor` at a mean of ~19 s and a **max
of 279 s**, dominated by `preview_system_rays_bundle` → `trace_preview_bundles`
on the `NsTraceLoop` (non-sequential) backend at **~80 ms/ray** (sequential is
~0.55 ms/ray; rendering is an innocent ~11 ms/frame).

## Diagnosis

Headless profiling (`tools/perf_ns_mesh_trace.py`, which traces a converging cone
through a BK7 cube STL and reads `MeshRayTrace.reset_mesh_trace_stats` /
`mesh_trace_stats_snapshot`):

- The actual ray-mesh intersection (`vtkOBBTree.IntersectWithLine`) was only
  ~8–12 % of the wall; intersections/ray was a constant 5.0.
- Yet total wall scaled hard with mesh cell count (273 ms @ 12 cells →
  **1494 ms @ 49 k cells**) while the **transmit focus was bit-identical at every
  tessellation** — so there was large O(cells) work *outside* the intersection.

`cProfile` of the 49 k-cell trace pinned it: **`InterNormalCalc.__InterNormalSolidObject`
→ `pyvista cell_normals` → `compute_normals` → VTK `Update()` = 0.946 s of a
1.695 s trace (≈ 70 %)**. PyVista's `mesh.cell_normals` property re-runs the full
`compute_normals` pipeline over every cell on **each access**, and the per-hit
normal lookup reads it once per ray-solid intersection (242 times here). The
normals were recomputed hundreds of times for geometry that never changes during
a trace.

## Fix

`MeshRayTrace.mesh_cell_normals(mesh)` computes the cell-normal array **once** and
caches it in the mesh's `cell_data` (key `KrakenCellNormals`); the cache lives and
dies with the mesh object, so a resized / re-promoted solid (a new object) gets
fresh normals. `InterNormalCalc.__InterNormalSolidObject` reads it at the per-hit
normal lookup instead of the recomputing property. The cached values are
identical to the property, so **the trace optics are unchanged**.

## Measured result (`tools/perf_ns_mesh_trace.py`)

| cells | wall before | wall after | focus z (both) |
|------:|------------:|-----------:|---------------:|
| 3,072 | 393 ms | 180 ms | 213.67 |
| 12,288 | 628 ms | 235 ms | 213.67 |
| 49,152 | 1494 ms | **445 ms (3.4×)** | 213.67 |

`cProfile` total 1.695 s → **0.564 s**; the `compute_normals`/`Update()` hot path
is gone. The win grows with mesh fineness — exactly the fine vendor STL→STL
solids that triggered the minutes-long traces.

A **decimated trace proxy** (lever #1, the cube decimates losslessly) stacks on
top: 49 k → 1.2 k cells gives a further ~2.7× with `|Δfocus| = 0`. Remaining
levers for the multi-element production case: sparser NS preview fan + fewer
redundant per-branch bundles + not `force_retrace`-ing on every edit.

## Tests

- `python -m KrakenOS.UI.validate_nonseq_mesh_normal_cache` — display-free; checks
  the cache returns property-equal values + caches in `cell_data`, the source
  wiring, and that the transmit focus is invariant across tessellation (lossless).
  Penta **phase 97** (baseline → 98).
- NS-trace regression validators still pass (`beam_splitter_branch_detectors`,
  `beam_splitter_transmit_and_second_axis`, `moved_splitter_keeps_focus`,
  `per_branch_pupil`, `detector_hard_stop_clip`); `bugs/repro_0093.py` trace
  physics unchanged.
