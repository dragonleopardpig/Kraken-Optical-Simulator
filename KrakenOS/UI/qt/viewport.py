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

#: how the preview system is built for display -- the same call the Open 3D preview path uses.
PREVIEW_SAMPLING = "world_envelope"

#: label -> RGB, for the imported STEP bodies a scene may carry.
BODY_COLOURS = {
    "optical": (0.29, 0.64, 0.71),
    "lens": (0.25, 0.45, 0.55),
    "camera": (0.45, 0.45, 0.50),
    "led": (0.85, 0.65, 0.20),
}
BODY_OPACITY = 0.45


def _rgb(colour) -> tuple[float, float, float]:
    """A mesh record's colour as VTK wants it. The model gives an RGB triple or a name/hex."""
    try:
        if isinstance(colour, (tuple, list)) and len(colour) >= 3:
            return tuple(float(channel) for channel in colour[:3])
    except (TypeError, ValueError):
        pass
    try:
        import pyvista as pv

        return tuple(float(channel) for channel in pv.Color(colour).float_rgb)
    except Exception:
        return (0.5, 0.5, 0.5)


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
        self.element_actors: list[object] = []

    @property
    def interactor_style(self):
        return self.render_window.GetInteractor().GetInteractorStyle()

    def clear(self) -> None:
        for actor in list(self.body_actors.values()) + self.element_actors:
            self.renderer.RemoveActor(actor)
        self.body_actors.clear()
        self.element_actors.clear()

    def show_editor_scene(self, editor) -> dict:
        """Draw the scene: the model's optical elements AND the imported STEP bodies.

        Returns ``{"elements": [...], "bodies": [...], "error": str | None}``.
        """
        self.clear()
        elements, error = self._draw_optical_elements(editor)
        bodies = self._draw_step_bodies(editor)
        self.reset_camera()
        return {"elements": elements, "bodies": bodies, "error": error}

    def _draw_optical_elements(self, editor) -> tuple[list[tuple[int, str, int]], "str | None"]:
        """The mirrors, prisms, lenses, stop and panels -- from the model's own display geometry.

        `_scene_surface_meshes` is what the Tk 3D view draws, built from the system the trace
        runs on, and every record carries the colour and opacity that view uses. Nothing is
        re-derived here: a viewport that invented its own geometry would drift from the physics
        the moment either side changed.
        """
        from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper

        try:
            system, _rays, bundle = editor._build_preview_system_rays_bundle(
                sampling_mode=PREVIEW_SAMPLING, update_state=False)
            items = editor._scene_surface_meshes(system, bundle, include_reference_surfaces=False)
        except Exception as exc:  # a scene the model cannot build must not take the window with it
            return [], f"{type(exc).__name__}: {exc}"

        drawn: list[tuple[int, str, int]] = []
        for item in items:
            mesh = item.mesh
            if getattr(item, "is_stop", False) and not getattr(item, "is_body", False):
                # the stop is drawn as a RING in the Tk view, not a filled disc
                try:
                    ring = editor._legacy_3d_stop_ring_mesh(mesh, item.row)
                except Exception:
                    ring = None
                if ring is not None and int(getattr(ring, "n_points", 0)) > 0:
                    mesh = ring
            if mesh is None or int(getattr(mesh, "n_points", 0)) == 0:
                continue
            mapper = vtkDataSetMapper()
            mapper.SetInputData(mesh)
            mapper.ScalarVisibilityOff()
            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(*_rgb(item.color))
            actor.GetProperty().SetOpacity(float(item.opacity))
            self.renderer.AddActor(actor)
            self.element_actors.append(actor)
            drawn.append((int(item.row_index), str(getattr(item.row, "name", "")),
                          int(mesh.GetNumberOfPoints())))
        return drawn, None

    def _draw_step_bodies(self, editor) -> list[tuple[str, int]]:
        """The imported STEP hardware: the camera, the lens barrel, the stage, the LED."""
        from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper

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
        return drawn

    def reset_camera(self) -> None:
        self.renderer.ResetCamera()

    def render(self) -> None:
        self.render_window.Render()
