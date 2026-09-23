# 0863 -- report controls: the path filter and the target selector

The first Qt report ports showed each Tk dialog's default and nothing else: Path Throughput could
not be filtered, and Source Illumination always reported on the target the editor resolves as
"Auto". This adds the controls -- and, more usefully, the mechanism for the rest of the family.

## The mechanism

A `Report` may declare `ReportChoice` controls: `key` (the builder's keyword), `label`, `choices`
and the current `value`. The dialog renders one combo box per control, and on a change it collects
every control's value and calls **the builder** again:

    dialog.rebuild(**{control.key: current_value, ...})  ->  a fresh Report

So a control needs no Qt-side logic, the filtering stays in the model, and a builder stays
callable with no arguments at all (every control keyword has a default). `ReportDialog.set_report`
swaps in the new table, summary and choices.

| report | control | choices from |
|---|---|---|
| Path Throughput | Path filter | `branch_throughput_filter_choices(all_records)` |
| Source Illumination | Target surface | `editor._source_illumination_target_choices()` |

"Auto" still defers to `_source_illumination_target_index()`, so the dialog opens on the same
target the Tk one does; any other choice is parsed the way the editor parses its own variable.

On `om05a_folded.py`: filtering to `Terminal: S10 Aperture: Aperture Stop` narrows 2 paths to 1,
and re-aiming illumination from Auto (S24, 106/226 rays) to S1 First RA mirror A gives 113/226.

## Guard

`validate_open3d_0863_report_controls.py`, penta phase 642. K every controlled builder takes its
control as a keyword WITH a default. D the controls are the model's own choice lists with the Tk
defaults selected (5 filters, 26 targets). F a filter change rebuilds to exactly the rows
`filtered_branch_throughput_records` returns, cell for cell. T a target change re-aims the report
to the model's summary for that target, and it differs from Auto's. O **one change rebuilds
once** -- refreshing a combo's own choices inside the refresh must not re-enter the rebuild, which
is the classic Qt signal loop. S a filter value the choices do not contain is kept and offered
rather than silently dropped.
