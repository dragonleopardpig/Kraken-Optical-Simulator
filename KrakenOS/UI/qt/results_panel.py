"""The results and debug panels in Qt (docs/design_qt_migration.md phase 6).

The analysis's 98 property/value pairs, every debug line and every progress line were written
straight into a `ttk.Treeview` and two `tk.Text`s by model code, which is why the Qt shell had
none of those panels (bugs/0898). The model now publishes `editor.results_items`,
`editor.debug_lines` and `editor.progress_lines` and calls `editor.show_results(items)`,
`editor.show_debug_line(line)` and `editor.show_progress_line(line)`; this is the Qt half of all
three, and a headless editor simply has no shell to call.
"""
from __future__ import annotations


def make_results_model(editor):
    """A QAbstractTableModel over `editor.results_items` (built here so importing needs no Qt)."""
    from PySide6.QtCore import QAbstractTableModel, Qt

    class ResultsModel(QAbstractTableModel):
        HEADINGS = ("Property", "Value")

        def __init__(self) -> None:
            super().__init__()
            self.editor = editor

        @property
        def items(self):
            return list(getattr(self.editor, "results_items", []) or [])

        def rowCount(self, parent=None) -> int:
            return len(self.items)

        def columnCount(self, parent=None) -> int:
            return 2

        def data(self, index, role=Qt.ItemDataRole.DisplayRole):
            if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
                return None
            item = self.items[index.row()]
            return str(item[index.column()]) if index.column() < len(item) else ""

        def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
            if role != Qt.ItemDataRole.DisplayRole:
                return None
            if orientation == Qt.Orientation.Horizontal:
                return self.HEADINGS[section]
            return str(section)

        def refresh(self) -> None:
            self.beginResetModel()
            self.endResetModel()

    return ResultsModel()


def _log_widget(lines):
    """A read-only log, pre-filled with whatever the model wrote before this panel existed."""
    from PySide6.QtWidgets import QPlainTextEdit

    widget = QPlainTextEdit()
    widget.setReadOnly(True)
    widget.setMaximumBlockCount(5000)
    for line in list(lines or []):
        widget.appendPlainText(str(line))
    return widget


class ResultsPanel:
    """The Results table, the Debug log and the Progress log, and the seams the model calls."""

    def __init__(self, editor) -> None:
        from PySide6.QtWidgets import QAbstractItemView, QTableView

        self.editor = editor
        self.model = make_results_model(editor)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 200)

        self.log = _log_widget(getattr(editor, "debug_lines", []))
        self.progress = _log_widget(getattr(editor, "progress_lines", []))

        editor.show_results = self.show_results
        editor.show_debug_line = self.show_debug_line
        editor.show_progress_line = self.show_progress_line
        self.show_results(getattr(editor, "results_items", []))

    def show_results(self, _items=None) -> None:
        """The model published new results: the table reads them from the editor."""
        self.model.refresh()

    def show_debug_line(self, line: str) -> None:
        self._append(self.log, line)

    def show_progress_line(self, line: str) -> None:
        self._append(self.progress, line)

    @staticmethod
    def _append(widget, line: str) -> None:
        widget.appendPlainText(str(line))
        bar = widget.verticalScrollBar()
        bar.setValue(bar.maximum())

    def rows(self) -> list:
        """What the table is showing, as text -- what a guard compares."""
        from PySide6.QtCore import Qt

        return [[str(self.model.data(self.model.index(row, column),
                                     Qt.ItemDataRole.DisplayRole))
                 for column in range(self.model.columnCount())]
                for row in range(self.model.rowCount())]
