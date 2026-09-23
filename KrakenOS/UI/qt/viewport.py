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
        self.ray_actors: list[object] = []

    @property
    def interactor_style(self):
        return self.render_window.GetInteractor().GetInteractorStyle()

    def clear(self) -> None:
        for actor in list(self.body_actors.values()) + self.element_actors + self.ray_actors:
            self.renderer.RemoveActor(actor)
        self.body_actors.clear()
        self.element_actors.clear()
        self.ray_actors.clear()

    def show_editor_scene(self, editor) -> dict:
        """Draw the scene: the model's optical elements, its traced rays, and the STEP bodies.

        Returns ``{"elements": [...], "rays": int, "bodies": [...], "error": str | None}``.
        """
        self.clear()
        errors: list[str] = []
        system = rays = bundle = None
        try:
            # ONE build for the whole scene: the elements and the rays must come from the same
            # traced system, or the drawn light would belong to a different geometry than the
            # drawn glass.
            system, rays, bundle = editor._build_preview_system_rays_bundle(
                sampling_mode=PREVIEW_SAMPLING, update_state=False)
        except Exception as exc:
            errors.append(f"display geometry: {type(exc).__name__}: {exc}")

        elements: list[tuple[int, str, int]] = []
        ray_count = 0
        if system is not None:
            try:
                elements = self._draw_optical_elements(editor, system, bundle)
            except Exception as exc:
                errors.append(f"optical elements: {type(exc).__name__}: {exc}")
            try:
                ray_count = self._draw_rays(editor, rays, bundle)
            except Exception as exc:
                errors.append(f"rays: {type(exc).__name__}: {exc}")

        bodies = self._draw_step_bodies(editor)
        self.reset_camera()
        return {"elements": elements, "rays": ray_count, "bodies": bodies,
                "error": "; ".join(errors) or None}

    def _draw_optical_elements(self, editor, system, bundle) -> list[tuple[int, str, int]]:
        """The mirrors, prisms, lenses, stop and panels -- from the model's own display geometry.

        `_scene_surface_meshes` is what the Tk 3D view draws, built from the system the trace
        runs on, and every record carries the colour and opacity that view uses. Nothing is
        re-derived here: a viewport that invented its own geometry would drift from the physics
        the moment either side changed.
        """
        from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper

        items = editor._scene_surface_meshes(system, bundle, include_reference_surfaces=False)
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
        return drawn

    def _draw_rays(self, editor, rays, bundle) -> int:
        """The traced light, through the model's own display pipeline.

        Every step here is the one the Tk 3D view takes, and for a reason: the points are BOUNDED
        for display (`_bounded_3d_ray_points_for_display`) so a ray that misses the detector
        visibly misses instead of stopping short or teleporting, the vertex inset keeps segment
        ends off the glass, and the per-ray style carries the terminal status -- colour is
        physics, not decoration.
        """
        from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

        from KrakenOS.UI.scene_projector import scene_display_center_radius

        if rays is None or bundle is None:
            return 0
        centre, radius = scene_display_center_radius(bundle)
        paths = editor._scene_ray_path_by_index(bundle)
        inset = editor._ray_vertex_display_inset(radius)
        drawn = 0
        for ray_index, colour, points, terminal_status in editor._iter_3d_scene_ray_records(
                rays, bundle):
            path = paths.get(int(ray_index))
            display_points, _bounded = editor._bounded_3d_ray_points_for_display(
                points, centre, radius,
                terminal_status=terminal_status,
                terminal_target=editor._missed_detector_target_for_path(bundle, path),
                terminal_direction=editor._terminal_display_direction_for_path(path))
            line = editor._ray_segment_mesh_for_3d_display(display_points, vertex_inset=inset)
            if line is None or int(getattr(line, "n_points", 0)) < 2:
                continue
            style = editor._ray_terminal_3d_style(colour, terminal_status)
            mapper = vtkPolyDataMapper()
            mapper.SetInputData(line)
            mapper.ScalarVisibilityOff()
            actor = vtkActor()
            actor.SetMapper(mapper)
            prop = actor.GetProperty()
            prop.SetColor(*_rgb(style["line_color"]))
            prop.SetOpacity(float(style["line_opacity"]))
            prop.SetLineWidth(float(style["line_width"]))
            prop.SetLighting(False)  # a ray is light, not a lit surface
            self.renderer.AddActor(actor)
            self.ray_actors.append(actor)
            drawn += 1
        return drawn

    def set_rays_visible(self, visible: bool) -> None:
        for actor in self.ray_actors:
            actor.SetVisibility(bool(visible))

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
