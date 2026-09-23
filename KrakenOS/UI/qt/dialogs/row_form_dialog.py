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
        from PySide6.QtWidgets import (QComboBox, QDialogButtonBox, QFormLayout, QLabel,
                                       QLineEdit, QVBoxLayout)

        super().__init__(parent)
        self.form = form
        self.host = host if host is not None else host_of(parent)

        self.setWindowTitle(form.title)
        self.setMinimumWidth(620)
        layout = QVBoxLayout(self)

        if form.note:
            note = QLabel(form.note)
            note.setWordWrap(True)
            layout.addWidget(note)

        grid = QFormLayout()
        self.widgets: dict = {}
        for field in form.fields:
            if field.kind == "choice":
                widget = QComboBox()
                widget.addItems(list(field.choices))
                current = str(form.values.get(field.key, ""))
                if current in field.choices:
                    widget.setCurrentText(current)
            else:
                widget = QLineEdit(str(form.values.get(field.key, "")))
                widget.setMaximumWidth(14 * max(field.width, 8))
            widget.setToolTip(field.hint)
            self.widgets[field.key] = widget
            label = QLabel(field.label)
            label.setToolTip(field.hint)
            grid.addRow(label, widget)
        layout.addLayout(grid)

        self.summary = QLabel(form.summary)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.buttons = QDialogButtonBox()
        role = QDialogButtonBox.ButtonRole.ActionRole
        self.validate_button = self.buttons.addButton("Validate", role)
        self.apply_button = self.buttons.addButton("Apply", role)
        self.cancel_button = self.buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.validate_button.clicked.connect(self.validate)
        self.apply_button.clicked.connect(self.apply_to_row)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def values(self) -> dict:
        return {key: (widget.currentText() if hasattr(widget, "currentText") else widget.text())
                for key, widget in self.widgets.items()}

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
            host_of(self).showerror(self.form.title, str(exc))
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
