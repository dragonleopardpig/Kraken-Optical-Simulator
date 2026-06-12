# 0068 — Open 3D: the camera STEP renders as a thin sensor-window slab, not the full camera body

## Symptom (user's words)

In-app repro bundle `attachment/recorded_bug_repros/flag_20260612_113305_426`
(layout `machine_vision_120mm_65M`):

> Camera STEP is wrong.

The layout `attachment/machine_vision_120mm_65M.py` mounts the 65 MP vendor
camera *Japan Bopixel BC-GM(C)65M12X4-F*
(`camera_step_path = attachment/Cameras/BC-GM(C)65M12X4-F.STEP.step`). Instead of
the real industrial-camera body in `attachment/65M.png` (black ~80 mm cube body,
yellow heat-sink fins, silver lens-mount flange), the overlay drew a thin slab
floating at the sensor.

The recorded `scene_state` makes the collapse explicit:

* `step_actor_bounds["camera"] = X[-20.875, 20.875] Y[-17.875, 17.875] Z[434.43, 440.67]`
  — a **41.75 × 35.75 × 6.24 mm** plate (only ~6 mm deep along the optical axis),
  not the ~80 × 80 × 96 mm body.
* `step_actor_counts = {"lens": 1, "camera": 1}` — exactly one camera actor was
  drawn, so this is not a missing-part / culling issue; the single actor is
  itself the wrong piece.

## Root cause

The camera overlay was loaded with `largest_component=True`. That routes the
imported mesh through `LayoutPolylineDisplayMixin._largest_connected_step_component`,
which splits the mesh into connected regions (`mesh.connectivity("all")`) and
keeps the single region with the **most triangles**:

```python
counts = np.bincount(region_ids)
keep = int(np.argmax(counts))          # ranks by CELL (triangle) count
```

That metric is right for a *lens* — one glass element is the densest connected
region and isolating it strips mount hardware — but a **camera is a multi-part
assembly**. The vendor STEP is 37 solids (body + heat sink + mount + window cover
+ connectors). Its densest connected region is **not** the body: it is solid #3,
a small, highly-curved sensor-window cover — **41.75 × 35.75 × 6.24 mm**, ~49.9 k
triangles at 0.1 mm deflection. The real body (solids #0 / #19, **80 × 80 × 29 mm**,
~23× the volume) is a simpler box that tessellates to only ~7–10 k triangles each
and **loses the triangle-count vote**.

So `argmax(counts)` selected the window cover and discarded the body — and the
kept region's bounds (41.75 × 35.75 × 6.24 mm) match the captured `step_actor_bounds`
slab exactly. The camera collapsed to its window.

## Fix (display-only — the optical solve is untouched)

A camera is a multi-part assembly, so render the **whole** thing:
`largest_component=False`. Changed at both camera codepaths:

* `LayoutPolylineDisplayMixin._transformed_imported_camera_step_mesh` — the build
  path (`_load_step_mesh(..., largest_component=False)`).
* `ThreeDSceneToolsMixin._open3d_step_cache_warmup_specs` — the cache warm-up spec
  (`("camera", "imported_camera_step_path", False)`).

Switching the flag also switches the analytic mesh-cache key from
`*.analytic_largest.v2.vtp` (the thin slab) to `*.analytic.v2.vtp` (the full
assembly), so the fix is **not** masked by the stale largest-component cache on
disk — the full cache simply regenerates from the STEP on the next load.

The `largest=False` mesh anchors by its **front face** to `target_front_z`
(`_cad_mesh_aligned_to_optical_axis(..., front_face="max", target_front_z=camera_front_z)`),
so the lens-mount flange sits at the camera front and the body extends behind the
sensor — physically correct.

Performance is a non-issue: the full 37-solid assembly is **~116 k triangles** at
0.1 mm — barely more than the ~107 k-cell slab the app already rendered for the
window alone — well inside the in-code "100 k cells render comfortably" envelope.
The **lens** overlay's `largest_component` (which legitimately isolates one glass
element) is left untouched.

## Test (fails before, passes after)

`KrakenOS/UI/validate_open3d_camera_step_full_body.py` (new, display-free +
portable — the vendor STEP is a gitignored attachment, never required):

* **A** (synthetic, always runs) — the metric trap on a two-region mesh: a coarse
  big body `pv.Box(...).triangulate()` (12 cells) merged with a dense small window
  `pv.Box(...).triangulate().subdivide(3)` (768 cells). The **production**
  `_largest_connected_step_component` keeps the dense-but-tiny window (A2: kept ==
  window cells), whose bbox volume is `<< 0.25×` the body's (A3) — exactly the
  failure that shrank the camera.
* **B** (behavioral wiring, fail-before/pass-after) — the real
  `_open3d_step_cache_warmup_specs` emits one camera spec (B0) and its
  largest-component flag is `False` (B1).
* **C** (source wiring, fail-before/pass-after) — `inspect.getsource` of the
  camera build contains `largest_component=False` (C1) and no longer contains
  `largest_component=True` (C2).
* **D** (skip-if-absent, real vendor cache) — D1: the on-disk
  largest-component cache **is** the thin slab (41.8 × 35.8 × 6.2 mm, dz < 10 mm),
  proving the old path was wrong on real data; D2: once present, the
  full-assembly cache is the deep body (dz > 60 mm) — skipped until the next
  in-app load materializes it.

`git stash`-ing the two source edits makes B1 / C1 / C2 FAIL (and the warm-up /
build request the window slab again); restoring them passes.

## Integrated

Phase 73 of `validate_open3d_penta_telescope_comprehensive.py` (display-free
wrapper over the new guard). Baseline `tools/penta_validator_baseline.json`
updated (`"73": "pass"` + title). The gate now tracks 74 phases (0–73).

## Verification note

The live camera render cannot be confirmed headless (this machine-vision layout
class SIGSEGVs the offscreen Xvfb llvmpipe renderer). The fix is pinned by the
display-free guard above — which proves, against the **real** production selector
and the **real** vendor cache, that the old path kept the 41.8 × 35.8 × 6.2 mm
window slab and that both camera codepaths now request the full assembly — plus
the source-inspection wiring checks; the user confirms the full camera body
rendering in-app.
