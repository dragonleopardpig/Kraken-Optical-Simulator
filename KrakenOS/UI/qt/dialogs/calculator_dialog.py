"""The Paraxial Calculator, Qt side (docs/design_qt_migration.md phase 3).

A form dialog rather than a report: fields, a solve, and an apply that writes back into the
layout. Every one of those lives in `KrakenOS/UI/paraxial_calculator.py`, which the Tk dialog was
rewired onto -- this class is the form.
"""
from __future__ import annotations

from KrakenOS.UI.paraxial_calculator import (
    OBJECT_MODES,
    PROMPT,
    SOLVE_TARGETS,
    CalculatorFailed,
    CalculatorInputs,
    NothingToApply,
    apply_solution,
    field_states,
    format_calc,
    initial_inputs,
    load_from_layout,
    solve,
)
from KrakenOS.UI.uihost import host_of

TITLE = "Paraxial Calculator"
#: field key -> label, in form order
FIELDS = (
    ("effl", "EFL / EFFL [mm]"),
    ("ppa", "H1 offset PPA [mm]"),
    ("ppp", "H2 offset PPP [mm]"),
    ("object_distance", "Object distance [mm]"),
    ("image_distance", "Image distance [mm]"),
    ("magnification", "Magnification"),
)


def _dialog_class():
    from PySide6.QtWidgets import QDialog

    return QDialog


class ParaxialCalculatorDialog(_dialog_class()):
    def __init__(self, editor, parent=None, host=None) -> None:
        from PySide6.QtWidgets import (QComboBox, QDialogButtonBox, QFormLayout, QLabel,
                                       QLineEdit, QVBoxLayout)

        super().__init__(parent)
        self.editor = editor
        self.host = host if host is not None else host_of(parent)
        self.loaded_solution: "dict | None" = None
        self.payload: dict = {}

        self.setWindowTitle(TITLE)
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # The combos are connected at the END of this constructor: setting their text here would
        # fire currentTextChanged into refresh_field_states before the distance fields exist.
        self.solve_for = QComboBox()
        self.solve_for.addItems(list(SOLVE_TARGETS))
        form.addRow("Solve for", self.solve_for)

        opening = initial_inputs(editor)
        self.solve_for.setCurrentText(opening.solve_for)
        self.fields: dict = {}
        for key, label in FIELDS[:3]:
            self.fields[key] = QLineEdit(getattr(opening, key))
            form.addRow(label, self.fields[key])

        self.object_mode = QComboBox()
        self.object_mode.addItems(list(OBJECT_MODES))
        form.addRow("Object mode", self.object_mode)

        self.object_mode.setCurrentText(opening.object_mode)
        for key, label in FIELDS[3:]:
            self.fields[key] = QLineEdit(getattr(opening, key))
            form.addRow(label, self.fields[key])

        self.entrance_pupil = QLabel("n/a")
        self.exit_pupil = QLabel("n/a")
        form.addRow("Entrance pupil z [mm]", self.entrance_pupil)
        form.addRow("Exit pupil z [mm]", self.exit_pupil)
        layout.addLayout(form)

        self.note = QLabel(PROMPT)
        self.note.setWordWrap(True)
        self.result = QLabel(PROMPT)
        self.detail = QLabel("")
        for label in (self.note, self.result, self.detail):
            label.setWordWrap(True)
            layout.addWidget(label)
        font = self.result.font()
        font.setBold(True)
        self.result.setFont(font)

        self.buttons = QDialogButtonBox()
        role = QDialogButtonBox.ButtonRole.ActionRole
        self.load_button = self.buttons.addButton("Use Current Layout", role)
        self.solve_button = self.buttons.addButton("Solve", role)
        self.apply_button = self.buttons.addButton("Apply", role)
        self.apply_close_button = self.buttons.addButton("Apply and Close", role)
        self.close_button = self.buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self.load_button.clicked.connect(self.use_current_layout)
        self.solve_button.clicked.connect(self.solve)
        self.apply_button.clicked.connect(self.apply_to_layout)
        self.apply_close_button.clicked.connect(self.apply_and_close)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.solve_for.currentTextChanged.connect(self.refresh_field_states)
        self.object_mode.currentTextChanged.connect(self.refresh_field_states)
        self.use_current_layout()

    # ---- state -----------------------------------------------------------------------------------
    def inputs(self) -> CalculatorInputs:
        return CalculatorInputs(
            solve_for=self.solve_for.currentText(),
            effl=self.fields["effl"].text(), ppa=self.fields["ppa"].text(),
            ppp=self.fields["ppp"].text(), object_mode=self.object_mode.currentText(),
            object_distance=self.fields["object_distance"].text(),
            image_distance=self.fields["image_distance"].text(),
            magnification=self.fields["magnification"].text())

    def refresh_field_states(self, _text=None) -> None:
        states = field_states(self.solve_for.currentText(), self.object_mode.currentText())
        for key, state in states.items():
            widget = self.fields.get(key)
            if widget is None:
                continue
            widget.setEnabled(state != "disabled")
            widget.setReadOnly(state == "readonly")
        self.payload = {}

    # ---- actions ---------------------------------------------------------------------------------
    def use_current_layout(self) -> None:
        rows = getattr(self.editor, "rows", ()) or ()
        if rows:
            self.object_mode.setCurrentText(self.editor._current_object_mode())
            self.fields["object_distance"].setText(f"{float(rows[0].thickness):.6g}")
            image_row = max(0, len(rows) - 2)
            self.fields["image_distance"].setText(f"{float(rows[image_row].thickness):.6g}")
        values, note, self.loaded_solution = load_from_layout(self.editor)
        if "effl" in values:
            for key in ("effl", "ppa", "ppp"):
                self.fields[key].setText(values[key])
        self.entrance_pupil.setText(values.get("ep_z", "n/a"))
        self.exit_pupil.setText(values.get("xp_z", "n/a"))
        self.note.setText(note)
        self.refresh_field_states()
        self.solve()

    def solve(self) -> dict:
        self.payload = {}
        try:
            solution = solve(self.editor, self.inputs(), self.loaded_solution)
        except Exception as exc:
            message = (str(exc) if isinstance(exc, CalculatorFailed)
                       else getattr(self.editor, "short_error_message", str)(exc))
            self.result.setText(f"Solve failed: {message}")
            self.detail.setText("")
            return {}
        self.payload = dict(solution.payload)
        if solution.magnification is not None:
            self.fields["magnification"].setText(format_calc(solution.magnification))
        if solution.object_distance is not None:
            self.fields["object_distance"].setText(format_calc(solution.object_distance))
        if solution.image_distance is not None:
            self.fields["image_distance"].setText(format_calc(solution.image_distance))
        self.result.setText(solution.result)
        self.detail.setText(solution.detail)
        return self.payload

    def apply_to_layout(self) -> bool:
        if not self.payload:
            self.solve()
            if not self.payload:
                return False
        try:
            status = apply_solution(self.editor, dict(self.payload), self.result.text())
        except NothingToApply as exc:
            self.note.setText(str(exc))
            return False
        except Exception as exc:
            message = (str(exc) if isinstance(exc, CalculatorFailed)
                       else getattr(self.editor, "short_error_message", str)(exc))
            self.host.showerror(TITLE, message)
            self.note.setText(f"Apply failed: {message}")
            return False
        self.note.setText(status)
        window = self.parent()
        if hasattr(window, "refresh_from_model"):
            window.refresh_from_model()  # the table and the 3D view follow the layout
        return True

    def apply_and_close(self) -> None:
        if self.apply_to_layout():
            self.accept()
