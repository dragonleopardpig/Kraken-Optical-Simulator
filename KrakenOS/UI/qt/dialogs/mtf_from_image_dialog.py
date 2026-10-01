"""Measure MTF from a captured image, in the Qt shell (docs/design_qt_migration.md phase 5g, bugs/0938).

A view over `mtf_from_image_session.MtfFromImageSession` -- the session the Tk dialog renders too.
The image is drawn at the session's display scale; a left drag draws a box, handed to the session
in display coordinates (it stores image pixels). The plot is the session's own `draw` on a Qt
matplotlib canvas; a click on it enlarges it, as in Tk.
"""
from __future__ import annotations

from KrakenOS.UI import mtf_from_image_session as mfs


def _widget_base():
    from PySide6.QtWidgets import QWidget

    return QWidget


def _dialog_base():
    from PySide6.QtWidgets import QDialog

    return QDialog


class ImageBoxWidget(_widget_base()):
    """The image at the session's display scale, its ROI boxes, and the box being dragged."""

    def __init__(self, session, on_box) -> None:
        from PySide6.QtCore import Qt

        super().__init__()
        self.session = session
        self.on_box = on_box
        self.pixmap = None
        self._pixmap_path = None
        self._start = None
        self._end = None
        self.setFixedSize(*mfs.MAX_DISPLAY)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def refresh(self) -> None:
        from PySide6.QtGui import QImage, QPixmap

        session = self.session
        if session.path is None:
            self.pixmap, self._pixmap_path = None, None
        elif self._pixmap_path != session.path:
            rgb = session.display_rgb()
            data = rgb.tobytes("raw", "RGB")
            image = QImage(data, rgb.size[0], rgb.size[1], 3 * rgb.size[0], QImage.Format.Format_RGB888).copy()
            self.pixmap, self._pixmap_path = QPixmap.fromImage(image), session.path
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt's name)
        from PySide6.QtCore import QRectF, Qt
        from PySide6.QtGui import QColor, QFont, QPainter, QPen

        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#20242b"))
        if self.pixmap is not None:
            painter.drawPixmap(0, 0, self.pixmap)
        pen = QPen(QColor("#22d3ee"), 2)
        painter.setPen(pen)
        font = QFont(painter.font())
        font.setPointSize(8)
        painter.setFont(font)
        for index in range(len(self.session.rois)):
            x0, y0, x1, y1 = self.session.roi_display_box(index)
            painter.drawRect(QRectF(x0, y0, x1 - x0, y1 - y0))
            painter.drawText(int(x0 + 3), int(y0 + 12), self.session.roi_caption(index))
        if self._start is not None and self._end is not None:
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            (x0, y0), (x1, y1) = self._start, self._end
            painter.drawRect(QRectF(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)))
        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        from PySide6.QtCore import Qt

        if event.button() == Qt.MouseButton.LeftButton and self.session.gray is not None:
            point = event.position()
            self._start = self._end = (point.x(), point.y())
            self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._start is not None:
            point = event.position()
            self._end = (point.x(), point.y())
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        from PySide6.QtCore import Qt

        if event.button() != Qt.MouseButton.LeftButton or self._start is None:
            return
        point = event.position()
        (x0, y0), self._start, self._end = self._start, None, None
        self.update()
        self.on_box(x0, y0, point.x(), point.y())


