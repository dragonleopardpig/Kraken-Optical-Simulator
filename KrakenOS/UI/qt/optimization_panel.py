"""Optimisation in Qt (docs/design_qt_migration.md phase 6).

Start/Stop, the worker count, which merit operands are in use, and each operand's settings. The
operands and which settings each has are `OperandSpec` data; what each setting is comes from
`KrakenOS/UI/optimization_controls.py`; the choice of operands is read by the model through the
`selected_merit_operands` seam and Start/Stop hears the run state through
`show_optimization_state` (bugs/0904). Every value lives in the model's own per-operand
variables, which this binds to exactly as the System dock binds to its inputs.
"""
from __future__ import annotations

from KrakenOS.UI.optimization_controls import controls_for, worker_choices


class OptimizationPanel:
    """The optimisation dock's widgets over the model's operands and variables."""

    def __init__(self, editor) -> None:
        from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QLabel,
                                       QListWidget, QPushButton, QVBoxLayout, QWidget)

        from KrakenOS.UI.layout_editor import OPERAND_REGISTRY

        self.editor = editor
        self.specs = tuple(OPERAND_REGISTRY.values())
        editor.ensure_operand_variables()

        self.widget = QWidget()
        layout = QVBoxLayout(self.widget)

        row = QHBoxLayout()
        self.start_stop = QPushButton("Start Optimization")
        self.start_stop.clicked.connect(self.start_or_stop)
        row.addWidget(self.start_stop)
        row.addWidget(QLabel("Workers"))
        self.workers = QComboBox()
        self.workers.addItems(worker_choices())
        workers_var = getattr(editor, "optimization_workers_var", None)
        if workers_var is not None:
            self.workers.setCurrentText(str(workers_var.get()))
            self.workers.currentTextChanged.connect(lambda text: workers_var.set(text))
        row.addWidget(self.workers)
        row.addStretch(1)
        layout.addLayout(row)

        layout.addWidget(QLabel("Merit operands"))
        self.operands = QListWidget()
        self.operands.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.operands.addItems([spec.label for spec in self.specs])
        self._select_labels(editor._selected_operand_labels())
        self.operands.itemSelectionChanged.connect(self._operands_changed)
        layout.addWidget(self.operands)

        self.settings = QWidget()
        self.settings_layout = QVBoxLayout(self.settings)
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.settings, stretch=1)
        self.fields: dict = {}
        self._build_settings()

        editor.selected_merit_operands = self.selected_labels
        editor.select_merit_operands = self._select_labels
        editor.show_optimization_state = self.show_state
        self.show_state(bool(getattr(editor, "optimization_running", False)))

    # ---- the operand list ---------------------------------------------------------------------
    def selected_labels(self) -> list:
        """The model's `selected_merit_operands` seam: the operands ticked here, in list order."""
        return [self.operands.item(i).text() for i in range(self.operands.count())
                if self.operands.item(i).isSelected()]

    def _select_labels(self, labels) -> None:
        wanted = {str(label) for label in labels}
        self.operands.blockSignals(True)
        try:
            for index in range(self.operands.count()):
                item = self.operands.item(index)
                item.setSelected(item.text() in wanted)
        finally:
            self.operands.blockSignals(False)
        if hasattr(self, "settings_layout"):
            self._build_settings()

    def _operands_changed(self) -> None:
        # choosing operands is undoable in Tk too: capture before, commit after
        self.editor._begin_history_capture()
        self._build_settings()
        self.editor._commit_history_capture()

    # ---- each selected operand's settings -----------------------------------------------------
    def _build_settings(self) -> None:
        from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLineEdit

        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.fields = {}
        chosen = set(self.selected_labels())
        for spec in self.specs:
            if spec.label not in chosen:
                continue
            box = QGroupBox(spec.label)
            form = QFormLayout(box)
            for control in controls_for(spec):
                variable = (getattr(self.editor, control.variables, None) or {}).get(spec.label)
                if variable is None:
                    continue
                if control.kind == "choice":
                    field = QComboBox()
                    field.addItems(list(control.choices))
                    field.setCurrentText(str(variable.get()))
                    field.currentTextChanged.connect(
                        lambda text, variable=variable: self._commit(variable, text))
                else:
                    field = QLineEdit(str(variable.get()))
                    field.editingFinished.connect(
                        lambda field=field, variable=variable: self._commit(variable, field.text()))
                form.addRow(control.label, field)
                self.fields[(spec.label, control.name)] = field
            self.settings_layout.addWidget(box)
        self.settings_layout.addStretch(1)

    def _commit(self, variable, text) -> None:
        """What a Tk card entry does on commit: capture, write, and mark the plot stale."""
        if str(variable.get()) == str(text):
            return
        self.editor._begin_history_capture()
        variable.set(str(text))
        self.editor._mark_plot_update_pending()

    # ---- Start / Stop -------------------------------------------------------------------------
    def show_state(self, running: bool) -> None:
        """The model's `show_optimization_state` seam."""
        self.start_stop.setText("Stop Optimization" if running else "Start Optimization")

    def start_or_stop(self) -> None:
        if bool(getattr(self.editor, "optimization_running", False)):
            self.editor.stop_optimization()
        else:
            self.editor.start_optimization()
