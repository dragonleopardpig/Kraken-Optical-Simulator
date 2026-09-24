# 0871 -- the Error Map row form, and two freezes it exposed

The third row form, and a different shape again: **no editable fields.** It carries a CANDIDATE
error map, shows where it came from and what it holds, and offers two ACTIONS -- Import (ask for a
file, load it, validate it) and Clear.

## FormAction

`FormAction(key, label, run)` is the framework's answer. `run(form, host)` returns the message to
show and may rewrite `form.values`, `form.summary` and `form.state`; the view refreshes from them
afterwards. It asks for whatever it needs through the **UI host**, so one implementation drives
the Tk dialog's `filedialog` and the Qt dialog's `QFileDialog`. `FormField` also gained
`kind="static"` for a value that is shown but never collected back.

On a 49-sample CSV: Import loads and validates it, Apply stores `Error_map` as the model's own
literal (X, Y, Z, SPACE), and applying an empty form removes it from the row.

## Two freezes this found, both real

**A Qt dialog must message through its OWN host.** `RowFormDialog` and `ParaxialCalculatorDialog`
reported refusals with `host_of(self)`. A `QDialog` has no `ui` attribute and no `editor`, so
`host_of` fell through to `TkUiHost(dialog)` -- which raises a **modal tkinter messagebox inside
the Qt application**. It never returns: the app is simply dead, with no visible dialog in the Qt
window. Every dialog now uses `self.host`, which is the `QtUiHost` it was given.

**Applying cleared the table's selection.** A row form opens on the row selected in the surface
table. `refresh_from_model()` resets the table model, which clears the view's current index -- so
the moment a form applied, the next `Edit -->` action found no row and refused with "Select a
surface row first". `refresh_from_model` now restores the selection.

Both were invisible until an action-bearing form existed: the first two row forms never refused
and never applied twice in a row.

## Guard

`validate_open3d_0871_error_map_row_form.py`, penta phase 649. R the two refusals. I Import asks
the host and updates source, summary and state. C Clear empties the candidate. P1/P2 apply stores
the literal (4 parts) and an empty form removes it. T the REAL Tk dialog shows the builder's
source and contents. Q/Q2 the Qt Import and Apply do the same. **S the selection survives the
apply's model reset. H a refusal reaches the dialog's own host** -- the guard would hang, as it
did while being written, if either regressed.
