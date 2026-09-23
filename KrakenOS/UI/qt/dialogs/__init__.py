"""Qt dialogs (docs/design_qt_migration.md phase 3).

The recipe every port follows: a dialog's DATA moves to `KrakenOS/UI/reports/` as a toolkit-free
builder, and each toolkit keeps only its layout. `ReportDialog` is the Qt layout for the whole
family of summary-plus-table-plus-export dialogs, so porting one of those becomes a builder plus
a menu entry.

Nothing here imports PySide6 at package level.
"""
from __future__ import annotations

__all__ = ["ReportDialog"]


def __getattr__(name):
    if name == "ReportDialog":
        from KrakenOS.UI.qt.dialogs.report_dialog import ReportDialog

        return ReportDialog
    raise AttributeError(name)
