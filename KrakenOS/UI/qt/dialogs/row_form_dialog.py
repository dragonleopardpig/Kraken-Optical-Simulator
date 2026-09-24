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
            layout.addWidget(self.tabs, stretch=1)
            grid = None
        else:
            grid = QFormLayout()
        for field in (() if form.groups else form.fields):
            label, widget = self._build_field(field)
            grid.addRow(label, widget)
        if grid is not None:
            layout.addLayout(grid)

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
            widget.addItems(list(self.form.choices_for(field.key)))
            if value in self.form.choices_for(field.key):
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
        self.refresh_from_form()
        if message:
            self.summary.setText(message)
        return message

    def run_action(self, action) -> str:
        """Run a form action, then show whatever it changed."""
        try:
            message = action.run(self.form, self.host)
        except FormRefused as exc:
            self.host.showerror(self.form.title, str(exc))
            self.summary.setText(f"{action.label}: {str(exc).splitlines()[0]}")
            return ""
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
                if value and value in wanted:
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
