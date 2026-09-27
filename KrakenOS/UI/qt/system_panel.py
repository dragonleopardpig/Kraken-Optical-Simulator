"""The system, source and trace inputs in Qt (docs/design_qt_migration.md phase 6).

Object mode, wavelength, ray fan count, aperture and field -- the controls that decide what is
traced (bugs/0900); the 23 that decide what LAUNCHES the light (bugs/0901); and the 15 that
decide how the trace runs and what the plots show (bugs/0902).
`KrakenOS/UI/system_controls.py` says which model variable each one edits, what to call after a
change, which model rule says whether it applies right now, and -- for a list the model fills at
runtime -- where its choices come from. So this is layout and binding only, and one class
renders any group.

Binding is the trick the status bar uses: every one of these variables carries `trace_add`
whether a Tk panel or a UI host made it, so the model writing a value repaints the widget, and
the widget writing one goes through the model's own commit. Relevance and the live lists arrive
through `refresh_state`, which the shell calls from the model's `show_control_state` seam.
"""
from __future__ import annotations

from KrakenOS.UI.system_controls import SYSTEM_CONTROLS


def _truthy(value) -> bool:
    """A boolean variable's value, whichever variable class holds it."""
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


class SystemPanel:
    """A form over one group of the model's own variables."""

    def __init__(self, editor, controls=SYSTEM_CONTROLS) -> None:
        from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QLabel, QLineEdit,
                                       QWidget)

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
                field.addItems(list(control.choices_for(editor)))
                field.setEditable(False)
                field.currentTextChanged.connect(
                    lambda _text, control=control: self._commit(control))
            elif control.kind == "bool":
                field = QCheckBox()
                field.toggled.connect(lambda _checked, control=control: self._commit(control))
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
        self.refresh_state()

    # ---- model -> view ---------------------------------------------------------------------
    def _model_wrote(self, control) -> None:
        variable = getattr(self.editor, control.key, None)
        if variable is None:
            return
        try:
            raw = variable.get()
        except Exception:
            return
        field = self.widgets[control.key]
        self._writing = True
        try:
            if control.kind == "bool":
                if field.isChecked() != _truthy(raw):
                    field.setChecked(_truthy(raw))
            elif control.kind == "choice":
                value = str(raw)
                if value and value not in self._items(field):
                    # the model may hold a value this list was built without
                    field.addItem(value)
                field.setCurrentText(value)
            elif field.text() != str(raw):
                field.setText(str(raw))
        finally:
            self._writing = False
        self.labels[control.key].setText(control.label_for(self.editor))

    @staticmethod
    def _items(field) -> list:
        return [field.itemText(index) for index in range(field.count())]

    def refresh_state(self) -> None:
        """Re-read what the model decides: which inputs apply, and the lists it fills live.

        A rebuilt list keeps the model's current value selected; nothing here writes a variable,
        so refreshing cannot trigger a commit.
        """
        self._writing = True
        try:
            for control in self.controls:
                field = self.widgets[control.key]
                relevant = control.is_relevant(self.editor)
                field.setEnabled(relevant)
                self.labels[control.key].setEnabled(relevant)
                if control.kind == "choice" and control.choices_from:
                    choices = list(control.choices_for(self.editor))
                    if self._items(field) != choices:
                        current = field.currentText()
                        field.clear()
                        field.addItems(choices)
                        if current in choices:
                            field.setCurrentText(current)
        finally:
            self._writing = False
        for control in self.controls:
            if control.kind == "choice" and control.choices_from:
                self._model_wrote(control)

    # ---- view -> model ---------------------------------------------------------------------
    def _commit(self, control) -> None:
        if self._writing:
            return
        variable = getattr(self.editor, control.key, None)
        field = self.widgets[control.key]
        if control.kind == "bool":
            value = field.isChecked()
        elif control.kind == "choice":
            value = field.currentText()
        else:
            value = field.text()
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
        shown = {}
        for control in self.controls:
            widget = self.widgets[control.key]
            if control.kind == "bool":
                shown[control.key] = widget.isChecked()
            elif control.kind == "choice":
                shown[control.key] = widget.currentText()
            else:
                shown[control.key] = widget.text()
        return shown

    def enabled(self) -> dict:
        """Which inputs the form offers right now -- what a guard compares with the rules."""
        return {key: widget.isEnabled() for key, widget in self.widgets.items()}
