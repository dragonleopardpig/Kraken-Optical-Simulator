# 0942 -- menu parity, part 1: every working Tk menu command gets a Qt route

Follow-up to the 0941 probe, which ran every Tk menu-bar command inside the Qt shell and recorded
what each one actually opened. Many already worked under the Qt shell and simply had no Qt menu
entry. This part routes those, and fixes three Qt-shell bugs the routes exposed.

## Routes

`ACTIONS` entries can now name `editor:<method>`: the action runs the editor's own method through
`KrakenQtMainWindow.run_editor_command`. Afterwards:
- methods in `EDITOR_REFRESH` change the model, so every view re-reads it;
- every other method re-titles the window, since Save / Save As may name the layout.

Added:
- **File:**
  - Save (Ctrl+S, new; the Qt shell had no Save at all);
  - Save As (Ctrl+Shift+S);
  - Reset;
  - the Zemax / CAD / STEP imports;
  - the STEP / DXF / wavefront / Zernike exports.
  Quit stays last.
- **Edit:**
  - Undo (Ctrl+Z) and Redo (Ctrl+Y and Ctrl+Shift+Z) are at the top. They enable and disable
    with the model's history through a new `show_undo_state` seam, called from
    `_update_undo_redo_buttons`.
  - Copy / Paste rows (Ctrl+C / Ctrl+V). These two shortcuts act only while the surface table
    has focus (`TABLE_SHORTCUTS`), as Tk binds them on its table. Window-wide, they would take
    copy away from the report tables.
  - The CAD clears, and 3D Place/Orient.
- **View:** Refresh Plot, Folded Assembly.
- **Analysis:** benchmark, report copies, Clear Zemax reference, Clear Marks.
- **Help:** formula sheet, manual index, Copy Debug.

**Ribbon:** Save, Save As, Undo and Redo get icons on the Home tab. The rest are menu-and-palette
only, each listed in `RIBBON_EXCLUDED` with its reason. Reset stays off the ribbon, like Quit: it
wipes the layout (Undo brings it back).

**Already ported:** four commands the probe listed as "opens a Tk window" were already ported
under other labels, because they call the same Tk methods. They are:
- Stock Lens Catalog (= Import Stock Lens);
- Inspect Ray / Surface Physics (= Ray Inspector: the same report builder);
- Inspection Part;
- Inspection Cell.

## Bugs the routes exposed

1. **File → Reload (Ctrl+R) and Reset destroyed the hosted 3D inspector.** A full layout load
   (`load_layout_by_name`, behind the Qt shell's Reload and `load_layout_path`) and Reset run
   `_close_scene_viewers_for_layout_replacement`. That closes the separate Tk 3D window, but it
   also destroyed the inspector hosted in the Qt shell's dock. The dock then held a dead
   inspector, and the editor's `_three_d_inspector` was None. File → Open takes another path and
   was not affected (measured: reverting the fix leaves Open passing and fails Reload / Reset).
   - Now an inspector with a `_shell_vtk_host` is kept and marked `_layout_replaced_pending`.
     The shell's `refresh_from_model` then calls the new `adopt_replaced_layout()`.
   - That shared step (also used by the bugs/0294 import path) drops the old layout's
     carry/rotation/selection handles and re-reads the new layout's 3D-session sidecar, as a
     fresh inspector would. It then runs `_apply_model_change()`.
2. **Paste went to the wrong place in Qt.** `_selected_insert_index` read the HIDDEN Tk table's
   selection, which is always empty in the Qt shell, so Paste inserted before the Image row
   instead of after the selection. It now asks `_selected_table_indices()`, the shell seam from
   0903. Stock-lens insert shares it.
3. **`_current_selected_row_index` read the hidden Tk table too.** It now uses the same seam.
   The inspector's "selected row" readers depend on it: the CAD/STL placement row, the grid's
   primary placement, the optical-faces opener and the placement-target pick. Tk is unchanged:
   with no shell seam, it reads its own Treeview as before.

## Guard: `validate_qt_menu_parity` (phase 718)

- **S:** all 75 Tk menu-bar commands are covered: 54 are routed in Qt, and 21 are `KNOWN_GAPS`
  with reasons. The gap list may only SHRINK: a gap that gains a route fails until it is deleted.
  Every `editor:` target exists on the editor.
- **H:** Undo / Redo restore the model AND the Qt table, and enable and disable with the history.
- **A:** Save As asks once and titles the window. Save after an edit re-asks nothing, and the
  file reloads with the edit.
- **C:** Ctrl+C / Ctrl+V on the table paste right after the Qt selection; Ctrl+C in Results copies
  no rows.
- **I:** File → Open shows the new layout in the inspector (its scene bounds change). File → Reload
  keeps it alive, still the editor's, and done adopting the reloaded layout.
- **R:** Reset gives Object + Image in the model and the table. The inspector survives and is
  redrawn: its scene shrinks to the blank layout. Undo brings the layout back.

0855 (B) and 0860 (A) now accept `editor:<method>` targets, but only if the editor defines the
method. `validate_qt_ribbon` (714):
- C requires icons only for ribbon actions.
- B now covers a disabled action. Redo starts disabled with nothing to redo, so its button rightly
  ignores a click. B checks that the button is disabled too, then enables the action to prove the
  click lands.

**Mutation-checked**, each fix reverted on its own:
- Paste reads the Tk selection → C fails.
- Layout swap destroys the hosted inspector → I (Reload) and R fail.
- Ctrl+C / Ctrl+V window-wide → C fails (Ctrl+C in Results copied rows).
- The shell never adopts the kept inspector → I and R fail (the scene stayed on the old layout
  after Reset).

**Gated:**
- Qt-shell phases 634-654, 669-695, 697 and 704-718, plus the phases whose validators read the
  touched code (257, 258, 263, 268, 316, 476, 485, 492, 500): 73/73 after the 714 B fix.
- The `--shell qt` harness gate passes 352/352. It took 2611 s, longer than the run that recorded
  its baseline; the cause was not measured.

## Remaining gaps (part 2+)

- 18 commands call Tk messagebox / simpledialog directly and need `host_of`:
  - the 6 tolerance reports and 5 tolerance CSV exports;
  - the 5 path / detector / field CSV exports;
  - lens-drawing properties and export.
- The path-view component / stock-lens placement commands end in Tk row forms.
- Atmospheric Settings opens a Tk window and needs a Qt port.
