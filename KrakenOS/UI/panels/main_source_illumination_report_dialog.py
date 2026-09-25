"""Source illumination report dialog (docs/design_qt_migration.md phase 4).

Widgets only: the records, the target-surface control, the per-source detail prose and the
exported values come from `reports/source_illumination.py`, which the Qt shell renders too,
through `ReportWindow`.
"""

from __future__ import annotations

from typing import Any

from KrakenOS.UI.panels.report_view import ReportWindow
from KrakenOS.UI.reports import build_source_illumination_report
from KrakenOS.UI.reports.source_illumination import AUTO
from KrakenOS.UI.source_illumination_analysis import source_illumination_record_detail_text


class MainSourceIlluminationReportDialog:
    """Own the Source Illumination Report window while delegating target/sample logic to the editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "_report_window", ReportWindow(
            self, self._build_report, geometry="1160x600", minsize=(860, 420),
            csv_title="Source Illumination"))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    @property
    def _source_illumination_window(self):
        """The Toplevel, for the case-study capture scripts that photograph it."""
        return self._report_window.window

    @property
    def _source_illumination_target_var(self):
        """The target control's variable: setting it and refreshing picks that target."""
        return self._report_window.controls.get("target")

    def _build_report(self, target: str = AUTO):
        return build_source_illumination_report(self, target=target or AUTO)

    def open_source_illumination_report(self) -> None:
        self._report_window.open()

    def _close_source_illumination_report(self) -> None:
        self._report_window.close()

    def _refresh_source_illumination_report_if_open(self) -> None:
        self._report_window.refresh_if_open()

    def _refresh_source_illumination_report(self) -> None:
        self._report_window.refresh()

    def _current_source_illumination_target(self) -> str:
        """The target the open window is showing, or Auto when it is closed."""
        return self._report_window.control_values().get("target", "") or AUTO

    # ---- the detail pane ----------------------------------------------------------------
    def _set_source_illumination_detail_text(self, text: str) -> None:
        widget = self._report_window.detail_widget
        if widget is None:
            return
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", str(text or ""))
        widget.configure(state="disabled")

    def _source_illumination_record_detail_text(self, record: dict[str, object]) -> str:
        return source_illumination_record_detail_text(record)

    def _refresh_source_illumination_detail(self) -> None:
        self._report_window.refresh_detail()

    def _source_illumination_report_text(self) -> str:
        return self._build_report(self._current_source_illumination_target()).text

    def copy_source_illumination_report_to_clipboard(self) -> None:
        try:
            self._report_window.copy_text()
        except Exception as exc:
            self.append_debug(f"Source illumination report failed: {exc}")

    def export_source_illumination_csv(self) -> None:
        self._report_window.export_csv()
