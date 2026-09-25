"""Toolkit-free report data for the dialogs both toolkits show
(docs/design_qt_migration.md phase 3).

The migration recipe for a report dialog: move its DATA here as a function returning a
:class:`Report`, leave the widgets behind, and let each toolkit render the same object.
"""
from __future__ import annotations

from KrakenOS.UI.reports.base import (DetailText, DetailView, Report, ReportChoice,
                                      ReportColumn, ReportFailed, ReportValue, TreeRow)
from KrakenOS.UI.reports.branch_gaussian_q import build_branch_gaussian_q_report
from KrakenOS.UI.reports.branch_throughput import build_branch_throughput_report
from KrakenOS.UI.reports.detector_aperture import build_detector_aperture_report
from KrakenOS.UI.reports.gaussian_beam import (build_gaussian_beam_report,
                                               gaussian_cavity_eigenmode)
from KrakenOS.UI.reports.paraxial_matrix import build_paraxial_matrix_report
from KrakenOS.UI.reports.ray_inspector import build_ray_inspector_report
from KrakenOS.UI.reports.source_illumination import build_source_illumination_report
from KrakenOS.UI.reports.trace_paths import build_trace_path_report

#: name -> builder, for a shell that opens reports by name
REPORT_BUILDERS = {
    "paraxial_matrix": build_paraxial_matrix_report,
    "branch_gaussian_q": build_branch_gaussian_q_report,
    "detector_aperture": build_detector_aperture_report,
    "branch_throughput": build_branch_throughput_report,
    "source_illumination": build_source_illumination_report,
    "gaussian_beam": build_gaussian_beam_report,
    "ray_inspector": build_ray_inspector_report,
    "trace_paths": build_trace_path_report,
}

__all__ = ["Report", "ReportChoice", "ReportColumn", "ReportFailed", "ReportValue",
           "DetailText", "DetailView", "TreeRow",
           "REPORT_BUILDERS", "gaussian_cavity_eigenmode",
           "build_paraxial_matrix_report", "build_branch_gaussian_q_report",
           "build_detector_aperture_report", "build_branch_throughput_report",
           "build_source_illumination_report", "build_gaussian_beam_report",
           "build_ray_inspector_report", "build_trace_path_report"]
