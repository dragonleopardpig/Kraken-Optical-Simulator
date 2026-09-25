"""Path throughput report dialog (docs/design_qt_migration.md phase 4).

Widgets only: every number, heading, filter choice and exported value comes from
`reports/branch_throughput.py`, which the Qt shell renders too, through the shared
`ReportWindow`.
"""

from __future__ import annotations

from typing import Any

from KrakenOS.UI.branch_throughput_analysis import (
    filtered_branch_throughput_records,
    normalize_branch_throughput_filter_label as _normalize_path_filter_label,
)
from KrakenOS.UI.panels.report_view import ReportWindow
from KrakenOS.UI.reports import build_branch_throughput_report


class MainBranchThroughputReportDialog:
    """Own the Path Throughput Report window while delegating path analysis to the editor."""

    def __init__(self, editor: Any, *, analysis_path_filter_default: str) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "analysis_path_filter_default", analysis_path_filter_default)
        object.__setattr__(self, "_report_window", ReportWindow(
            self, self._build_report, geometry="1120x560", minsize=(820, 360),
            csv_title="Path Throughput"))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {"editor", "analysis_path_filter_default"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _build_report(self, filter_text: str = ""):
        return build_branch_throughput_report(
            self, filter_text=_normalize_path_filter_label(
                filter_text or self.analysis_path_filter_default))

    def open_branch_throughput_report(self) -> None:
        self._report_window.open()

    def _close_branch_throughput_report(self) -> None:
        self._report_window.close()

    def _refresh_branch_throughput_report_if_open(self) -> None:
        self._report_window.refresh_if_open()

    def _refresh_branch_throughput_report(self) -> None:
        self._report_window.refresh()

    def _current_branch_throughput_filter(self) -> str:
        """The filter the open window is showing, or the default when it is closed."""
        value = self._report_window.control_values().get("filter_text", "")
        return _normalize_path_filter_label(value or self.analysis_path_filter_default)

    def _filtered_branch_throughput_records_for_dialog(
            self, records: list[dict[str, object]]) -> list[dict[str, object]]:
        return filtered_branch_throughput_records(records, self._current_branch_throughput_filter())

    def _branch_throughput_report_text(self) -> str:
        return self._build_report(self._current_branch_throughput_filter()).text

    def copy_branch_throughput_report_to_clipboard(self) -> None:
        try:
            self._report_window.copy_text()
        except Exception as exc:
            self.append_debug(f"Path throughput report failed: {exc}")

    def export_branch_throughput_csv(self) -> None:
        self._report_window.export_csv()
