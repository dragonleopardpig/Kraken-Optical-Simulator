# 0908 -- penta phase 330 failing: stale text checks on the Scene Source Manager

**Found:** the 0907 gate run blocked on phase 330, "Source panel folds into the Scene Source
Manager" (guard `validate_open3d_source_panel_into_manager`, bugs/0402/0403). It fails
identically at HEAD before 0907 -- the same 19 failures -- so it is an existing failure that
landed after the 2026-09-20 gate baseline, when it still passed.

## Root cause: the checks read code that moved, not a behaviour that broke

- **MANAGER-VARS (11 failures) and FORM-PERSIST (7 failures).** The check searched the Tk class
  `MainSceneSourceManagerDialog` for `"pupil_pattern": tk.` and `spec["pupil_pattern"]`.
  bugs/0881 (032eda4c) moved the Manager's fields, parsing and save into the toolkit-free
  `row_forms/scene_sources.py`, which both shells render. Nothing had changed for the user: the
  form still has all seven fields, and `_spec_from_values` still writes all seven.
- **SHORTCUT centre (1 failure).** The check wanted `_show_centered_dialog` inside
  `open_scene_source_edit_dialog`. bugs/0885 (d9322268) made that dialog a row form, and every
  row form is centred by `render_row_form` (`owner._show_centered_dialog(window)`).

This is the "guards assert claims, not calls" trap: pinning where the code sat fails when the code
moves, even though the claim still holds.

## Fix: measure the claims

- **MANAGER-VARS.** Build the Manager's REAL field list (`_fields(model(owner), ())`). Require a
  field for each of the 7 keys, the 4 labels the user reads, and choice fields that offer the
  real pupil/Gaussian value lists.
- **FORM-PERSIST.** Save NON-default values for all 7 keys through the real `_spec_from_values`,
  then require every one to come back parsed (7, 11, 2.5, 1.75, the chosen choices) and to
  survive `normalize_scene_source_specs`.
  - Mutation check: dropping `pupil_rad` from the save makes it fail with "a save wrote
    'pupil_rad' = None, not 7".
- **Centre.** The Edit Source dialog either centres itself, or renders through
  `render_row_form`, which centres.

No product code changed.
