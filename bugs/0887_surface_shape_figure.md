# 0887 -- `FormFigure`: the matplotlib seam, and the dialog that needed it

The Surface Shape Builder is everything that makes a surface a **shape** rather than a radius:
asphere and Zernike coefficients, an ExtraData preset, a UDA preset, a mask preset, and an
optical CAD/STL path. Its explanation is a **plot** -- an `imshow` of the sag/departure map with
a colorbar, beside the aperture/UDA/mask footprint.

`FormPreview` (0886) could not carry that: it draws polygons and text with no dependencies.

## The ninth family property

```python
@dataclass(frozen=True)
class FormFigure:
    width: float = 7.2
    height: float = 5.4
    dpi: int = 100
    draw: Callable[[Any, dict, Any], str]   # form, values, figure -> the status line
```

The **model draws into a figure the view supplies**. The view owns the canvas and its lifecycle
-- Tk embeds `FigureCanvasTkAgg`, Qt embeds `FigureCanvasQTAgg` -- and clears the figure before
each draw. `draw` returns the **status line**, which is where a validation warning about the
drawn candidate belongs: the same `validate_advanced_surface_inputs` call that guards Apply also
captions the plot.

**This one seam is most of phase 6.** Only four files in the tree embed matplotlib: the main 2D
layout plot, this dialog, the CAD face-roles editor and MTF-from-image. The last two also need
**picking**, so they stay in phase 5; `FormFigure` is draw-only, like `FormPreview`.

## "Refresh Preview" is gone on purpose

The old dialog had a Refresh Preview button *and* a `trace_add` on every variable. In the
framework every field redraws the figure as it is typed, so there is nothing left to press. The
guard pins the behaviour that button existed for: a Ronchi preset draws 24 mask patches where
`None` draws 0, **before any Apply**.

`panels/main_surface_shape_builder_dialog.py` 375 -> 80 lines.

## Two guard assertions I had to correct

- `"[1.0, inf]"` does **not** reach the finiteness check -- `inf` is not a Python literal, so it
  fails to *parse* first. `1e400` parses and overflows, which is what actually exercises it.
- `FigureCanvasTkAgg`'s widget is a plain `tk.Canvas`; the figure hangs off the canvas **object**,
  not the widget. Detect the embed by the widget's size, not by an attribute it does not have.

## Guard

`KrakenOS/UI/validate_open3d_0887_surface_shape_figure.py` (penta phase 675):

- **B** -- 11 shape fields, one Browse verb, a figure; an Image row refuses
- **D** -- draw fills 3 axes (two subplots and the colorbar) and reports the model's verdict
- **F** -- the plot follows the values: Ronchi -> 24 mask patches, None -> 0, with no Apply
- **V** -- "must be a numeric list", "contains non-finite values"
- **A** -- apply writes `advanced`, `extra_data` and `uda` together (mask preset, `Mask_Type`,
  and a 6-sided UDA)
- **T** -- the REAL Tk dialog embedded a 720 px matplotlib canvas
- **Q** -- the Qt dialog embedded one with 3 axes and the same 24 patches
