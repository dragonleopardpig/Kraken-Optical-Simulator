# 0728 — show WHERE the image forms, detached from the sensor, with an in-scene summary

User: *"let the image detach from the Sensor and sit in front of the sensor with perfect ray
focusing, then raise a banner to tell user about the summary… User can then immediately know
what is happening from the scene"*, then: *"generalize this to all .py files or any future
setup: instead of showing ray defocusing at the sensor, show the perfect focus image detached
from the sensor and give a message focused image is located at XX.XX mm from the sensor."*

## What it does

After **every** real trace, the viewer measures where the rays actually form the image and, when
that is not the sensor plane, draws it: a sensor-sized magenta rectangle at the focus, a dashed
connector across the gap, a label, and a summary on the in-scene banner:

```
SOLVE: delivering 20 x 20 mm (|m| 1.152); the lens moved -138.6 mm along its leg
FOCUS: the image forms 78.54 mm in front of the sensor -- spot 0.174 um there vs 1.86 mm on the sensor
Move the device stage / camera focus to land it -- vendor hardware untouched
```

Nothing is drawn when the image already sits on the sensor, so an in-focus scene is unchanged.

## How the plane is measured (not computed)

`detector_coverage_overlay.focus_waist_from_rays` — rays are straight in image space, so the
waist is analytic: advancing along the detector normal moves a ray at rate `a = d/(d·n) − n`, and
the least-squares minimum of the transverse spread is `t* = −Σ(r′·a′)/Σ|a′|²`. It returns the
signed offset, which side of the sensor it is on (from the direction of travel, not the sign
alone), and the spot at both planes.

`focus_waist_from_grouped_rays` does it **per field**. This matters: rays from different field
points stay separated by the image height at every plane, so a pooled fit minimises the image
SIZE, not the blur — measured on a synthetic 3-field bundle, pooling reports a 4.9 mm "spot"
where the true waist is 0. Each field's waist must actually converge (waist RMS < ½ the spread at
the sensor) before it votes; the best-sampled field sets the plane and the field-to-field spread
is recorded. With no usable group it falls back to the pooled bundle and flags it. Nothing is
ever fabricated: too few rays, degenerate directions or a collimated bundle return None.

`layout_table_workbench._measure_focused_image_plane(scene_bundle)` groups the bundle's paths by
`(source_id, field_index)` — the bundle's own field identity — keeping only rays that reached the
detector (`termination_reason` "image", the scene builder's stamp; "target_termination" is the
older spelling). Called from `plot_refresh` and `three_d_scene_tools` beside the split-field strip
measurement, so it is scene-agnostic.

## Verified on real scenes

| scene | measured | cross-check |
|---|---|---|
| `om05a_folded_80mm` after a 20 × 20 solve | **78.54 mm in front**, spot 0.174 µm vs 1.86 mm on the sensor, 91 rays / 2 fields | banner + overlay rendered |
| `150mm.py` (in focus) | **9e-9 mm** → nothing drawn | detector z 625.000 = paraxial image plane 625.000 |
| `doublet.py` (defocused demo) | **728.8 mm behind**, spot 55 µm vs 4.83 mm | independent scan of the traced rays: RMS 4.83 → 3.50 (+200) → **0.055 (+728.8)** → 1.80 (+1000); `_real_ray_best_focus_shift_for_rows()` = 749 mm |
| Cooke triplet case study | 744.7 mm behind, spot 1.59 µm vs 1.11 mm | — |

Note the om05a number is **measured 78.5 mm**, where the thin-lens first order predicts ~98 mm:
the folded chain's prism glass is not in that reference. The drawn plane follows the rays
([[feedback_display_follows_physics]]).

## Guard

`validate_open3d_0728_focused_image_plane` = penta phase 527 (display-free, synthetic rays):
A the analytic waist, the side convention, and the None cases (few rays, collimated); B grouping
by field vs the field-height contamination of pooling, the convergence filter, the pooled
fallback; C the drawn rectangle is centred on and lies in the focus plane, and nothing draws when
in focus; D the banner wording (no-op vs move, distance + side + both spots, silence when in
focus); E the wiring pins.

`validate_open3d_0726`'s banner-colour pin was updated: the amber branch now also covers a pure
focus summary (no refusal), so it pins the dependency on the outcome and the alarm-red fallback
rather than the exact comparison.

## Follow-up

The focus label can overlap the solve banner in a tight view; both are readable but a stagger
would be tidier.
