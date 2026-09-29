"""The 3D inspector's Live Controls in the Qt shell (docs/design_qt_migration.md phase 5f, part 2).

What `open3d_live_panel.py` names, laid out as one Qt form bound to the SAME model: the header
(Live Mode, Trace now, Update 2D), the two display choices the System/Source/Trace docks do not
carry, Quick Estimation (toggle, readouts, actions, role choices) and the Variable-thickness solve.
The Field / Trace / Source inputs of the Tk panel are the main window's docks here (0900-0902) --
the same editor variables, so there is one place to edit each.

A widget writes the model and runs the model's commit; a model write reaches the widget through
the variable's ``trace_add``, signals blocked so a repaint never commits again.
"""
from __future__ import annotations

from KrakenOS.UI import open3d_live_panel as catalogue
from KrakenOS.UI import open3d_toolbar as toolbar


def _truthy(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _watch(variable, repaint) -> None:
    try:
        variable.trace_add("write", lambda *_args: repaint())
    except Exception:
        pass


class LiveControlsForm:
    """The form; ``controls`` maps a label to its widget, ``readouts`` a key to its value label."""

    def __init__(self, inspector, *, open_system_selection=None) -> None:
        from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                                       QLabel, QPushButton, QVBoxLayout, QWidget)

        self.inspector = inspector
        self.editor = inspector.editor
        self.controls: dict = {}
        self.readouts: dict = {}
        self.widget = QWidget()
        outer = QVBoxLayout(self.widget)

        header = QHBoxLayout()
        for item in catalogue.HEADER:
            header.addWidget(self._control(item))
        header.addStretch(1)
        outer.addLayout(header)

        display = QGroupBox("Display")
        form = QFormLayout(display)
        for entry in catalogue.DISPLAY_CHOICES:
            var_name, label, _choices, handler = entry
            variable = getattr(self.editor, var_name, None)
            if variable is None:
                continue
            combo = QComboBox()
            combo.addItems(list(catalogue.display_choices(entry)))
            combo.setCurrentText(str(variable.get()))

            def chosen(text, v=variable, h=handler) -> None:
                v.set(text)
                inspector._commit_live_control_update(handler=getattr(self.editor, h))

            combo.currentTextChanged.connect(chosen)
            self._repaint_combo(combo, variable)
            form.addRow(label, combo)
            self.controls[label] = combo
        outer.addWidget(display)

        qe = QGroupBox("Object / Image / FOV (Quick Estimation)")
        qe_layout = QVBoxLayout(qe)
        qe_layout.addWidget(self._control(catalogue.QUICK_ESTIMATION_TOGGLE))
        grid = QGridLayout()
        row = 0
        for entry in catalogue.READOUTS:
            if entry is None:
                row += 1
                continue
            key, label = entry
            variable = inspector._quick_estimation_readout_vars.get(key)
            value = QLabel(str(variable.get()) if variable is not None else "--")
            value.setStyleSheet("color: #1a3b6d")
            if variable is not None:
                _watch(variable, lambda w=value, v=variable: w.setText(str(v.get())))
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(value, row, 1)
            self.readouts[key] = value
            row += 1
        qe_layout.addLayout(grid)
        actions = QHBoxLayout()
        for item in catalogue.QUICK_ESTIMATION_ACTIONS:
            actions.addWidget(self._control(item))
        qe_layout.addLayout(actions)
        roles = QHBoxLayout()
        roles.addWidget(QLabel("Roles:"))
        from KrakenOS.UI.services.quick_estimation import ROLES

        self.role_combos: dict = {}
        for quantity, short in catalogue.QUICK_ESTIMATION_ROLES:
            roles.addWidget(QLabel(short))
            combo = QComboBox()
            combo.addItems(list(ROLES))
            combo.setCurrentText(str(inspector._quick_estimation_service().role(quantity)))
            combo.currentTextChanged.connect(lambda text, q=quantity: self._set_role(q, text))
            roles.addWidget(combo)
            self.role_combos[quantity] = combo
            self.controls[short] = combo
        qe_layout.addLayout(roles)
        outer.addWidget(qe)

        self.solve_box = QGroupBox("Variable thickness")
        self.solve_layout = QVBoxLayout(self.solve_box)
        self.gap_checks: dict = {}
        self.gaps_host = QWidget()
        self.gaps_layout = QVBoxLayout(self.gaps_host)
        self.gaps_layout.setContentsMargins(0, 0, 0, 0)
        self.solve_layout.addWidget(self.gaps_host)
        buttons = QHBoxLayout()
        refresh = QPushButton("Refresh gaps")
        refresh.clicked.connect(self.refresh_gaps)
        buttons.addWidget(refresh)
        for label, mode in catalogue.SOLVES:
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, m=mode: inspector._open3d_run_thickness_solve(m))
            buttons.addWidget(button)
            self.controls[label] = button
        self.solve_layout.addLayout(buttons)
        outer.addWidget(self.solve_box)

        self._build_design_constraints(outer)

        # the calculator the Tk panel embeds opens as the main window's dialog -- one copy (0930)
        sizing = QGroupBox("Camera + lens (System Selection)")
        sizing_layout = QVBoxLayout(sizing)
        open_button = QPushButton("System Selection Calculator…")
        if open_system_selection is not None:
            open_button.clicked.connect(lambda _checked=False: open_system_selection())
        else:
            open_button.setEnabled(False)
        sizing_layout.addWidget(open_button)
        self.controls["System Selection Calculator…"] = open_button
        outer.addWidget(sizing)
        outer.addStretch(1)
        self.refresh_gaps()
        try:
            inspector._quick_estimation_service().update_readout()
        except Exception:
            pass

    # ---- design constraints (0930) -------------------------------------------------------------
    def _build_design_constraints(self, outer) -> None:
        """The design-constraint block (0930): the same rows, header and service calls as the Tk block,
        from `design_constraints_model`."""
        from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                                       QLineEdit, QPushButton, QRadioButton, QVBoxLayout)

        from KrakenOS.UI import design_constraints_model as model

        box = QGroupBox("Solve: constraints")
        layout = QVBoxLayout(box)
        modes = QHBoxLayout()
        self.design_mode = "design"
        group = QButtonGroup(box)
        for value, label in model.MODES:
            radio = QRadioButton(label)
            radio.setChecked(value == "design")
            radio.toggled.connect(lambda checked, v=value: checked and self._set_design_mode(v))
            group.addButton(radio)
            modes.addWidget(radio)
            self.controls[label] = radio
        layout.addLayout(modes)
        self.design_header = QLabel(model.header_text("design"))
        self.design_header.setStyleSheet("color: #555555")
        layout.addWidget(self.design_header)
        grid = QGridLayout()
        self.design_checks, self.design_values = {}, {}
        for row, (quantity, label, unit) in enumerate(model.ROWS):
            check = QCheckBox(label)
            value = QLineEdit()
            value.setMaximumWidth(110)
            check.toggled.connect(lambda _checked: self.recompute_design())
            value.editingFinished.connect(self.recompute_design)
            grid.addWidget(check, row, 0)
            grid.addWidget(value, row, 1)
            grid.addWidget(QLabel(unit), row, 2)
            self.design_checks[quantity] = check
            self.design_values[quantity] = value
        layout.addLayout(grid)
        self.design_result = QLabel("Pin two knowns to size the lens.")
        self.design_result.setWordWrap(True)
        layout.addWidget(self.design_result)
        buttons = QHBoxLayout()
        for label, handler in (("Compute lens", self.recompute_design), ("Apply to layout", self.apply_design)):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, h=handler: h())
            buttons.addWidget(button)
            self.controls[label] = button
        layout.addLayout(buttons)
        outer.addWidget(box)
        self.recompute_design()


    def _set_design_mode(self, mode: str) -> None:
        self.design_mode = mode
        self.recompute_design()


    def _design_pins(self) -> dict:
        from KrakenOS.UI import design_constraints_model as model

        return model.collect_pins({q: c.isChecked() for q, c in self.design_checks.items()},
                                  {q: e.text() for q, e in self.design_values.items()})


    def recompute_design(self) -> None:
        from KrakenOS.UI import design_constraints_model as model

        self.design_header.setText(model.header_text(self.design_mode))
        try:
            states, result = model.evaluate(self.inspector, self.design_mode, self._design_pins())
        except Exception:
            return
        for quantity, check in self.design_checks.items():
            entry = self.design_values[quantity]
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
        self.design_result.setText(result.get("message") or "Pin the remaining knowns to size the lens.")
        self.design_result.setStyleSheet(f"color: {model.STATUS_COLORS.get(result.get('status'), '#1a3b6d')}")


    def apply_design(self) -> None:
        from KrakenOS.UI import design_constraints_model as model

        try:
            model.apply(self.inspector, self.design_mode, self._design_pins())
        except Exception:
            return
        self.recompute_design()

    # ---- pieces -------------------------------------------------------------------------------
    def _control(self, item):
        from PySide6.QtWidgets import QCheckBox, QPushButton

        inspector = self.inspector
        if isinstance(item, toolbar.Check):
            variable = toolbar.resolve(inspector, item.var)
            box = QCheckBox(item.label)
            box.setChecked(_truthy(variable.get()))

            def written(checked, v=variable, t=item.target) -> None:
                v.set(bool(checked))
                toolbar.callback(inspector, t)()

            box.toggled.connect(written)

            def repaint(b=box, v=variable) -> None:
                blocked = b.blockSignals(True)
                try:
                    b.setChecked(_truthy(v.get()))
                finally:
                    b.blockSignals(blocked)

            _watch(variable, repaint)
            self.controls[item.label] = box
            return box
        button = QPushButton(item.label)
        button.clicked.connect(lambda _checked=False, i=item: toolbar.callback(inspector, i.target, i.args)())
        self.controls[item.label] = button
        return button

    @staticmethod
    def _repaint_combo(combo, variable) -> None:
        def repaint() -> None:
            blocked = combo.blockSignals(True)
            try:
                combo.setCurrentText(str(variable.get()))
            finally:
                combo.blockSignals(blocked)

        _watch(variable, repaint)

    def _set_role(self, quantity: str, role: str) -> None:
        service = self.inspector._quick_estimation_service()
        summary = service.set_role(quantity, role)
        service.update_readout()
        for q, combo in self.role_combos.items():
            blocked = combo.blockSignals(True)
            try:
                combo.setCurrentText(str(service.role(q)))
            finally:
                combo.blockSignals(blocked)
        if summary:
            self.inspector.status_var.set(summary)

    def refresh_gaps(self) -> None:
        """Rebuild the gap list from the solve service -- the rows change with the system."""
        from PySide6.QtWidgets import QCheckBox

        while self.gaps_layout.count():
            item = self.gaps_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.gap_checks = {}
        try:
            service = self.inspector._open3d_solve_service()
            gaps = list(service.thickness_gap_rows())
        except Exception:
            return
        for row_index, label in gaps:
            box = QCheckBox(str(label))
            box.setChecked(bool(service.is_variable(row_index)))
            box.toggled.connect(lambda checked, ri=row_index: self._toggle_gap(ri, checked))
            self.gaps_layout.addWidget(box)
            self.gap_checks[row_index] = box

    def _toggle_gap(self, row_index: int, checked: bool) -> None:
        # the explicit value: the Tk toggle would read the hidden Tk checkbox Qt never flips
        self.inspector._open3d_set_variable_thickness(row_index, checked)
        service = self.inspector._open3d_solve_service()
        box = self.gap_checks.get(row_index)
        if box is not None:
            blocked = box.blockSignals(True)
            try:
                box.setChecked(bool(service.is_variable(row_index)))
            finally:
                box.blockSignals(blocked)

