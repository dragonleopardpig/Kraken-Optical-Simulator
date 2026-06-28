# 0178 — FEATURE: field-resolved surrogate (per-field Zemax spot data → real coma/astigmatism)

## Goal (option 2, step 3 — the field-dependent extension)

The wavefront-augmented surrogate (bugs/0177) shows the real on-axis spot, but the Zemax OPD
map is on-axis only, so the same blob rides every field — it can't show the edge coma and
astigmatism that grow off-axis. A vendor's Zemax **"Spot Diagram Data"** export
(`Lens/<id>/spot radius/Mag*.txt`) carries the per-field RMS spot size — and crucially the
**RMS X (sagittal)** and **RMS Y (tangential/meridional)** sizes *separately* — so the spot can
grow AND elongate with field exactly as the real lens does.

For `Lens/15056` (the MV-150 surrogate):

| field (image height) | RMS radius | RMS X (sag) | RMS Y (tan) | shape |
|---|---|---|---|---|
| 0.0 mm  | 1.28 µm | 0.90 µm | 0.90 µm | round |
| 10.0 mm | 3.98 µm | 1.30 µm | 3.76 µm | elongated in Y |
| 16.5 mm | 7.38 µm | 2.08 µm | 7.08 µm | strongly elongated in Y |

The Y-elongation is the real meridional aberration (coma + astigmatism + field curvature).

## What it does

- **Source module** `services/zemax_field_spot.py` (pure numpy):
  - `parse_zemax_spot_radius(path)` → per-field `{field_mm, rms_radius_um, rms_x_um, rms_y_um,
    max_radius_um}` (UTF-16 Zemax "Listing of Spot Diagram Data"; `field_mm` = the image-
    coordinate height = the chief-ray height).
  - `field_resolved_scatter(chief_u, chief_v, records)` → for each chief position, interpolate
    the sagittal (X) and tangential (Y) RMS by the field **radius**, build an anisotropic
    hexapolar scatter (RMS-sagittal ⟂ to the radius, RMS-tangential along it), and rotate it to
    the field's **azimuth**. Round on-axis; a radial ellipse pointing outward at the edge — the
    physically-correct rotationally-symmetric behaviour (a +Y field stretches in v, a +X field
    stretches in u). Returns `(scatters, rms_radius_mm)`.
- **Apply** (`_compute_spot_field_map_spec`): when a `spot radius/<same name>` sibling sits
  beside the attached wavefront map (`_surrogate_spot_radius_path`), it replaces the uniform
  on-axis OPD blob with the per-field scatter + RMS. The Airy circle (real-NA) is unchanged.
  When there is no sibling, the on-axis wavefront-augmented (0177) behaviour stands.
- **Verdict flip:** `_scene_surrogate_optics_info().reason` and the Spot-map label read
  **"✓ Field-resolved surrogate (Zemax per-field spot data — real coma/astig, RMS to X µm at
  edge)"** instead of "wavefront-augmented (on-axis)".

## Why it is honest

- The spot **sizes/shapes are the vendor's measured Zemax spot RMS**, field by field — not a
  synthetic aberration model. The synthesis is only the *arrangement* of points to reproduce
  the per-field RMS-X/RMS-Y, oriented radially (the rotationally-symmetric assumption).
- Caveat: a symmetric ellipse reproduces the RMS elongation but not the coma *skew* (the
  teardrop tail); the RMS-X/Y are the available data. Good enough to show where/how the spot
  degrades across the field; the exact tail needs the full per-field spot diagrams.

## Files

- `KrakenOS/UI/services/zemax_field_spot.py` (new, pure)
- `KrakenOS/UI/services/three_d_scene_tools.py` — `_surrogate_spot_radius_path`,
  `_field_resolved_spot_for_surrogate`, the apply in `_compute_spot_field_map_spec`, the
  `field-resolved` verdict in `_scene_surrogate_optics_info`
- `KrakenOS/UI/open3d_inspector.py` — the Spot-map label prefers the field-resolved verdict
- `KrakenOS/UI/validate_open3d_field_resolved_surrogate.py` (new guard) + penta phase 170
- `KrakenOS/UI/validate_open3d_wavefront_augmented_surrogate.py` — now isolates the
  wavefront-only (uniform) path in a sibling-less temp dir so 0177 and 0178 are pinned apart

## Status

Shipped. Guard `validate_open3d_field_resolved_surrogate` (parse + integration + contract) +
penta phase 170 green; baseline 171 phases. ON-AXIS-to-edge from the real Lens/15056 data:
RMS 1.3 → up to 7.4 µm; the spot map's own field grid reaches ~11.5 mm so it shows up to
~4.8 µm — push the field sampling to the 16.5 mm edge to see the full 7.4 µm. In-app eyeball
owed (the radial elongation + the verdict label).
