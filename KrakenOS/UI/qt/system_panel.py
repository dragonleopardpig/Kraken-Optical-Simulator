"""The system and source inputs in Qt (docs/design_qt_migration.md phase 6).

Object mode, wavelength, ray fan count, aperture and field -- the controls that decide what is
traced (bugs/0900) -- and the 23 that decide what LAUNCHES the light (bugs/0901).
`KrakenOS/UI/system_controls.py` says which model variable each one edits and what to call after
a change, so this is layout and binding only, and one class renders any group.

Binding is the same trick the status bar uses: every one of these variables carries `trace_add`
whether a Tk panel or a UI host made it, so the model writing a value repaints the widget, and
the widget writing one goes through the model's own commit.
"""
from __future__ import annotations

from KrakenOS.UI.system_controls import SYSTEM_CONTROLS


class SystemPanel:
    """A form over one group of the model's own variables."""

    def __init__(self, editor, controls=SYSTEM_CONTROLS) -> None:
        from PySide6.QtWidgets import (QComboBox, QFormLayout, QLabel, QLineEdit, QWidget)

        self.editor = editor
        self.controls = tuple(controls)
        self.widgets: dict = {}
        self.labels: dict = {}
        self._traces: list = []
        self._writing = False

        self.widget = QWidget()
        layout = QFormLayout(self.widget)
        for control in self.controls:
            variable = getattr(editor, control.key, None)
            if control.kind == "choice":
                field = QComboBox()
                field.addItems([str(choice) for choice in control.choices])
                field.setEditable(False)
                field.currentTextChanged.connect(
                    lambda _text, control=control: self._commit(control))
            else:
                field = QLineEdit()
                field.editingFinished.connect(lambda control=control: self._commit(control))
            label = QLabel(control.label_for(editor))
            layout.addRow(label, field)
            self.widgets[control.key] = field
            self.labels[control.key] = label
            if variable is not None and hasattr(variable, "trace_add"):
                self._traces.append((variable, variable.trace_add(
                    "write", lambda *_args, control=control: self._model_wrote(control))))
            self._model_wrote(control)

    # ---- model -> view ---------------------------------------------------------------------
    def _model_wrote(self, control) -> None:
        variable = getattr(self.editor, control.key, None)
        if variable is None:
            return
        try:
            value = str(variable.get())
        except Exception:
            return
        field = self.widgets[control.key]
        self._writing = True
        try:
            if hasattr(field, "currentText"):
                if value and value not in [field.itemText(i) for i in range(field.count())]:
                    # the model may offer a value this list was built without (a target surface)
                    field.addItem(value)
                field.setCurrentText(value)
            elif field.text() != value:
                field.setText(value)
        finally:
            self._writing = False
        self.labels[control.key].setText(control.label_for(self.editor))

    # ---- view -> model ---------------------------------------------------------------------
    def _commit(self, control) -> None:
        if self._writing:
            return
        variable = getattr(self.editor, control.key, None)
        field = self.widgets[control.key]
        value = field.currentText() if hasattr(field, "currentText") else field.text()
        if variable is not None:
            try:
                variable.set(value)
            except Exception:
                return
        commit = getattr(self.editor, control.commit, None)
        if commit is not None:
            commit()

    def values(self) -> dict:
        """What the form is showing -- what a guard compares."""
        return {key: (widget.currentText() if hasattr(widget, "currentText") else widget.text())
                for key, widget in self.widgets.items()}
