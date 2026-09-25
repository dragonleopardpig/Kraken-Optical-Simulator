"""Ray Inspector and Trace Path Inspector dialogs (docs/design_qt_migration.md phase 4).

Widgets only: the rays, the paths nested under them, the hits of whichever is selected, the two
~140-column CSVs and the Open Ray verb all come from `reports/ray_inspector.py` and
`reports/trace_paths.py`, which the Qt shell renders too, through the shared `ReportWindow`.
"""

from __future__ import annotations

from typing import Any

from KrakenOS.UI.panels.report_view import ReportWindow
from KrakenOS.UI.reports import build_ray_inspector_report, build_trace_path_report
from KrakenOS.UI.reports.trace_paths import selected_ray_index


class MainRayTraceInspectorDialogs:
    """Own ray and trace-path inspector windows while delegating trace data to the editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "_ray_window", ReportWindow(
            self, lambda: build_ray_inspector_report(self), geometry="1180x660",
            minsize=(780, 420), csv_title="Ray Inspector"))
        object.__setattr__(self, "_path_window", ReportWindow(
            self, lambda: build_trace_path_report(self), geometry="1160x680",
            minsize=(820, 460), csv_title="Trace Path Tree"))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    # ---- Ray Inspector --------------------------------------------------------------------
    def open_ray_inspector(self) -> None:
        self._ray_window.open()

    def _close_ray_inspector(self) -> None:
        self._ray_window.close()

    def _refresh_ray_inspector_if_open(self) -> None:
        self._ray_window.refresh_if_open()

    def _refresh_ray_inspector(self) -> None:
        self._ray_window.refresh()

    def _populate_ray_inspector_hits(self, _event=None) -> None:
        self._ray_window.refresh_detail()

    def select_ray_inspector_row(self, ray_index: int) -> bool:
        """Show `ray_index` in the Ray Inspector; False when the trace has no such ray.

        The row is found by the record's own `ray_index`, not by position: the report is a list
        of rays in trace order and a second trace renumbers them (bugs/0880).
        """
        if not self._ray_window.is_open():
            self._ray_window.open()
        else:
            self._ray_window.refresh()
        report = self._ray_window.report
        if report is None:
            return False
        for position, record in enumerate(report.rows):
            try:
                if int(record.get("ray_index", -1)) == int(ray_index):
                    self._ray_window.select_row(position)
                    return True
            except (TypeError, ValueError):
                continue
        return False

    def export_ray_inspector_csv(self) -> None:
        self._ray_window.export_csv()

    def export_ray_events_csv(self) -> None:
        report = self._ray_window.report or self._ray_window._build()
        if report is None:
            return
        for action in report.actions:
            if action.label == "Export Events CSV":
                self._ray_window.run_action(action)
                return

    # ---- Trace Path Inspector -------------------------------------------------------------
    def open_branch_tree_inspector(self) -> None:
        self._path_window.open()

    def _close_branch_tree_inspector(self) -> None:
        self._path_window.close()

    def _refresh_branch_tree_if_open(self) -> None:
        self._path_window.refresh_if_open()

    def _refresh_branch_tree_inspector(self) -> None:
        self._path_window.refresh()

    def _populate_branch_tree_hits(self, _event=None) -> None:
        self._path_window.refresh_detail()

    def _branch_tree_selected_ray_index(self) -> int | None:
        """The ray of the selected node -- a ray node's own, or the ray of a path node."""
        key = self._path_window.selected_key()
        ray_index = selected_ray_index(key)
        if ray_index is not None:
            return ray_index
        report = self._path_window.report
        if report is None or key is None:
            return None
        try:
            record = report.rows[int(key)]
        except (IndexError, TypeError, ValueError):
            return None
        try:
            return int(record.get("ray_index", -1))
        except (TypeError, ValueError):
            return None

    def _open_branch_tree_selected_ray(self) -> None:
        ray_index = self._branch_tree_selected_ray_index()
        if ray_index is None or ray_index < 0:
            return
        self._select_ray_inspector_ray(int(ray_index))

    def export_branch_tree_csv(self) -> None:
        self._path_window.export_csv()
