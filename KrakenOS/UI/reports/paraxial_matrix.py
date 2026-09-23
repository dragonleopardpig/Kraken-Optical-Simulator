"""The Paraxial Matrix Report's data (docs/design_qt_migration.md phase 3).

Extracted from the Tk dialog so both toolkits render the same numbers. Nothing here builds a
widget; the Tk dialog in `panels/main_paraxial_analysis_dialogs.py` and the Qt dialog in
`qt/dialogs/` are thin views over what this returns.
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.reports.base import Report, ReportColumn, ReportFailed

TITLE = "Paraxial Matrix Report"

COLUMNS = (
    ReportColumn("surface", "Surf"),
    ReportColumn("name", "Name", numeric=False, width=150, stretch=True),
    ReportColumn("glass", "Glass", numeric=False),
    ReportColumn("n_before", "n0"),
    ReportColumn("n_after", "n1"),
    ReportColumn("radius", "R [mm]"),
    ReportColumn("curvature", "C [1/mm]"),
    ReportColumn("thickness", "T [mm]"),
    ReportColumn("kind", "Kind", numeric=False, width=150, stretch=True),
    ReportColumn("A", "A"),
    ReportColumn("B", "B"),
    ReportColumn("C", "C"),
    ReportColumn("D", "D"),
    ReportColumn("K00", "K00"),
    ReportColumn("K01", "K01"),
    ReportColumn("K10", "K10"),
    ReportColumn("K11", "K11"),
)


def matrix_cell(matrix, row: int, column: int) -> float:
    return float(np.asarray(matrix, dtype=float)[row, column])


def surface_kind(surface) -> str:
    if surface.is_mirror:
        return "mirror"
    return "thin_lens" if surface.is_thin_lens else "surface"


def build_paraxial_matrix_report(owner) -> Report:
    """Build the report from ``owner`` -- the editor, or any panel that forwards to it.

    Raises :class:`ReportFailed` with the message a dialog should show.
    """
    try:
        system = owner.build_system(force_rebuild=True)
        trace = system.ParaxMatrices(owner._current_wavelength())
    except Exception as exc:
        message = getattr(owner, "short_error_message", lambda e: str(e))(exc)
        raise ReportFailed(str(message)) from exc

    summary = (
        f"Wavelength {float(trace.wavelength):.6g} um | "
        f"EFFL {float(trace.effl):.6g} mm | "
        f"PPA {float(trace.ppa):.6g} mm | PPP {float(trace.ppp):.6g} mm | "
        f"ABCD=[{matrix_cell(trace.system_matrix_abcd, 0, 0):.6g}, "
        f"{matrix_cell(trace.system_matrix_abcd, 0, 1):.6g}; "
        f"{matrix_cell(trace.system_matrix_abcd, 1, 0):.6g}, "
        f"{matrix_cell(trace.system_matrix_abcd, 1, 1):.6g}]"
    )

    rows: list[dict[str, object]] = []
    for surface in trace.surfaces:
        rows.append({
            "surface": int(surface.surface_index),
            "name": str(surface.surface_name or ""),
            "glass": str(surface.glass),
            "n_before": float(surface.n_before),
            "n_after": float(surface.n_after),
            "radius": float(surface.radius),
            "curvature": float(surface.curvature),
            "thickness": float(surface.thickness),
            "kind": surface_kind(surface),
            "A": matrix_cell(surface.abcd_matrix, 0, 0),
            "B": matrix_cell(surface.abcd_matrix, 0, 1),
            "C": matrix_cell(surface.abcd_matrix, 1, 0),
            "D": matrix_cell(surface.abcd_matrix, 1, 1),
            "K00": matrix_cell(surface.kraken_matrix, 0, 0),
            "K01": matrix_cell(surface.kraken_matrix, 0, 1),
            "K10": matrix_cell(surface.kraken_matrix, 1, 0),
            "K11": matrix_cell(surface.kraken_matrix, 1, 1),
        })

    return Report(title=TITLE, summary=summary, columns=COLUMNS, rows=rows,
                  status=f"Paraxial matrix report: {len(rows)} surfaces.")


#: the failure path names the dialog with this
build_paraxial_matrix_report.TITLE = TITLE
