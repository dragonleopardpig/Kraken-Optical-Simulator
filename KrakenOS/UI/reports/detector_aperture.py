"""The Detector Aperture Report's data (docs/design_qt_migration.md phase 3).

Like the branch Gaussian q report, this dialog's data layer was already shared:
`detector_aperture_analysis.py` owns the columns, headings, layout, value formatting, summary and
report text, and `services/analysis_reports._collect_detector_aperture_records` collects. The
builder calls exactly what the Tk dialog calls.
"""
from __future__ import annotations

from KrakenOS.UI.detector_aperture_analysis import (
    DETECTOR_APERTURE_CSV_COLUMNS,
    DETECTOR_APERTURE_TABLE_HEADINGS,
    DETECTOR_APERTURE_TABLE_LAYOUT,
    detector_aperture_report_text,
    detector_aperture_summary_text,
    detector_aperture_table_values,
)
from KrakenOS.UI.reports.base import Report, ReportColumn, ReportFailed

TITLE = "Detector Aperture Report"
EMPTY = "No detector aperture data. Click Update first."

#: the Tk dialog's own layout, turned into report columns ("w"/"center"/"e" -> l/c/r)
COLUMNS = tuple(
    ReportColumn(key, DETECTOR_APERTURE_TABLE_HEADINGS.get(key, key),
                 numeric=anchor != "w", width=width, stretch=anchor == "w",
                 align={"w": "l", "center": "c", "e": "r"}.get(anchor, ""))
    for key, width, anchor in DETECTOR_APERTURE_TABLE_LAYOUT
)


def build_detector_aperture_report(owner) -> Report:
    try:
        records = owner._collect_detector_aperture_records(
            ray_records=owner._active_ray_analysis_records())
    except Exception as exc:
        raise ReportFailed(str(exc)) from exc
    records = list(records)
    return Report(
        title=TITLE,
        summary=detector_aperture_summary_text(records),
        columns=COLUMNS,
        rows=records,
        display_rows=[tuple(str(value) for value in detector_aperture_table_values(record))
                      for record in records],
        csv_keys=tuple(DETECTOR_APERTURE_CSV_COLUMNS),
        text=detector_aperture_report_text(records),
        status=(f"Detector aperture report: {len(records)} detectors." if records else EMPTY),
    )


build_detector_aperture_report.TITLE = TITLE
