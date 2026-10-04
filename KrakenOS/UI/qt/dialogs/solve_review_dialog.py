"""A solve's result for review, in the Qt shell (bugs/0955).

A view of `solve_reviews.SolveReview`, the description the Tk window shows too: what was solved,
the numbers, the rule that produced them, Apply / Cancel. Modal: the solve command waits for the
answer before it writes anything.
"""
from __future__ import annotations


def _dialog_base():
    from PySide6.QtWidgets import QDialog

    return QDialog


class SolveReviewDialog(_dialog_base()):
    def __init__(self, review, *, parent=None) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

        super().__init__(parent)
        self.review = review
        self.setWindowTitle(review.title)
        self.setModal(True)
        layout = QVBoxLayout(self)
        self.intro = QLabel(review.intro)
        self.intro.setWordWrap(True)
        layout.addWidget(self.intro)
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        #: (label, value) as shown, for a guard to read
        self.rows: list = []
        for index, (label, value) in enumerate(review.rows):
            name = QLabel(str(label))
            number = QLabel(str(value))
            font = number.font()
            font.setBold(True)
            number.setFont(font)
            number.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(name, index, 0)
            grid.addWidget(number, index, 1, Qt.AlignmentFlag.AlignRight)
            self.rows.append((name, number))
        layout.addLayout(grid)
        self.rule = QLabel(review.rule)
        self.rule.setWordWrap(True)
        self.rule.setStyleSheet("color: #4b5563")
        layout.addWidget(self.rule)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.apply_button = QPushButton(review.apply_label)
        self.cancel_button = QPushButton(review.cancel_label)
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(lambda _checked=False: self.accept())
        self.cancel_button.clicked.connect(lambda _checked=False: self.reject())
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)

    def shown_rows(self) -> list:
        return [(name.text(), number.text()) for name, number in self.rows]
