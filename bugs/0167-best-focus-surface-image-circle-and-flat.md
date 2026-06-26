# 0167 — Best-focus surface: size it to where the rays land + make the curvature visible

Three in-app flags on the just-shipped "Focus surf" overlay (Double Gauss 28°,
`flag_20260626_212607_959` ray-on, `_212627_584` ray-off, `_212954_385` / `_213408_193`
YZ edge-on):

> Is the rings surface showing curvature? Seems flat. And why the image plane in
> focus smaller than the rings surface (the rays actually hit the ring surface,
> beyond the circular image plane) … the rays are actually hitting beyond the image
> circle, all the way to the rings plane, most outer ring.

## Two real problems

1. **The bowl was sized to the lens CLEAR-APERTURE, not where the rays land.** v1 used
   `radius = anchor_target.diameter / 2`. On the double gauss that is 24.8 mm — which
   only *coincidentally* matched the real image height. The correct size is the real
   chief-ray image height per field. (The `Image circle Ø28.6` marker is a *separate*
   bug — see bugs/0168; it reads 14.3 mm when the rays actually land at 24.55 mm.)
2. **The bowl looked flat.** The true field curvature of a corrected double gauss is
   ~0.08 mm P-V over a ~24 mm radius — edge-on (the YZ flags) it is a straight line.

## Fix

* **Size the rings to the real image height.** `_sample_field_curvature_distortion`
  now also exports the chief-ray `image_height` per field (purely additive — the 2D
  Field Curvature / Distortion panels and their validators are unaffected).
  `build_best_focus_surface` takes those image heights directly: ring i sits at the
  real radius where field i lands, so the rim ring is the real image circle (24.55 mm
  on the double gauss) and the bowl matches the traced rays. The `target.diameter/2`
  path remains only as a fallback when the scan didn't export heights.
* **Auto-exaggerate the axial sag + label it.** The sag is magnified so the peak is a
  visible fraction (~12%) of the rim radius (×45 on the double gauss); `ring_dz` keeps
  the TRUE offsets, `points`/`display_dz` carry the exaggerated ones, and the overlay
  draws a billboard label `Best-focus surface · field curv P-V <true> mm (×N)`. The
  bowl now arcs off the flat image plane — and that gap IS the field-dependent
  defocus (the documented intent), now visible and honestly labeled.

## Guard

`validate_open3d_best_focus_surface` updated: pure geometry now checks true-scale
(`exaggeration=1`) AND auto-exaggeration (factor > 1 for a tiny sag, `display_dz =
medial × factor`, `ring_dz` stays true, rim = max image height); the double-gauss
integration asserts `rim ≈ max real chief-ray image height (24.55)`, factor > 1, and a
visible exaggerated sag. Penta phase 158 (same phase, updated guard). Field-curvature
+ double-gauss + two-arm + 0166 validators still pass. Rendered bowl still owed a
final in-app eyeball.
