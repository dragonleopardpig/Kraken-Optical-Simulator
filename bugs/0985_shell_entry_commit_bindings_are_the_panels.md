# 0985 -- the left panel's entry-commit bindings are the Tk panels' own

Phase 7d of the Qt migration (docs/design_qt_migration.md), fourth part: the modules that load
tkinter through what they import. Three were left after 0984.

## What was there

`services/layout_shell_controls.py` loaded tkinter for ONE import, `widgets.bind_entry_commit`
(importing anything from `widgets` loads the whole Tk widgets package). Two helpers used it:

- `_bind_deferred_refresh(widget)` -- Return, the keypad's Enter and leaving the field mark the plot
  owed; focus-in begins a history capture.
- `_bind_deferred_manual_update(widget, sync_fields=False)` -- the same gestures, but the controls
  are synced first.

Each had exactly one caller, a Tk panel: the optimization panel's operand entries (7 calls) and the
atmosphere panel's entries (2 calls). They were Tk view code living in the model because the panels
reach the editor's methods by forwarding.

## Change

- Each binder is a method of the panel that uses it: `MainOptimizationPanel._bind_deferred_refresh`,
  `MainAtmospherePanel._bind_deferred_manual_update`. The nine call sites are unchanged.
- What a committed atmosphere entry DOES stays the model's: `_commit_manual_update` (sync the
  controls, then mark the plot owed). `sync_fields` is kept on it as it was; no caller passes it.
- The service no longer imports from `widgets`.

Nothing a user sees changes in either interface.

## What it clears, measured by the interpreter

Modules of the toolkit-free layers that load tkinter when imported: 3 -> **2**. Left:
`layout_import_export` (its lens-drawing panel is Tk itself) and `layout_table_workbench`
(the in-cell editor, tied to phase 7b).

## Guard: `validate_shell_entry_commit_bindings` (phase 751)

- **S:** the service imports nothing from `widgets` and names no `bind_entry_commit`; the mixin has
  the model's commit and neither binder; each panel defines its own; nothing else calls either.
- **L:** by the interpreter, in a fresh process -- importing the service loads no tkinter.
- **M:** the model's commit, no display -- left-mode controls then plot owed; the object controls
  with `sync_fields`; an event argument is accepted.
- **T:** a real Tk editor -- all 35 operand entries the optimization panel built, and the 10
  atmosphere entries of the hidden panel and the 10 of the settings dialog, bind the four gestures;
  on a real atmosphere entry of the dialog and on an entry bound by the optimization panel each
  gesture calls exactly what it should, and the status line says the plot is owed.
