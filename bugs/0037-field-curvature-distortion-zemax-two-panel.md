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
