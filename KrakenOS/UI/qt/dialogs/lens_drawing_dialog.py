"""Lens-drawing surface properties in the Qt shell (bugs/0945).

A view over `lens_drawing_session.LensDrawingPropertiesSession` -- the session the Tk window renders
too. One table row per lens surface: the seven row facts read-only, then one line edit per drawing
property (its hint as placeholder, its help as tooltip). The footer is the session's own buttons;
the dialog closes when the session says so. Shown modally: a PDF export waits on its answer.
"""
from __future__ import annotations

from KrakenOS.UI import lens_drawing_session as lds


def _dialog_base():
    from PySide6.QtWidgets import QDialog

    return QDialog


class LensDrawingPropertiesDialog(_dialog_base()):
    def __init__(self, session, *, parent=None) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                                       QTableWidget, QTableWidgetItem, QVBoxLayout)

        super().__init__(parent)
        self.session = session
        self.setWindowTitle(lds.TITLE)
        self.setModal(True)
        self.resize(1360, 700)
        layout = QVBoxLayout(self)
        note = QLabel(lds.NOTE)
        note.setWordWrap(True)
        layout.addWidget(note)

        fields = session.fields()
        headings = session.headings()
        table = self.table = QTableWidget(len(session.surface_indices), len(headings))
        table.setHorizontalHeaderLabels(headings)
        table.verticalHeader().setVisible(False)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        fixed = len(lds.FIXED_COLUMNS)
        for offset, field in enumerate(fields):
            header = table.horizontalHeaderItem(fixed + offset)
            if header is not None and field.help:
                header.setToolTip(field.help)
        #: (row_index, field key) -> its line edit, for the session's values and a guard
        self.edits: dict = {}
        for table_row, row_index in enumerate(session.surface_indices):
            for column, text in enumerate(session.fixed_cells(row_index)):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(table_row, column, item)
            for offset, field in enumerate(fields):
                edit = QLineEdit(session.values[row_index][field.key])
                edit.setPlaceholderText(field.hint)
                if field.help:
                    edit.setToolTip(field.help)
                edit.setMinimumWidth(max(80, field.width * 7))
                edit.textEdited.connect(lambda text, r=row_index, k=field.key: session.set_value(r, k, text))
                table.setCellWidget(table_row, fixed + offset, edit)
                self.edits[(row_index, field.key)] = edit
        table.resizeColumnsToContents()
        layout.addWidget(table, 1)

        footer = QHBoxLayout()
        self.status = QLabel(session.status)
        self.status.setStyleSheet("color: #5f6b7a")
        self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        #: label -> button; the Tk window packs them right to left, so they read in reverse
        self.buttons: dict = {}
        for label, method in reversed(session.buttons()):
            button = self.buttons[label] = QPushButton(label)
            button.clicked.connect(lambda _checked=False, m=method: getattr(session, m)(parent=self))
            footer.addWidget(button)
        layout.addLayout(footer)
        session.listeners.append(self.sync)
        self.finished.connect(self._forget)

    def sync(self) -> None:
        """Show the session: field text (Clear / Load JSON rewrite it), the status line, closing."""
        session = self.session
        for (row_index, key), edit in self.edits.items():
            value = session.values[row_index][key]
            if edit.text() != value:
                edit.setText(value)
        self.status.setText(session.status)
        if session.closed and self.isVisible():
            self.accept()

    def _forget(self, _result=None) -> None:
        if self.sync in self.session.listeners:
            self.session.listeners.remove(self.sync)
