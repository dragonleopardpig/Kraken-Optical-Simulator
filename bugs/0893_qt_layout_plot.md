# 0893 -- the 2D layout plot in Qt, and the last two Tk leaks out of the model

The 2D plot was never view code: the model draws into `editor.ax` and calls
`editor.canvas.draw_idle()`. What was toolkit-specific was the **canvas** -- plus two things that
had leaked into `services/layout_plot_interaction.py`, which is model/controller code and should
never have known what a Tk widget is:

```python
widget = self.canvas.get_tk_widget()
y_display = float(widget.winfo_height() - event.y)      # a TK event needed flipping
...
self.canvas.get_tk_widget().configure(cursor=cursor)
```

## Both are gone

- **The click is a matplotlib `button_press_event`.** Matplotlib already reports display
  coordinates with the origin at the bottom left -- the same frame `get_window_extent` uses --
  so the flip disappears and the widget lookup with it. Both shells connect the same event.
- **The cursor goes through `editor.set_plot_cursor(name)`.** The names stay Tk's ("hand2", "")
  because that is what this code has always said; the Tk shell configures the widget, the Qt
  shell maps the name onto a `QCursor` shape, and a headless editor silently ignores it.

`KrakenOS/UI/qt/plot2d.py` is then small: make a `FigureCanvasQTAgg`, hand the editor its figure
and axes, connect the same three events. It docks on the right so the 3D view keeps the centre.

## Measured, and worth knowing

**`refresh_plot` REPLACES `editor.ax` on every draw** -- it re-lays the figure out for the
analysis panes. A view must therefore read the axes *live* and never cache the one it created.
The first version of this port cached it and reported an empty plot while the real axes held
**30 lines, 106 collections and 17 texts** titled `'YZ full 3D'`. `LayoutPlot2D.axes` is a
property onto `editor.ax` for exactly this reason.

## Guard

`KrakenOS/UI/validate_open3d_0893_qt_layout_plot.py` (penta phase 681):

- **S** -- no `get_tk_widget()` **call** and no `winfo_height()` left in the service, and both
  shells connect `button_press_event`. The check looks for the *call*, not the word: the
  docstring that explains the fix says "get_tk_widget()" too, and the first version failed on
  its own prose
- **C / C2** -- the cursor seam in both shells, and its silence when headless
- **Q** -- the editor's figure and canvas *are* the Qt ones, with a real layout drawn into them
- **L** -- the axes replacement
- **K** -- a matplotlib click in the layout axis reaches the model and it acts. Which branch
  fires (ray pick, row pick, open axis) depends on what is under the centre, so the guard pins
  that it was *handled* rather than pinning the scene

The four existing 2D guards -- `layout_plot_controller`, `2d_refresh_after_solve`,
`model_change_marks_2d_stale`, `2d_3d_projection_sync` -- all still pass, which is the check that
matters for the Tk side. (Penta phases 1-4 exercise this path end to end but take over ten
minutes each; the four guards cover the same ground in seconds.)
