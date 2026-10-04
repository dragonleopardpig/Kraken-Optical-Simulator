"""The design-constraint block as a Qt widget (bugs/0930; reusable since bugs/0953).

"Pin first-order knowns, solve for the lens": the rows, the Design / Placement header, the pin
collection and the evaluate / apply calls all come from `design_constraints_model`, which the Tk
block (`panels/design_constraint_controls.py`) renders too. It sits in the 3D Live dock, and --
with a `context` -- under Quick Estimation's FOV and detector forms, where the form pins one
quantity itself (the field typed above it, the detector's image distance): that row and its twin
are then left out and named in a note, as the Tk popups do.
"""
from __future__ import annotations

from KrakenOS.UI import design_constraints_model as model


class DesignConstraintsBlock:
    """One block: `box` is the widget; `recompute()` after anything it depends on changed."""

    def __init__(self, inspector, *, title: str = "Solve: constraints", mode: str = "design",
                 context=None, compact: bool = False) -> None:
        from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                                       QLineEdit, QPushButton, QRadioButton, QVBoxLayout)

        self.inspector = inspector
        self.mode = model.normal_mode(mode)
        #: () -> {quantity: value} pinned by whatever hosts the block; None in the 3D Live dock
        self.context = context
        self.compact = bool(compact)
        box = self.box = QGroupBox(title)
        layout = QVBoxLayout(box)
        modes = QHBoxLayout()
        group = QButtonGroup(box)
        #: mode label -> its radio button
        self.mode_radios: dict = {}
        for value, label in model.MODES:
            radio = QRadioButton(label)
            radio.setChecked(value == self.mode)
            radio.toggled.connect(lambda checked, v=value: checked and self.set_mode(v))
            group.addButton(radio)
            modes.addWidget(radio)
            self.mode_radios[label] = radio
        layout.addLayout(modes)
        self.header = QLabel(model.header_text(self.mode))
        self.header.setStyleSheet("color: #555555")
        layout.addWidget(self.header)
        # rows the host pins are not offered again -- and a pinned FOV hides its magnification
        # twin (the same degree of freedom)
        pinned = set(self.context_pins()) if self.compact else set()
        hidden = set(pinned) | {model.TWIN[key] for key in pinned if key in model.TWIN}
        self.context_note = None
        if self.compact:
            self.context_note = QLabel("")
            self.context_note.setStyleSheet("color: #1a6d2f")
            self.context_note.setWordWrap(True)
            layout.addWidget(self.context_note)
        grid = QGridLayout()
        self.checks, self.values = {}, {}
        for row, (quantity, label, unit) in enumerate(q for q in model.ROWS if q[0] not in hidden):
            check = QCheckBox(label)
            value = QLineEdit()
            value.setMaximumWidth(110)
            check.toggled.connect(lambda _checked: self.recompute())
            value.editingFinished.connect(self.recompute)
            grid.addWidget(check, row, 0)
            grid.addWidget(value, row, 1)
            grid.addWidget(QLabel(unit), row, 2)
            self.checks[quantity] = check
            self.values[quantity] = value
        layout.addLayout(grid)
        self.default_message = ("Pin one more to size the lens." if pinned
                                else "Pin two knowns to size the lens.")
        self.result = QLabel(self.default_message)
        self.result.setWordWrap(True)
        layout.addWidget(self.result)
        buttons = QHBoxLayout()
        #: button label -> the button
        self.buttons: dict = {}
        for label, handler in (("Compute lens", self.recompute), ("Apply to layout", self.apply)):
            button = QPushButton(label)
            button.setAutoDefault(False)         # Return in a field above must not press it
            button.clicked.connect(lambda _checked=False, h=handler: h())
            buttons.addWidget(button)
            self.buttons[label] = button
        layout.addLayout(buttons)
        self.recompute()

    def set_mode(self, mode: str) -> None:
        self.mode = model.normal_mode(mode)
        self.recompute()

    def context_pins(self) -> dict:
        if self.context is None:
            return {}
        try:
            return model.clean_context(self.context() or {})
        except Exception:
            return {}

    def pins(self) -> dict:
        """What the host pins, then what the user ticked (the user's entry wins a clash)."""
        typed = model.collect_pins({q: c.isChecked() for q, c in self.checks.items()},
                                   {q: e.text() for q, e in self.values.items()})
        return {**self.context_pins(), **typed}

    def recompute(self) -> None:
        self.header.setText(model.header_text(self.mode))
        context = self.context_pins()
        if self.context_note is not None:
            self.context_note.setText(
                "From this view: " + ", ".join(f"{model.LABELS.get(q, q)} = {v:.4g}" for q, v in context.items())
                if context else "")
        try:
            states, result = model.evaluate(self.inspector, self.mode, self.pins())
        except Exception:
            return
        for quantity, check in self.checks.items():
            entry = self.values[quantity]
            state = (states.get(quantity) or {}).get("state", "available")
            locked = state == "locked"
            check.setEnabled(not locked)
            entry.setEnabled(not locked)
            if locked:
                value = (states.get(quantity) or {}).get("value")
                if value is not None:
                    try:
                        entry.setText(f"{float(value):.4g}")
                    except (TypeError, ValueError):
                        pass
        self.result.setText(result.get("message") or "Pin the remaining knowns to size the lens.")
        self.result.setStyleSheet(f"color: {model.STATUS_COLORS.get(result.get('status'), '#1a3b6d')}")

    def apply(self) -> None:
        try:
            model.apply(self.inspector, self.mode, self.pins())
        except Exception:
            return
        self.recompute()
