"""The 2D layout plot in Qt (docs/design_qt_migration.md phase 6, bugs/0893).

The 2D plot has never been view code: the model draws into `editor.ax` and calls
`editor.canvas.draw_idle()`. What was toolkit-specific was the CANVAS -- and two things that had
leaked into `services/layout_plot_interaction.py`: a Tk `<Button-1>` binding (whose event needed
the widget height to flip y) and `canvas.get_tk_widget().configure(cursor=...)`.

0893 removed both. The click is a matplotlib `button_press_event`, which already reports display
coordinates in the frame `get_window_extent` uses, and the cursor goes through
`editor.set_plot_cursor(name)`, which each shell implements. So this module is only: make a
canvas, hand the editor its figure and axes, connect the same three events.
"""
from __future__ import annotations

#: the model asks for Tk cursor names, because that is what it has always said
CURSORS = {"": "ArrowCursor", "hand2": "PointingHandCursor", "watch": "WaitCursor"}


class LayoutPlot2D:
    """The editor's own figure, on a Qt canvas."""

    def __init__(self, editor, parent=None) -> None:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure

        self.editor = editor
        self.figure = Figure(figsize=(7, 5), dpi=100)
        # `refresh_plot` REPLACES the editor's axes on every draw (it re-lays out the figure for
        # the analysis panes), so this is only the first one -- never cache it as the live axes,
        # read `self.axes` below instead. The FIGURE is reused, which is why the canvas can be.
        first_axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setParent(parent)

        # the editor draws into these -- the same attribute names the Tk shell sets
        editor.figure = self.figure
        editor.ax = first_axes
        editor.canvas = self.canvas
        editor.set_plot_cursor = self.set_cursor

        self.canvas.mpl_connect("motion_notify_event", editor._on_plot_canvas_motion)
        self.canvas.mpl_connect("figure_leave_event", editor._on_plot_canvas_leave)
        self.canvas.mpl_connect("button_press_event", editor._on_plot_widget_click)

    @property
    def widget(self):
        return self.canvas

    @property
    def axes(self):
        """Whatever the editor is drawing into RIGHT NOW -- never a cached reference."""
        return self.editor.ax

    def set_cursor(self, cursor: str) -> None:
        """The Qt half of the plot-cursor seam: map the model's Tk name onto a Qt shape."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QCursor

        shape = getattr(Qt.CursorShape, CURSORS.get(str(cursor), "ArrowCursor"))
        try:
            self.canvas.setCursor(QCursor(shape))
        except Exception:
            pass

    def draw(self) -> None:
        self.canvas.draw_idle()
