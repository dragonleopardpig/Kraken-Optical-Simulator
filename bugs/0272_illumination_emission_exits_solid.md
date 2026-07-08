# 0272 — the illumination emission EXITS the solid (draw the engine-traced path, not a source+hits stub)

User flag `flag_20260709_072825_805` on the MV-150 coaxial-LED scene:

> *"the illumination rays not exiting the BS cube."*

After bugs/0270 the marked-face emission traces and reflects, but on the beam-splitter cube the cyan flood
rendered as a dense cross-hatch **trapped inside the glass** — every drawn ray stopped at the cube's far
face and none continued out toward the object / lens.

## Root cause — the overlay dropped the terminal free-flight point

The physics engine is **correct**. Reproduced headlessly (a promoted BK7 prism, the +X face marked
illumination-inward): each ray emits from the face (`[12.5, 1.48, 13.98]`), crosses the glass, **refracts at
the exit face** (`[-12.5, 2.1, 6.28]`), and flies onward to a terminal point ~70 mm **beyond** the cube
(`[-82.49, 3.21, -7.54]`, outgoing dir `[-0.981, 0.016, -0.194]`). All three vertices are already in the
path's `points_world`.

The bug was purely in the overlay geometry. `_marker_record_polyline` rebuilt the line from the record's
`source_x/y/z` + **`hits`**, and `hits` is derived from **surface events only**
(`scene_bundle_ray_analysis_records`). The refracted terminal free-flight point lives in the *separate*
**terminal** event, absent from `hits` — so the reconstruction was `[origin, exit-face]` and stopped dead at
the cube boundary. Imaging rays looked fine only because their terminal (the image plane) *is* a surface
event. The marker rays, which "Miss image after S1", had their one continuation segment silently dropped.
Display was not following the physics (violates the display-follows-physics principle).

## Fix — draw the engine's own `points_world`

* `_isolated_ray_analysis_records` (`services/analysis_reports.py`) — after building the records it attaches
  each path's engine-traced `points_world` as `record["traced_polyline_world"]` (records are 1:1 with
  `bundle.ray_paths` in build order; guarded by a length match). Still **never** writes `_last_scene_bundle`
  (bugs/0266 preserved).
* `_marker_record_polyline` (`services/source_illumination_rays_overlay.py`) — now **prefers**
  `traced_polyline_world` (source → every surface hit → the refracted terminal free-flight point), so the ray
  REFLECTS off surfaces AND continues OUT of the solid after refracting at the exit face. Falls back to the
  source+hits reconstruction only for records without an attached polyline (the pure unit tests).

The emission is still isolated (its own keeper, forced non-seq) and render-only — the imaging image-plane /
detector / optical axis stay fixed.

## Verification

* Reproduced: pre-fix the drawn polylines were 2 vertices ending at the exit face (x≈−12.5, per-ray span ≈ the
  25 mm cube width); post-fix every ray is ≥3 vertices, terminals reach x≈−82 (per-ray span mean ≈ 129 mm),
  i.e. the rays refract out and continue.
* Guard `validate_open3d_illumination_marker_emission` (phase **236**, updated in place — same title/baseline):
  WIRING now asserts the isolated extractor attaches `traced_polyline_world` and the overlay prefers it; PURE
  adds an exit-continuation case (a record whose `hits` stop at the exit face but whose traced polyline
  continues is drawn from the traced polyline); BINDING now asserts the drawn emission span reaches well
  beyond the solid's own span (540 mm vs 50 mm on the fixture) — it EXITS, not just reflects. Siblings
  0268/0269/0271 re-verified — no regression.

## Notes

* **In-app eyeball owed:** headless can't drive the embedded-VTK inspector. The user should reopen the MV-150
  coaxial scene, mark the BS illumination face, and confirm the cyan emission now floods OUT of the cube (not
  trapped inside) — Overlays → "Illum emission". Requires an app restart to pick up this fix.
* **Unblocks Stage 3 (0273 — Option-B coupling):** the illumination now visibly exits the BS toward the
  object, which is the prerequisite for tracing it through the Object scatter (bugs/0271) onto the detector.
* Still deferred (bugs/0270): the emission footprint is an area-matched **disk** that over-sizes a rectangular
  face at the corners; branch-sensor suppression on an illumination face.
