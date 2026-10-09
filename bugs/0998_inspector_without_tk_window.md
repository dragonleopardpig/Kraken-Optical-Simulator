# 0998 -- the hosted 3D inspector can be built with no Tk window

Phase 7f of the Qt migration (docs/design_qt_migration.md): after the editor (bugs/0993-0997), the
inspector.

## What was there

In the Qt shell the inspector draws into a Qt widget and takes its input from Qt (bugs/0906). It
still made a Tk window -- `self.window`, withdrawn and never shown (bugs/0992) -- and built its Tk
panels into it. Measured in the Qt shell: 247 Tk widgets (the live controls 102, the scene
components 43, the entry widgets 28, the design constraints 21, the system selection 17, the top
controls 16, menus 11, its own 9) and 38 Tk variables, for nobody to see.

## Measured first: what the model needs of that window

A session in the Qt shell with every lookup the inspector forwards to its Tk window recorded.
After construction the model asked the window for exactly one thing: `winfo_exists`, "is the
inspector still there" -- from the table's selection sync, the trace refresh, the scene tools.
That question is asked by that name in twenty places of the model.

And the inspector's own state does not depend on its Tk panels: built with the window and
without, its 207 plain attributes are equal after every step (the addresses of its VTK actors
aside). Phase 5 (bugs/0905-0939) had already taken the inspector's model out of its panels; what
only the inspector with a window holds is 17 Tk widgets and two leftovers of the panels (a slot
for an entry, and the check boxes' variables that mirror which thicknesses are variable -- the
truth is the rows').

## Change

- `Kraken3DInspector(editor, vtk_host=..., tk_window=False)` makes no window and builds no Tk
  panel. Without a window nothing is forwarded to one, so a leftover Tk call raises
  `AttributeError`. Without a shell's VTK widget it is refused: there would be nothing to draw
  into.
- The inspector answers `winfo_exists()` itself: the window's answer when it has one, exactly as
  before; with none, true until it is closed. An inspector built with `__new__` (guards build
  them) still raises, as it always did.
- The Qt shell asks for it only on request: `KRAKEN_QT_TK_FREE=inspector`
  (`KrakenOS/UI/qt/tk_free.py`). The default is unchanged until the whole shell has been measured
  that way.

## Found on the way: the FOV dialog after a lens swap never opened in Qt

After an interactive lens swap the editor says "Enter the field you want in the FOV dialog and
Solve for Thickness." and opens the object-plane FOV dialog 120 ms later (bugs/0609). It asked for
that with `inspector.after(...)` -- a Tk timer on the inspector's window -- and nothing runs Tk
timers under the Qt shell. Measured (`bugs/0998_fov_prompt_after_swap.py`):

| shell | the model says | the FOV dialog is asked for |
|---|---|---|
| Tk | Enter the field you want ... | yes |
| Qt, before | Enter the field you want ... | **never** |
| Qt, after | Enter the field you want ... | yes |
| Qt, no Tk window, after | Enter the field you want ... | yes |

It is asked for on the inspector's host: the same Tk timer for a Tk inspector, the shell's timer
when it is hosted. (Under a shell the dialog itself has been a row form since bugs/0953.)

## Guard: `validate_inspector_without_tk_window` (phase 760)

Two sessions in the Qt shell, the inspector with its Tk window and without: built, refreshed, rays
off and on, a cell committed, a row selected, a thickness made a variable and not, undo, a plot
refresh, the after-swap prompt, closed.

- **W:** on request the inspector has no Tk window, and building it makes no Tk widget and no Tk
  variable (as it always was: a withdrawn `Kraken3DInspectorWindow`, 247 widgets, 38 variables);
  the 3D scene is up with the same 57 actors.
- **S:** after each of 10 steps about 526 plain attributes of the inspector and of the editor are
  equal in the two; what only the inspector with a window holds is listed exactly.
- **L:** without a window it says it exists until it is closed and then that it does not, and
  the editor has forgotten it; five Tk calls on it raise `AttributeError`; asked for without a VTK
  widget it is refused; one built with `__new__` still raises for `winfo_exists`.
- **F:** the FOV dialog after a lens swap is asked for in Tk, in Qt, and in Qt without the
  inspector's Tk window.

## What is left of phase 7f

Running the Qt shell's own guards with `KRAKEN_QT_TK_FREE=inspector` is the wide measurement -- the
guards of phase 5 drive the scene components, the live controls, placement, the tools and the
menus through Qt. Two of them ask the inspector's Tk window for its state and are expected to say
so. Then `KRAKEN_QT_TK_FREE=all` (the editor without its root as well), and making it the default.
