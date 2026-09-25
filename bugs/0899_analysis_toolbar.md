# 0899 -- the analysis picker and Update in Qt

The Qt shell could open every dialog and, since 0898, show every result -- but it could not set
an analysis **up**. The 24 plots a user can tick, their grouping in the picker and their
tooltips were literals inside the Tk toolbar's `build()`, and the model reached back into that
toolbar to write the button's caption:

```python
menubutton.configure(text="Plots: 3 ▾")
```

## The plots are data

`KrakenOS/UI/analysis_modes.py` holds `MODE_GROUPS` (5 groups, 24 `(caption, mode)` pairs),
`MODE_TOOLTIPS`, and `selection_label(count)` -- the picker's own caption. The caption reaches a
shell through `show_analysis_modes(modes, caption)`, the same seam shape as 0893's
`set_plot_cursor` and 0898's three panels. `selected_analysis_modes` stays the one truth; a
shell only ticks what it is handed, and ticking calls the model's own `toggle_analysis_mode`.

Qt gets a toolbar: a checkable **Select plots** menu that stays open across ticks (which is what
the Tk dropdown was hand-rolled for -- a `tk.Menu` unposts on every click), an **Update** that
calls the model's own `_manual_update_plot`, and **WFront 3D**.

## Two tables, two jobs

The toolbar captions are deliberately **not** `layout_plot_controller.ANALYSIS_MODE_LABELS`.
Five of them differ:

| mode | button | prose |
|---|---|---|
| `wavefront` | WFront | Wavefront |
| `polarization` | Pol | Polarization |
| `field_map` | FldMap | FieldMap |
| `illum_map` | IllMap | IllumMap |
| `interferogram` | Interf | Interferogram |

A toolbar button has room for the short one; the status line and the plot titles want the long
one. The guard pins that difference on purpose, so nobody "deduplicates" two tables that do two
different jobs.

## Guard

`KrakenOS/UI/validate_open3d_0899_analysis_toolbar.py` (penta phase 687):

- **C** -- 24 plots in 5 groups with a tooltip each, and the Tk panel reads the catalogue
- **N** -- those five captions differ from the long labels
- **S** -- the model configures no widget; it hands its selection and caption to the seam
- **T** -- the REAL Tk toolbar ticks the model's own variables and shows the model's caption
- **Q** -- the Qt menu offers all 24; ticking and unticking drive the model, and the caption
  follows the model rather than the click
- **U** -- Qt's Update runs the analysis the model was told to run (71 results rows,
  `analysis_mode="mtf"`)
