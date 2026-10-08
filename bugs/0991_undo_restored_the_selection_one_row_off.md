# 0991 -- after Undo the selection was one row off, and Delete removed the wrong rows

Found by the selection record of bugs/0990, which showed it before and after that change.

## What happened

The history keeps, with each state, which rows were selected -- as row numbers. Restoring a state,
the editor took each number as a PLACE in the table:

```python
items = list(table rows)
selected_items = [items[index] for index in selected_indices ...]
```

A row's number and its place in the table are the same only while every table line is a surface
row, in order. They differ as soon as

- the scene has an illumination source: its row sits above row 1 and shifts every place by one;
- a path view is on: rows of other paths are hidden.

Measured in the Tk interface, on the two-arm doublets (one source row): rows 2 and 3 selected
("Splitter rear face", "Transmit doublet crown front"), a thickness committed, Undo -- rows 1 and 2
were selected, and Delete then removed "50/50 splitter front" and "Splitter rear face": the beam
splitter. Undoing a delete could even leave the source row selected.

The Qt table keeps its own selection across an Undo, and the Qt shell's verbs ask that table, so
there the right rows were deleted; only the model's own copy of the selection was wrong.

## Fix

`services/layout_table_workbench.py`, the history restore: each saved row number is looked up as a
row (`_table_item_for_row_index`). A row the current view does not show is simply not selected.

## What changed, measured

The selection record (`bugs/0990_selection_record.py`, sixteen layouts on a real Tk editor, 537
steps) before and after: fourteen layouts identical. The two that changed are the two with a source
row, and each differs from its first Undo on -- there the selection is on the rows that were
selected, where it was one row up.

## Not fixed here: the active cell is never restored

The same code is meant to put the active cell back after an Undo. It never does: the state saves the
cell's COLUMN as `#6`, and the restore accepts only a field name such as `thickness`. Making it work
would change what the Tk table shows after every Undo (the cell cursor would come back), so it is
left for a decision rather than slipped in here.

## Guard: `validate_undo_restores_selected_rows` (phase 757)

- **M:** the model, on a headless editor -- with a source row above: Undo and Redo leave rows 2 and
  3 selected, Delete removes exactly them, undoing the delete selects them again; in a path view a
  selected row comes back as that row; a scene with no source row behaves as before.
- **T:** the Tk interface -- after Undo the selection's outline is on rows 2 and 3, measured against
  the table's own cells, and Delete removes those rows.
- **Q:** the Qt interface -- after Undo the Qt table and the model name the same rows.

## Checks

**Mutations: 4 of 4 caught.** The saved row numbers taken as places again -- the bug itself, which
fails all three claims; Undo leaving the selection where it is; Undo restoring the selection but not
the focus item; the selection not captured with the state.

The second one drove a change to the guard before it was run: as first written, nothing selected
another row between the edit and the Undo, so "restored" and "left alone" looked the same. The
model claim now selects elsewhere before every Undo and Redo.

**Passing after the change:** the selection and cells guards (756, 755), the three table workflow
guards, the overlays guard (753), the panel delegations, the interaction contract, and ten gate
phases about undo and the table (365, 424, 439, 510, 594, 595, 657, 691, 700, 753).

**Baseline:** phase 757 recorded (pass; 756 phases). The full Tk gate was last run at 2052dda3; it
is owed for 0989-0991.
