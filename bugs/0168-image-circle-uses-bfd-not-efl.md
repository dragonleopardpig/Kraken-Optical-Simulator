# 0168 — "Image circle" used the back-focal-distance, not the EFL (wrong on every thick infinity lens)

## Symptom (user, while eyeballing the 0167 best-focus surface on Double Gauss 28)

> the image plane in focus [is] smaller than the rings surface … the rays are
> actually hitting beyond the image circle, all the way to … the most outer ring …
> **my god, is the wrong image circle across all layout or just this particular
> double gauss .py file?**

The traced rays land at the real image height (24.55 mm at the 14° field) but the
green "Image circle Ø28.6" overlay (R = 14.29 mm) was far smaller — so the rays
visibly overshot it.

## Root cause (across ALL infinity-object layouts, not one file)

`_field_metrics_for_value` (`services/layout_scene_bundle_display.py`) computed, in
the non-finite-magnification (infinity / Angle-field) branch:

```python
real_image_height = image_distance * np.tan(np.deg2rad(angle_deg))
```

`image_distance` is the **back focal distance** (last surface → image). But an
object-space field angle θ images to **`EFL · tan(θ)`** — the pivot is the rear nodal
point, which sits an EFL (not a BFD) from the image. On a thick lens BFD < EFL, so
`max_real_image_height` underread by the **EFL/BFD** ratio. The detector-coverage
"image circle" (`detector_coverage_overlay._image_circle_radius`) read that value, so
the drawn circle was too small everywhere:

| layout (infinity) | old image circle R | correct R | error |
|---|---:|---:|---:|
| Zemax Double Gauss 28° | 14.29 | 24.81 | **1.74×** |
| Double Gauss 5° | 0.90 | 4.44 | 4.92× |
| F-Theta 50mm | 7.09 | 18.20 | 2.57× |
| **Cooke Triplet** | 2.62 | 42.26 | **16.13×** |

Finite-conjugate layouts use the `finite_magnification` branch (`real = mag ·
object_height`), which is correct — so the bug is specific to infinity objects.

(Note: the same wrong `image_distance*tan` term *round-tripped* the "Real Image
Height" field-type input — `angle = arctan2(H, image_distance)` then back — which is
why it survived; the round-trip is preserved below by routing through the EFL.)

## Fix

`_field_metrics_for_value`: map the field through the **EFL**, not the BFD —
`angle = arctan2(real_image_height, EFL)` for the "Real Image Height" input, and
`real_image_height = paraxial_image_height` (= `EFL·tan(angle)`) for the estimate
(true distortion comes from the traced image diameter, not this non-tracing quick
estimator). `_field_metrics_summary` now also exports the object-mode-aware
`field_image_radius` (= max paraxial for infinity, max real for finite — the value
line 115 already computed for `image_diameter`), and the detector-coverage
`_image_circle_radius` reads it.

## Guard

`validate_open3d_image_circle_efl` (display-free): on each checked-out infinity
layout (double gauss ~1.7×, Cooke ~16×) — `field_image_radius == max_paraxial`,
`max_real_image_height == field_image_radius` (no longer the BFD value), the radius is
EFL/BFD times bigger than the old `image_distance*tan` value (fail-before/pass-after),
and `_image_circle_radius` reads `field_image_radius`. Penta phase 159. Broad sweep
clean: inscribed-sensor (0163), camera-FOV launch (0162), det-coverage gate, two-arm
fold, Cooke & double-gauss case studies, field-curvature, FOV-label — all still pass.
In-app eyeball owed: the green image circle should now reach the traced rays.
