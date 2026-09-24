# 0876 -- the Path-Local Pose and Element Settings row forms

The last two dialogs in `panels/main_scene_element_dialogs.py`. Both edit the pose and metadata
of a placed element; Element Settings edits the whole record, Path-Local Pose only the six pose
numbers in the element's own path frame.

## They edit a BLOCK, not a row

An element is a **run of consecutive rows sharing one element key** -- a doublet is three
surfaces. Every row form until now assumed one row.

| piece | what |
|---|---|
| `RowForm.row_index` | the block's **first** row -- the row a view selects, and the row whose `advanced` dict holds the element's metadata |
| `form.state["indices"]` | the block itself |
| `resolve_block(owner, row_index, ...)` | the caller's row grown into its block (`_element_block_for_index`, exactly as `_selected_element_blocks` grows one), or the table's selection when a view has no row to offer |

A selection spanning two elements refuses ("Open Element Settings for one element at a time."),
which is why the resolver takes both messages: the Tk context menu has no row to hand over, the
Qt surface table always does.

Reading the metadata from `indices[0]` is not a detail. The first attempt pointed the pose form
at row 2 of the *Splitter* block; the block grew to rows 1-2 and the form correctly refused,
because row 1 is where that element's record lives.

## One more field property: an editable choice

`FormField(kind="choice", editable=True)`. The parent-splitter list is a convenience, not the
whole domain -- an element may name a splitter this scene does not hold yet, which the Tk
`ttk.Combobox` (not `state="readonly"`) always allowed. Qt sets `setEditable(True)`, and
`refresh_from_form` stops discarding a value that is not in the list.

## Four dialogs, one renderer

`main_scene_element_dialogs.py` went from **616 lines to 242**. `_run_row_form_dialog(form)` is
now the Tk half of what `qt/dialogs/row_form_dialog.py` does for Qt -- static / bool / choice /
entry widgets, `form.locked` followed through `sync_enabled()`, `on_change` bound to any choice
that declares one, and the Validate / Apply / actions / Cancel footer -- and
`_open_row_form(title, builder, *args)` is the read-the-table-then-build wrapper all four share.
It is the only place in the file that knows about widgets.

## No shipped scene carries a path-placement record

`_metadata_has_path_pose` wants `path_component_type` or `path_frame_source`, which only the
path-component/stock-lens commands write, and no scene under `attachment/` has one. The guard
therefore runs on `common_optical_layouts/beam_splitter_two_arm_doublets.py` (a real `Beam
Splitter` row, two arms) and writes the record onto the transmit block's first row itself, the
way an insert would -- both halves of the guard call the same `prepare()`.

## Guard

`KrakenOS/UI/validate_open3d_0876_element_row_forms.py` (penta phase 654):

- **B** -- row 8 grows into block [7, 8, 9] with `row_index=7`; two selected blocks refuse
- **R** -- the pose editor refuses an element with no path-placement metadata
- **V** -- "arm distance expects a number.", "local tilt x must be finite.", "Element name cannot
  be empty.", "Choose a valid path role."
- **P** -- the pose apply writes `arm_distance` through `_apply_path_local_pose_to_indices`
- **E** -- Element Settings writes the name, the role and an `Auto` selector resolved to
  `reflect` to **every** row of the block
- **T** -- both REAL Tk dialogs open on the builders' values; the combos read
  `['readonly', 'editable', 'editable']`
- **Q** -- the Qt pair does the same, with an editable parent combo

## Files

- `KrakenOS/UI/row_forms/element_forms.py` (new), registered in `row_forms/__init__.py`
- `KrakenOS/UI/row_forms/base.py` -- `FormField.editable`
- `KrakenOS/UI/qt/dialogs/row_form_dialog.py` -- editable combos
- `KrakenOS/UI/panels/main_scene_element_dialogs.py` -- one renderer for all four dialogs
- `KrakenOS/UI/qt/actions.py`, `KrakenOS/UI/qt/main_window.py` -- Edit > Path-Local Pose... /
  Element Settings...
