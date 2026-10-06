# 0969 -- an operand's surface choices are model data, not a walk over the window

Phase 7c of the Qt migration (docs/design_qt_migration.md), second half.

## What was wrong -- measured

`_refresh_operand_surface_choices` is model code and runs on every table sync. It built the list an
operand's "Surf" picker offers, then found the pickers by walking **every widget of the Tk window**
and comparing each combobox's variable name with the operands' variables.

On the two-arm doublets layout:

- the window holds **409 widgets**; eight of them are operand "Surf" pickers;
- **none of the eight is laid out** -- no operand declares a surface setting today, so the picker
  is built per card and never shown, in either shell;
- the refresh took **2.0-4.6 ms per call**, of a table sync that takes about 5 ms in all.

So roughly two fifths of every table sync went on filling eight invisible pickers. And the walk is
what tied this piece of the model to a Tk widget tree at all (phase 7f takes the tree away).

It is NOT a gap a Qt user can see today. The Qt optimisation panel built its picker from the
catalogue's fixed `("Auto",)`, which would have been wrong the day an operand declared a surface
setting; it is right now by the same change.

## Change

- **The list is model data:** `operand_surface_options()` -- Auto, then every row that is neither
  the object nor the image, as "index: name".
- **The refresh hands it over instead of hunting for pickers.** The Tk panel registers each card's
  picker on the editor (`operand_surface_menus`); a shell with pickers of its own gets the list
  through a `show_operand_surface_choices` seam. `_apply_surface_values_to_descendants` is gone.
- **The catalogue says where a setting's choices come from:** `OperandControl.options` names the
  editor method (`"operand_surface_options"` for the surface setting), and `choices_for(control,
  editor)` returns the model's list or the setting's fixed choices.
- **The Qt panel** builds a choice from `choices_for`, and installs the seam: an open "Surf" picker
  is refilled and shows its operand's variable, with no write going back.

Unchanged: an operand aimed at a surface that no longer exists goes back to Auto; an empty value is
left (it already reads as Auto).

After: the refresh takes **0.2 ms**, a table sync **2.8 ms**.

## Guard: `validate_operand_surface_choices` (phase 737)

- **P1:** the model with no display -- the list; a vanished surface back to Auto, a valid one kept;
  every registered picker and the shell's seam handed the list; the window asked for its widgets
  not once; an owner with no picker and no shell (a stripped snapshot editor) does not raise.
- **P2:** the catalogue -- the surface setting names the model's method; `choices_for` with and
  without a model; a fixed setting keeps its own choices.
- **T:** a real Tk editor -- eight pickers registered, one per operand, each offering the model's
  11 choices; after a rename and a table sync they offer the new list; the sync makes no
  `winfo_children` call on the editor.
- **Q:** a real Qt shell, one operand given a surface setting for the test -- the seam is the
  panel's; the picker offers the model's 11 choices; choosing one writes that operand's variable;
  with ANOTHER row renamed the open picker shows the new list and still that surface; with that
  surface's own row removed, the variable and the open picker are both back on Auto.

## Checks (2026-10-06, X299-SSD; every run alone, at low priority)

**Mutations: 11 of 11 caught**, each restored from a copy, the tree clean afterwards.

| Mutation | Caught by |
|---|---|
| the object and image rows are offered | P1 |
| a vanished surface is not put back to Auto; the shell is not handed the list | P1, Q |
| the registered pickers are not handed the list; the refresh walks the window again | P1, T |
| the catalogue's surface setting names no model method; `choices_for` ignores the model | P2, Q |
| the Tk panel does not register its pickers | T |
| the Qt panel does not install the seam; the Qt picker is built from the fixed choices | Q |
| the open Qt picker does not restore its selection after a refill | Q |

**One of these survived the first guard, and that was a hole in the guard:** the seam refilled the
open picker without restoring its selection, and the only case tested ended on "Auto" either way (a
refilled combo box selects its first entry). Q now renames ANOTHER row and requires the picker to
show the new list and still the chosen surface (6db27814). A second mutation was first caught only
by the guard raising; P1 fails that claim cleanly now.

**Neighbouring guards:**
- pass, none skipped: Optimisation in Qt (0904), the interaction contract (655), the table
  component workflow, the scene row mapping, the preset and bounds forms (0891), the optimisation
  controls catalogue;
- `validate_fast_contracts` exits 1 on ONE of its checks, `ui-modular-maintainability`: three files
  are over their line budgets (`open3d_inspector.py` 26 533 lines against 9 000, and two more). It
  was failing before this batch (26 496 lines at 8403abde), it is in no gate phase, and it is not
  about this change. Its other checks pass, the optimisation-controls one among them.

**Baseline:** phase 737 recorded (1 pass, 0 fail). The full Tk gate is owed since 8403abde.

