# 0037 — Field Curvature / Distortion should match the Zemax two-panel layout

**Status:** Fixed (2026-06-08).
**Component:** Field Curvature / Distortion analysis plot
(`KrakenOS/UI/services/analysis_plot.py`).
**Reported via:** `attachment/distortion_zemax.png` (Zemax: two side-by-side
panels, FIELD CURVATURE with tangential **T** + sagittal **S** in millimeters,
beside DISTORTION in percent, field on the vertical axis). In the user's words:
*"can we match the zemax look of attachment/distortion_zemax.png?"*

## Diagnosis

The `field_curvature` analysis branch drew a single axis with the distortion
overlaid on a `twinx()`: best-focus shift on the left spine, distortion [%] on
the right spine, **field on the horizontal axis**, markers + dashed polynomial
fits, and a legend. That is a perfectly readable engineering plot but looks
nothing like Zemax's Field Curvature / Distortion printout, which is:

- **two separate panels** side by side;
- left **FIELD CURVATURE**: tangential (T) and sagittal (S) best-focus curves in
  millimeters;
- right **DISTORTION**: a single distortion curve in percent;
- **field on the vertical axis** (Zemax's +Y convention), with a vertical x = 0
  reference axis carrying the field tick marks.

(The single-axis + twin design is also what made bug 0035 possible — clicking the
plot dropped the distortion that lived on the twin.)

## Fix

New `AnalysisPlotService._plot_field_curvature_distortion_panels` replaces the
twin-overlay drawing. It splits the host analysis cell into two equal panels:

- **Left panel** (the host axis): FIELD CURVATURE. Tangential = meridional (Y)
  best-focus shift, sagittal = X best-focus shift, plotted as smooth curves with
  the field on the vertical axis; labelled **T** / **S** at the curve tops.
- **Right panel** (a new axis added with `sharey=host`): DISTORTION in percent,
  field on the vertical axis.

Because the right panel shares the field (y) axis, it is a shared-axis sibling of
the host — so the bug 0035 export fix keeps **both** panels when the plot is
clicked, and the distortion can never be dropped again.

Supporting helpers:
- `_field_curve_xy` sorts the |field| samples and fits a low-order polynomial so
  each series is the clean monotone curve Zemax draws from the axis (field 0) to
  the edge.
- `_symmetric_axis_limit` rounds the data extent up to a tidy 1/2/5·10ᵏ symmetric
  ± limit so the centred x = 0 axis has readable ticks.

Both panels get a centred `axvline(0)`, the FIELD CURVATURE / DISTORTION titles,
a "+Y" field-axis marker, "Millimeters" / "Percent" x-labels, and a small
"FIELD CURVATURE / DISTORTION … max field … wavelength" footer band. The host's
`set_box_aspect` (pinned by `plot_analysis`) is cleared so the two explicitly
positioned panels keep equal height.

## Follow-up: the best-focus magnitude was wrong (≈ tens of mm)

On review the field-curvature curve sat at ±50–100 mm — implausible for a
~100 mm Double Gauss whose field curvature is sub-mm — and the millimetre axis
looked off-centre. The user asked *"axis not centered at zero, are you sure -100
is correct?"* Three data/plot fixes (`services/analysis_plot.py`):

1. **Best-focus shift was computed from absolute image coordinates.** The
   longitudinal best focus is `-Σ(y·s)/Σ(s²)`, but `y` and the slope `s = m/n`
   must be measured *relative to the chief/centroid ray*, not absolutely. Using
   absolute heights, `Σ(y·s)` is dominated by the field offset × chief slope, so
   the result collapsed to the ray's axis-crossing distance (tens of mm), not
   the field curvature. Now both `y` and `s` are de-meaned per field before the
   least-squares focus, giving sub-mm shifts.
2. **The constant defocus of the image plane was not removed.** The built
   analysis system sat ~24.5 mm from on-axis best focus, so every field shared
   that offset. The focus shifts are now referenced to the on-axis (field 0)
   sample — the Zemax convention where the T/S curves rise from ~0 at the axis —
   so the panel shows the field-*dependent* curvature, not where the image plane
   happens to sit.
3. **The curve fit wandered off the origin and warned "poorly conditioned".**
   `_field_curve_xy` now fits against the *normalised* field-squared (field
   curvature and distortion are even in field): the +/- pair collapses onto one
   branch, the curve is anchored near the axis at field 0, and the regressor in
   [0, 1] keeps the polynomial well conditioned.

With these the FIELD CURVATURE panel shows T/S curves rising from the centred
zero axis to a few tenths of a mm at the field edge, matching Zemax's scale.

## Tests

`KrakenOS/UI/validate_field_curvature_distortion_panels.py` (display-free, Agg):
renders the field-curvature analysis on the Double Gauss case-study layout and
asserts two panels titled FIELD CURVATURE and DISTORTION exist; the distortion
panel shares the field (y) axis; the field is on the vertical axis (shared y
spans 0..max) with a vertical x = 0 line in each panel; and the field-curvature
panel carries both the T and S curves. SKIPs cleanly if the analysis is
unavailable on a given clone. Folded into the comprehensive harness as
**Phase 43**. The bug 0035 export guard (Phase 41) was updated to assert the new
shared-field-axis panel structure.

## Verification note

The reworked plot was rendered headless (`/tmp/fieldcurv0037.png`) from the
Double Gauss case study and inspected: two aligned panels with the field on the
vertical axis, T/S focus curves on the left in millimeters and the distortion
curve on the right in percent — matching the Zemax layout in
`attachment/distortion_zemax.png`.
