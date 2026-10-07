# 0987 -- what the Tk surface table draws over its rows is a panel

Phase 7d of the Qt migration (docs/design_qt_migration.md), the last module: after 0986 one module
of the toolkit-free layers still loaded tkinter when imported, and named it sixteen times at run
time through globals the editor copies into it.

## What was there

`services/layout_table_workbench.py`, the surface table's model, also held the Tk table's drawing
code. A `ttk.Treeview` has no cell border, no grid and nothing per cell, so the Tk table places small
widgets over itself, and all of that was here:

| | Tk used |
|---|---|
| The border round each block of selected rows | `tk.Frame` x 4 |
| The border round the active cell; its re-draw on scroll | `tk.TclError` x 2 |
| The grid lines | `tk.Frame` x 2, `tk.TclError` x 2 |
| The "V" marker of an optimization variable | `tk.Label` |
| The entry a cell is edited in | `widgets.place_commit_cell_entry` -- the import that loaded tkinter |
| The choice menu of a Surface or Material cell, and posting a popup menu | `tk.Menu`, `tk.TclError` |
| Undo / Redo of the Tk Edit menu | `tk.TclError` |
| Scheduling a selection change | `tk.TclError` |
| The default answer of one question | `messagebox.NO` |

## Change

- **`panels/main_surface_table_overlays.py`** (new): the thirteen methods that draw over the table --
  borders, grid, markers, and the three scroll handlers that re-draw them -- cut from the service as
  one contiguous block, plus `_place_cell_editor`, the one Tk line of `begin_edit`.
- **`panels/main_popup_helpers.py`**: `_show_choice_menu` and `_post_popup_menu` join the popup-menu
  helpers that moved there with 0981.
- **`panels/main_window.py`**: `_show_tk_undo_state`. The panel that builds the Edit menu shows the
  undo state in it; the model computes the two booleans and tells the Tk view and a shell's seam
  alike.
- **The service** keeps which rows are selected, which cell is active, which cells are variables,
  what a committed edit does, and whether there is anything to undo. Its selection-change scheduling
  catches whatever the host raises, as the other host calls in these layers do, and the question's
  default is the string `"no"` -- which is what `messagebox.NO` is.
- **The editor** delegates the seventeen names to the three panels.

The methods were cut and pasted by a script from the service's own source, not retyped. Two things
had to change in them, and either would have been invisible until someone looked at the table:

1. The moved code read `self.__dict__` in two places -- "is there a table at all", and "which
   outlines are up". On a panel that is the PANEL's dict: the first would have drawn no selection
   outline ever, the second never removed one. Both read the editor's dict now.
2. The choice menu was made with `tk.Menu(self)`. On a panel that works, but the menu's owner is
   then the panel object; it is `tk.Menu(self.editor)`.

The panel forwards every attribute it sets to the editor, so the state these methods keep -- the
active cell, the overlay lists, the two pending-redraw ids -- stays where the model reads it.

Nothing a user sees changes in either interface.

## Proof that nothing visible changed

One fixed scene (the two-arm doublets, rows 2-3 and 6 selected, an active cell, three variable
cells), recorded at the commit before and after:

- every widget on the table -- 25 grid lines, 8 outline pieces, 4 active-cell pieces, 3 markers --
  with its class, colours, text and placement; the in-cell entry's placement and value; the choice
  menu's entries, owner and position; the Edit menu's states; what scrolling does: **identical**;
- a screenshot of the whole window: **identical, pixel for pixel** (`0987_tk_table_overlays_before.png`,
  `0987_tk_table_overlays_after.png`).

## What it clears, measured by the interpreter

| | Before | After |
|---|---|---|
| Modules of the toolkit-free layers that load tkinter when imported | 1 | **0** |
| Modules there that name tkinter at run time without importing it | 1 (16 uses) | **0** |
| `layout_table_workbench.py` | 10359 lines | 10059 |

Both of phase 738's lists are empty now, and a module that reaches or names tkinter again fails
there. What is left of Tk in the services is of another kind, and belongs to later phases: they name
a Tk view CLASS 37 times -- the `_main_*` panel factories (7f) and the legacy viewer's calls on the
inspector class (7e) -- and the cell parser still reads the hidden Tk table (7b).

## Guard: `validate_surface_table_overlays_view` (phase 753)

- **S:** the service imports nothing from `widgets` and names no tkinter at run time; none of the
  fifteen moved methods is still on the model; the three panels define them; the editor delegates
  each of the seventeen names.
- **L:** by the interpreter, in a fresh process -- importing the service loads no tkinter.
- **M:** no display -- the undo state is told to the Tk view and to a shell's seam alike; a
  selection change is scheduled once, and a host that cannot schedule leaves nothing pending.
- **G, B, E, C, U, X:** a real Tk editor, measured against the table's own cells -- the grid and the
  markers; the outlines of the selection and of the active cell, and their state on the editor; the
  in-cell entry, typed into and committed to the model's row, and cancelled; the two choice menus,
  one chosen from; the Edit menu's states; scrolling.

## Checks

**Mutations: 28 of 29 caught.** Among them the two traps of the move -- the panel asking its own
dict whether there is a table, or which outlines are up -- and the third one that a panel can fall
into, keeping underscore state on itself as some panels do. Also: the choice menu owned by the
panel, or posted past the editor's poster; the in-cell entry off its cell, without Escape,
committing to another field, or opening empty; the undo state told the wrong way round, or not told
to a shell; a separator one pixel off; re-drawing piling overlays up; markers not drawn, or not
clickable; a scroll that schedules no re-draw; a row that is gone staying the active cell; a
pending re-draw never cleared.

Two survived the first run:

- **A selection outline's right edge 10 px inside the table.** A hole in the guard: it compared an
  outline's bounding box, which is still right when one side is misplaced, because the two sides
  across it span it. Claims B and X compare the four 2-pixel pieces now, and catch it -- with the
  same slip on the active cell's outline, and a bottom edge on the wrong row.
- **The active cell's outline not re-placed by the horizontal-scroll handler.** Not a hole: three
  paths re-place that outline after a horizontal scroll (the handler, the table's own scroll
  callback, and the grid re-draw), and with one cut the outline still follows the cell. With all
  three cut the guard fails, so the claim is live; the handler's own call is redundant.

**Passing after the change:** the popup-helpers guard (748), the panel delegations, the interaction
contract (655), the commit bindings, the table component workflow and scene row mapping guards, the
Qt table's context menu (722), the selector menus (740), phase 738 with both lists empty -- and the
twelve guards that build a fake editor from the table mixin alone, any of which a method that left
the mixin could have broken.

**Baseline:** phases 753, 738 and 748 recorded (pass; 752 phases).
