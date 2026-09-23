"""The Branch Gaussian Q Report's data (docs/design_qt_migration.md phase 3).

Unlike the paraxial matrix report, this dialog's data layer was ALREADY shared: the records come
from `services/analysis_reports._collect_branch_gaussian_q_records`, and
`KrakenOS/UI/branch_gaussian_q_report.py` owns the value formatting, the summary line and the
report text. So this builder does not re-implement any of it -- it calls exactly what the Tk
dialog calls, and hands the result over as a `Report`. Both views therefore format through one
function rather than through two implementations that happen to agree.

The Tk dialog is deliberately left as it is: rewiring a working window would risk it for no gain,
because the shared layer is already the single source of truth.
"""
from __future__ import annotations

from KrakenOS.UI.branch_gaussian_q_report import (
    BRANCH_GAUSSIAN_Q_CSV_COLUMNS,
    branch_gaussian_q_report_text,
    branch_gaussian_q_summary_text,
    branch_gaussian_q_table_values,
)
from KrakenOS.UI.reports.base import Report, ReportColumn, ReportFailed

TITLE = "Branch Gaussian Q Report"
EMPTY = "No Gaussian q branch records. Click Update first."

#: the Tk dialog's columns, headings, widths and alignment, in its order
COLUMNS = (
    ReportColumn("ray", "Ray", width=58),
    ReportColumn("path", "Path", numeric=False, width=130, stretch=True),
    ReportColumn("step", "Step", width=55),
    ReportColumn("surface", "Surface", numeric=False, width=150, stretch=True),
    ReportColumn("event", "Event", numeric=False, width=92),
    ReportColumn("note", "q note", numeric=False, width=240, stretch=True),
    ReportColumn("incidence", "Inc [deg]", width=78),
    ReportColumn("n", "n0->n1", width=80),
    ReportColumn("ct", "Ct", width=90),
    ReportColumn("cs", "Cs", width=90),
    ReportColumn("qt", "qT [mm]", width=150),
    ReportColumn("qs", "qS [mm]", width=150),
    ReportColumn("w", "wT/wS [mm]", width=120),
    ReportColumn("clip", "Clip", width=76),
    ReportColumn("stable", "Stable", width=70),
)


def build_branch_gaussian_q_report(owner) -> Report:
    """Build the report from ``owner`` -- the editor, or any panel that forwards to it."""
    try:
        rows, summary = owner._collect_branch_gaussian_q_records(
            records=owner._active_ray_analysis_records())
    except Exception as exc:
        raise ReportFailed(str(exc)) from exc

    had_failures = int((summary or {}).get("failure_count", 0) or 0)
    return Report(
        title=TITLE,
        summary=branch_gaussian_q_summary_text(summary) if (rows or had_failures) else EMPTY,
        columns=COLUMNS,
        rows=list(rows),
        # the shared formatter the Tk Treeview inserts, cell for cell
        display_rows=[tuple(str(value) for value in branch_gaussian_q_table_values(row))
                      for row in rows],
        csv_keys=tuple(BRANCH_GAUSSIAN_Q_CSV_COLUMNS),
        text=branch_gaussian_q_report_text(list(rows), summary),
        status=(f"Branch Gaussian q report: {len(rows)} records." if rows else EMPTY),
    )


#: the failure path names the dialog with this
build_branch_gaussian_q_report.TITLE = TITLE
