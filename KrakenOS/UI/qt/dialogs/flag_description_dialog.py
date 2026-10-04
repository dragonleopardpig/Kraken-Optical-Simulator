"""The bug-flag description prompt in the Qt shell (bugs/0950).

A view over `services.flag_description.FlagDescription` -- the session the Tk popup uses too. Not
modal: a carry or a drag in the 3D view stays live while it is open. Save (or Ctrl+Return) keeps the
flag with the typed text, Keep screenshot keeps it without, Discard deletes it; closing the window
any other way saves typed text and discards an empty box.
"""
from __future__ import annotations


def _dialog_base():
    from PySide6.QtWidgets import QDialog

    return QDialog


class FlagDescriptionDialog(_dialog_base()):
    def __init__(self, session, *, parent=None) -> None:
        from PySide6.QtGui import QKeySequence, QShortcut
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout

        super().__init__(parent)
        self.session = session
        #: how the prompt ended -- "save", "keep", "discard" or "dismiss"; None while it is open
        self.outcome: "str | None" = None
        self.setWindowTitle(session.title)
        self.setModal(False)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(session.prompt))
        self.text = QPlainTextEdit()
        self.text.setMinimumSize(480, 80)
        layout.addWidget(self.text, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        self.discard_button = QPushButton("Discard")
        self.keep_button = QPushButton("Keep screenshot")
        self.save_button = QPushButton("Save")
        self.save_button.setDefault(True)
        for button, how in ((self.discard_button, "discard"), (self.keep_button, "keep"), (self.save_button, "save")):
            # no button takes Return: it must make a new line in the description, as in the Tk box
            button.setAutoDefault(False)
            button.clicked.connect(lambda _checked=False, h=how: self.finish(h))
            row.addWidget(button)
        layout.addLayout(row)
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(lambda: self.finish("save"))
        self.text.setFocus()

    def finish(self, how: str) -> None:
        """End the prompt: tell the session what was chosen -- once -- then close."""
        if self.outcome is None:
            self.outcome = how
            typed = self.text.toPlainText()
            if how == "save":
                self.session.save(typed)
            elif how == "keep":
                self.session.keep()
            elif how == "discard":
                self.session.discard()
            else:
                self.session.dismiss(typed)
        super().reject()          # QDialog's own way out: hides the window and emits `finished`

    def reject(self) -> None:
        # Escape -- and the window's close button, which QDialog routes through reject() too. An
        # override that does not hide the dialog leaves it open: QDialog.closeEvent ignores the
        # close when the dialog is still visible afterwards.
        self.finish("dismiss")
