"""Optical CAD/STL utility dialogs -- the Tk view.

"Inspect Optical CAD/STL Solids" is a `Report` (`reports/optical_solid_diagnostics.py`, bugs/0936)
shown through `ReportWindow`; the Qt shell renders the same report. The numeric "Place/Orient"
assistant that also lived here had no caller since a53b72a3 (2026-05-04), which replaced it with
the 3D inspector's placement handler (Qt: `row_forms/stl_placement.py`, 0925); 0936 removed it.
"""

from __future__ import annotations

from typing import Any

from KrakenOS.UI.reports.window import ReportWindow
from KrakenOS.UI.reports.optical_solid_diagnostics import (NO_SOLIDS, TITLE,
                                                          build_optical_solid_diagnostics_report,
                                                          optical_solid_diagnostics_text)

MENU_LABEL = "Inspect Optical CAD/STL Solids"


class MainOpticalSolidDialogs:
    """Own the optical CAD/STL diagnostics window."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "_diagnostics_window", ReportWindow(
            self, lambda: build_optical_solid_diagnostics_report(self), geometry="1100x620",
            minsize=(760, 420), csv_title=TITLE))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _optical_stl_diagnostics_text(self) -> str:
        return optical_solid_diagnostics_text(self)

    def open_optical_stl_diagnostics(self) -> None:
        from KrakenOS.UI.uihost import host_of

        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            host_of(self.editor).showerror(MENU_LABEL, f"Could not read the surface table:\n\n{exc}")
            return
        text = self._optical_stl_diagnostics_text()
        if not text:
            # an empty layout is information, not a failure (the report builder refuses it)
            host_of(self.editor).showinfo(MENU_LABEL, NO_SOLIDS)
            return
        self._diagnostics_window.open()
        self.append_debug(text.strip())
