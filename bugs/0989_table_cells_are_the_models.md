# 0989 -- the surface table's cells are the model's; the parser no longer reads a Tk widget

Phase 7b of the Qt migration (docs/design_qt_migration.md), first part: "the model off the hidden
Tk table".

## What was there

A cell of the surface table is text. `_sync_table` formats the rows into texts; a typed or chosen
value replaces one text; and the cell parser, `_read_rows_from_table`, makes the rows again from the
texts -- one parse path for a typed value and a displayed one, named 57 times in 24 files.

The texts lived in the Tk table widget. The parser asked a `ttk.Treeview` for its items and their
values; a commit wrote into the widget and parsed it back; "is this row shown in the current path
view" was a question to the widget. So the Qt shell, whose own table already showed the model's
texts, and every headless editor kept a hidden Tk table to parse a typed number.

One thing was already wrong because of it: the path-local mode of the pose columns -- which changes
what the parser does with them -- was only recorded when a Tk table existed.

## Change

- **`services/table_cells.py`** (new, no toolkit): the table's rows in display order, each a list of
  texts and its colour tags. As dumb as the widget it replaces; what a text means is the parser's.
- **The model** (`services/layout_table_workbench.py`): `_sync_table` fills the cells; a committed
  cell, a chosen material or surface type and the image row's diameter each set one text
  (`_set_table_cell_text`); "which rows are shown" is asked of the cells; the path-local mode is the
  model's, table or no table.
- **The parser** (`services/editable_table_rows.py`) reads the cells.
- **The Tk table is a view**: `panels/main_surface_table_overlays.py` puts the model's rows, one
  cell, or the headings into the `ttk.Treeview`, and does nothing when there is no Tk table.
- **Two builder scripts** (`build_penta_telescope_layout.py`, `build_penta_analytic_telescope_layout.py`)
  renamed a row by writing its name into the Tk widget, so that the next parse would not put the old
  name back. They tell the model's cells now.

Nothing a user sees changes in either interface.

## Measured

| | Before | After |
|---|---|---|
| Uses of the editor's Tk table for its CELLS in the toolkit-free layers | 26 | **0** |
| ... for the selection (`selection*`, `focus`, `see`) | 57 | 57 |
| ... for the pointer and geometry (`bbox`, `identify_*`, `xview`, ...) | 16 | 16 |
| A headless editor with its Tk table destroyed: 35 cell edits and path-view changes | raised | **same answers, same rows** |

The 57 are the second part of 7b (bugs/0990); the 16 are Tk event handlers and go with the editor's Tk side
(7f). (This report first said 58: one of them was another table, the ray inspector's -- see bugs/0990.)

## Proof that nothing changed

`bugs/0989_cells_record.py`, run at the commit before and after: for each of the 164 tracked layouts
(the common layouts and the test fixtures), loaded one after another into one headless editor --

- the table's cell texts and tags, as the Tk table holds them;
- the rows after a parse, and after a second parse;
- eleven edits on each of the first three rows (a number, a name, a pose list, a material, a refused
  word, ...), a surface type change, a mirror tilt list;
- each path view: its rows, a thickness and a pose typed there, an edit of a hidden row;

each step recorded as its answer, a digest of every row and a digest of every cell. **5 857 steps,
identical before and after**; and identical between two runs at the same commit, so the comparison
means something.

## Guard: `validate_table_cells_model` (phase 755)

- **S:** no module of the toolkit-free layers asks the editor's Tk table about its cells (0, counted);
  what they still ask is counted exactly and may only shrink; the cell store names no tkinter.
- **C:** the cell store on its own.
- **N:** a headless editor whose Tk table is destroyed and removed takes the same 35 steps as one
  that has it -- same answers, same rows -- and knows it is in a path view.
- **P:** a text written straight into the Tk widget is NOT parsed; a text given to the model is, and
  the Tk table shows it; the two builders' rename survives a parse.
- **V:** the Tk table shows exactly the model's cells -- rows, order, texts, tags -- after a load, a
  committed cell, a chosen material, a path view and back; with the path-local headings there.

Three guards that fed the parser through a stand-in Tk table give the texts to the model's cells
instead (`validate_phase6_path_workbench`, `validate_table_component_workflow`; `validate_scene_row_mapping`
needed no change).

## Checks

**Mutations: 15 of 15 caught.** The parser reading the Tk widget again; a sync not showing the Tk
table the rows; a text given to the model not shown, or shown but not kept; "is this row shown"
asked of the widget; showing the rows needing a Tk table; the rows shown without their tags, or in
reverse; the path-local mode recorded only when there is a Tk table, as before; the cell store not
padding a short row, or keeping an id's first place; a hidden row taking an edit; a builder writing
its rename into the widget again; the path view's headings staying plain.

One survived the first run: **the image row's diameter cell written to the Tk widget only.** The
guard called that re-format but never changed the diameter, so the text was the same either way. It
changes it now, and requires the model's cell, the Tk table and a parse to agree.

**Passing after the change:** 22 neighbour guards -- the overlays (753) and popup (748) guards, the
panel delegations, the interaction contract (655), the selector menus (740), phase 738, the three
that stood in for the Tk table, and the twelve that build a fake editor from the table mixin alone
-- and 32 gate phases about the table, rows, undo, saving, the row forms and the Qt table (365, 371,
373, 410, 424, 439, 510, 514, 594, 595, 599, 619, 624, 631, 636, 647-654, 657, 672, 691, 692, 700,
722, 737, 749, 753), run one at a time.

**Baseline:** phase 755 recorded (pass; 754 phases). The full Tk gate was last run at 2052dda3,
before this change; it is owed.
