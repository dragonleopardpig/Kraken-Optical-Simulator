"""The 3D viewport: VTK inside a Qt widget (docs/design_qt_migration.md phase 2).

Proved by `bugs/spike_0854_qt_viewport.py`. Three things here are not optional -- each one, left
out, produces a viewport that looks broken in a different way; the spike's docstring has the full
account.
"""
from __future__ import annotations

# Before ANY render window is created: without it VTK's object factory has no OpenGL override and
# vtkRenderWindow() hands back the ABSTRACT base class -- Render() then draws nothing silently,
# pixel readback returns no pixels, and a window-to-image capture segfaults.
import vtkmodules.vtkInteractionStyle  # noqa: F401  (registers the interactor styles)
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401  (registers the OpenGL factory overrides)

#: label -> RGB, for the imported STEP bodies a scene may carry.
BODY_COLOURS = {
    "optical": (0.29, 0.64, 0.71),
    "lens": (0.25, 0.45, 0.55),
    "camera": (0.45, 0.45, 0.50),
    "led": (0.85, 0.65, 0.20),
}
BODY_OPACITY = 0.45


class SceneViewport:
    """A `QVTKRenderWindowInteractor` and the renderer behind it.

    Build it only once `parent` is inside a SHOWN window: the widget hands VTK its window id in
    its constructor, and Qt destroys and recreates a native window when a widget is reparented, so
    a viewport built too early leaves VTK drawing into a dead handle -- blank, and deaf to the
    mouse.
    """

    def __init__(self, parent) -> None:
        from PySide6.QtWidgets import QApplication

        from KrakenOS.UI.qt.app import require_viewport_platform

        # Before the widget exists: on the wrong platform VTK is handed a window id the X server
        # does not know, and Xlib aborts the whole process instead of raising (bugs/0856).
        application = QApplication.instance()
        if application is not None:
            require_viewport_platform(application.platformName())

        from vtkmodules.qt import QVTKRenderWindowInteractor as _module
        from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
        from vtkmodules.vtkRenderingCore import vtkRenderer

        self.widget = _module.QVTKRenderWindowInteractor(parent)
        self.render_window = self.widget.GetRenderWindow()
        if not self.render_window.IsA("vtkOpenGLRenderWindow"):
            raise RuntimeError(
                "VTK returned a non-OpenGL render window "
                f"({self.render_window.GetClassName()}): the OpenGL factory overrides were not "
                "registered before it was created")
        self.renderer = vtkRenderer()
        self.renderer.SetBackground(1.0, 1.0, 1.0)
        self.render_window.AddRenderer(self.renderer)
        self.widget.Initialize()
        # vtkInteractorStyleSwitch, the default, starts in JOYSTICK mode: the camera moves on
        # timer ticks rather than on move deltas, so a press-drag-release does nothing at all.
        self.widget.GetRenderWindow().GetInteractor().SetInteractorStyle(
            vtkInteractorStyleTrackballCamera())
        self.body_actors: dict[str, object] = {}

    @property
    def interactor_style(self):
        return self.render_window.GetInteractor().GetInteractorStyle()

    def clear(self) -> None:
        for actor in self.body_actors.values():
            self.renderer.RemoveActor(actor)
        self.body_actors.clear()

    def show_editor_scene(self, editor) -> list[tuple[str, int]]:
        """Draw the editor's imported STEP bodies. Returns [(label, point count), ...]."""
        from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper

        self.clear()
        drawn: list[tuple[str, int]] = []
        for label, colour in BODY_COLOURS.items():
            try:
                mesh = editor._transformed_imported_step_mesh_for_label(label)
            except Exception:
                continue  # a scene need not carry every body
            if mesh is None:
                continue
            mapper = vtkDataSetMapper()
            mapper.SetInputData(mesh)
            # These meshes carry `kraken_step_selection_face_index` as their ACTIVE cell scalars
            # (face picking reads it). Left on, the mapper colours by that array through the
            # default lookup table and ignores the colour below -- the body comes out invisible.
            mapper.ScalarVisibilityOff()
            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(*colour)
            actor.GetProperty().SetOpacity(BODY_OPACITY)
            self.renderer.AddActor(actor)
            self.body_actors[label] = actor
            drawn.append((label, int(mesh.GetNumberOfPoints())))
        self.reset_camera()
        return drawn

    def reset_camera(self) -> None:
        self.renderer.ResetCamera()

    def render(self) -> None:
        self.render_window.Render()
