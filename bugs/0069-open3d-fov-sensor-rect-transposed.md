# 0069 — Open 3D: the FOV / sensor rectangles draw portrait (transposed), not landscape

## Symptom (user's words)

From `attachment/3D.png` (layout `machine_vision_120mm_65M`, the 65 MP Bopixel
sensor 29.9 × 22.4 mm):

> the FOV numerical value is correct, but the rectangle drawn is reverse

and, on a second look:

> both object and image WxH seems reverse

The numeric labels read the right way round (`29.9 x 22.4`), but the drawn
rectangles were **portrait**: the long 29.9 mm sensor *width* ran along the
VERTICAL screen axis and the short 22.4 mm *height* ran horizontal. A landscape
sensor must read landscape — width (the long side) along the horizontal in-plane
axis. This affected BOTH the green object-FOV rectangle and the orange
image-sensor rectangle.

## Root cause

The optical solve is correct (the labels prove it). This is a pure display-axis
swap: every in-plane rectangle producer fed the sensor **width** to the
**vertical** in-plane axis. There are three producers across two coordinate
frames, and all three had the same transposition:

* `scene_geometry.scene_target_active_footprint_polylines` — the shared detector
  footprint (the orange sensor rect AND the 2D layout footprint). It mapped
  width → `tangent` (the +Y vertical / meridional axis) and height → `bitangent`
  (the horizontal / sagittal axis).
* `services.detector_coverage_overlay.detector_coverage_overlay_specs` — the green
  object-FOV rect. It built `_rect_points(obj_pt, u, v, half_w, half_h)`, and
  `_basis(axis=+Z)` returns `u = +Y` (vertical), so width (`half_w`, scaled along
  the first axis `u`) landed on the vertical.
* `services.quick_estimation_overlay` — the yellow recommended-sensor rect, same
  `_basis`, same `_rect_points(img_pt, u, v, ...)` width→vertical wiring.

`_rect_points(center, A, B, half_w, half_h)` scales `half_w` along `A` and
`half_h` along `B`; passing the vertical axis as `A` puts the width vertical.

## Fix (display-only — the optical solve is untouched)

Width spans the HORIZONTAL in-plane axis, height the vertical:

* `scene_target_active_footprint_polylines` — corners now offset width by
  `bitangent * half_w` (horizontal) and height by `tangent * half_h` (vertical).
* `detector_coverage_overlay_specs` — the object-FOV rect builds
  `_rect_points(obj_pt, v, u, half_w, half_h)` (width → `v`, the horizontal axis).
* `quick_estimation_overlay` — the recommended-sensor rect builds
  `_rect_points(img_pt, v, u, ...)` (width → `v`).

Because the footprint producer is **shared** with the 2D layout
(`scene_projector` / `layout_plot_controller`), the 2D detector footprint is
corrected by the same change. `validate_layout_plot_controller.py` had an
assertion that locked in the old transposition (it required the 4.0 width to span
the vertical Y and the 2.0 height to span X); it was updated to the corrected
landscape orientation (width → X, height → Y).

## Test (fails before, passes after)

`KrakenOS/UI/validate_open3d_fov_rect_orientation.py` (new, display-free +
portable — pure geometry, no vendor assets, no X server). On a deliberately
non-square **landscape** sensor (W=30, H=20) so a transposition is visible:

* **A** — the shared footprint (via a real `SceneTarget3D` with optical axis +Z,
  tangent +Y) puts width on the horizontal X axis (`ptpX == 30`), height on the
  vertical Y axis (`ptpY == 20`), and reads landscape (`X > Y`).
* **B** — the detector-coverage object-FOV rect (mag 0.5, so FOV = sensor / |m| =
  60 × 40) does the same: `ptpX == 60`, `ptpY == 40`, `X > Y`.
* **C** (fail-before / pass-after source wiring) — `inspect.getsource` proves the
  footprint maps width → `bitangent` (`"bitangent * half_w"` present) and no
  longer maps height → `bitangent` (`"bitangent * half_h"` absent — the only
  marker that discriminates, since `tangent * X` is a substring of
  `bitangent * X`); the object-FOV rect builds `_rect_points(obj_pt, v, u,` and
  the QE recommended-sensor rect builds `_rect_points(img_pt, v, u,`.

Reverting any one producer to width→vertical fails its A/B geometry check and/or
its C source-wiring check.

## Integrated

Phase 74 of `validate_open3d_penta_telescope_comprehensive.py` (display-free
wrapper over the new guard). Baseline `tools/penta_validator_baseline.json`
updated (`"74": "pass"` + title). The gate now tracks 75 phases (0–74).

## Verification note

The display-free guard pins the geometry and the source wiring of all three
producers. The live render of this specific machine-vision layout can't be
confirmed headless (it SIGSEGVs the offscreen Xvfb llvmpipe renderer); the user
confirms the landscape rectangles in-app.
