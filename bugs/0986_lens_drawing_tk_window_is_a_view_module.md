# 0986 -- the lens-drawing properties' Tk window is a view module

Phase 7d of the Qt migration (docs/design_qt_migration.md), fifth part: the modules that load
tkinter through what they import. Two were left after 0985.

## What was there

`panels/main_lens_drawing_dialogs.py` does three things: it shows the lens-drawing properties
session in the running shell's dialog, or in Tk's window, and it exports the PDF (bugs/0945). The Tk
window -- 110 lines of widgets -- was one of its methods. So the panel loaded tkinter, and through
the panel `services/layout_import_export.py` did; its other two panels only show forms and stopped
loading it with 0983.

## Change

The window is `panels/lens_drawing_properties_view.py`, one function over the panel and the session.
The panel imports it at the moment Tk draws -- after it has asked for a shell. The body was moved by
a script from the method's own source, not retyped; its four uses of the panel (the window's parent,
twice; the centring; the wait) are the same calls.

Nothing a user sees changes in either interface.

## What it clears, measured by the interpreter

| | Before | After |
|---|---|---|
| Modules of the toolkit-free layers that load tkinter when imported | 2 | **1** |
| Tk view classes named in services | 38 uses of 32 classes | 37 uses of 31 classes |

The one left is `services/layout_table_workbench.py`: the surface table's in-cell editor and choice
menu, which go with phase 7b.

## Guard: `validate_lens_drawing_tk_view` (phase 752)

What the window does with real typing, and that both shells leave the same properties, is phase 719.
This guard holds what the move added:

- **S:** the panel imports and names no tkinter and nothing from `widgets`; the view module defines
  the window; the panel asks for a shell before it reaches for the Tk view.
- **L:** by the interpreter, in fresh processes -- importing the panel loads no tkinter, and neither
  does importing the import/export service.
- **Q:** under a shell on a headless editor -- no lens in the table: the host is told, the shell is
  not asked; with the two-arm doublets the shell gets a session of 8 surfaces, continued answers
  True and cancelled False -- and the Tk view is never imported.
- **T:** the Tk app -- a Tk window owned by the editor, titled as the session says, 112 entries
  (8 surfaces x 14 properties) and the session's six buttons, waited on; Close answers True, Cancel
  Export False; afterwards the window is gone and the session has no listener left.
