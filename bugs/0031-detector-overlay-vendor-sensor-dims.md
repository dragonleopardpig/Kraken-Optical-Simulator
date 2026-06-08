# 0031 — Detector overlay must use the vendor sensor size, not the image-surface diameter

**Status:** Fixed (2026-06-08).
**Component:** scene targets / detector active-area overlay
(`KrakenOS/UI/scene_builder.py`), camera database
(`KrakenOS/UI/camera_database.py`), editor scene-bundle wiring
(`KrakenOS/UI/services/layout_polyline_display.py`,
`KrakenOS/UI/services/layout_scene_bundle_display.py`).
**Reported via:** in-app bug recorder bundle
`attachment/recorded_bug_repros/flag_20260608_084132_519/` on the
machine-vision 150 mm measured layout. In the user's words:
*"I turned on the detector overlay, how come the image circle is inside the
detector square/rectangle? Shouldn't it be the other way round?"* Follow-up
directive: *"the UI should get the sensor dimension from the vendor
specification (~/attachment/Cameras)."*

## Diagnosis

The detector overlay draws two things at the image plane: a filled disk at the
image **surface** semi-diameter (the "image circle") and an active-area
rectangle (the "detector square"). The rectangle is sized from the detector
row's `advanced["Detector"]` `active_width_mm` / `active_height_mm`, which **fall
back to the row diameter** when unset — in four places that all shared the same
`<= diameter` fallback:

- `scene_geometry.scene_target_active_dimensions` (2D overlay),
- `three_d_scene_tools._target_active_dimensions_for_display` (3D overlay),
- `scene_builder._detector_plane_contact` (ray contact classification),
- `scene_builder._detector_plane_miss_intersection` (ray miss classification).

On `machine_vision_150mm_measured` the Image row has `diameter = 25` and no
explicit detector settings, so the footprint became a **25 × 25 placeholder
square** that fully circumscribed the Ø25 image disk (square diagonal 35.36 mm >
25 mm) — exactly the "image circle inside the detector square" the user saw. The
selected camera (`Allied Vision hr25MCX`, sensor 23.04 × 23.04 mm from its
datasheet) was never consulted for the active area; `camera_database` only fed
`image_diameter_mm` into the row diameter on dropdown change.

## Fix

Source the detector active area from the camera's datasheet sensor and let it
override the diameter fallback, **display-time only** (no prescription
mutation), so it works on load and after a camera change without writing the
saved layout.

`camera_database.py`:
- New `camera_sensor_active_mm(name)` → `(sensor_width_mm, sensor_height_mm)` or
  `None`. For hr25MCX that is `(23.04, 23.04)`.

`layout_polyline_display.py` (editor mixin):
- `_current_camera_sensor_active_mm()` and
  `_camera_detector_active_dims_overrides()` → `{row_index: (w, h)}` keyed to the
  **final `Image` row only** (the same row whose diameter
  `_on_camera_model_changed` sets), so secondary detectors keep their own size.

`scene_builder.py`:
- New `_detector_override_dims(overrides, row_index)` helper — the single source
  of the camera fallback, used by both the overlay (`build_scene_targets`) and
  the ray hit/miss classifiers (`_detector_plane_contact`,
  `_detector_plane_miss_intersection`) so the drawn footprint and the
  inside/outside-sensor ray classification always agree.
- Threaded a `detector_active_dims_overrides` kwarg through `build_scene_bundle`
  → `build_scene_targets` and `_build_ray_paths` →
  `_sync_detector_miss_terminal_event` → the two classifiers. Precedence:
  explicit per-row `advanced["Detector"]` value > camera sensor > row diameter.

`layout_scene_bundle_display.py`:
- The editor's `_build_scene_bundle` passes
  `detector_active_dims_overrides=self._camera_detector_active_dims_overrides()`.

`render_layout_snapshot.py`:
- `_snapshot_editor` now sets `camera_model_var` from settings so the headless
  render path (and tests) resolve the camera the same way the GUI does.

After the fix the footprint is the real 23.04 × 23.04 sensor: its half-width
(11.52 mm) is smaller than the image-disk radius (12.5 mm), so the image circle
extends past the sensor edges instead of the square enclosing the disk. (The
sensor *corners* still fall just outside this particular Ø25 image disk — that is
a property of the design's image-surface aperture, not a UI bug; the directive
was scoped to the sensor dimension.)

## Tests

`KrakenOS/UI/validate_detector_overlay_vendor_sensor.py` (display-free): asserts
`camera_sensor_active_mm` returns the datasheet 23.04 × 23.04; with the camera
selected the detector `SceneTarget3D` active dims equal the vendor sensor (not
the row diameter) and the sensor half-width is smaller than the image-disk
radius; with no camera the detector falls back to the diameter; an explicit
per-row Detector override (10 × 12) wins over the camera; and
`_detector_override_dims` returns the sensor for the keyed row and `(0, 0)`
otherwise. Folded into the comprehensive harness as **Phase 37**.
