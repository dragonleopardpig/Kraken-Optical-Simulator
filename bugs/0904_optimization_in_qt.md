# 0904 -- optimisation in Qt

After 0903 the Qt shell could edit the lens but not optimise it. Three things stood in the way,
and all three were the model reaching into Tk widgets.

## Which operands are in use

The chosen merit operands existed **only** as a Tk Listbox's selection --
`merit_mode_list.curselection()` -- read by three model functions (`_selected_operand_labels`,
`_selected_operand_specs`, `_update_operand_setup_visibility`). The Qt shell keeps a hidden Tk
Listbox, so from Qt the model would always have read Tk's default ("Spot RMS").

`_selected_operand_labels()` now asks a shell's `selected_merit_operands()` first, then the Tk
Listbox, then the headless list, and the other two readers call it; `_set_selected_operand_labels`
also tells a shell's `select_merit_operands`.

## Start / Stop

`_update_optimization_button_state` configured the Tk button's text and command itself. It also
tells a shell through `show_optimization_state(running)` now.

## Marking a variable, and its bounds

"Select *param* for optimization", "Set bounds…" and "Clear bounds" were Tk-menu verbs keyed on
the Tk item under the mouse (`current_menu_row_id`). `optimization_cell_state(row, field)`,
`toggle_optimization_cell(row, field)` and `clear_bounds_for_cell(row, field)` take a row and a
field; the Tk menu verbs delegate. "Set bounds…" opens the same row form both shells already use
(0891).

## The settings

Which settings an operand has was already data (`OperandSpec.controls`); what each setting **is**
-- label, the per-operand variable that holds it, its choices, its starting value -- was written
into the Tk panel's `build()`. It is `KrakenOS/UI/optimization_controls.py` now, and the Tk panel
takes the MTF mode and algorithm lists from it. Worth knowing: the Tk panel builds wavelength,
field and surface widgets for *every* operand card and then hides them, because no current
operand's `controls` names them; only weight and target show, plus frequency/mode/algorithm for
MTF. `ensure_operand_variables()` makes any per-operand variable a view has not -- today only the
Tk panel creates them, so a shell without it would have had none.

The Qt shell gets an **Optimization** dock (Start/Stop, Workers, the operand list, each chosen
operand's settings) and the optimisation entries of the cell menu. A marked cell carries the Tk
marker's colour, decided by the model's own `_optimization_marker_fields_for_row`.

## Measured

- **A real optimisation started from the Qt dock matches Tk exactly.** Spot RMS on the Cooke
  triplet case study goes **25.0547 → 0.053189** from Qt and from Tk; the button goes Stop →
  Start.
- **On `om05a_folded`, Spot RMS evaluates to the 1e9 failure sentinel in both shells.** Marking
  a thickness and running Spot RMS moves the thickness (21.6 → 28.005) on a flat merit and reports
  `1e+09 -> 1e+09` -- identically in Tk. So it is not a Qt fault; it looks like the Spot RMS
  operand cannot evaluate this folded, non-sequential scene. **Recorded, not fixed here.**

## Guard

`KrakenOS/UI/validate_open3d_0904_optimization_in_qt.py` (penta phase 692):

- **S** -- the Tk Listbox is read in exactly one place (the fallback), Start/Stop has a seam, and
  the Tk menu verbs delegate to the row-and-field ones
- **C1/C2** -- every control the 8 operand specs name is catalogued; the Tk panel takes the MTF
  lists from the catalogue; `ensure_operand_variables` fills all 19 settings for a shell-less
  owner and none where Tk already did; the defaults equal what the Tk panel creates
- **T** -- Tk unchanged: its Listbox shows the model's choice, its menu toggle marks the cell, its
  button follows the run state
- **Q1/Q2** -- in Qt a pick is what the model reads, each operand shows exactly its settings, a
  typed weight reaches `_operand_weight`, the cell menu offers select / set bounds / clear bounds
  with the right enabled states, and a marked cell carries the Tk marker colour
- **Q3** -- a real optimisation from the Qt dock ends on the same merit as the same run in Tk

## Not covered

The Tk cell menu has eleven more submenus (Convert Type, Insert Component Below, Shape/Aperture,
Material, Coating/Polarization, Geometry, Advanced, tolerance compensator/coupling/manufacturing,
paraxial solves). Only the optimisation entries moved here; the rest are on the migration plan.
`_refresh_operand_surface_choices` still walks every Tk descendant widget to update operand
surface lists -- harmless while no operand shows a surface control, but it is another widget walk
in model code.
