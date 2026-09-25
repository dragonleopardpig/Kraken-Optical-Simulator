"""The Source Illumination Report's data (docs/design_qt_migration.md phase 3).

`source_illumination_analysis.py` owns the columns, widths, formatting, summary and report text.
The TARGET surface is a report control. "Auto" defers to the editor's own
`_source_illumination_target_index()` -- the target the Tk dialog starts on -- and any other
choice is one of `_source_illumination_target_choices()`, parsed the way the editor parses it.
"""
from __future__ import annotations

from KrakenOS.UI.reports.base import (DetailText, Report, ReportChoice, ReportColumn,
                                      ReportFailed)
from KrakenOS.UI.source_illumination_analysis import (
    SOURCE_ILLUMINATION_CSV_COLUMNS,
    SOURCE_ILLUMINATION_TABLE_COLUMNS,
    SOURCE_ILLUMINATION_TABLE_HEADINGS,
    SOURCE_ILLUMINATION_TABLE_WIDTHS,
    source_illumination_record_detail_text,
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


AUTO = "Auto"


def resolve_target(owner, target: str):
    """A choice label -> a row index, exactly as the editor reads its own variable."""
    text = str(target or AUTO).strip()
    if text and text != AUTO:
        try:
            index = int(text.split(":", 1)[0].strip())
        except ValueError:
            return owner._source_illumination_target_index()
        if 0 <= index < len(owner.rows):
            return index
    return owner._source_illumination_target_index()


def build_source_illumination_report(owner, target: str = AUTO) -> Report:
    try:
        target_index = resolve_target(owner, target)
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
        detail_text=DetailText(
            text=lambda index: source_illumination_record_detail_text(records[index]),
            label="Selected source details",
            empty="Select a source row to inspect loss and footprint diagnostics."),
        controls=(ReportChoice("target", "Target surface",
                               tuple(owner._source_illumination_target_choices()),
                               str(target or AUTO)),),
        status=(f"Source illumination report: {len(records)} sources onto {label}."
                if records else "No source illumination data. Click Update first."),
    )


build_source_illumination_report.TITLE = TITLE
