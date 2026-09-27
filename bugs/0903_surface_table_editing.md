# 0903 -- the surface table is editable in Qt

Since 0900–0902 the Qt shell could set up and run everything **except the lens itself**. Its
surface table was read-only, and the six table verbs -- add, delete, duplicate, flip, move up,
move down -- could not be offered, because each one read its selection straight from the Tk
Treeview:

```python
def delete_selected(self) -> None:
    selected = self.table.selection()
```

The Qt shell keeps a hidden Tk table (the editor still builds its Tk panels), so from Qt every
verb would always have seen "nothing selected".

## The selection belongs to whichever shell shows the table

Three seams, the same shape as the 0893/0898 ones:

- `_selected_table_indices()` asks a shell's `selected_row_indices()` first
- `_select_table_indices()` also tells a shell's `select_rows(indices, focus)`
- `_sync_table()` tells a shell's `show_rows()` when the rows were rebuilt

A Tk-only editor installs none of them, so Tk behaves exactly as before. The six verbs ask
`_selected_table_indices()` instead of touching `self.table`.

## One commit for an edit

`commit_cell(row_index, field, text)` is the single commit both shells take. Tk's `_finish_edit`
and its surface/glass choice menu call it; the Qt model's `setData` calls it. It returns "" or the
reason for a refusal, so the Qt shell can report a refusal in its status bar instead of a Tk
message box popping up over a Qt window.

**It still parses through the Tk table** (`table.set` then `_read_rows_from_table`), exactly as
a Tk edit always has. That is deliberate for now: one parser rather than a second one that could
disagree about `*` variable markers, tolerance sequences or formatting. It is also why a Qt edit
cannot be reverted by the hidden table -- the commit writes *through* it, so there is nothing
stale left to re-read. The guard checks exactly that. Moving the cell parser off the Tk table is
the next seam in this area, and it is a larger job: `_read_rows_from_table` rebuilds every row.

## The Qt cells are the Tk text

The Qt table used a private seven-column formatter (radius as `f"{v:.4f}"` and so on). It now
shows all 15 fields as the model's own `_table_values_for_surface_row` renders them, which is the
text the Tk table shows -- and therefore the text an edit starts from. Surface and glass open a
combo with the same choices Tk offers (`TABLE_GLASS_CHOICES` is now one shared constant; a
loaded glass outside the quick list stays selectable). A cell the surface type disallows
(`_table_cell_enabled`) and the `#` column are not editable. `refresh_from_model` now keeps the
**whole** selection, so a verb that selected the two rows it duplicated does not come back with
one.

## Found along the way

`KrakenOS.UI.qt` lazily exported `SurfaceRowsModel`, a name that never existed at module level
-- the class is built inside `make_rows_model` so the package imports without Qt. Reaching for it
has raised `ImportError` since 0855. The package exports the real factories now.

## Guard

`KrakenOS/UI/validate_open3d_0903_surface_table_editing.py` (penta phase 691):

- **S** -- no verb reads the Tk selection; the selection, the rebuild and the commit all go
  through the seams or `commit_cell`
- **T** -- Tk is unchanged: its selection drives duplicate/delete, its typed edit and glass choice
  commit, and a bad value still raises its own error box
- **Q1** -- all 25 × 15 Qt cells are the Tk text
- **Q2** -- an edit commits (18.0 → 19.5), `abc` is refused with the model's message and changes
  nothing, a cell the surface type disallows and the `#` column are not editable
- **Q3** -- all six verbs act on the Qt selection. Flip is checked by order and names:
  `om05a_folded` has no curved Standard surface, so the radius negation cannot be seen on it
- **Q4** -- an edit survives a later verb **and** a forced re-read from the hidden Tk table

Re-pointed with it: `validate_open3d_0855_qt_shell` Q2 (the cells are the Tk text now, a
stronger claim than "the Qt formatter of the raw attribute").
