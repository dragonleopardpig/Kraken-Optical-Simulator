"""The Qt view of a `Report` (docs/design_qt_migration.md phase 3).

Layout only: every number, heading and exported value comes from the `Report`, which the Tk
dialog renders too. A report dialog ports by writing its builder -- not by re-reading the model
from Qt code.
"""
from __future__ import annotations

from KrakenOS.UI.uihost import host_of


def _widget_class():
    from PySide6.QtWidgets import QWidget

    return QWidget


def make_report_model(report):
    """A QAbstractTableModel over a `Report` (built here so importing needs no Qt)."""
    from PySide6.QtCore import QAbstractTableModel, Qt

    class ReportTableModel(QAbstractTableModel):
        def __init__(self) -> None:
            super().__init__()
            self.report = report

        def rowCount(self, parent=None) -> int:
            return len(self.report.rows)

        def columnCount(self, parent=None) -> int:
            return len(self.report.columns)

        def data(self, index, role=Qt.ItemDataRole.DisplayRole):
            if not index.isValid():
                return None
            if role == Qt.ItemDataRole.DisplayRole:
                return self.report.cell(index.row(), index.column())
            if role == Qt.ItemDataRole.TextAlignmentRole:
                column = self.report.columns[index.column()]
                flag = {"r": Qt.AlignmentFlag.AlignRight,
                        "c": Qt.AlignmentFlag.AlignHCenter,
                        "l": Qt.AlignmentFlag.AlignLeft}[column.alignment]
                return int(flag | Qt.AlignmentFlag.AlignVCenter)
            return None

        def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
            if role != Qt.ItemDataRole.DisplayRole:
                return None
            if orientation == Qt.Orientation.Horizontal:
                return self.report.columns[section].heading
            return str(section)

    return ReportTableModel()


def make_detail_model(columns):
    """A table model over already-formatted rows, for the detail half of a master/detail dialog."""
    from PySide6.QtCore import QAbstractTableModel, Qt

    class DetailTableModel(QAbstractTableModel):
        def __init__(self) -> None:
            super().__init__()
            self.columns = columns
            self.rows: list = []

        def set_rows(self, rows) -> None:
            self.beginResetModel()
            self.rows = list(rows)
            self.endResetModel()

        def rowCount(self, parent=None) -> int:
            return len(self.rows)

        def columnCount(self, parent=None) -> int:
            return len(self.columns)

        def data(self, index, role=Qt.ItemDataRole.DisplayRole):
            if not index.isValid():
                return None
            if role == Qt.ItemDataRole.DisplayRole:
                row = self.rows[index.row()]
                return str(row[index.column()]) if index.column() < len(row) else ""
            if role == Qt.ItemDataRole.TextAlignmentRole:
                flag = {"r": Qt.AlignmentFlag.AlignRight, "c": Qt.AlignmentFlag.AlignHCenter,
                        "l": Qt.AlignmentFlag.AlignLeft}[self.columns[index.column()].alignment]
                return int(flag | Qt.AlignmentFlag.AlignVCenter)
            return None

        def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
            if role != Qt.ItemDataRole.DisplayRole:
                return None
            if orientation == Qt.Orientation.Horizontal:
                return self.columns[section].heading
            return str(section)

    return DetailTableModel()


def _dialog_class():
    from PySide6.QtWidgets import QDialog

    return QDialog


