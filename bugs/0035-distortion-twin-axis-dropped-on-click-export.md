# 0035 — Distortion series disappears after clicking the field-curvature plot

> **Note (2026-06-09, bug 0042):** the `_high_res_export_kept_axes` fix below still
> stands (the export keeps any axis sharing an axis with the clicked one). Field
> curvature and distortion were since split into two single-panel modes, so the
> field-curvature plot no longer carries a distortion twin; the guard (Phase 41)
> now exercises the same export logic through the atmosphere plot's `twinx`
> dispersion overlay.

**Status:** Fixed (2026-06-08).
**Component:** high-res click-to-export of an analysis axis
(`KrakenOS/UI/services/layout_plot_interaction.py`).
**Reported via:** screenshots `attachment/distortion_before_click.png` (embedded
plot, distortion visible) vs `attachment/distortion_after_click.png` (after
clicking the plot, the distortion series and its right axis are gone).
In the user's words: *"refer distortion_before_click.png vs
distortion_after_click.png, why there is a different after click?"*

## Diagnosis

Clicking the analysis plot opens a high-resolution copy in the system image
viewer via `_open_high_res_plot_in_system_viewer(target_ax)` (dispatched from
`_on_plot_widget_click` → `_open_plot_axis_once`).

To export *only* the clicked axis, that method hid every other axis in the
figure:

```python
for axis in self.figure.axes:
    if axis is target_ax:
        continue
    axis.set_visible(False)
self.figure.savefig(image_path, dpi=320, bbox_inches=bbox)
```

But the Field-Curvature / Distortion plot draws the distortion series on a
**twin axis** (`ax2 = analysis_ax.twinx()` in
`KrakenOS/UI/services/analysis_plot.py`): the focus curves live on the primary
axis, the distortion markers/curves and the right-hand "Distortion [%]" spine
live on the twin. The click always targets the primary axis (the twin is not in
`_analysis_axes`), so the export hid the twin — dropping the distortion series
and its axis. The focus curves and the legend (which lives on the primary axis)
remained, so the legend still listed "X/Y distortion" with empty swatches. That
is exactly the "different after click" image.

The export also computed its crop box from `target_ax.get_tightbbox()` alone, so
even without the visibility bug the right spine would have been cropped off.

## Fix

Keep twin axes — any axis that shares an axis with the clicked one — visible in
the export, and crop to the union of their tight bounding boxes.

New helper `_high_res_export_kept_axes(target_ax)` returns the clicked axis plus
its `get_shared_x_axes()` / `get_shared_y_axes()` siblings (a `twinx`/`twiny`
overlay shares the orthogonal axis), intersected with the live figure axes. The
export then:
- unions the tight bboxes of all kept axes for the crop (`Bbox.union`), so the
  secondary spine is included; and
- hides only axes **not** in the kept set.

Matching-mode single-axis plots (spot, MTF, wavefront, …) have no twin, so the
kept set is just `{target_ax}` and their export is unchanged.

## Tests

`KrakenOS/UI/validate_field_curvature_export_twin_axis.py` (display-free, Agg):
renders the field-curvature analysis on the Double Gauss case-study layout and
asserts a second distortion panel is created and carries the distortion curve;
that panel shares the primary's field (y) axis; `_high_res_export_kept_axes(primary)`
keeps **both** panels; and the export hide-pass (hide everything not kept) leaves
the distortion panel visible. The guard SKIPs cleanly if the analysis itself is
unavailable on a given clone. Folded into the comprehensive harness as **Phase 41**.

## Follow-up: the field-curvature plot is now a two-panel layout (bug 0037)

The Zemax-look rework (bug 0037) replaced the single-axis + `twinx` distortion
overlay with a two-panel layout — **FIELD CURVATURE** (tangential/sagittal focus,
mm) beside **DISTORTION** (percent), field on the vertical axis. The distortion
panel now shares the *field (y)* axis with the host panel instead of the
distortion living on a `twinx` that shares x. The general export fix above keeps
**any** shared-axis sibling, so it covers the new shared-y panel exactly as it
covered the old shared-x twin: clicking the plot exports both panels and the
distortion can never be dropped. The guard was updated to assert the shared-y
panel structure accordingly.

## Verification note

The fixed export was rendered headless (`/tmp/export0035_fixed.png`) and
inspected: the distortion data is present in the export alongside the focus
curves, matching the embedded (pre-click) plot.
