# 0032 — Image circle must cover the sensor (real ray-traced circle + object FOV rectangle + auto-fill)

**Status:** Fixed (2026-06-08).
**Component:** detector coverage overlay (new
`KrakenOS/UI/services/detector_coverage_overlay.py`), Open 3D scene refresh
wiring (`KrakenOS/UI/open3d_inspector.py`,
`KrakenOS/UI/services/open3d_scene_refresh.py`), camera database
(`KrakenOS/UI/camera_database.py`), camera-select handler
(`KrakenOS/UI/services/layout_table_workbench.py`).
**Reported via:** in-app bug recorder bundle
`attachment/recorded_bug_repros/flag_20260608_093231_330/` on the machine-vision
150 mm measured layout with the `Allied Vision hr25MCX` camera. In the user's
words: *"the circular image still within the sqaure sensor."* Follow-up
directives:
- *"The circle shown is within sensor square, it is too much and vignetting
  occurs. Actual optical or imaging design should be sensor within the Image
  Circle. If by calculation or ray trace, the image circle is unable to cover
  the image sensor, that is design problem, not UI problem. If so, please
  suggest a correct configuration ... Option B is what we should go next."*
- *"the object side, FOV should be now square/rectangle due to the sensor. Can
  you apply overlay of FOV to the object plane as well?"*
- *"Also automatically fill in the Real Image Height value in the panel
  according to the Camera selected."*

This is the design-side follow-on to bug 0031, which fixed the **sensor**
footprint (drawn at the vendor 23.04 × 23.04 mm instead of the 25 mm placeholder)
but explicitly left the corners outside the image disk as "a property of the
design's image-surface aperture, not a UI bug." The user confirmed that is the
thing to fix: the sensor must sit **inside** the image circle, corners included.

## Diagnosis

The cyan disk the user reads as "the image circle" was never a coverage
indicator — it is the generic image-**surface** clear-aperture disk, drawn at the
Image row's `diameter / 2`. It bears no relation to where rays actually land. On
this layout the field is a Real Image Height of 11.52 mm, so the **real**
ray-traced image (the field's `max_real_image_height`) only reaches radius
11.52 mm, while the sensor corner is at the half-diagonal
`hypot(11.52, 11.52) = 16.29` mm. The imaged field therefore stops well short of
the sensor corners — real vignetting — and no overlay communicated the actual
ray-traced coverage or how to close the gap.

Key numbers (machine-vision 150 mm measured + hr25MCX): finite object, paraxial
`|m| = 1.1467`; sensor 23.04 × 23.04 (half-diagonal 16.29, diagonal 32.58); stock
Real Image Height 11.52 → image circle Ø23.04, which **inscribes** the sensor
(touches the edge midpoints, clips the corners). To cover the corners the real
image semi-height must reach 16.29 → image circle Ø32.58 = the sensor diagonal.
The object-plane field of view that maps onto the sensor is `sensor / |m|` =
20.09 mm square (semi 10.05). Confirmed display-free that the field metric is not
clipped by the surface aperture: setting Real Image Height 16.29 with surface
Ø25 still ray-traces `max_real_image_height = 16.29`, so auto-filling the field
genuinely produces a covering circle.

## Fix

**Option B — draw the real ray-traced image circle, not the placeholder disk.**
New display-free geometry module
`KrakenOS/UI/services/detector_coverage_overlay.py`:

- `detector_coverage_metrics(sensor_w, sensor_h, image_circle_radius, |m|)` —
  pure coverage relationship. `covers` is `radius >= half_diagonal - eps`. The
  tolerance `_COVER_EPS = 1e-3` mm (1 µm, under a quarter of the 4.5 µm pixel) is
  physically negligible yet wide enough to absorb the 6-significant-figure
  rounding of the Real Image Height shown in the panel, so the suggested value is
  self-consistent (set exactly X → it then covers). `required_real_image_height`
  is the half-diagonal; object FOV half-extents are the sensor half-extents / |m|.
- `detector_coverage_overlay_specs(object_pt, image_pt, metrics, *,
  object_mode_finite)` — pure polylines: the **image circle** at the real image
  semi-height (cyan when it covers the sensor corners, amber when short); a
  dashed amber **required** ring at the sensor half-diagonal, emitted **only**
  when short, so the gap to close is visible; and an object-plane **FOV
  rectangle** sized `sensor / |m|` (green), matching the sensor shape rather than
  a circle, emitted only for a finite object.
- `DetectorCoverageOverlayService` renders those specs as pyvista line meshes and,
  when the circle is short, surfaces a debug-log suggestion naming the exact
  Real Image Height that closes the gap ("image circle Ø… does not cover the …
  sensor (needs Ø…). Set Field Real Image Height to … mm.").

Wired into the Open 3D scene refresh next to the Quick Estimation overlays,
gated on the existing **"Det"** detector overlay toggle
(`show_detector_overlays_var`):
`open3d_inspector._add_detector_coverage_overlays` (lazy service accessor) called
from `open3d_scene_refresh` after the step bodies register.

**Suggest a correct configuration + auto-fill (camera-driven).**
`camera_database.camera_image_coverage_mm(name)` →
`(sensor_diagonal, half_diagonal)` (hr25MCX = Ø32.58 / 16.29). Selecting a camera
in `layout_table_workbench._on_camera_model_changed` now sets the image-surface
clear aperture to the sensor **diagonal** (the smallest covering circle) and
auto-fills the **Real Image Height** field to the **half-diagonal**, so the real
image circle covers that sensor out of the box. With no vendor sensor the handler
falls back to the previous `camera_image_diameter_mm` behaviour and leaves the
field untouched.

## Tests

`KrakenOS/UI/validate_detector_coverage.py` (display-free): asserts
`camera_image_coverage_mm` returns the diagonal + half-diagonal (None without a
camera); `detector_coverage_metrics` reports *not covered* at the stock 11.52 mm
(required 16.29) and *covered* at the half-diagonal, with object FOV half-extents
= sensor/2 / |m| and zero FOV when magnification is unknown;
`detector_coverage_overlay_specs` emits the object FOV rectangle (finite only,
green), the image circle (amber short / cyan covering) with the right radius, and
the dashed required ring **only** when short; and end to end on the real layout
the service's own data lookups feed a *not covered* result while simulating the
camera-select auto-fill (image diameter → diagonal, Real Image Height →
half-diagonal) re-traces to a covering circle. Folded into the comprehensive
harness as **Phase 38**.
