"""The Qt view of a `RowForm` (docs/design_qt_migration.md phase 3).

Layout only: the fields, their order and their hints come from the form, and Validate and Apply
call the model's own callables. Porting a row-editing dialog is therefore a builder plus a menu
entry, as a report is.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormRefused
from KrakenOS.UI.uihost import host_of


def _dialog_class():
    from PySide6.QtWidgets import QDialog

    return QDialog


class RowFormDialog(_dialog_class()):
    def __init__(self, form, parent=None, host=None) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialogButtonBox, QFormLayout,
                                       QLabel, QLineEdit, QPlainTextEdit, QTabWidget,
                                       QVBoxLayout, QWidget)

        super().__init__(parent)
        self.form = form
        # Always message through THIS host. host_of(dialog) would find no `ui` on a QDialog and
        # fall back to TkUiHost(dialog) -- a modal TKINTER box inside the Qt app, which never
        # returns (bugs/0871).
        self.host = host if host is not None else host_of(parent)

        self.setWindowTitle(form.title)
        self.setMinimumWidth(620)
        layout = QVBoxLayout(self)

        if form.note:
            note = QLabel(form.note)
            note.setWordWrap(True)
            layout.addWidget(note)

        self.widgets: dict = {}
        self.tabs = None
        self.records_view = None
        # A record-list form (the Scene Source Manager) edits ONE item of a collection it also
        # owns, so the list goes beside the fields and the selection is model state, not view
        # state: picking a row calls form.records.select(form, index) and the form rewrites
        # itself (bugs/0881).
        host_widget = self
        if form.records is not None:
            from PySide6.QtWidgets import QSplitter, QTableWidget, QTableWidgetItem
            from PySide6.QtCore import Qt

            splitter = QSplitter(Qt.Orientation.Horizontal)
            self.records_view = QTableWidget(0, len(form.records.columns))
            self.records_view.setHorizontalHeaderLabels(list(form.records.columns))
            self.records_view.setSelectionBehavior(
                QTableWidget.SelectionBehavior.SelectRows)
            self.records_view.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            self.records_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.records_view.verticalHeader().setVisible(False)
            splitter.addWidget(self.records_view)
            fields_host = QWidget()
            splitter.addWidget(fields_host)
            splitter.setStretchFactor(1, 2)
            layout.addWidget(splitter, stretch=1)
            host_layout = QVBoxLayout(fields_host)
            host_layout.setContentsMargins(0, 0, 0, 0)
            host_widget = fields_host
            self._records_item = QTableWidgetItem
            self.setMinimumSize(1120, 720)
        if form.groups:
            # one tab per group, in field order -- Shape Params, each attribute group, Custom
            self.tabs = QTabWidget()
            for group in form.groups:
                page = QWidget()
                page_layout = QFormLayout(page)
                for field in form.fields_in(group):
                    label, widget = self._build_field(field)
                    page_layout.addRow(label, widget)
                self.tabs.addTab(page, group)
            (host_layout if host_widget is not self else layout).addWidget(self.tabs,
                                                                            stretch=1)
            grid = None
        else:
            grid = QFormLayout()
        for field in (() if form.groups else form.fields):
            label, widget = self._build_field(field)
            grid.addRow(label, widget)
        if grid is not None:
            if host_widget is not self:
                # ~30 fields is taller than a laptop screen: give the form its own scroll area
                from PySide6.QtWidgets import QScrollArea

                page = QWidget()
                page.setLayout(grid)
                scroller = QScrollArea()
                scroller.setWidgetResizable(True)
                scroller.setWidget(page)
                host_layout.addWidget(scroller)
            else:
                layout.addLayout(grid)
        if self.records_view is not None:
            self.records_view.itemSelectionChanged.connect(self.on_record_selected)
            self.refresh_records()

        self.preview_label = None
        self.preview_caption = None
        if form.preview is not None:
            from PySide6.QtWidgets import QHBoxLayout

            preview_row = QWidget()
            preview_layout = QHBoxLayout(preview_row)
            preview_layout.setContentsMargins(0, 0, 0, 0)
            self.preview_label = QLabel()
            self.preview_label.setFixedSize(form.preview.width, form.preview.height)
            preview_layout.addWidget(self.preview_label)
            self.preview_caption = QLabel()
            self.preview_caption.setWordWrap(True)
            self.preview_caption.setTextFormat(Qt.TextFormat.PlainText)
            font = self.preview_caption.font()
            font.setFamily("monospace")
            font.setPointSize(8)
            self.preview_caption.setFont(font)
            preview_layout.addWidget(self.preview_caption, stretch=1)
            layout.addWidget(preview_row)

        self.summary = QLabel(form.summary)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.buttons = QDialogButtonBox()
        role = QDialogButtonBox.ButtonRole.ActionRole
        self.action_buttons: dict = {}
        for action in form.actions:
            button = self.buttons.addButton(action.label, role)
            button.clicked.connect(lambda _checked=False, a=action: self.run_action(a))
            self.action_buttons[action.key] = button
        self.validate_button = self.buttons.addButton("Validate", role)
        self.apply_button = self.buttons.addButton("Apply", role)
        self.cancel_button = self.buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.validate_button.clicked.connect(self.validate)
        self.apply_button.clicked.connect(self.apply_to_row)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        if self.preview_label is not None:
            for key, widget in self.widgets.items():
                if hasattr(widget, "textEdited"):
                    widget.textEdited.connect(lambda _text: self.redraw_preview())
                elif hasattr(widget, "currentTextChanged"):
                    widget.currentTextChanged.connect(lambda _text: self.redraw_preview())
                elif hasattr(widget, "toggled"):
                    widget.toggled.connect(lambda _checked: self.redraw_preview())
            self.redraw_preview()

    def redraw_preview(self) -> None:
        """Ask the MODEL what to draw, then paint it -- the same shapes Tk draws."""
        if self.preview_label is None:
            return
        from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QPolygon
        from PySide6.QtCore import QPoint

        values = self.values()
        try:
            shapes = list(self.form.preview.shapes(self.form, values))
            caption = str(self.form.preview.caption(self.form, values))
        except Exception:
            return  # a half-typed number is not an error, it is just not drawable yet
        pixmap = QPixmap(self.form.preview.width, self.form.preview.height)
        pixmap.fill(QColor("#fafafa"))
        painter = QPainter(pixmap)
        try:
            for shape in shapes:
                if shape.get("kind") == "polygon":
                    points = [QPoint(int(x), int(y)) for x, y in shape.get("points", ())]
                    if len(points) >= 3:
                        painter.setBrush(QColor(shape.get("fill", "#ffffff")))
                        painter.setPen(QPen(QColor(shape.get("outline", "#000000")), 1))
                        painter.drawPolygon(QPolygon(points))
                elif shape.get("kind") == "text":
                    painter.setPen(QPen(QColor(shape.get("fill", "#000000"))))
                    font = painter.font()
                    font.setPointSize(int(shape.get("size", 7)))
                    painter.setFont(font)
                    painter.drawText(int(shape.get("x", 0)) - 60, int(shape.get("y", 0)),
                                     str(shape.get("text", "")))
        finally:
            painter.end()
        self.preview_label.setPixmap(pixmap)
        self.preview_caption.setText(caption)

    @staticmethod
    def _widget_text(widget) -> str:
        if hasattr(widget, "currentText"):
            return widget.currentText()
        if hasattr(widget, "toPlainText"):
            return widget.toPlainText()
        if hasattr(widget, "isChecked"):
            return "true" if widget.isChecked() else "false"
        return widget.text()

    def _build_field(self, field):
        """One label and one widget for a field, whatever its kind. Returns (label, widget)."""
        from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QPlainTextEdit

        value = str(self.form.values.get(field.key, ""))
        if field.kind == "choice":
            widget = QComboBox()
            widget.setEditable(field.editable)
            widget.addItems(list(self.form.choices_for(field.key)))
            if value in self.form.choices_for(field.key) or field.editable:
                widget.setCurrentText(value)
            if field.on_change is not None:
                widget.currentTextChanged.connect(
                    lambda text, f=field: self.on_field_changed(f, text))
        elif field.kind == "bool":
            widget = QCheckBox()
            widget.setChecked(value.strip().lower() in ("1", "true", "yes", "on"))
        elif field.kind == "static":
            widget = QLabel(value)
            widget.setWordWrap(True)
            widget.setTextInteractionFlags(widget.textInteractionFlags().TextSelectableByMouse)
        elif field.kind == "textarea":
            widget = QPlainTextEdit(value)
            widget.setMinimumHeight(18 * max(field.height, 3))
        else:
            widget = QLineEdit(value)
            widget.setMaximumWidth(14 * max(field.width, 8))
            if field.on_change is not None:
                # a live filter: every keystroke re-asks the model for the rows
                widget.textEdited.connect(
                    lambda text, f=field: self.on_field_changed(f, text))
        widget.setToolTip(field.hint)
        # is_enabled, never field.enabled -- a choice may lock a field after the form is built
        widget.setEnabled(self.form.is_enabled(field.key))
        self.widgets[field.key] = widget
        label = QLabel(field.label)
        label.setToolTip(field.hint)
        return label, widget

    def values(self) -> dict:
        """Every field's text. A static label is shown, never collected back."""
        return {key: self._widget_text(widget) for key, widget in self.widgets.items()
                if not (hasattr(widget, "setWordWrap") and not hasattr(widget, "isChecked"))}

    def on_field_changed(self, field, text: str) -> str:
        """A field that rewrites another one -- the model decides what changes."""
        if field.on_change is None:
            return ""
        self.form.values[field.key] = text
        try:
            message = field.on_change(self.form, text)
        except FormRefused as exc:
            self.host.showerror(self.form.title, str(exc))
            return ""
        self.refresh_records()
        self.refresh_from_form()
        self.redraw_preview()
        if message:
            self.summary.setText(message)
        return message

    def refresh_records(self) -> None:
        """Redraw the master list from the model and re-select what the form is editing."""
        if self.records_view is None:
            return
        rows = list(self.form.records.rows(self.form))
        self.records_view.blockSignals(True)
        try:
            self.records_view.setRowCount(len(rows))
            for position, row in enumerate(rows):
                for column, text in enumerate(row):
                    self.records_view.setItem(position, column,
                                              self._records_item(str(text)))
            if rows:
                self.records_view.selectRow(
                    min(max(0, self.form.selected_index), len(rows) - 1))
            self.records_view.resizeColumnsToContents()
        finally:
            self.records_view.blockSignals(False)

    def on_record_selected(self) -> str:
        rows = self.records_view.selectionModel().selectedRows()
        if not rows:
            return ""
        index = int(rows[0].row())
        if index == self.form.selected_index:
            return ""
        try:
            message = self.form.records.select(self.form, index)
        except FormRefused as exc:
            self.summary.setText(str(exc))
            return ""
        self.refresh_from_form()
        if message:
            self.summary.setText(message)
        return message

    def run_action(self, action) -> str:
        """Run a form action, then show whatever it changed."""
        if self.form.records is not None:
            self.form.values.update(self.values())
        try:
            message = action.run(self.form, self.host)
        except FormRefused as exc:
            self.host.showerror(self.form.title, str(exc))
            self.summary.setText(f"{action.label}: {str(exc).splitlines()[0]}")
            return ""
        if self.form.records is not None and self.form.state.pop("close_after", False):
            self.refresh_from_form()
            self.summary.setText(message or self.form.summary)
            self.accept()
            return message
        self.refresh_records()
        self.refresh_from_form()
        self.summary.setText(message or self.form.summary)
        return message

    def refresh_from_form(self) -> None:
        """Re-read every widget from the form -- an action may have rewritten its values."""
        for key, widget in self.widgets.items():
            widget.setEnabled(self.form.is_enabled(key))
            value = str(self.form.values.get(key, ""))
            if hasattr(widget, "isChecked"):
                widget.setChecked(value.strip().lower() in ("1", "true", "yes", "on"))
            elif hasattr(widget, "setWordWrap"):
                widget.setText(value)
            elif hasattr(widget, "setCurrentText"):
                wanted = list(self.form.choices_for(key))
                if [widget.itemText(i) for i in range(widget.count())] != wanted:
                    widget.blockSignals(True)
                    try:
                        widget.clear()
                        widget.addItems(wanted)
                    finally:
                        widget.blockSignals(False)
                if value and (value in wanted or self.form.field(key).editable):
                    widget.blockSignals(True)
                    try:
                        widget.setCurrentText(value)
                    finally:
                        widget.blockSignals(False)
            elif hasattr(widget, "setPlainText"):
                if widget.toPlainText() != value:
                    widget.setPlainText(value)
            elif widget.text() != value:
                widget.setText(value)

    def validate(self) -> list:
        errors = list(self.form.validate(self.values()))
        if errors:
            self.summary.setText(f"Validation failed: {errors[0]}")
        else:
            try:
                self.summary.setText("Validation passed: " + self.form.describe(self.values()))
            except FormRefused as exc:
                self.summary.setText(f"Validation failed: {exc}")
        return errors

    def apply_to_row(self) -> bool:
        try:
            status = self.form.apply(self.values())
        except FormRefused as exc:
            self.host.showerror(self.form.title, str(exc))
            self.summary.setText(f"Apply refused: {str(exc).splitlines()[0]}")
            return False
        self.summary.setText(status)
        window = self.parent()
        if hasattr(window, "refresh_from_model"):
            window.refresh_from_model()  # the table and the 3D view follow the row
        if hasattr(window, "statusBar"):
            # after the redraw, which reports on itself; the model already wrote this line to
            # status_var, so the bar would show it anyway once the redraw is done
            window.statusBar().showMessage(status)
        self.accept()
        return True
