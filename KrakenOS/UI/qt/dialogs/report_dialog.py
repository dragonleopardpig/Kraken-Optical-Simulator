"""The Qt view of a `Report` (docs/design_qt_migration.md phase 3).

Layout only: every number, heading and exported value comes from the `Report`, which the Tk
dialog renders too. A report dialog ports by writing its builder -- not by re-reading the model
from Qt code.
"""
from __future__ import annotations

from KrakenOS.UI.uihost import host_of


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


def _dialog_class():
    from PySide6.QtWidgets import QDialog

    return QDialog


class ReportDialog(_dialog_class()):
    """A summary line, the table, and Export CSV / Close."""

    def __init__(self, report, parent=None, host=None, rebuild=None) -> None:
        from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialogButtonBox, QHBoxLayout,
                                       QLabel, QLineEdit, QTableView, QVBoxLayout)

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

        self.model = make_report_model(report)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        for index, column in enumerate(report.columns):
            self.table.setColumnWidth(index, column.width)
        layout.addWidget(self.table, stretch=1)

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
