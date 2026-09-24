# 0874 -- the Detector Settings row form

Marks a surface as a terminal detector for the path analyses and sizes it: active width, active
height, a bins override and a pixel pitch.

This is the first dialog the framework absorbed with **nothing new** -- four fields, one `Clear`
action, the model's own normaliser. After five row forms that each needed another property
(`choices`, `on_change`, `group`, `enabled`, `kind="bool"`), a dialog that is just a builder plus
a menu entry is what a finished framework is supposed to feel like.

## The model is split, and neither half is where you would look

| piece | where it actually lives |
|---|---|
| `_detector_settings(row)` | a `LayoutTableWorkbenchMixin` static method on the editor |
| `normalize_detector_settings` | a **constructor kwarg** of the Tk dialog shell, passed in from the workbench |
| `_normalize_detector_settings` | `KrakenOS.UI.services.element_scene_metadata` |
| `_set_detector_settings(row, data)` | the workbench again |

So `model(owner)` reads each name off the owner when it has it and falls back to the defining
module otherwise -- the same pattern the other row forms needed, because the dialog shell's
kwargs are not attributes of the editor. My first version fell back to
`element_scene_metadata._detector_settings`, which does not exist: the *normaliser* is there, the
*reader* is on the workbench. The guard caught it on the first run.

## The rules belong to the normaliser, not the dialog

`_normalize_detector_settings` owns them, and the form only reports them:

- bins outside 4-512 are **clamped**, not refused (so the form refuses first, with a message, and
  the user sees what they typed rather than a silently changed number);
- `Auto`, `default` and `none` all mean **blank** -- use the global Detector bins field;
- sizes and pitch are coerced non-negative and non-finite values become 0.

And `_set_detector_settings` **removes** the `Detector` key when the settings are all-default
rather than storing zeros. That is exactly what `Clear` does: `write({}, ...)`.

## Guard

`KrakenOS/UI/validate_open3d_0874_detector_settings_row_form.py` (penta phase 652), display-free,
with the Qt half in a subprocess as always:

- **R** -- a row out of range refuses with "Select a surface row first.", an Object row with
  "Object rows cannot be detector planes."
- **V** -- the messages for a non-number, a negative size and bins out of range; `Auto` passes
- **D** -- the description reports size, bins and pitch
- **A** -- apply writes through the editor's own setter (12.5 mm, bins=64); `Clear` removes them
- **T** -- the REAL Tk dialog opens on the builder's values (5 bound variables)
- **Q** -- the Qt form opens with the same four fields and its `Clear` action, and applies the same

## Files

- `KrakenOS/UI/row_forms/detector_settings.py` (new), registered in `row_forms/__init__.py`
- `KrakenOS/UI/panels/main_scene_element_dialogs.py` -- `open_detector_settings` rewired onto the
  builder; the Validate/Apply/Clear/Cancel footer is unchanged
- `KrakenOS/UI/qt/actions.py`, `KrakenOS/UI/qt/main_window.py` -- Edit > Detector Settings...
