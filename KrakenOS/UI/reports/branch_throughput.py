"""The Path Throughput Report's data (docs/design_qt_migration.md phase 3).

`branch_throughput_analysis.py` owns the columns, formatting, filtering and text; the collector
lives on the editor. The Tk dialog also offers a path FILTER -- the Qt view shows the default,
every path, until phase 3 gives this family its controls.
"""
from __future__ import annotations

from KrakenOS.UI.branch_throughput_analysis import (
    BRANCH_THROUGHPUT_CSV_COLUMNS,
    BRANCH_THROUGHPUT_FILTER_DEFAULT,
    BRANCH_THROUGHPUT_TABLE_HEADINGS,
    BRANCH_THROUGHPUT_TABLE_LAYOUT,
    branch_throughput_report_text,
    branch_throughput_summary_text,
    branch_throughput_table_values,
    filtered_branch_throughput_records,
)
from KrakenOS.UI.reports.base import Report, ReportColumn, ReportFailed

TITLE = "Path Throughput Report"
EMPTY = "No path throughput data. Click Update first."

COLUMNS = tuple(
    ReportColumn(key, BRANCH_THROUGHPUT_TABLE_HEADINGS.get(key, key),
                 numeric=anchor != "w", width=width, stretch=anchor == "w",
                 align={"w": "l", "center": "c", "e": "r"}.get(anchor, ""))
    for key, width, anchor in BRANCH_THROUGHPUT_TABLE_LAYOUT
)


def build_branch_throughput_report(owner, filter_text: str = BRANCH_THROUGHPUT_FILTER_DEFAULT) -> Report:
    try:
        all_records = list(owner._collect_branch_throughput_records(
            ray_records=owner._active_ray_analysis_records()))
    except Exception as exc:
        raise ReportFailed(str(exc)) from exc
    records = list(filtered_branch_throughput_records(all_records, filter_text))
    return Report(
        title=TITLE,
        summary=(branch_throughput_summary_text(records, all_records, filter_text)
                 if all_records else EMPTY),
        columns=COLUMNS,
        rows=records,
        display_rows=[tuple(str(value) for value in branch_throughput_table_values(record))
                      for record in records],
        csv_keys=tuple(BRANCH_THROUGHPUT_CSV_COLUMNS),
        text=branch_throughput_report_text(records, all_records, filter_text),
        status=(f"Path throughput report: {len(records)} paths." if records else EMPTY),
    )


build_branch_throughput_report.TITLE = TITLE
