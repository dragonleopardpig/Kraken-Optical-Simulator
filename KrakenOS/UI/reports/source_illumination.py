"""The Source Illumination Report's data (docs/design_qt_migration.md phase 3).

`source_illumination_analysis.py` owns the columns, widths, formatting, summary and report text.
The TARGET surface is resolved by the editor's own `_source_illumination_target_index()`, which
answers "Auto" when no dialog variable is set -- so the Qt view gets the same target the Tk dialog
starts on, without a selector of its own yet.
"""
from __future__ import annotations

from KrakenOS.UI.reports.base import Report, ReportColumn, ReportFailed
from KrakenOS.UI.source_illumination_analysis import (
    SOURCE_ILLUMINATION_CSV_COLUMNS,
    SOURCE_ILLUMINATION_TABLE_COLUMNS,
    SOURCE_ILLUMINATION_TABLE_HEADINGS,
    SOURCE_ILLUMINATION_TABLE_WIDTHS,
    source_illumination_report_text,
    source_illumination_summary_text,
    source_illumination_table_values,
)

TITLE = "Source Illumination Report"
TEXT_COLUMNS = {"source", "model", "terminals"}

COLUMNS = tuple(
    ReportColumn(key, SOURCE_ILLUMINATION_TABLE_HEADINGS.get(key, key),
                 numeric=key not in TEXT_COLUMNS,
                 width=int(SOURCE_ILLUMINATION_TABLE_WIDTHS.get(key, 90)),
                 stretch=key in TEXT_COLUMNS)
    for key in SOURCE_ILLUMINATION_TABLE_COLUMNS
)


def target_label(owner, target_index) -> str:
    """The label the Tk dialog puts in its summary."""
    if target_index is None:
        return "None"
    try:
        return f"S{int(target_index)}: {owner.rows[int(target_index)].name}"
    except Exception:
        return f"S{target_index}"


def build_source_illumination_report(owner) -> Report:
    try:
        target_index = owner._source_illumination_target_index()
        records = list(owner._collect_source_illumination_records(
            target_index, ray_records=owner._active_ray_analysis_records()))
    except Exception as exc:
        raise ReportFailed(str(exc)) from exc
    label = target_label(owner, target_index)
    return Report(
        title=TITLE,
        summary=source_illumination_summary_text(records, label),
        columns=COLUMNS,
        rows=records,
        display_rows=[tuple(str(value) for value in source_illumination_table_values(record))
                      for record in records],
        csv_keys=tuple(SOURCE_ILLUMINATION_CSV_COLUMNS),
        text=source_illumination_report_text(records, label),
        status=(f"Source illumination report: {len(records)} sources onto {label}."
                if records else "No source illumination data. Click Update first."),
    )


build_source_illumination_report.TITLE = TITLE
