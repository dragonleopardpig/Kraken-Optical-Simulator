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
        from `design_constraints_model` -- the widget Quick Estimation's forms embed too (0953)."""
        from KrakenOS.UI.qt.design_constraints_block import DesignConstraintsBlock

        block = self.design_block = DesignConstraintsBlock(self.inspector)
        self.design_header = block.header
        self.design_checks, self.design_values = block.checks, block.values
        self.design_result = block.result
        self.controls.update(block.mode_radios)
        self.controls.update(block.buttons)
        outer.addWidget(block.box)

    @property
    def design_mode(self) -> str:
        return self.design_block.mode

    def _set_design_mode(self, mode: str) -> None:
        self.design_block.set_mode(mode)

    def _design_pins(self) -> dict:
        return self.design_block.pins()

    def recompute_design(self) -> None:
        self.design_block.recompute()

    def apply_design(self) -> None:
        self.design_block.apply()

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

