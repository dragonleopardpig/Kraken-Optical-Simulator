# 0895 -- the Ray and Trace Path inspectors render their builders

0867 and 0868 built these two reports -- a master/detail table of rays, and a master **tree** of
rays with their paths nested underneath -- and the Qt shell has rendered them ever since. The Tk
dialogs never moved: 1 078 lines of their own widgets, and with them two things the `Report`
could not express.

## An export that is not the table

Each inspector flattens every ray (or path) into **one row per hit**, under ~140 columns:

| file | columns | bytes on `om05a_folded` |
|---|---|---|
| Ray Inspector CSV | 157 | 3 669 720 |
| Trace Path Tree CSV | 83 | 3 206 508 |
| Ray Events CSV | (the canonical event records) | 2 363 119 |

`Report.write_csv` writes the *table* -- 22 columns -- so **Qt was exporting a different, much
smaller file for the same report**. `Report.csv_writer` now lets the model own the file, and
`reports/ray_csv.py` writes both. Before deleting the hand-written versions I ran them and the
new module over the same records and compared: **byte-identical**, both files. The per-hit block
was duplicated between the two exports and differs by exactly one field (`hit_branch`, which the
trace-path CSV does not need because its branch id is already a master column), so one function
writes both.

## Toolbar verbs

"Export Events CSV" and "Open Ray" were Tk buttons, so Qt simply did not have them.
`ReportAction` carries a verb the **model** defines; a view supplies only the two things a
toolkit must -- a file chooser (`save_title`) and which row is selected (`needs_selection`) --
so it renders a verb it has never heard of.

## A ray node had no detail

In the tree, a **ray** node carried no `detail_key`, because a ray has no hits of its own. Tk had
always shown every hit of every path beneath it; Qt showed nothing. The node now carries
`"ray:<index>"` and `detail_rows` answers it, which is why `detail_nodes()` counts 452 (226 rays
+ 226 paths) where 0868 used to see 226.

## A Tk leak out of the model

`services/layout_plot_interaction._select_ray_inspector_ray` -- what a ray click on the 2D plot
calls -- reached into the dialog: `self._ray_inspector_ray_table`, `table.exists(iid)`,
`table.selection_set(iid)`. It now asks the panel, which finds the row by the record's **own**
`ray_index` rather than by position (a second trace renumbers them, bugs/0880) and returns False
when the trace has no such ray. Ten more declarations left `layout_editor.__init__`, two more
names left `DIALOG_SCOPED_VARIABLES`, and `_branch_tree_record_for_iid` -- which took a Tk iid
and nothing outside called -- is gone.

`main_ray_trace_inspectors.py`: **1 078 -> 129 lines**.

## Guard

`KrakenOS/UI/validate_open3d_0895_inspectors_on_report_view.py` (penta phase 683):

- **L / S1** -- the panel holds no `ttk.Treeview`, `tk.Toplevel` or `csv.DictWriter`, and the
  plot-click service holds no Tk table
- **X / X2** -- Export CSV defers to the model's 157-column writer rather than the 22-column
  table, and one per-hit block writes both files
- **A1 / A2** -- Export Events CSV writes the event records; Open Ray shows the selected ray
- **D** -- both masters fill from the builder, including a ray node showing every hit beneath it
- **S2** -- a ray is found by its own `ray_index`, and one the trace does not have is refused
  rather than landing on a wrong row

Re-pointed with it: `validate_open3d_0868_trace_path_tree` (ray nodes carry keys now, so its
node census and detail check say so) and `validate_3d_interaction_contract` (the titles and verbs
are the builders'; the horizontal scrollbar is the shared renderer's).