class MtfFromImageDialog(_dialog_base()):
    def __init__(self, session, *, parent=None, host=None) -> None:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
        from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QComboBox, QFormLayout,
                                       QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton,
                                       QTableWidget, QVBoxLayout, QWidget)

        super().__init__(parent)
        self.session = session
        self.host = host
        self._syncing = False
        self.setWindowTitle(mfs.TITLE)
        self.setModal(False)
        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        self.import_button = QPushButton("Import Image...")
        self.import_button.clicked.connect(self.import_image)
        bar.addWidget(self.import_button)
        bar.addWidget(QLabel("   Target:"))
        self.mode_buttons = {}
        group = self.mode_group = QButtonGroup(self)
        for text, value in (("Slanted edge", "edge"), ("USAF three-bar", "usaf")):
            radio = self.mode_buttons[value] = QRadioButton(text)
            group.addButton(radio)
            radio.clicked.connect(lambda _c=False, v=value: session.set_mode(v))
            bar.addWidget(radio)
        bar.addStretch(1)
        layout.addLayout(bar)

        fields = self.usaf_fields = QWidget()
        row = QHBoxLayout(fields)
        row.setContentsMargins(0, 0, 0, 0)
        self.field_widgets = {}
        for label, key, width in (("Next ROI →  Group", "group", 40), ("Element", "element", 40),
                                  ("Bars", "orientation", 100), ("Cycles", "cycles", 40)):
            row.addWidget(QLabel(label))
            if key == "orientation":
                widget = QComboBox()
                widget.addItems(list(mfs.ORIENTATIONS))
            else:
                widget = QLineEdit()
            widget.setMaximumWidth(width)
            self.field_widgets[key] = widget
            row.addWidget(widget)
        row.addStretch(1)
        layout.addWidget(fields)
        self.instruction = QLabel(session.instruction)
        self.instruction.setWordWrap(True)
        self.instruction.setStyleSheet("color: #1d4ed8")
        layout.addWidget(self.instruction)

        body = QHBoxLayout()
        self.image = ImageBoxWidget(session, self.add_box)
        body.addWidget(self.image)
        right = QVBoxLayout()
        right.addWidget(QLabel("ROIs:"))
        table = self.table = QTableWidget(0, len(mfs.ROI_COLUMNS))
        table.setHorizontalHeaderLabels([title for _c, title, _w in mfs.ROI_COLUMNS])
        for column, (_key, _title, width) in enumerate(mfs.ROI_COLUMNS):
            table.setColumnWidth(column, width)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setMaximumHeight(180)
        right.addWidget(table)
        roi_buttons = QHBoxLayout()
        self.delete_button = QPushButton("Delete ROI")
        self.delete_button.clicked.connect(self.delete_selected)
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(lambda: session.clear_rois())
        roi_buttons.addWidget(self.delete_button)
        roi_buttons.addWidget(self.clear_button)
        roi_buttons.addStretch(1)
        right.addLayout(roi_buttons)
        calib = QGroupBox("Calibration (optional)")
        form = QFormLayout(calib)
        self.calibration_widgets = {}
        for key, label in mfs.CALIBRATION_FIELDS:
            widget = self.calibration_widgets[key] = QLineEdit()
            form.addRow(label, widget)
        self.space = self.calibration_widgets["space"] = QComboBox()
        form.addRow("Frequency axis", self.space)
        right.addWidget(calib)
        actions = QHBoxLayout()
        self.buttons = {}
        for text, slot in (("Compute MTF", lambda: self._act(session.compute)), ("Save CSV...", self.save_csv),
                           ("Close", self.close)):
            button = self.buttons[text] = QPushButton(text)
            button.clicked.connect(slot)
            actions.addWidget(button)
        actions.addStretch(1)
        right.addLayout(actions)
        self.status = QLabel(session.status)
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: #475569")
        right.addWidget(self.status)
        self.figure = Figure(figsize=(3.6, 2.6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.plot_canvas = FigureCanvasQTAgg(self.figure)
        self.plot_canvas.setMinimumSize(360, 260)
        from PySide6.QtCore import Qt

        # bugs/0415: click the curve to enlarge it (a high-res PNG in the system image viewer)
        self.plot_canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.plot_canvas.mpl_connect("button_press_event", lambda _e: session.enlarge(self.figure))
        right.addWidget(self.plot_canvas, 1)
        hint = QLabel(mfs.ENLARGE_HINT)
        hint.setStyleSheet("color: #64748b; font-size: 8pt")
        right.addWidget(hint)
        holder = QWidget()
        holder.setLayout(right)
        holder.setMinimumWidth(380)
        body.addWidget(holder, 1)
        layout.addLayout(body, 1)
        session.listeners.append(self.sync)
        self.finished.connect(self._forget)
        session.set_mode(session.mode)

    # ---- widgets <-> session -----------------------------------------------------------------------
    def _push(self) -> None:
        for key, widget in self.field_widgets.items():
            self.session.fields[key] = widget.currentText() if key == "orientation" else widget.text()
        for key, widget in self.calibration_widgets.items():
            self.session.calibration[key] = widget.currentText() if key == "space" else widget.text()

    def _act(self, action, *args):
        self._push()
        return action(*args)

    def sync(self) -> None:
        from PySide6.QtWidgets import QTableWidgetItem

        session = self.session
        self._syncing = True
        try:
            self.mode_buttons[session.mode].setChecked(True)
            self.usaf_fields.setEnabled(session.mode == "usaf")
            for key, widget in self.field_widgets.items():
                value = str(session.fields[key])
                if key == "orientation":
                    widget.setCurrentText(value)
                elif widget.text() != value:
                    widget.setText(value)
            spaces = list(session.frequency_spaces())
            if [self.space.itemText(i) for i in range(self.space.count())] != spaces:
                self.space.clear()
                self.space.addItems(spaces)
            for key, widget in self.calibration_widgets.items():
                value = str(session.calibration[key])
                if key == "space":
                    widget.setCurrentText(value)
                elif widget.text() != value:
                    widget.setText(value)
            self.instruction.setText(session.instruction)
            rows = session.roi_rows()
            self.table.setRowCount(len(rows))
            for r, cells in enumerate(rows):
                for c, text in enumerate(cells):
                    self.table.setItem(r, c, QTableWidgetItem(text))
            self.image.refresh()
            session.draw(self.ax)
            try:
                self.figure.tight_layout()
            except Exception:
                pass
            self.plot_canvas.draw_idle()
            self.status.setText(session.status)
        finally:
            self._syncing = False

    # ---- actions -----------------------------------------------------------------------------------
    def import_image(self) -> None:
        path = self.host.askopenfilename(title="Import captured MTF-target image", filetypes=mfs.IMAGE_FILETYPES) \
            if self.host is not None else ""
        if path:
            self._act(self.session.load_image, path)

    def add_box(self, x0, y0, x1, y1) -> None:
        self._act(self.session.add_roi_display, x0, y0, x1, y1)

    def delete_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if rows:
            self.session.delete_roi(rows[0])

    def save_csv(self) -> None:
        if self.session.result is None:
            self.session.save_csv("")
            return
        path = self.host.asksaveasfilename(title="Save MTF CSV", defaultextension=".csv",
                                           initialfile=self.session.default_csv_name(),
                                           filetypes=[("CSV", "*.csv")]) if self.host is not None else ""
        if path:
            self.session.save_csv(path)

    def _forget(self, _result=None) -> None:
        if self.sync in self.session.listeners:
            self.session.listeners.remove(self.sync)
        try:
            self.figure.clf()
        except Exception:
            pass
