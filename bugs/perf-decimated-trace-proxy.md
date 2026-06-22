# perf — Trace planar optical solids against a lossless decimated proxy

Follow-on to `perf-nonseq-mesh-normal-cache.md`. After caching cell normals, the
remaining non-sequential cost on a **metadata-bearing** fine STL solid was still
O(cells): the OBBTree `IntersectWithLine` plus the per-hit face work
(`__OpticalSolidFaceIsInternal`, `__OpticalSolidScenePoints`, plane-match face-id
lookup) all scale with the solid's triangle count, and a promoted vendor cube is
~50× finer than ray intersection needs.

Measured on a 49 k-cell beam-splitter cube **with face metadata** (the real
promoted-solid case), 361 rays warm:

| | cube trace cells | time | per ray |
|---|---:|---:|---:|
| full mesh | 49,152 | 15,125 ms | 41.9 ms |
| **decimated proxy** | **982** | **1,625 ms** | **4.5 ms** |
| | | | **9.3×** |

(Without face metadata the per-hit face work is skipped, so the bare-mesh trace is
already cheap and decimation shows no gain — the win is specifically the
metadata-bearing promoted solid, which is exactly the slow production case.)

## Fix

`MeshRayTrace.decimate_optical_solid_trace_mesh(mesh, world_faces)` returns a
decimated proxy of an optical-solid trace mesh — **but only when it is provably
lossless**: after `decimate_pro` (feature-preserving, topology-preserving), every
proxy cell centroid must still lie within tolerance of an original optical-face
plane with an aligned normal. A planar polyhedron (cube / prism) passes and
collapses ~50×; a **curved** surface (a lens) cannot be decimated without moving
the surface, so a proxy cell drifts off the face planes, the check fails, and the
full mesh is returned unchanged (it still gets the normal cache). Only the
trace geometry (`system.EEE`) is swapped — the display mesh keeps full resolution.

The proxy's cells no longer correspond to the original triangles, so its face ids
are assigned by **plane match**: `assign_mesh_cell_face_ids(..., prefer_plane_match=True)`
skips the exact-triangle-membership path, and the proxy stamps
`KRAKEN_ORIGINAL_CELL_ID = -1` so an `arange` id can never alias a proxy cell to
an original triangle's face. Wired at `KrakenSys.__SceneMeshWithFaceIds` (the
single cached chokepoint that already tags + swaps the trace mesh), so decimation
runs once per solid per refresh and is amortised over every traced ray.

## Lossless verification

- Plate cube: transmit focus with proxy == full mesh, **|Δ| = 0.00000 mm**.
- Beam-splitter cube: the 45° splitter face survives decimation and still fires —
  **98 branch entries from 49 rays, identical with the proxy on or off**.
- NS-trace regression validators (`beam_splitter_branch_detectors`,
  `transmit_and_second_axis`, `moved_splitter_keeps_focus`, `per_branch_pupil`) and
  `bugs/repro_0093.py` trace physics unchanged.

## Tests

- `python -m KrakenOS.UI.validate_nonseq_decimated_trace_proxy` — display-free;
  checks a planar cube decimates with every cell on a face plane, a curved sphere
  is returned unchanged (lossless gate), the end-to-end transmit focus is
  unchanged (proxy on vs off), and the source wiring. Penta **phase 98**
  (baseline → 99).
