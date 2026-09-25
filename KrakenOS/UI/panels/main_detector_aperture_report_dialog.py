"""Detector aperture report dialog (docs/design_qt_migration.md phase 4).

Widgets only: the numbers, headings and exported values come from
`reports/detector_aperture.py`, which the Qt shell renders too, through `ReportWindow`.
"""

from __future__ import annotations

from typing import Any

from KrakenOS.UI.panels.report_view import ReportWindow
from KrakenOS.UI.reports import build_detector_aperture_report


class MainDetectorApertureReportDialog:
    """Own the Detector Aperture Report window while delegating sample collection to the editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "_report_window", ReportWindow(
            self, self._build_report, geometry="1160x520", minsize=(860, 340),
            csv_title="Detector Aperture"))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _build_report(self):
        return build_detector_aperture_report(self)

    def open_detector_aperture_report(self) -> None:
        self._report_window.open()

    def _close_detector_aperture_report(self) -> None:
        self._report_window.close()

    def _refresh_detector_aperture_report_if_open(self) -> None:
        self._report_window.refresh_if_open()

    def _refresh_detector_aperture_report(self) -> None:
        self._report_window.refresh()

    def _detector_aperture_report_text(self) -> str:
        return self._build_report().text

    def copy_detector_aperture_report_to_clipboard(self) -> None:
        try:
            self._report_window.copy_text()
        except Exception as exc:
            self.append_debug(f"Detector aperture report failed: {exc}")

    def export_detector_aperture_csv(self) -> None:
        self._report_window.export_csv()
