# 0993 -- the editor can be built with no Tk root

Phase 7f of the Qt migration (docs/design_qt_migration.md), first step.

## What was there

`KrakenLayoutEditor(...)` always made a `tk.Tk()` and built every Tk panel -- also under the Qt
shell, which hid the result. Measured: the Qt shell starts with 1 Tk root and 399 Tk widgets, and
adds 247 when the 3D scene is shown; a headless editor starts with 384 widgets and 148 Tk
variables, 696 widgets after a 35-step session.

It could not simply be left out. An editor given a stand-in for the root failed at once
(`AttributeError: main_pane`), and where it did not fail it was a different model. Parts of the
MODEL only worked because Tk panels existed.

## Change

`KrakenLayoutEditor(headless=True, ui=<a host>, tk_root=False)` builds the editor with no root
and no Tk panel. It is opt-in: 94 guards build a headless editor and use its hidden Tk table, and
the Qt shell does not ask for it yet (see "What is left").

Without a root nothing is forwarded to one, so a leftover Tk call raises `AttributeError` -- it
fails loudly instead of reaching a window nobody sees. Without a UI host it is refused.

Each of the following was found by comparing the two editors on one session, not by reading:

1. **The Tk window's pane layout was in the model.** Eight methods of the toolkit-free
   `services/layout_shell_controls.py` -- the sashes, the two sidebars and their restore strips,
   the left panel's scrolling -- and the model asks for a re-layout after every plot refresh.
   They are `MainWindowBuilder`'s now (`panels/main_window.py`), where there is nothing to lay out
   when there is no Tk window.
2. **Model reactions were wired by Tk panels.** The source summary follows 23 source values, a
   typed direction names its preset, the atmosphere summary follows eleven values: variable traces
   the source and atmosphere panels added while building their entries. No panel, no reaction --
   the summary still said "Pupil / field source" after a scene with a collimated disk source was
   loaded. They are the model's (`_install_source_summary_reactions`,
   `_install_atmosphere_summary_reactions` in `services/source_modeling.py`); the two panels call
   them at the same point, in the same order, and an editor without panels calls them once its
   variables exist.
3. **The field's state was kept only while a Tk widget existed.** `_sync_field_mode_ui` returned
   when there was no Tk field-type menu, so the field's label, note, status hint and sample count
   did not follow the object mode; `_sync_field_sample_count_state` returned when there was no Tk
   entry, so the count was never "NA" while the field is zero. Both keep the model's part always
   and tell the Tk widgets through two view methods of the window builder.
4. **What a temporary trace printed reached the debug log only if a Tk text box existed.** The
   log has been the model's since 0898; the test asks for the model's list now.
5. **The field value was declared with its value after start-up** (`model_variables.py` records
   "the value after start-up", and until now nothing ever created a variable from it). Start-up
   computes the blank scene's image diameter in its first table sync, while the field value is
   still the panel's initial 5.0, and only then zeroes the field. Created with 0.0, the blank
   scene's image was 4 mm wide; the Tk editor's is 17.497733. `CREATED_WITH` names the variable
   and what a panel creates it with. (Two more variables are changed by start-up, the sample
   count and the status hint; creating them either way leaves the same editor, so they are not
   listed.)
6. **The atmosphere's ten numbers were not declared at all.** The Tk panel makes them by name
   from `ATMOSPHERE_CONTROL_SPECS` and the model reads them by name, so neither end was seen by
   the scan that keeps the registry complete. Without the panel an observatory preset filled
   nothing and a saved layout's numbers were dropped on load. The registry declares them from the
   same list: 79 model variables, was 69.

## Proof that the Tk editor did not change

- **The model.** `bugs/0993_tk_before_after.py` runs the guard's scripted session on the
  Tk-rooted editor at the commit before, twice, and with the change: 35 steps (load, commit,
  select, duplicate, undo, redo, group, move, delete, path view, object mode, field, aperture,
  source model and values, direction, observatory, atmosphere, a settings round trip, plot
  refresh, add, trace mode, reset, undo), 386 attributes of the editor recorded after each. No
  attribute differs at any step; the two runs before agree with each other.
- **The window.** `bugs/0993_pane_snapshot.py` on a real Tk editor: pane count, sash positions,
  which sidebar and restore strip is shown, the status line, through six hide/show steps and a
  re-layout, the canvas's scroll region and width -- identical before (twice) and after, and the
  screenshots are the same file byte for byte (`0993_tk_window_before.png`,
  `0993_tk_window_after.png`).

## Guard: `validate_editor_without_tk_root` (phase 759)

- **N:** through the session the editor without a root makes no Tk root, widget or variable
  (counted at tkinter's constructors); its 79 model variables are its host's; five Tk calls on it
  each raise `AttributeError`; it closes; without a UI host it is refused.
- **S:** after each of the 35 steps about 300 plain attributes of the two editors are compared.
  They differ in 16, all listed in the guard by cause; the list is exact, so one that stops
  differing has to leave it and a new one fails.
- **R:** sixteen reactions of the model hold with no Tk: both summaries follow their inputs, the
  typed direction names its preset, the observatory fills the numbers, the field's label, count
  and hint follow the object mode, settings restore what they saved, a trace's print is in the
  debug log.
- **T:** the Tk window lays itself out from the window builder: three panes, each sidebar hides
  and comes back with its restore strip, the status line and the same sashes; the canvas follows
  its width and content; the sample-count entry is greyed while the field is zero and the field
  types are offered in the object mode's order.
- **L:** the eight pane methods are the window builder's and not the service's; the two panels
  wire no variable trace of their own; of 57 editor attributes that hold a Tk widget, the
  toolkit-free layers name 19, 61 times -- it was 30, 103 times. Exact, may only shrink.

`validate_open3d_0852_model_variables` (phase 631) holds the registry: 79 declared, the ten
atmosphere numbers with their list's defaults, and -- claim R4 -- an editor with no root holds
exactly the registry's values after its start-up and begins with the Tk editor's blank scene.

## Seen on the way, not changed

The blank scene the editor starts with is not the blank scene File > Reset gives, in the Tk editor
too: Image diameter 17.497733 at start-up, 25 after Reset, the field 0 and the image diameter mode
Auto both times. The start-up value is what a 5 degree field would need -- the field panel's
initial value, which start-up zeroes only after it has sized the image. Finding 5 above keeps that
start-up scene as it is, so the two editors agree; which of the two blank scenes is the intended
one is not decided here.

## What is left of phase 7f

The 16 attributes that still differ are model state that still lives in a Tk panel, two causes:

- **The optimizer's operands** (14): the weight, target, wavelength, field, surface, frequency and
  MTF settings of each merit operand are variables the Tk optimization panel creates, and which
  operands are selected is a Tk list box's selection. Without the panel the saved settings and
  every undo state carry no operands.
- **Which inputs apply** (2): the value an input that does not apply is set aside with, and the
  sample count's "NA", are worked out over the widgets the Tk panels register. The rules are
  already the model's (0902); the loop over them is not.

Then the inspector's own Tk window and hidden panels, and only then the Qt shell asks for an
editor without a root. Nothing a user sees changes with this step, in either interface.
