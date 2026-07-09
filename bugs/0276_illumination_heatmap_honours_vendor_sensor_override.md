# 0276 — Relative-illumination heatmap window ignores the vendor-camera sensor override

## Symptom (flag_20260709_104624_302)

A **direct follow-up** to bugs/0275. On the same MV-150 **coaxial-LED** vendor-STEP scene, after
0275 shipped, the on-detector relative-illumination heatmap (Feature A) flipped from *too big* to
*too small*:

> "the illumination area is smaller than the sensor, and there is no 2 side dark edges + 2 side
> uniform edges."

The heatmap quad no longer reached the orange sensor square, and instead of the wanted **2 dark
(fold / X) + 2 uniform (perp / Y)** edges it showed a cropped patch (a coarse blob field). Because
the window had shrunk *inside* the sensor, the fold dark edges — which live **at** the sensor edge —
were clipped away entirely.

## Root cause

0275 removed the round catch-**DIAMETER** fallback from `source_illumination_map_extent`: with no
explicit rectangular active area, the window now falls through to the illuminated **data footprint**
(data min/max + 20 % pad). That is correct only when the detector genuinely has no sensor. But this
detector **does** have a sensor — the orange square is drawn — so the window should have been the
sensor. It wasn't, because the heatmap and the orange square read the sensor size from **two
different places**:

* **Orange square** (`scene_builder.build_scene_targets`, lines 414–419) resolves a detector's active
  dims from `row.advanced["Detector"]` **and**, when that is empty, falls back to the runtime
  `_camera_detector_active_dims_overrides()` — the vendor-glued **camera** sensor size, keyed to the
  final `Image` row.
* **Heatmap** (`_source_illumination_target_model`, `analysis_reports.py`) read **only**
  `row.advanced["Detector"]` (via `_detector_settings_for_surface`). A vendor-glued camera stores its
  sensor size in the **override**, not the surface row, so the heatmap saw `active_width/height = 0`.

With active dims 0, the extent skipped the sensor branch and fell to the data footprint — the wrong
size. (Pre-0275 the same 0 fell to the 78 mm catch diameter → the *too big* 093800 symptom; 0275
just changed which wrong answer you got.) A headless probe confirmed the divergence exactly: with the
39×39 dims in `advanced["Detector"]` the target-model reports `39×39`; move them into the override
only (the real vendor case) and it collapses to `0×0`.

## Fix

`_source_illumination_target_model` now consults the **same** override the orange square uses. When
`advanced["Detector"]` yields 0 active dims, it calls a new helper
`_source_illumination_detector_override_dims(target_index)` →
`self._camera_detector_active_dims_overrides()[target_index]`, mirroring `scene_builder`. The heatmap
window is the 39×39 sensor again, so the fold dark edges land at the sensor edge and the 2-dark /
2-uniform pattern reads correctly inside the orange square. The consult is guarded (getattr / try) so
detectors without a camera override are unaffected — they still fall through to the data footprint
(0275's universal safety net).

## Verification

Guard `validate_open3d_illumination_heatmap_override` (phase **243**), display-free (numpy + one
headless coaxial-LED trace, no VTK/Tk). The fixture moves the detector's active dims **out** of the
surface row and **into** a `_camera_detector_active_dims_overrides` override — the faithful
vendor-glue case:

* **MODEL differential** — the override-only detector's target-model reports the sensor dims
  (`39×39`); dropping the override collapses it to `0` (the override consult is load-bearing, not the
  row block).
* **INTEGRATION** — the real overlay quad spans the 39×39 sensor (half **18.3 mm** bin-centres), not
  the raw data footprint, and still reads the fold edge columns darker than the perpendicular edge
  rows (fold `0.787` < perp `1.234`; fold-edge `0.67` < perp-edge `0.98`): 2 dark + 2 uniform.

Negative control (fix stashed) fails both: target-model `0×0`, quad half **50.8 mm** (this
wide-catch fixture's data footprint overruns the sensor). A rendered snapshot of the coarse 16×16
overlay `relative` grid confirms the visual — green/dark left+right (fold) edges, red/uniform
top+bottom (perp) edges, spanning ±19.5 mm — saved beside the flag as `heatmap_after_fix.png`.

Sibling phase 242 (`validate_open3d_illumination_heatmap_extent`, the 0275 guard) stays green.
Baseline updated in place (243 → pass).

## Notes

* **Data footprint is the wrong size *either way*.** In the user's in-app scene it cropped *inside*
  the sensor ("smaller than the sensor"); in this wide-catch clean fixture it *overruns* the sensor
  (~50 mm) because the off-sensor coaxial scatter reaches well past the 39 mm FOV. Both are the same
  root cause — the illuminated data envelope is not the sensor — so the guard bounds the quad half on
  **both** sides.
* **In-app eyeball owed.** The headless clean-fixture reproduces the mechanism (dims in the override
  only → window = sensor), but the user's actual vendor-STEP scene still owes a visual check in the
  running app that the heatmap now fills the orange square with the 2-dark / 2-uniform pattern.
* The *3×3 blob* look the user saw is the coarse 16×16 overlay grid rendered over the cropped window
  at low ray density; once the window is the full sensor with adequate rays it resolves into the
  smooth fold/perp gradient. Ray density is a separate quality knob, not this bug.
