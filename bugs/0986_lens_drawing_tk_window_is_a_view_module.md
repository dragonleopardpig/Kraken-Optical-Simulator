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

## Checks

**Mutations: 12 of 12 caught, each by exactly the claims expected.** The panel importing the Tk
view, or a Tk widget, when imported; ignoring the shell; asking the shell and then drawing with Tk
as well; answering True whatever the session says; going on with no lens in the table; not passing
`for_export` on; the Tk window owned by the panel, not waited on, left up when the session closes,
leaving its listener on the session, or titled otherwise.

The first run showed a weakness in the guard itself: with the panel ignoring the shell, the Tk
window it drew waited on nobody, and the claim failed only after the driver's ten-minute timeout.
Claim Q now refuses any Tk window while the shell is asked, so it fails in seconds and says why.

**Passing after the change:** phase 719 (real typing in the Qt dialog and the Tk window, the same
properties and byte-identical JSON), the lens-drawing properties and PDF guards, the interaction
contract (655), the panel delegations, the form presenter (749), and phase 738 at one module.

`validate_fast_contracts` exits 1, on one of its 178 checks: the line budgets of
`validate_ui_modular_maintainability` (`open3d_inspector.py` 26531 lines against 9000,
`layout_table_workbench.py` 10359 against 6500, `three_d_scene_tools.py` 6856 against 3000). None
of the three files is touched here and the counts are the same at the commit before; it is not a
gated phase.

**Baseline:** phases 752, 738 and 719 recorded (pass; 751 phases). The full Tk gate was last run
at ff4c2088.
