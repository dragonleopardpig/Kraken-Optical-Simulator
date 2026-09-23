# 0860 -- the Branch Gaussian Q report in the Qt shell (phase 3, second dialog)

The second dialog ported, and a different starting point from the first.

## Two kinds of dialog

0859's Paraxial Matrix Report had its data **inside** the Tk dialog, so the port extracted it into
a builder and rewired the Tk dialog onto it. This one was already well separated:
`services/analysis_reports._collect_branch_gaussian_q_records` collects the records, and
`KrakenOS/UI/branch_gaussian_q_report.py` owns the value formatting
(`branch_gaussian_q_table_values`), the summary line and the whole-report text.

So `reports/branch_gaussian_q.py` re-implements none of it -- it calls exactly what the Tk dialog
calls and hands the result over as a `Report`. **The Tk dialog is deliberately untouched**:
rewiring a working window would risk it for no gain, because the shared layer already is the
single source of truth. The guard proves the point by comparing the Qt table against
`branch_gaussian_q_table_values` -- the very tuple the Tk Treeview inserts.

`Report` grew three optional fields for this family: `display_rows` (cells the MODEL already
formats), `csv_keys` (this CSV's 33 fieldnames are not the table's 15 columns) and `text` (for
Copy). The Qt dialog shows a Copy button whenever the model can produce report text, and puts it
on the clipboard through the UI host.

Adding a report is now one builder plus one menu entry: `main_window.open_report(builder)` is the
whole Qt side, and the guard checks every builder in `REPORT_BUILDERS` has an action of the same
name.

## What actually made it work

The dialog first came up empty -- "No Gaussian q branch records. Click Update first." The reports
read the LIVE trace state (`last_system` / `last_rays`), and the Qt viewport was calling
`_build_preview_system_rays_bundle(update_state=False)`: a flag copied from a validator, not from
the app. Every analysis in the shell therefore had nothing to report on.

The Qt redraw IS the app tracing, exactly as the Tk Open 3D refresh is, so `update_state` now
stays at its default. On `om05a_folded.py` the report went from 0 to 2 670 records (226/226
traces stable, 952 diagnostics, 0 failures).

## Guard

`validate_open3d_0860_branch_gaussian_q_report.py`, penta phase 639. E the empty state without a
trace; A every builder has an action naming a real method and carries its title; S after a redraw
the live trace state is set and the analyses see the records; B1 all 2 670 x 15 cells equal
`branch_gaussian_q_table_values`; B2 the summary is the collector's own; B3 the CSV uses the 33
BRANCH_GAUSSIAN_Q_CSV_COLUMNS and holds the raw records; B4 Copy puts the model's report text on
the clipboard through the host.
