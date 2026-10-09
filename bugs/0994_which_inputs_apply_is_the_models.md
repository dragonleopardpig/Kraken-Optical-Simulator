# 0994 -- which inputs apply is worked out by the model, not over Tk widgets

Phase 7f of the Qt migration (docs/design_qt_migration.md), second step. One of the two causes
bugs/0993 left on its list of differences between an editor with a Tk root and one without.

## What was there

Not every input applies to every system: a Gaussian beam has no pupil pattern, a scene with its
own light source has no field type, the sample count means nothing while the field is zero. An
input that does not apply keeps its value set aside (`_left_mode_saved_values`), and
`_left_mode_text` reads it from there when the input says "NA".

WHICH input applies has been the model's rule since 0902 -- each input of the catalogue
(`system_controls`) names its rule. But the loop that applied the rules,
`_sync_left_mode_controls`, went over the WIDGETS the Tk panels register, and returned at once
when none was registered. So in an editor without Tk panels:

- nothing was ever set aside;
- the sample count was not re-examined (that call sat below the early return): after switching
  from a Gaussian beam back to the default source with a zero field, the count stayed 3 where the
  Tk editor has "NA" and 3 set aside.

Measured first: the Tk panels register 48 widgets, 45 of them for an input, and those 45 are
exactly the catalogue's 46 inputs but the source model itself, which always applies. The same
inputs, twice.

## Change

`_sync_left_mode_controls` is two parts:

- `_set_aside_inputs_that_do_not_apply` -- the model's: over the catalogue, each input that does
  not apply has its value set aside, each that applies and says "NA" gets its value back -- what
  was set aside, or else what the variable is created with (`model_variables.created_with`; the
  Tk loop used the value the widget's variable had when the widget was registered, which is the
  same value);
- the Tk widgets follow: each registered widget is enabled or disabled, the panel is laid out
  again -- nothing to do when no panel registered one.

Then, always, the sample count and the shell's notice.

An editor without a Tk root takes its first look at which inputs apply in its constructor, while
every input still holds what it was created with -- where the Tk source panel takes it as it
finishes building. Without that, the values set aside were whatever the first loaded scene held
(its seed 3, not 1).

## Proof that the Tk editor did not change

- **The left panel.** `bugs/0994_left_panel_snapshot.py`, on a real Tk editor, walks every
  source model, every scene-trace mode and both object modes, then a field, a zeroed field, and an
  input saying "NA" with nothing set aside. At each of 21 points, for each of the 48 registered
  widgets: its state, whether and where it is gridded, the flag the reflow uses; every input's
  value; everything set aside; the source row's span and whether the field panel shows. Identical
  at the commit before (twice) and after, and so is the screenshot.
- **The model.** `bugs/0993_tk_before_after.py`: the guard's session on the Tk-rooted editor, at
  the commit before (twice) and with the change -- no attribute differs at any step.

## Guard: `validate_editor_without_tk_root` (phase 759), extended

- **S:** `_left_mode_saved_values` and `field_count_var` left the list of known differences; the
  two editors now differ only in the optimizer's operands (14 attributes).
- **R:** new facts, with no Tk: the sample count follows the field (NA, 1, 5, NA) and its value is
  set aside; an input found saying "NA" gets the value it was created with, or the one set aside
  for it; an input that stops applying is set aside (the field type, once a scene with its own
  source is loaded); the first values are set aside from the start, not from the first loaded
  scene; the count is "NA" again when the default source returns with a zero field.
- **T:** on the Tk window, for the default source and for a Gaussian beam: each of the 45
  registered inputs' widgets is live and in the panel exactly when the catalogue says the input
  applies; the source row spans and the field panel shows as the source model wants.

`validate_open3d_0852_model_variables` (phase 631) holds what a variable is created with.

## What is left of phase 7f

The optimizer's operands (their settings are variables the Tk optimization panel creates, the
selected ones a Tk list box's selection), a wider session, the inspector's Tk window, and then the
Qt shell asks for an editor without a root. Nothing a user sees changes with this step.