class ReportDialog(_dialog_class()):
    """A summary line, the table, and Export CSV / Close."""

    def __init__(self, report, parent=None, host=None, rebuild=None) -> None:
        from PySide6.QtCore import Qt as _Qt
        from PySide6.QtGui import QStandardItem, QStandardItemModel
        from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialogButtonBox, QHBoxLayout,
                                       QLabel, QLineEdit, QSplitter, QTableView, QTreeView,
                                       QVBoxLayout, QWidget)

        super().__init__(parent)
        self.report = report
        self.host = host if host is not None else host_of(parent)
        #: called with every control's current value to produce a fresh Report
        self.rebuild = rebuild
        self.controls: dict[str, QComboBox] = {}

        self.setWindowTitle(report.title)
        self.resize(1180, 620)
        self.setMinimumSize(860, 420)

        layout = QVBoxLayout(self)
        self.summary_label = QLabel(report.summary)
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(
            self.summary_label.textInteractionFlags().TextSelectableByMouse)
        layout.addWidget(self.summary_label)

        if report.controls:
            row = QHBoxLayout()
            for control in report.controls:
                if hasattr(control, "choices"):
                    widget = QComboBox()
                    widget.addItems(list(control.choices))
                    if control.value and control.value in control.choices:
                        widget.setCurrentText(control.value)
                    widget.currentTextChanged.connect(self._on_control_changed)
                else:
                    # a typed-in value: rebuild when the field is committed, not per keystroke
                    widget = QLineEdit(str(control.value))
                    widget.setMaximumWidth(12 * max(control.width, 6))
                    widget.editingFinished.connect(self._on_control_changed)
                self.controls[control.key] = widget
                row.addWidget(QLabel(control.label))
                row.addWidget(widget)
            row.addStretch(1)
            layout.addLayout(row)

        self.model = None
        self.table = None
        self.tree_model = None
        self.tree_view = None
        if report.tree is not None:
            # a master TREE: rays with their paths nested underneath (bugs/0868)
            self.tree_model = QStandardItemModel()
            self.tree_model.setHorizontalHeaderLabels(
                [report.tree_heading, *[column.heading for column in report.columns]])

            def add(parent_item, rows):
                for row in rows:
                    label = QStandardItem(str(row.label))
                    label.setEditable(False)
                    label.setData(row.detail_key, _Qt.ItemDataRole.UserRole)
                    items = [label]
                    for cell in row.cells:
                        item = QStandardItem(str(cell))
                        item.setEditable(False)
                        items.append(item)
                    parent_item.appendRow(items)
                    if row.children:
                        add(label, row.children)

            add(self.tree_model.invisibleRootItem(), report.tree)
            self.tree_view = QTreeView()
            self.tree_view.setModel(self.tree_model)
            self.tree_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.tree_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.tree_view.setColumnWidth(0, 200)
            for index, column in enumerate(report.columns):
                self.tree_view.setColumnWidth(index + 1, column.width)
            self.tree_view.expandAll()
            master_view = self.tree_view
        else:
            self.model = make_report_model(report)
            self.table = QTableView()
            self.table.setModel(self.model)
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.verticalHeader().setVisible(False)
            for index, column in enumerate(report.columns):
                self.table.setColumnWidth(index, column.width)
            master_view = self.table

        self.detail_model = None
        self.detail_table = None
        if report.detail is not None:
            # master/detail: the hits of whichever row is selected, under the list itself
            self.detail_model = make_detail_model(report.detail.columns)
            self.detail_table = QTableView()
            self.detail_table.setModel(self.detail_model)
            self.detail_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.detail_table.verticalHeader().setVisible(False)
            for index, column in enumerate(report.detail.columns):
                self.detail_table.setColumnWidth(index, column.width)
            splitter = QSplitter(_Qt.Orientation.Vertical)
            splitter.addWidget(master_view)
            detail_box = QWidget()
            detail_layout = QVBoxLayout(detail_box)
            detail_layout.setContentsMargins(0, 0, 0, 0)
            self.detail_label = QLabel(report.detail.label)
            detail_layout.addWidget(self.detail_label)
            detail_layout.addWidget(self.detail_table)
            splitter.addWidget(detail_box)
            splitter.setStretchFactor(0, 3)
            splitter.setStretchFactor(1, 2)
            layout.addWidget(splitter, stretch=1)
            master_view.selectionModel().currentRowChanged.connect(self._on_master_row)
            self.select_master_row(0)
        else:
            layout.addWidget(master_view, stretch=1)

        self.buttons = QDialogButtonBox()
        self.copy_button = None
        if report.text:
            # the Tk dialogs of this family have a Copy button; the text comes from the model
            self.copy_button = self.buttons.addButton(
                "Copy", QDialogButtonBox.ButtonRole.ActionRole)
            self.copy_button.clicked.connect(self.copy_text)
        self.export_button = self.buttons.addButton(
            "Export CSV", QDialogButtonBox.ButtonRole.ActionRole)
        self.close_button = self.buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self.export_button.clicked.connect(self.export_csv)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    # ---- master/detail ---------------------------------------------------------------------------
    def select_master_row(self, index: int) -> None:
        """Select master row `index` (a table row, or the index-th node that HAS detail)."""
        if self.detail_model is None:
            return
        if self.tree_model is not None:
            keys = self.detail_nodes()
            if not keys:
                return
            index = max(0, min(int(index), len(keys) - 1))
            item = keys[index]
            self.tree_view.setCurrentIndex(item.index())
            self.detail_model.set_rows(self.report.detail.rows(
                item.data(self._user_role())))
            return
        if not self.report.rows:
            return
        index = max(0, min(int(index), len(self.report.rows) - 1))
        self.table.selectRow(index)
        self.detail_model.set_rows(self.report.detail.rows(index))

    @staticmethod
    def _user_role():
        from PySide6.QtCore import Qt

        return Qt.ItemDataRole.UserRole

    def detail_nodes(self) -> list:
        """Every tree item that carries a detail key, depth first -- the Tk dialog's own order."""
        if self.tree_model is None:
            return []
        found: list = []

        def walk(item):
            for row in range(item.rowCount()):
                child = item.child(row, 0)
                if child is None:
                    continue
                if child.data(self._user_role()) is not None:
                    found.append(child)
                walk(child)

        walk(self.tree_model.invisibleRootItem())
        return found

    def _on_master_row(self, current, _previous=None) -> None:
        if self.detail_model is None or current is None or not current.isValid():
            return
        if self.tree_model is not None:
            item = self.tree_model.itemFromIndex(current.siblingAtColumn(0))
            key = item.data(self._user_role()) if item is not None else None
            self.detail_model.set_rows(self.report.detail.rows(key))
            return
        self.detail_model.set_rows(self.report.detail.rows(current.row()))

    def control_values(self) -> dict:
        return {key: (widget.currentText() if hasattr(widget, "currentText") else widget.text())
                for key, widget in self.controls.items()}

    def _on_control_changed(self, _text=None) -> None:
        if self.rebuild is None:
            return
        self.set_report(self.rebuild(**self.control_values()))

    def set_report(self, report) -> None:
        """Show a freshly built report: the table, the summary, and the controls' own choices."""
        self.report = report
        self.model.beginResetModel()
        self.model.report = report
        self.model.endResetModel()
        self.summary_label.setText(report.summary)
        if self.detail_model is not None and report.detail is not None:
            self.select_master_row(0)
        for control in report.controls:
            widget = self.controls.get(control.key)
            if widget is None:
                continue
            # a control's own state can change with the data; refresh it without re-entering
            widget.blockSignals(True)
            try:
                if hasattr(control, "choices"):
                    if [widget.itemText(i) for i in range(widget.count())] != list(control.choices):
                        widget.clear()
                        widget.addItems(list(control.choices))
                    if control.value and control.value in control.choices:
                        widget.setCurrentText(control.value)
                elif widget.text() != str(control.value):
                    widget.setText(str(control.value))
            finally:
                widget.blockSignals(False)
        if self.copy_button is not None:
            self.copy_button.setEnabled(bool(report.text))

    def copy_text(self) -> str:
        """Put the whole report on the clipboard, through the UI host."""
        self.host.clipboard_set(self.report.text)
        return self.report.text

    def export_csv(self) -> str:
        """Ask through the UI host -- the same call the Tk dialog makes."""
        path = self.host.asksaveasfilename(
            title=f"Export {self.report.title} CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return ""
        self.report.write_csv(path)
        return str(path)
