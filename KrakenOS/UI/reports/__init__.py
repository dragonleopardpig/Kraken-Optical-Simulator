"""Toolkit-free report data for the dialogs both toolkits show
(docs/design_qt_migration.md phase 3).

The migration recipe for a report dialog: move its DATA here as a function returning a
:class:`Report`, leave the widgets behind, and let each toolkit render the same object.
"""
from __future__ import annotations

from KrakenOS.UI.reports.base import Report, ReportColumn, ReportFailed
from KrakenOS.UI.reports.branch_gaussian_q import build_branch_gaussian_q_report
from KrakenOS.UI.reports.paraxial_matrix import build_paraxial_matrix_report

#: name -> builder, for a shell that opens reports by name
REPORT_BUILDERS = {
    "paraxial_matrix": build_paraxial_matrix_report,
    "branch_gaussian_q": build_branch_gaussian_q_report,
}

__all__ = ["Report", "ReportColumn", "ReportFailed", "build_paraxial_matrix_report",
           "build_branch_gaussian_q_report", "REPORT_BUILDERS"]
