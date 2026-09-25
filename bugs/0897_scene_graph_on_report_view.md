# 0897 -- the Non-Sequential Scene Graph renders a builder

The last dialog of the report family, and the first whose data had **no builder at all**: Qt had
never shown it. The collector (`services/nonseq_scene_graph_records.py`) returns *flat* records
carrying `id` and `parent`, which is exactly what a `ttk.Treeview` wants;  `TreeRow` wants
children, so `reports/nonseq_scene_graph.py` nests them once and both toolkits draw the result.

Its three verbs -- **Select Row**, **Set Target**, **Edit Target** -- act on the selected node,
and two of them needed things a `Report` could not yet say.

## A key that survives a rebuild

**Set Target adds a target node.** A node key that is a row *index* would afterwards point at a
different node than the user had selected, so the key is the record's own `id` string, as the Tk
dialog's iids always were. That is also what `_nonseq_scene_selected_record` -- which the Scene
Target editor opens on -- looks up.

Set Target returns a `ReportUpdate(status=..., rebuild=True)` rather than a status line, so the
rebuild happens *inside* the verb and the verb's own message is what the status bar keeps. The
first version refreshed after the verb and the status read "167 nodes." instead.

## Where to start, and where to stay

`Report.initial_key` -- the Tk dialog opened on the first **surface** node, not the first node.
And a refresh now keeps whatever the user had selected in **every** report: Update rebuilds these
windows behind the user, and 0895 had quietly lost the Ray Inspector's own selection-preserving
refresh when it moved onto the shared renderer. Both toolkits do it now.

`ReportAction.on_activate` carries the double-click, which ran Select Row.

## A selection is not a detail view

Both views refused to select anything in a report with no `DetailView`, because selecting had
only ever existed to fill the detail table -- `select_master_row` began with
`if not self.has_detail(): return`. This report has no detail and three verbs that act on the
selection, so selecting is now its own job in both toolkits. The Qt half of the guard caught it:
the dialog drew all 166 nodes and reported `selected_key() == None`.

`main_nonseq_scene_graph_dialog.py`: **276 -> 70 lines**, and with the last dialog-made variable
gone, `DIALOG_SCOPED_VARIABLES` is **empty**.

## Guard

`KrakenOS/UI/validate_open3d_0897_scene_graph_on_report_view.py` (penta phase 685):

- **L** -- one `ReportWindow`, no editor-held widgets, `DIALOG_SCOPED_VARIABLES` empty
- **N / N2** -- 166 nodes for 166 records, 161 nested under a parent, every cell row the
  record's own, opening on `surface:0`
- **K** -- the refresh keeps the node, and Set Target grows the graph 166 -> 167 while leaving
  the user on the node they had, with its own message in the status bar
- **V** -- Select Row selects the table row, and the CSV carries the 14 record keys, not the 10
  shown columns
- **Q / T** -- the Qt shell has the dialog at last, and its tree is the Tk tree: one SHA-256
  over all 166 nodes, labels and cells
