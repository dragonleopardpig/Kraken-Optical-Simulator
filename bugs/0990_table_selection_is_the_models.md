# 0990 -- which rows are selected, and which has the focus, is the model's

Phase 7b of the Qt migration (docs/design_qt_migration.md), second part. With 0989 the table's
cells became the model's; the selection was still asked of the Tk table.

## What was there

The Tk table shows a selection as borders, never as the `ttk.Treeview`'s own highlight. To get
that, the widget's `selection`, `selection_set`, `selection_remove`, `selection_add` and
`selection_toggle` had been replaced, on the widget instance, by closures over a list the editor
holds. So the state was the model's -- but it lived in a widget's methods, existed only once a Tk
table was built, and the model reached it through the widget: `self.table.selection()`,
`self.table.selection_set(...)`, `self.table.focus(...)`, `self.table.see(...)`, 57 times in three
service modules. The Qt shell kept a hidden Tk table for model verbs to select rows in.

## Change

- **The model** (`services/layout_table_workbench.py`): `_table_selection`, `_set_table_selection`,
  `_remove_from_table_selection`, `_add_to_table_selection`, `_toggle_table_selection` -- the
  closures' bodies, moved as written -- and `_table_focus_item`, `_set_table_focus_item`,
  `_show_table_item`. They need no table.
- **Every call site** in the model -- 44 in the table workbench, 3 in the import/export service, the
  scene placement commands' two through a local alias -- uses them.
- **The Tk table is pointed at the model** (`panels/main_surface_table_overlays.py`): its
  `selection*` methods ARE the model's methods, so a Tk panel that asks the widget asks the model.
  The panel also clears what the widget selects natively, mirrors the focus item, and scrolls a row
  into view.
- **The focus item** stays the Tk table's own while there is one: Tk panels set it on the widget,
  and it is lost when the rows are rebuilt. Without a Tk table the model remembers it, and loses it
  at the same moment.
- Two places did their selection work only IF a Tk table existed -- capturing the selection for
  undo, and selecting a path's rows when the path view changes. They do it regardless now. And the
  two overlay entry points (the active cell's outline, the grid) do nothing when there is no Tk
  table to draw on.

Nothing a user sees changes in either interface.

## Measured

| What the toolkit-free layers ask the editor's Tk table | Before 0989 | After 0989 | Now |
|---|---|---|---|
| about its cells | 26 | 0 | 0 |
| for its selection, focus item, or to scroll | 57 | 57 | **0** |
| whether there is one, to do something only then | 13 | 13 | 10 |
| about the pointer and the view (Tk event handlers) | 16 | 16 | 16 |

A correction to 0989: its report and guard said 58 selection uses. One of the 58 was another table
-- the ray inspector's -- caught by a pattern that matched any local named `table`. The count is of
the editor's surface table only now: 55 direct uses and 2 through a local alias, 57.

## Proof that nothing changed

`bugs/0990_selection_record.py`, on a real Tk editor, run at the commit before and after: for
sixteen layouts -- two selects through the model; plain, Control, Shift and Shift-Control clicks on a
cell and on the row label; six arrow keys; a click on a variable marker; clicks on a source row;
clear; a commit, undo and redo; duplicate, move down and up, group, ungroup, delete and its undo; a
sync; add surface; two path views with a click in each -- and after every step the selected items,
the focus item, the active cell, the anchor, what each of five selection queries answers, the number
of border pieces, what the widget has selected natively, a digest of the rows, and every message box
the step raised. **537 steps, identical before and after**, and identical between two runs at one
commit. The cells record of 0989 (5 857 steps) is unchanged as well.

## Found on the way: bugs/0991

In a scene with an illumination-source row, Undo puts the selection on the wrong row: it saved row
numbers and restores them as positions in the table, and the source row shifts every position by
one. Both records show it, before and after; it is not from this change, and it is the next fix.

## Guard: `validate_table_selection_model` (phase 756)

- **S:** the toolkit-free layers ask the Tk table for its selection, focus item or scrolling nowhere
  (0, counted by phase 755's scan); the eight methods are the model's, the widget code the panel's.
- **M:** the model alone, on a headless editor whose Tk table and overlays are removed.
- **N:** with and without a Tk table, a script of 22 steps leaves the same selection, focus item,
  answers and rows after every step.
- **T:** a real Tk editor -- the widget's methods are the model's; a click, and a Tk panel calling the
  widget, both change what the model answers; nothing is selected natively; the borders follow; the
  focus item is mirrored both ways; a row out of sight is scrolled into view.

## Checks

**Mutations: 16 of 16 caught.** The model asking the Tk table again; a selection keeping a row
twice; a change not announced; a row that left the table staying selected; the focus item surviving
a rebuild; the model ignoring the Tk table's own focus item; a focus item not reaching the Tk table;
the Tk table keeping its own selection methods; scrolling doing nothing; the selection captured for
undo, or a path's rows selected, only when a Tk table exists; a toggle that only adds; the scene
placement commands asking a Tk table; the active cell's outline needing one.

Two survived the first run, both gaps in the guard:

- **A selection that stores a row which is not shown.** Every read prunes such a row, so nothing the
  guard asked could tell -- but it would come back selected the moment the row is shown again. Claim
  M looks at what was kept, before any read.
- **The Tk table's native selection not being cleared.** Nothing in the guard ever made the widget
  select natively. Claim T does, and requires the next change to clear it.

**Passing after the change:** 23 neighbour guards -- as for 0989, with the stand-in table of
`validate_table_component_workflow` given the model's selection state and pointed at it as the real
Tk table is -- and the same 32 gate phases, one at a time.

**Baseline:** phases 756 and 755 recorded (pass; 755 phases). The full Tk gate was last run at
2052dda3, before 0989; it is owed.
