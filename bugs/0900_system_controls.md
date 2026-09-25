# 0900 -- the system inputs in Qt

0899 let the Qt shell pick plots and press Update. It still could not change **what** was
traced: object mode, wavelength, ray fan count, aperture type/value and field
type/value/samples were labels and value lists written into two Tk panels' `build()`, and the
commit each one ran -- resync, mark the plot stale -- was a method on those panels rather than
on the model.

## The inputs are data

`KrakenOS/UI/system_controls.py` names, for each input, the **model variable** it edits and the
**model method** to call after a change:

```python
SystemControl("aperture_type_var", "Aperture type", "choice", ("STOP", "EPD", "FNO"))
SystemControl("field_value_var", "Field value", commit="commit_field_controls",
              label_key="field_value_label_var")
```

A view is then layout and binding only, and binding is the trick the status bar already uses:
every one of these variables is declared in `model_variables.py` and carries `trace_add` whether
a Tk panel or a UI host made it. The model writing a value repaints the widget; the widget
writing one goes through `commit_trace_controls` / `commit_field_controls`, which are on the
**model** now (the Tk panels keep a two-line callback that delegates).

Qt gets a **System** dock. On `om05a_folded` it opens on the loaded system -- FNO 4.5, Real
Image Semi-Height, 3 field samples -- repaints when the model writes, and on a commit leaves
*"Display settings changed. Click Update."* on the status line.

## Two drifts closed on the way

- **The four field types had two declarations**, one in `layout_editor.py` and an identical copy
  in `open3d_inspector.py`. Both import the one in `system_controls.py` now. That is also what
  broke the **import cycle**: `system_controls` cannot import `layout_editor`, because
  `layout_editor` imports the panels that read the catalogue.
- **A label that depends on the system.** The field value's caption is `"Real Image Semi-Height
  [mm]"` on this scene, not "Field value" -- it lives in `field_value_label_var`, so
  `SystemControl.label_for(owner)` reaches the model's live label and falls back to the
  catalogue's only when there is none.

## Guard

`KrakenOS/UI/validate_open3d_0900_system_controls.py` (penta phase 688):

- **C** -- 8 inputs, every one against a registry-declared variable, both Tk panels reading the
  catalogue's labels and choices
- **F** -- the field types are declared once and imported by the editor and the 3D inspector
- **S** -- the commits are the model's; the Tk panels delegate
- **L** -- the field value shows the model's live label, in both shells
- **Q / B** -- the Qt form opens on the loaded system; a model write repaints it and a form
  write reaches the model and marks the plot stale
