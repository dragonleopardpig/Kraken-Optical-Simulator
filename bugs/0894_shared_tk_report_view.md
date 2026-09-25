# 0894 -- the four report dialogs share one Tk renderer over their builders

Phase 3 gave every report dialog a toolkit-free builder in `reports/` and the Qt shell a single
view over it. Four Tk windows never made the trip: **Path Throughput**, **Detector Aperture**,
**Source Illumination** and **Branch Gaussian Q** each still hand-built their own
`ttk.Treeview` -- 806 lines that decided a *second* time what the columns, the widths, the
summary and the CSV were, over builders that already existed and were already rendered by Qt.

Two implementations of the same report can disagree on a number. This one already did.

## The drift it had

Only the Tk Source Illumination dialog had a **per-source detail pane**: a `tk.Text` filled by
`source_illumination_record_detail_text(record)`. That prose is report *content*, but it lived in
the dialog, so the Qt port simply did not have it. `Report.detail_text` (a `DetailText`, next to
the existing `DetailView` table) now carries it, and **both** shells show it -- the Qt half of
the guard drives the real Qt dialog to prove it.

## The renderer

`panels/report_view.ReportWindow` is the Tk counterpart of `qt/dialogs/report_dialog.py`: one
modeless, reusable window that builds, refreshes, copies and exports whatever `Report` its
builder returns -- summary line, control strip (`ReportChoice` -> combobox, `ReportValue` ->
entry), master table *or* tree, optional detail table or prose pane, Refresh / Copy / Export CSV
/ Close. Unlike `render_row_form` it is a **class**, because these windows are modeless: Update
refreshes whichever report is open, so the panel keeps the handle.

The four panels are now 58-91 lines of prologue around it:

| panel | before | after |
|---|---|---|
| `main_branch_throughput_report_dialog.py` | 199 | 75 |
| `main_detector_aperture_report_dialog.py` | 159 | 58 |
| `main_source_illumination_report_dialog.py` | 234 | 91 |
| `main_branch_gaussian_q_dialog.py` | 215 | 58 |

The editor no longer keeps any of those windows' widgets or variables: seventeen declarations
went out of `layout_editor.__init__`, six names out of `DIALOG_SCOPED_VARIABLES`, and `destroy()`
asks each panel that was ever built to close its own window. `_source_illumination_target_index`
and `_filtered_branch_throughput_records` read the live control through the panel instead of
reaching into a `__dict__` for a variable the dialog no longer makes.

## Two traps met on the way

- **Tk delivers `<<TreeviewSelect>>` through the event loop.** `selection_set` therefore shows
  nothing until someone pumps Tk, and the first guard saw an empty detail pane against 426
  characters of expected prose. `select_row` now calls `refresh_detail()` itself, exactly as
  Qt's `_apply_detail` does -- a caller that selects a row should not have to run an event loop
  to see the result.
- **A filter that narrows nothing makes a rebuild check vacuous.** The first version picked the
  first choice the combobox offered, which on `om05a_folded` was `Output: Primary path` -- all
  2 of 2 paths, identical to the default, so the check would have passed whether or not the view
  rebuilt at all. The guard now picks the choice the **model** says narrows most
  (`Terminal: S10 Aperture: Aperture Stop`, 1 of 2).

Also fixed, while it was next to the change: `ReportDialog.set_report` reset `self.model`
unconditionally, which is `None` for a tree report -- unreachable today only because no tree
report has controls yet.

## Guard

`KrakenOS/UI/validate_open3d_0894_shared_tk_report_view.py` (penta phase 682):

- **R / R2** -- the four panels hold no `ttk.Treeview` and no `tk.Toplevel`, and the renderer
  asks the *report* for every cell, the CSV and the detail prose
- **D** -- each REAL Tk window draws exactly the builder's grid, cell for cell, plus its summary
- **C** -- picking the narrowing path filter rebuilds through the builder to exactly
  `filtered_branch_throughput_records` for that filter
- **T / Q** -- selecting a source shows that record's own detail prose, in **both** toolkits
- **U** -- Update refreshes an open report and forgets one the user has closed

Re-pointed with it: `validate_3d_interaction_contract` (the report titles and table-value
functions are the builders' now, and one new check that all four panels share the renderer) and
`validate_detector_aperture_analysis` (its columns claim now reads the builder's `COLUMNS`
against `DETECTOR_APERTURE_TABLE_LAYOUT`, which is the real claim).
