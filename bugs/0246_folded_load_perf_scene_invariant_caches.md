# 0246 — Folded 3D initial load >60s after the 0243 real-trace rework

## Symptom
User: "after last night fixed, the initial load of 3D seems more than 60s." The bugs/0243
rework (folded scenes traced on the REAL system instead of an unfolded straight-equivalent)
made the folded promoted-RA-mirror preview noticeably slower to open.

## Root cause
0243 routes the folded preview through the FULL dense-mesh non-sequential trace. For the
real PYRITE 85 folded fixture that is ~3249 ray paths (9 world-cone bundles × 361 rays =
19×19) against the full scene mesh — ~2.5×10^5 mesh intersections per load. There is no
single dominant hot-spot; the cost is distributed. But several quantities that are FROZEN
for the whole trace were being recomputed on every ray step, multiplying that distributed
cost:

1. **`MultiBlock.__getitem__` re-wraps.** pyvista's `self.EEE[i]` ends in
   `wrap(self.GetBlock(i))`, allocating a NEW Python wrapper per access. The trace reads the
   same blocks hundreds of thousands of times, and — worse — the id-keyed decimation-proxy
   cache in `__SceneMeshWithFaceIds` never hit (a new `id(mesh)` each read), so every optical
   solid was re-decimated + re-face-id'd on every ray step.
2. **World-face signature rebuilt+hashed** per ray step for each optical solid (same cause).
3. **`pyvista PolyData.ray_trace`** re-wraps an obbTree call each invocation.
4. **`NonSequentialIntersectionPolicy.from_surfaces(SDT)`** — scene-scale tolerances that
   depend only on the frozen SDT — was rebuilt on every non-empty hit (~10^5×), rescanning
   every surface's Diameter/InDiameter/Thickness (`_surface_scale`).
5. **Mirror/TIR input-port answer** — a pure function of `surface_index` — was re-normalized
   from face metadata on every optical-solid hit.

(cProfile initially mis-pointed at the pyvista attribute glue because its ~1µs/call overhead
over-weighted millions of tiny calls; py-spy sampling gave the true, distributed breakdown
and redirected the work to the scene-invariant rebuilds above.)

## Fix
Five pure caches of frozen scene data (KrakenOS/KrakenSys.py + KrakenOS/MeshRayTrace.py),
all (re)initialized in `__init__` and cleared in `SetData`/`SetSolid` alongside the existing
scene caches:

1. `_eee_stable_block(index)` — one identity-STABLE wrapper per scene-mesh block, rebuilt
   only when `self.EEE` is re-bound (identity guard) and synced by `__ReplaceSceneMesh`.
   Kills the repeated `wrap()` AND makes the decimation-proxy cache hit.
2. `_optical_solid_mesh_fast_cache` — the resolved face-id proxy keyed by `(index, id(mesh))`
   so the world-face signature is not rebuilt+hashed per ray step.
3. `MeshRayTrace._fast_scene_ray_trace` — calls the obbTree directly (`vtkPoints`/`vtkIdList`)
   with a per-tracer `obbTree` cache, bypassing the `PolyData.ray_trace` wrapper allocation.
4. `_ns_intersection_policy_cache` — memoized `NonSequentialIntersectionPolicy`.
5. `_optical_solid_input_port_cache` — memoized input-port answer per `surface_index`.

## Byte-identical guarantee
These cache only frozen scene data — they must not change a single ray. Verified by hashing
ALL 3249 folded ray polylines (`rays.CC`, each (10,3)) plus `bundle.ray_paths[*].points_world`
of the real PYRITE 85 folded load with the edits vs. a `git stash` of the two files:

    CC[3249]   = 85aac277…6486   (identical edited vs baseline)
    PATHS[3249]= 5d6c3a0d…7e59   (identical edited vs baseline)

The trace is deterministic (two runs match) and the digests are bit-for-bit equal with the
caches on and off.

## Result
Clean back-to-back A/B (headless folded PYRITE 85 load, 2 passes each, same machine state):

    baseline 114.05s  →  edited 89.58s     (~21% faster; ~57.0 → ~44.8 s/pass)

The remaining cost has no whole-scene-recompute smell: raw `IntersectWithLine` (~13%,
irreducible), display scene-build (~14%), RayKeeper event recording (~10%), and distributed
small-array numpy in the chooser loop (~33%). Getting materially below this floor needs a
STRUCTURAL change (a coarser initial preview ray grid than 19×19, or a non-sequential
bounding-box pre-cull) that trades visual density or carries correctness risk — deferred to
the user's call, NOT bundled here.

## Verification
`validate_open3d_folded_trace_perf_caches` (display-free, on the fast two-fold AZ85 fixture)
pins one decisive cache-vs-fresh-recompute check per optimization:
  1. POLICY == fresh `from_surfaces(SDT)` (+ identity-stable);
  2. STABLE BLOCK identity-stable + points == live EEE re-wrap for every block;
  3. STABLE BLOCK rebuilds when `_eee_stable_src` is nulled (guard invalidates);
  4. INPUT PORT cached answer == fresh recompute;
  5. MESH FAST CACHE only holds meshes the slow face-id cache produced;
  6. OBBTREE FAST TRACE == `pyvista tracer.ray_trace` bit-exact (hit/tangent/miss battery);
  7. RESET BOUNDARY — the five caches declared + cleared by both SetData and SetSolid.
Added as penta phase 221; the 0243 `folded-real-trace-sync` phase 220 (real rays, first-
surface kinks, glass inert, detector termination) still passes — the caches are inert to it.
