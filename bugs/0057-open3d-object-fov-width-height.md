# 0057 — Open 3D: Object-plane FOV input accepts Width × Height

## Reported (direct request)

> Please change the FOV input to Width x Height as well.

Follow-up to bugs/0055 (click-on-plane FOV solve) and its W×H extension on the
**Image** plane. The Image-plane popup already took an explicit Width × Height;
the **Object**-plane popup still had a single "field width" entry and always
derived the vertical extent from the working 4:3 aspect. The user wants the
Object popup to accept an explicit Width × Height too.

## Root cause

Not a defect — a missing capability. The object branch of
`QuickEstimationService.fov_solve` (`services/quick_estimation.py`) only read a
horizontal width and mapped it to the model's circular image-circle diameter via
`horizontal_to_diagonal` (4:3 → horizontal/diagonal = 0.8). The popup
(`Kraken3DInspector._open_quick_estimation_fov_popup`) built a single Width entry
for the object plane (`height_var = None`).

## Fix

Object and Image popups now share one Width + Height layout (height optional):

- `_open_quick_estimation_fov_popup` builds Width/Height entries for **both**
  planes. Object prefill comes from the new
  `QuickEstimationService.object_fov_dimensions()` — the sensor rectangle
  (`sensor_active_dimensions`) divided by |magnification|, i.e. the object field
  that exactly fills the current sensor; it falls back to a 4:3 rectangle derived
  from the circular object-FOV diagonal when no magnification/sensor is available.
- `fov_solve("object", …)` now routes width+height through the existing
  `_sensor_wh(width, height)` helper:
  - `height` given → diagonal = √(W²+H²); the object field semi-height = diagonal/2.
  - `height` blank/`None` → the prior behaviour exactly: diagonal =
    `horizontal_to_diagonal(W)`, H derived for 4:3, so the diagonal (and every
    solved number) is unchanged.
  - `mode="thickness"` moves the conjugate pair so the W×H field fills the sensor.
  - `mode="sensor"` resizes the sensor to `|m|·W × |m|·H` (explicit rectangle),
    matching the object footprint instead of inscribing a 4:3 rectangle.

The Image-plane branch is unchanged. Because the height-omitted path is identical
to the old single-width path, existing layouts and the saved-state round-trip are
unaffected.

## Tests

`validate_open3d_fov_plane_solve.py` (display-free) adds:

- `object plane Solve for Image/Sensor Size (W x H)` — object 40 × 30 at |m|=0.5 →
  sensor 20 × 15 (Ø25), rectangular detector dims stored, no thickness change.
- `object plane Solve for Thickness (W x H)` — object 40 × 30 → diagonal 50, semi
  25; conjugate pair fills the Ø24 sensor, identical to the width-only path.
- `object plane W x H prefill` — `object_fov_dimensions()` = sensor (19.2 × 14.4)
  ÷ |m|=0.5 → 38.4 × 28.8.
- the double-click wiring guard now asserts **both** popups carry a Height field
  and the object popup prefills from `object_fov_dimensions`.

All pre-existing object/image width-only and bad-input cases still pass.
