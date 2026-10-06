"""The Inspection Cell view in the Qt shell (bugs/0967).

A view over `services.inspection_cell_session.InspectionCellSession` -- the session the Tk window
uses too. Not modal: a station opened from here is edited in the main window while this stays up,
and saving it re-composes the cell. The session's buttons, a VTK view, its status line.

The VTK view is built once the dialog is SHOWN (`build_view`): `QVTKRenderWindowInteractor` takes
its window id in its constructor, and Qt gives a widget a new native window when its parent chain
first reaches a shown top-level (the viewport rule of bugs/0855).
"""
from __future__ import annotations


def _dialog_base():
    from PySide6.QtWidgets import QDialog

    return QDialog


class InspectionCellDialog(_dialog_base()):
    def __init__(self, session, *, host, parent=None) -> None:
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

        super().__init__(parent)
        self.session = session
        self.host = host
        self.setWindowTitle(session.title)
        self.setModal(False)
        self.resize(1120, 820)
        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        self.buttons = {}
        for label, method in session.BUTTONS:
            button = QPushButton(label)
            button.setAutoDefault(False)
            button.clicked.connect(lambda _checked=False, m=method: getattr(self.session, m)())
            bar.addWidget(button)
            self.buttons[label] = button
        close = QPushButton("Close")
        close.setAutoDefault(False)
        close.clicked.connect(self.close)
        bar.addWidget(close)
        self.buttons["Close"] = close
        hint = QLabel(session.hint)
        hint.setStyleSheet("color: #475569")
        bar.addSpacing(12)
        bar.addWidget(hint, 1)
        layout.addLayout(bar)

        self.view_host = QWidget()
        self.view_layout = QVBoxLayout(self.view_host)
        self.view_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view_host, 1)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.vtk_widget = None
        self.renderer = None
        self._ended = False
        session.dialog_parent = self
        session.on_status(self.status.setText)

    # ---- the view ------------------------------------------------------------------------------
    def build_view(self) -> None:
        """The VTK view -- call once the dialog is SHOWN. The first composition is left to the
        event loop, so the window is on screen saying "Composing..." while the stations load."""
        import vtkmodules.vtkInteractionStyle  # noqa: F401  (registers the interactor styles)
        import vtkmodules.vtkRenderingOpenGL2  # noqa: F401  (the GL render window factory)
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
        from vtkmodules.vtkRenderingCore import vtkRenderer

        from KrakenOS.UI.services import inspection_cell_session, open3d_scene_look

        if self.vtk_widget is not None:
            return
        widget = self.vtk_widget = QVTKRenderWindowInteractor(self.view_host)
        self.view_layout.addWidget(widget)
        renderer = self.renderer = vtkRenderer()
        open3d_scene_look.apply_backdrop(renderer, True)     # the shell's scenes share one backdrop
        widget.GetRenderWindow().AddRenderer(renderer)
        widget.Initialize()
        interactor = widget.GetRenderWindow().GetInteractor()
        interactor.SetInteractorStyle(vtkInteractorStyleTrackballCamera())
        interactor.AddObserver("LeftButtonPressEvent", self._on_left_button_press)
        self.session.attach(renderer, self.render)
        self.session.set_status(inspection_cell_session.COMPOSING)
        self.host.after(50, self._first_compose)

    def _first_compose(self) -> None:
        if self._ended:
            return
        self.session.compose()
        self.session.start_watching()

    def render(self) -> None:
        if self.vtk_widget is not None and not self._ended:
            self.vtk_widget.GetRenderWindow().Render()

    def _on_left_button_press(self, _obj, _event) -> None:
        interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
        if int(interactor.GetRepeatCount()) < 1:      # a double-click reports repeat 1
            return
        x, y = interactor.GetEventPosition()
        self.session.double_click(x, y)

    # ---- the end -------------------------------------------------------------------------------
    def _end(self) -> None:
        """Close, Escape and the window's own button all end here, once: the session lets go of
        the scene, THEN the render window is finalized (VTK wants it gone before its widget)."""
        if self._ended:
            return
        self._ended = True
        self.session.close()
        if self.vtk_widget is not None:
            try:
                self.vtk_widget.GetRenderWindow().Finalize()
            except Exception:
                pass

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        self._end()
        super().closeEvent(event)

    def reject(self) -> None:
        self._end()
        super().reject()
