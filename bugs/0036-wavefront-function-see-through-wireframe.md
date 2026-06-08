# 0036 — Wavefront Function plot is a see-through wireframe, not the Zemax solid surface

**Status:** Fixed (2026-06-08).
**Component:** Wavefront Function analysis plot
(`KrakenOS/UI/services/layout_analysis_display.py`).
**Reported via:** `attachment/wavefront.png` (KrakenOS, see-through wireframe) vs
`attachment/wavefront_zemax.png` and `attachment/wavefront_zemax_optimized.png`
(Zemax, opaque hidden-line surface on a base plane). In the user's words:
*"refer attachment/wavefront.png vs wavefront_zemax.png, can we have the Zemax
look?"*

## Diagnosis

`_plot_wavefront_function_analysis` projected the OPD grid into an oblique
waterfall and then drew it as a stack of translucent polylines:

```python
for row_index in range(0, axis_x.shape[0], row_step):
    self._plot_axes_nan_segments(analysis_ax, axis_x[row_index, :], axis_y[row_index, :],
        color="#111827", linewidth=0.42, alpha=0.96)
```

Every slice was just a line. With nothing drawn *under* each slice, the back of
the surface showed straight through the front — the see-through wireframe in
`wavefront.png`. Zemax instead renders an opaque surface: nearer slices hide the
slices behind them (hidden-line removal), and the whole relief sits on a flat
base-plane parallelogram.

Two things were missing:
1. **Opacity / hidden-line removal.** Each slice needs an opaque fill beneath it
   so it occludes farther slices.
2. **The base plane.** The surface floated around a piston-removed zero instead
   of resting on a visible z=0 floor.

## Fix

Rewrote the projection + drawing into a painter's-algorithm waterfall.

`_wavefront_projected_axes_coordinates` now:
- references the relief to its own minimum (`z_norm -= min`), so the surface
  *rests on* the z=0 base plane instead of straddling it;
- additionally returns the per-point z=0 floor line `base_axis_y`
  (`0.20 * yy` projected — finite everywhere, constant within a waterfall row)
  and the four projected corners of the pupil grid box (`base_corners`).

New `_draw_wavefront_solid_waterfall`:
- draws the base-plane parallelogram first (lowest zorder) as a light apron;
- sorts the rows by floor depth and draws them **back-to-front**, each with an
  opaque white curtain (`fill_between` from the slice down to *its own* floor
  line) plus the dark slice line on top, with monotonically increasing zorder.

Because each curtain stops at that row's floor (not a global bottom), the
base-plane apron stays visible around the relief, matching Zemax. Nearer rows,
painted last, hide the rows behind them — the opaque hidden-line surface.

Helper `_fill_axes_nan_segments` mirrors `_plot_axes_nan_segments` but fills
each finite run down to a (scalar or per-sample) bottom, skipping NaN gaps.

## Tests

`KrakenOS/UI/validate_wavefront_function_solid_waterfall.py` (display-free, Agg):
builds a synthetic circular-pupil wavefront (spherical + coma + astigmatism) and
asserts the projection returns the surface grid, a finite-everywhere floor line
and a 4-corner base parallelogram; that every surface sample sits at or above its
floor; and that drawing produces opaque curtains (fill collections — the old
wireframe had none), the row lines, and the filled base-plane patch. Folded into
the comprehensive harness as **Phase 42**.

## Verification note

The fixed plot was rendered headless (`/tmp/wavefront0036.png`) from a synthetic
aberrated pupil and inspected: an opaque dome with hidden-line slices resting on
a light base-plane parallelogram apron — matching the Zemax look rather than the
prior see-through wireframe.
