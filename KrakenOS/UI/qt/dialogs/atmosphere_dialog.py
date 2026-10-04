"""Atmospheric Settings in the Qt shell (bugs/0954).

The Tk editor's last menu-bar command without a Qt route. The window is the model's own variables
in the form the System / Source / Trace docks already use: `system_controls.ATMOSPHERE_CONTROLS`
says which variable each input edits and what to call after a change, `SystemPanel` draws them.
Under it, the model's summary line (it follows the variables), and the Tk window's three buttons.
Not modal, and one instance: asking for it again brings it back to the front.
"""
from __future__ import annotations

from KrakenOS.UI import system_controls


def _dialog_base():
    from PySide6.QtWidgets import QDialog

    return QDialog


class AtmosphereSettingsDialog(_dialog_base()):
    def __init__(self, editor, *, parent=None) -> None:
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

        from KrakenOS.UI.qt.system_panel import SystemPanel

        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle(system_controls.ATMOSPHERE_TITLE)
        self.setModal(False)
        layout = QVBoxLayout(self)
        note = QLabel(system_controls.ATMOSPHERE_NOTE)
        note.setWordWrap(True)
        note.setStyleSheet("color: #475569")
        layout.addWidget(note)
        #: the inputs, bound to the model's variables both ways
        self.panel = SystemPanel(editor, system_controls.ATMOSPHERE_CONTROLS)
        layout.addWidget(self.panel.widget)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("color: #3f4a5a")
        layout.addWidget(self.summary)
        variable = getattr(editor, "atmosphere_summary_var", None)
        if variable is not None and hasattr(variable, "trace_add"):
            variable.trace_add("write", lambda *_args: self._show_summary())
        row = QHBoxLayout()
        row.addStretch(1)
        self.apply_button = QPushButton("Apply")
        self.apply_plot_button = QPushButton("Apply + Atmos")
        self.close_button = QPushButton("Close")
        self.apply_button.clicked.connect(lambda _checked=False: self.apply(show_plot=False))
        self.apply_plot_button.clicked.connect(lambda _checked=False: self.apply(show_plot=True))
        self.close_button.clicked.connect(lambda _checked=False: self.close())
        for button in (self.apply_button, self.apply_plot_button, self.close_button):
            button.setAutoDefault(False)          # Return commits the field being typed, no more
            row.addWidget(button)
        layout.addLayout(row)
        self.editor._update_atmosphere_summary()
        self._show_summary()

    def _show_summary(self) -> None:
        variable = getattr(self.editor, "atmosphere_summary_var", None)
        try:
            self.summary.setText(str(variable.get()) if variable is not None else "")
        except Exception:
            self.summary.setText("")

    def apply(self, *, show_plot: bool) -> None:
        # a field still being typed in has not been committed: leaving it commits it
        self.apply_button.setFocus()
        self.editor.apply_atmosphere_settings(show_plot=show_plot)
