"""Branch Gaussian q report dialog (docs/design_qt_migration.md phase 4).

Widgets only: the q records, their formatting and the CSV columns come from
`reports/branch_gaussian_q.py`, which the Qt shell renders too, through `ReportWindow`.
"""

from __future__ import annotations

from typing import Any

from KrakenOS.UI.panels.report_view import ReportWindow
from KrakenOS.UI.reports import build_branch_gaussian_q_report


class MainBranchGaussianQDialog:
    """Own the Branch Gaussian Q report window while delegating q-record collection to the editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "_report_window", ReportWindow(
            self, self._build_report, geometry="1320x620", minsize=(900, 420),
            csv_title="Branch Gaussian Q"))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _build_report(self):
        return build_branch_gaussian_q_report(self)

    def open_branch_gaussian_q_report(self) -> None:
        self._report_window.open()

    def _close_branch_gaussian_q_report(self) -> None:
        self._report_window.close()

    def _refresh_branch_gaussian_q_report_if_open(self) -> None:
        self._report_window.refresh_if_open()

    def _refresh_branch_gaussian_q_report(self) -> None:
        self._report_window.refresh()

    def _branch_gaussian_q_report_text(self) -> str:
        return self._build_report().text

    def copy_branch_gaussian_q_report_to_clipboard(self) -> None:
        try:
            self._report_window.copy_text()
        except Exception as exc:
            self.append_debug(f"Branch Gaussian q report failed: {exc}")

    def export_branch_gaussian_q_csv(self) -> None:
        self._report_window.export_csv()
