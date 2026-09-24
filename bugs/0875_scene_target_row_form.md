# 0875 -- the Scene Target row form

A row's scene-target metadata: its name, its role (Auto / Analysis Target / Detector / Object
Target / Diffuse Object / Aperture), whether it is the active non-sequential `TargSurf`, and --
**only when the role is Detector** -- that detector's active size, bins and pixel pitch.

## The one thing the framework could not express

`FormField.enabled` is decided when the form is **built**. It answers "the model will never take
edits to this" -- a literal the reader cannot parse back, a shape parameter on an Image row. Here
the answer changes while the dialog is open: pick Detector and the four detector fields become
editable; pick anything else and they lock again.

So `RowForm` grew the live half:

| piece | what |
|---|---|
| `RowForm.locked` | the fields locked *since* the form was built (live, like `choices`) |
| `form.is_enabled(key)` | `field.enabled and key not in locked` -- what a view must ask |
| `form.lock(*keys, locked=True)` | what an `on_change` calls to follow its own choice |

Both views now ask `is_enabled`, never `field.enabled` -- including the Tk advanced-surface
dialog, where the two agree but the rule should be one rule.

## Same split as every other row form

All four model pieces this dialog needs reach the Tk shell as **constructor kwargs** of
`MainSceneElementDialogs`, not as editor attributes: `scene_target_editor_kind_labels`,
`scene_target_editor_kind_choices`, `normalize_scene_target_editor_kind`,
`normalize_detector_settings`. `model(owner)` reads each off the owner and falls back to
`services/element_scene_metadata.py`. The `_`-prefixed workbench helpers
(`_scene_target_editor_kind_for_row`, `_default_detector_settings_for_target_row`,
`_apply_scene_target_editor_update`, `_clear_scene_target_editor_metadata`,
`_current_nonseq_target_surface_index`) are on the editor and need no fallback.

Which row the form opens on is model logic too, so `resolve_row_index()` holds it: the caller's
index, then the scene-graph selection (`_nonseq_scene_selected_record`), then the table.

## Guard

`KrakenOS/UI/validate_open3d_0875_scene_target_row_form.py` (penta phase 653), display-free, Qt
half in a subprocess:

- **R** -- an out-of-range row refuses with "Select a surface row or scene target first."; an
  Object row refuses the Detector role
- **L** -- S1 opens with all four detector fields locked, Detector unlocks all four, Auto locks
  them again, and `FormField.enabled` stays `True` throughout
- **V** -- the messages for a non-number, a negative pitch and bins out of range; `Auto` passes
- **A** -- apply writes the role, the name and the active `TargSurf`; Clear Target removes them
- **T** -- the REAL Tk dialog shows the builder's values and its four detector **entries are
  disabled** under Auto (7 bound variables, 4 disabled)
- **Q** -- the Qt widgets open disabled and the combo enables all four live; Apply writes
  role=detector, name, active and width

## Files

- `KrakenOS/UI/row_forms/scene_target.py` (new), registered in `row_forms/__init__.py`
- `KrakenOS/UI/row_forms/base.py` -- `locked`, `is_enabled()`, `lock()`
- `KrakenOS/UI/qt/dialogs/row_form_dialog.py` -- build and refresh follow `is_enabled`
- `KrakenOS/UI/panels/main_scene_element_dialogs.py` -- `open_scene_target_editor` rewired
- `KrakenOS/UI/panels/main_advanced_surface_dialog.py` -- asks `is_enabled` too
- `KrakenOS/UI/qt/actions.py`, `KrakenOS/UI/qt/main_window.py` -- Edit > Scene Target...
