"""Non-sequential scene graph dialog (docs/design_qt_migration.md phase 4).

Widgets only: the nodes, their nesting, the summary, the CSV and the three verbs come from
`reports/nonseq_scene_graph.py`, which the Qt shell renders too, through `ReportWindow`.
"""

from __future__ import annotations

from typing import Any

from KrakenOS.UI.panels.report_view import ReportWindow
from KrakenOS.UI.reports import build_nonseq_scene_graph_report
from KrakenOS.UI.reports.nonseq_scene_graph import record_for


class MainNonSequentialSceneGraphDialog:
    """Own the Non-Sequential Scene Graph window while delegating records to the editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "_report_window", ReportWindow(
            self, lambda: build_nonseq_scene_graph_report(self), geometry="1180x620",
            minsize=(860, 420), csv_title="Non-Sequential Scene Graph"))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_nonseq_scene_graph(self) -> None:
        self._report_window.open()

    def _close_nonseq_scene_graph(self) -> None:
        self._report_window.close()

    def _refresh_nonseq_scene_graph_if_open(self) -> None:
        self._report_window.refresh_if_open()

    def _refresh_nonseq_scene_graph(self) -> None:
        self._report_window.refresh()

    def _nonseq_scene_selected_record(self) -> "dict[str, object] | None":
        """The record behind the selected node -- what the Scene Target editor opens on."""
        report = self._report_window.report
        if report is None:
            return None
        return record_for(report.rows, self._report_window.selected_key())

    def _run_verb(self, label: str) -> None:
        report = self._report_window.report
        if report is None:
            return
        for action in report.actions:
            if action.label == label:
                self._report_window.run_action(action)
                return

    def _select_nonseq_scene_row(self) -> None:
        self._run_verb("Select Row")

    def _set_nonseq_scene_target(self) -> None:
        # the verb rebuilds the graph itself, so the status it sets is the one that survives
        self._run_verb("Set Target")

    def export_nonseq_scene_graph_csv(self) -> None:
        self._report_window.export_csv()
