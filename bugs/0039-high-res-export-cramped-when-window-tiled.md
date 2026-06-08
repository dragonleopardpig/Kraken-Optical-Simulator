# 0039 — Clicked plot export looks cramped/different when the UI window is tiled

**Status:** Fixed (2026-06-08).
**Component:** high-res click-to-export of a plot axis
(`KrakenOS/UI/services/layout_plot_interaction.py`).
**Reported via:** the user on a Wayland desktop that auto-tiles the app window.
In the user's words: *"when the UI is tiled, clicking any analysis plot will look
different (more cramp) than when the UI is fullscreen"* and *"the 2D and analysis
display after clicking to open in an image viewer looks different from when the UI
is fullscreen."*

## Diagnosis

Clicking a plot opens a high-resolution image via
`_open_high_res_plot_in_system_viewer`, which crops the **existing embedded
figure** to the tight bounding box of the clicked axis and `savefig`s it. The
embedded canvas resizes with the window: a Wayland compositor that auto-tiles the
app gives it a smaller canvas, so the matplotlib figure is physically smaller (in
inches). Fonts are a fixed point size, so on a small figure the labels are large
relative to the axes — the export comes out cramped, with overlapping tick labels
(the field-curvature two-panel especially jumbled its x ticks). The same plot
exported from a fullscreen (large) window looked comfortable, so tiled and
fullscreen exports looked different.

## Fix

Normalise the **exported content** to a window-independent size. After computing
the tight bbox (in inches) of the kept axes, scale the whole figure uniformly so
the clicked content reaches a fixed target width (`8.0"`), redraw, recompute the
bbox, then `savefig`. Scaling the figure uniformly preserves every axis's aspect
ratio and the field-curvature two-panel's manually positioned panels — only the
absolute size (hence the font-to-axis ratio) changes — so a tiled (small) window
and a fullscreen (large) window now export the same comfortable image. The
on-screen figure size is restored in `finally`.

The scale factor is computed by the pure helper
`_high_res_export_figure_scale(content_width_in, target_width_in=8.0)`, clamped to
`[0.5, 4.0]` so a degenerate/empty bbox can't blow up the figure.

## Tests

`KrakenOS/UI/validate_high_res_export_size_normalized.py` (pure-function,
display-free): asserts a small (tiled) content width scales up toward the target,
a large (fullscreen) width scales down, **different source widths normalise to the
same exported width** (so tiled and fullscreen match), and extreme/degenerate
widths are clamped. Folded into the comprehensive harness as a new phase.

## Verification note

The field-curvature two-panel was rendered from a small (4.5×6") source figure and
crop-exported with the normalisation: it scaled 2.09× to a 7.6" content width and
came out clean — well-separated FIELD CURVATURE / DISTORTION panels with readable,
non-overlapping x ticks, matching what a larger source figure produces.
