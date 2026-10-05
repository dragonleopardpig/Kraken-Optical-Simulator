"""The missing-CAD-assets window in the Qt shell (bugs/0965).

A view over `services.missing_assets_session.MissingAssetsSession` -- the session the Tk window uses
too. Not modal (bugs/0810): the layout has loaded with placeholders, and the 3D scene stays usable.
Locate... (or a double-click), Skip and Reset act on the selected entry; Locate folder... and Skip all
remaining on every unresolved one; Continue -- or closing the window -- ends the session, which
rebuilds what the relocations made possible and redraws.
"""
from __future__ import annotations


def _dialog_base():
    from PySide6.QtWidgets import QDialog

    return QDialog


class MissingAssetsDialog(_dialog_base()):
    COLUMNS = ("Where", "Reference", "Expected path", "Status")
    #: status -> the row's background
    TINTS = {"located": "#d8f5d6", "skipped": "#f5e2d6"}

    def __init__(self, session, *, host, parent=None) -> None:
        from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                                       QTableWidget, QVBoxLayout)

        super().__init__(parent)
        self.session = session
        self.host = host
        self.setWindowTitle(session.title)
        self.setModal(False)
        self.resize(960, 520)
        layout = QVBoxLayout(self)
        intro = QLabel(session.prompt)
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(list(self.COLUMNS))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self.locate_selected())
        layout.addWidget(self.table, 1)

        row = QHBoxLayout()
        self.buttons = {}
        for text, handler in (("Locate...", self.locate_selected), ("Skip", self.skip_selected),
                              ("Reset", self.reset_selected), (None, None),
                              ("Locate folder...", self.locate_folder), ("Skip all remaining", self.skip_all)):
            if text is None:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.VLine)
                row.addWidget(line)
                continue
            button = QPushButton(text)
            button.setAutoDefault(False)
            button.clicked.connect(lambda _checked=False, h=handler: h())
            row.addWidget(button)
            self.buttons[text] = button
        row.addStretch(1)
        done = QPushButton("Continue")
        done.setAutoDefault(False)
        done.clicked.connect(self.close)
        row.addWidget(done)
        self.buttons["Continue"] = done
        layout.addLayout(row)
        self.status = QLabel()
        layout.addWidget(self.status)
        self.repaint_entries()

    # ---- the list ------------------------------------------------------------------------------
    def repaint_entries(self) -> None:
        from PySide6.QtGui import QBrush, QColor
        from PySide6.QtWidgets import QTableWidgetItem

        rows = self.session.rows()
        selected = self.selected_index()
        self.table.setRowCount(len(rows))
        for index, values in enumerate(rows):
            tint = self.TINTS.get(values[3])
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if tint:
                    item.setBackground(QBrush(QColor(tint)))
                self.table.setItem(index, column, item)
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)
        if selected is not None and selected < len(rows):
            self.table.selectRow(selected)
        self.status.setText(self.session.summary())

    def selected_index(self):
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        return rows[0].row() if rows else None

    def _need_selection(self):
        index = self.selected_index()
        if index is None:
            self.host.showinfo("Select a row", "Pick a row in the list first.", parent=self)
        return index

    # ---- the buttons ---------------------------------------------------------------------------
    def locate_selected(self) -> None:
        index = self._need_selection()
        if index is None:
            return
        initial = self.session.initial_dir(index)
        path = self.host.askopenfilename(
            title=f"Locate file for {self.session.assets[index].short_label()}",
            initialdir=str(initial) if initial else "", filetypes=self.session.file_types, parent=self)
        if not path:
            return
        problem = self.session.locate(index, path)
        if problem:
            self.host.showerror("Not located", problem, parent=self)
        self.repaint_entries()

    def skip_selected(self) -> None:
        index = self._need_selection()
        if index is None:
            return
        self.session.skip(index)
        self.repaint_entries()

    def reset_selected(self) -> None:
        index = self.selected_index()
        if index is None:
            return
        self.session.reset(index)
        self.repaint_entries()

    def locate_folder(self) -> None:
        directory = self.host.askdirectory(
            title="Pick a folder that contains the missing STEP / STL files", parent=self)
        if not directory:
            return
        _matched, message = self.session.locate_folder(directory)
        self.repaint_entries()
        if message:
            self.host.showinfo("No matches", message, parent=self)

    def skip_all(self) -> None:
        self.session.skip_all()
        self.repaint_entries()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        # Continue, Escape and the window's close button all end here: the session rebuilds and
        # redraws, once
        self.session.close()
        super().closeEvent(event)

    def reject(self) -> None:
        # Escape: QDialog's reject() hides without a closeEvent -- end the session the same way
        self.session.close()
        super().reject()
