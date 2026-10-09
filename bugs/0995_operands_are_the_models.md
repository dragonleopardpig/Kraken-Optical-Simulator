# 0995 -- the optimizer's operands are the model's, with or without the Tk cards

Phase 7f of the Qt migration (docs/design_qt_migration.md), third step: the last cause on the list
of differences bugs/0993 left between an editor with a Tk root and one without.

## What was there

Each merit operand has settings -- weight, target and so on. They are variables in per-setting
tables on the editor (`operand_weight_vars[label]`, ...), read by the merit function and saved
with the layout. The Tk optimization panel made them while it built an operand's card, and the
first operand was "in use" because the panel's list box selected its first line. An editor
without that panel had no settings and no operand in use: its saved state, and every undo state,
carried no operands.

0904 gave the model `ensure_operand_variables` for the Qt panel, built from what an operand's
card SHOWS (`spec.controls`). Comparing the two editors showed that is not what the Tk card
MAKES. It makes a variable for the weight, target, wavelength, field and surface of every operand
and hides the widgets the operand does not use; for the MTF operand it also makes the field point
(x, y), the frequency, the mode and the algorithm. 45 settings for 8 operands, 19 of them shown.
The 26 hidden ones are saved with the layout all the same: `'EFFL': {'field': '0', 'surface':
'Auto', 'target': '100', 'wavelength': '0.55', 'weight': '1'}`.

## Change

- `optimization_controls.variables_for(spec)` says what an operand HOLDS: the five every operand
  holds, what its card shows, and the field point beside the field of an operand evaluated at a
  spatial frequency. `controls_for(spec)`, what a card shows, is as it was -- the Qt panel builds
  from it.
- `ensure_operand_variables` makes what an operand holds (45), not what it shows (19).
- An editor without a Tk root calls it in its constructor and starts with the first operand in
  use.

The Tk panel is not touched: it makes its own variables as before. What ties the two together is
the guard -- the tables the Tk cards fill, operand by operand, and their start values, are exactly
what `variables_for` and `default_for` say.

## Proof that the Tk editor did not change

`bugs/0993_tk_before_after.py`: the guard's session on the Tk-rooted editor at the commit before
(twice) and with the change -- no attribute differs at any step. (The files changed are the
catalogue, the model's routine and the constructor's branch for no root; the Tk panel's file is
not among them.)

## Guard: `validate_editor_without_tk_root` (phase 759), extended

- **S:** the list of known differences is EMPTY. After each step about 300 plain attributes of
  the editor without a root -- rows, cells, selection, 79 variables, the operands' settings and
  the ones in use, the undo and redo stacks -- equal the Tk-rooted editor's. (0993 began with 16
  differing.) The list stays, exact, for what a wider session finds.
- **R:** every operand holds its settings from the start (8, 8, 8, 8, 8 and 1 each of the MTF
  five), the first operand is in use, a choice of operands and a setting are kept, and a settings
  round trip restores both.
- **T:** on the Tk window the cards make 45 settings, exactly the ones the model declares, with
  the model's start values, and the first operand is in use.

`validate_open3d_0904_optimization_in_qt` (phase 692), claim C2: the model's routine makes all the
settings the operands hold for an owner with no shell and none where the Tk panel had, and every
one of them starts as the Tk panel's does.

## What is left of phase 7f

The session is 45 steps of editing, inputs and settings. Not in it yet: the analyses and their
mode switches (the Tk window keeps `analysis_mode_vars`), tolerances, an optimization run, saving
and loading a file. Then the inspector's own Tk window and its 247 hidden panel widgets, and only
then the Qt shell asks for an editor without a root. Nothing a user sees changes with this step.
