# 0724 — "Trace Now seems freezed": minutes of clustering for a guaranteed `None`

Live report (2026-09-06, build 7f2fe23f): *"live now, loaded the 3D scene, rays is on but
without rays. Press Trace Now button, seems freezed."*

## Diagnosis (from the running process, not a guess)

The app was at ~90–95% CPU on the main thread, and its own journals showed refreshes
*completing* (12 bundles, 4332 rays, ~26 s of tracing) — so it was computing, not deadlocked.
But `open3d_timing_latest.jsonl` then went silent for minutes while the process stayed pinned.

`py-spy dump --locals` on the live PID named the culprit exactly:

```
norm (numpy/linalg/_linalg.py)
_unit_vector (nonseq_output_ports.py:498)
_cluster_planar_faces_from_triangles (nonseq_output_ports.py:602)   max_faces: 162
_source_to_runtime_world_transform (nonseq_output_ports.py:651)
    row: "Live OPTICAL STEP optical solid"      <- the vendor prism assembly overlay
_apply_optical_solid_output_port_system_overrides_built (:2440)
build_system -> _build_preview_system_rays_bundle -> _trace_live_now   <- Trace Now
```

`_cluster_planar_faces_from_triangles` is a pure-Python double loop: every triangle is tested
against every plane group accumulated so far, each test doing `_unit_vector` + `np.linalg.norm`.
The live vendor STEP overlay row carries **~160 source faces** and its mesh has **57 090
triangles** (`prism_assembly_chunk_armA`). Measured cost on that mesh:

| triangles clustered | time |
|---|---|
| 2 000 | 0.04 s |
| 8 000 | 10.5 s |
| 57 090 | minutes (aborted) |

And the result was **thrown away**: the caller's face match is an `itertools.permutations`
search over the mesh pool, defined only for a handful of faces, so the tail read
`if len(mesh_pool) < source_count or source_count > 8: return None`. Every system build paid
the full clustering for a body whose answer was already determined to be `None`.

This is pre-existing (not from 0722/0723), but it is what the user hit: the om05a scene keeps
live vendor STEP overlays (prism assembly, lens, camera), and Trace Now rebuilds the system.

## Fix (general)

`nonseq_output_ports._source_to_runtime_world_transform`: decide on the face COUNT before
touching the mesh.

* new named constant `_SOURCE_FACE_MATCH_LIMIT = 8` (the permutation search's real domain);
* the top guard becomes `if len(source_faces) < 3 or len(source_faces) > _SOURCE_FACE_MATCH_LIMIT:
  return None` — before `_mesh_world_triangles` and the clustering;
* the tail's now-dead `or source_count > 8` test is removed.

Outcome is identical for every input; only the cost changes. Measured after the fix:

| case | before | after |
|---|---|---|
| 160-face live STEP row, 57 090-triangle mesh | minutes | **6.5 ms** |
| 9-face row, same mesh | minutes | 0.5 ms |
| real 5-face promoted row (BS cube A, First RA mirror A, Centre RA mirror B) | ~2 ms | ~2 ms, same transform |

## Guard

`validate_open3d_0724_source_face_match_limit` = penta phase 523 (display-free, no app): A a
160-face row returns `None` with the clustering patched to raise, in milliseconds; B the
boundary — 9 faces bails, exactly 8 still runs the match, <3 still bails; C the dead tail test
is gone and the signature is unchanged.

## What is left (legitimate) in a Trace Now on om05a

With this fixed, a full Trace Now on `om05a_folded_80mm.py` is ~50 s headless, and a profile
says ~52% of it is the real non-sequential mesh ray trace (12 bundles x 361 rays). Six bundles
cost ~4 s each and six ~0.2–0.6 s: the expensive half is the arm-B light, which only started
tracing for imaging rays with bugs/0723 (before that it was force-absorbed at BS cube B, so the
scene felt faster because half the physics was missing). Reducing that is a separate
optimisation, not a hang.

## Follow-ups

* `_cluster_planar_faces_from_triangles` is still O(triangles x groups) in Python with an
  unbounded group list; vectorising the group scan (same insertion-order semantics) would make
  the <=8-face path robust against large meshes too.
* Trace Now runs in-process on the UI thread, so any long build still freezes the window.
  A progress/cancel path (or moving the build off the Tk thread) is the real ergonomic fix.
