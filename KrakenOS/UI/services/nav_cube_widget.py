"""A genuine FreeCAD-style navigation cube for the Open 3D inspector (VTK).

VTK ships ``vtkCameraOrientationWidget``, but on this build it renders as three
axis balls -- not a labelled, clickable cube. This module builds a real one:

* an annotated cube (FRONT/BACK/TOP/BOTTOM/LEFT/RIGHT) parked in the upper-right
  corner on its own renderer, whose camera MIRRORS the main scene camera so the
  cube turns in lock-step as the user orbits;
* a transparent unit pick-cube co-located with it, so a left-click anywhere on the
  cube surface resolves to a LOCAL hit point that
  :mod:`KrakenOS.UI.services.nav_cube_orientation` classifies into one of the 26
  face/edge/corner orientations -- clicking a face is byte-identical to the matching
  ``+yz``/``-yz``/... preset button, edges/corners give the oblique "angled" views;
* six discrete-step arrow handles on a second, screen-fixed corner renderer: two
  roll arrows (roll the view +-45 deg about the sight line) and four orbit arrows
  (azimuth/elevation the view +-45 deg) -- the "discrete rotation step for rotation
  and Angled view" the plain cube lacked.

All camera MATH lives in the VTK-free ``nav_cube_orientation`` module (unit-tested
headless); this file is the thin VTK shell around it and is verified by eyeball.

The host wires three callbacks:

* ``apply_orientation(offset_unit, view_up)`` -- snap the main camera to a picked
  face/edge/corner (host reframes + renders);
* ``apply_step(kind)`` -- one of ``roll_ccw``/``roll_cw``/``az_left``/``az_right``/
  ``el_up``/``el_down`` from an arrow;
* ``get_main_camera()`` -- the live main ``vtkCamera`` to mirror each render.

Construction is fully defensive: any VTK failure leaves ``available`` False and the
inspector simply runs without the cube (as the old widget did on failure).
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from KrakenOS.UI.services.nav_cube_orientation import (
    FACE_LABELS,
    classify_pick,
    orientation_pose,
)

# Arrow-handle identifiers handed back to the host's apply_step callback.
STEP_KINDS = ("roll_ccw", "roll_cw", "az_left", "az_right", "el_up", "el_down")

_CUBE_LAYER = 3
_ARROW_LAYER = 4
_CUBE_VIEWPORT = (0.80, 0.78, 0.995, 0.995)
# World half-extent that must stay visible in the arrow renderer (the arrows reach
# ~1.28 from centre); the camera parallel scale is fitted to this each render so the
# arrows never clip whatever the corner viewport's pixel aspect turns out to be.
_ARROW_FIT_HALF = 1.42


def _import_vtk():
    """Return the VTK classes we need, or None if any is unavailable."""
    try:
        from vtkmodules.vtkRenderingAnnotation import vtkAnnotatedCubeActor
        from vtkmodules.vtkFiltersSources import vtkCubeSource
        from vtkmodules.vtkCommonDataModel import vtkPolyData
        from vtkmodules.vtkCommonCore import vtkPoints
        from vtkmodules.vtkRenderingCore import (
            vtkActor,
            vtkCellPicker,
            vtkPolyDataMapper,
            vtkRenderer,
        )
    except Exception:
        return None
    return {
        "AnnotatedCube": vtkAnnotatedCubeActor,
        "CubeSource": vtkCubeSource,
        "PolyData": vtkPolyData,
        "Points": vtkPoints,
        "Actor": vtkActor,
        "CellPicker": vtkCellPicker,
        "PolyDataMapper": vtkPolyDataMapper,
        "Renderer": vtkRenderer,
    }


class NavigationCube:
    """Custom labelled navigation cube + discrete-step arrows in the 3D corner."""

    def __init__(
        self,
        render_window,
        main_renderer,
        interactor,
        *,
        apply_orientation: Callable[[tuple, tuple], None],
        apply_step: Callable[[str], None],
        get_main_camera: Callable[[], object],
    ) -> None:
        self.available = False
        self._render_window = render_window
        self._main_renderer = main_renderer
        self._interactor = interactor
        self._apply_orientation = apply_orientation
        self._apply_step = apply_step
        self._get_main_camera = get_main_camera

        self._vtk = None
        self._cube_renderer = None
        self._arrow_renderer = None
        self._pick_cube_actor = None
        self._cube_picker = None
        self._arrow_picker = None
        # Strong refs to the arrow actors (VTK frees the Python wrapper otherwise,
        # so id()/is comparisons break); paired with their step kind.
        self._arrow_actors: list[tuple[object, str]] = []
        self._start_observer = None

        vtk = _import_vtk()
        if vtk is None or render_window is None or main_renderer is None:
            return
        self._vtk = vtk
        try:
            self._build_cube_renderer()
            self._build_arrow_renderer()
            self._sync_start_observer()
            self.available = True
        except Exception:
            self._teardown()
            self.available = False

    # ------------------------------------------------------------------ build --

    def _build_cube_renderer(self) -> None:
        vtk = self._vtk
        renderer = vtk["Renderer"]()
        renderer.SetLayer(_CUBE_LAYER)
        renderer.InteractiveOff()
        renderer.SetViewport(*_CUBE_VIEWPORT)
        renderer.SetPreserveColorBuffer(True)   # composite over the scene, no black box
        renderer.SetPreserveDepthBuffer(False)  # clear depth so the cube draws in front

        annotated = vtk["AnnotatedCube"]()
        # CAD face words (see FACE_LABELS): +Z FRONT, +Y TOP, +X RIGHT and opposites.
        annotated.SetXPlusFaceText(FACE_LABELS[(1, 0, 0)])
        annotated.SetXMinusFaceText(FACE_LABELS[(-1, 0, 0)])
        annotated.SetYPlusFaceText(FACE_LABELS[(0, 1, 0)])
        annotated.SetYMinusFaceText(FACE_LABELS[(0, -1, 0)])
        annotated.SetZPlusFaceText(FACE_LABELS[(0, 0, 1)])
        annotated.SetZMinusFaceText(FACE_LABELS[(0, 0, -1)])
        try:
            annotated.SetFaceTextScale(0.42)
            # The annotated cube supplies the LETTERS only: hide its own cube faces
            # (opacity 0) so the solid pick-cube below shows through, leaving the
            # text edges floating on each face. (Its own cube is fully transparent,
            # which vtkCellPicker skips -- hence the separate opaque pick target.)
            annotated.GetCubeProperty().SetOpacity(0.0)
            annotated.GetTextEdgesProperty().SetColor(0.12, 0.18, 0.32)
            annotated.GetTextEdgesProperty().SetLineWidth(1.6)
        except Exception:
            pass
        self._annotated_cube = annotated

        # Solid, exactly-unit cube ([-0.5, 0.5]^3): it is BOTH the visible cube face
        # colour AND the pick target. A click on it maps the world hit straight to a
        # cube-LOCAL point (cube axes == world axes here). It must be OPAQUE -- a
        # fully transparent actor is invisible to vtkCellPicker.
        source = vtk["CubeSource"]()
        source.SetXLength(1.0)
        source.SetYLength(1.0)
        source.SetZLength(1.0)
        source.SetCenter(0.0, 0.0, 0.0)
        source.Update()
        mapper = vtk["PolyDataMapper"]()
        mapper.SetInputConnection(source.GetOutputPort())
        pick_cube = vtk["Actor"]()
        pick_cube.SetMapper(mapper)
        pick_cube.GetProperty().SetColor(0.86, 0.90, 0.97)
        pick_cube.GetProperty().SetOpacity(1.0)
        pick_cube.GetProperty().SetAmbient(0.45)
        pick_cube.GetProperty().SetDiffuse(0.65)
        pick_cube.PickableOn()
        renderer.AddActor(pick_cube)
        self._pick_cube_actor = pick_cube
        # Letters drawn AFTER (on top of) the solid faces.
        renderer.AddActor(annotated)

        picker = vtk["CellPicker"]()
        picker.SetTolerance(0.001)
        picker.InitializePickList()
        picker.AddPickList(pick_cube)
        picker.PickFromListOn()
        self._cube_picker = picker

        self._add_renderer(renderer, _CUBE_LAYER)
        self._cube_renderer = renderer

    def _build_arrow_renderer(self) -> None:
        vtk = self._vtk
        renderer = vtk["Renderer"]()
        renderer.SetLayer(_ARROW_LAYER)
        renderer.InteractiveOff()
        renderer.SetViewport(*_CUBE_VIEWPORT)
        renderer.SetPreserveColorBuffer(True)
        renderer.SetPreserveDepthBuffer(False)

        picker = vtk["CellPicker"]()
        picker.SetTolerance(0.002)
        picker.InitializePickList()
        picker.PickFromListOn()

        orbit_color = (0.20, 0.55, 0.95)
        roll_color = (0.95, 0.60, 0.15)
        # Orbit arrows: filled triangles pointing off the four screen edges. The corner
        # viewport is narrow (aspect < 1), so the horizontal reach (half-width ~1.4 at
        # SetParallelScale 1.55 below) is tighter than the vertical -- keep tips within
        # ~1.28 of centre so nothing clips.
        r = 1.00
        tip = 0.28
        s = 0.16
        specs = {
            "az_right": ([(r, s), (r, -s), (r + tip, 0.0)], orbit_color),
            "az_left": ([(-r, s), (-r, -s), (-r - tip, 0.0)], orbit_color),
            "el_up": ([(-s, r), (s, r), (0.0, r + tip)], orbit_color),
            "el_down": ([(-s, -r), (s, -r), (0.0, -r - tip)], orbit_color),
            # Roll arrows: small triangles at the top corners, tangent hint by colour.
            "roll_ccw": ([(-0.86, 0.86), (-1.10, 0.98), (-0.80, 1.12)], roll_color),
            "roll_cw": ([(0.86, 0.86), (1.10, 0.98), (0.80, 1.12)], roll_color),
        }
        for kind, (pts, color) in specs.items():
            actor = self._triangle_actor(pts, color)
            renderer.AddActor(actor)
            picker.AddPickList(actor)
            self._arrow_actors.append((actor, kind))

        # Fixed, screen-aligned camera: arrows never rotate with the scene. The
        # parallel scale is (re)fitted to the live viewport aspect each render by
        # _sync_arrow_camera so the horizontal arrows never clip on a narrow corner.
        self._arrow_picker = picker
        self._add_renderer(renderer, _ARROW_LAYER)
        self._arrow_renderer = renderer
        self._sync_arrow_camera()

    def _triangle_actor(self, pts_xy, color):
        vtk = self._vtk
        points = vtk["Points"]()
        for (x, y) in pts_xy:
            points.InsertNextPoint(float(x), float(y), 0.0)
        poly = vtk["PolyData"]()
        poly.SetPoints(points)
        poly.Allocate(1)
        poly.InsertNextCell(5, 3, [0, 1, 2])  # VTK_TRIANGLE == 5
        mapper = vtk["PolyDataMapper"]()
        mapper.SetInputData(poly)
        actor = vtk["Actor"]()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().LightingOff()
        actor.PickableOn()
        return actor

    def _add_renderer(self, renderer, layer: int) -> None:
        window = self._render_window
        try:
            if window.GetNumberOfLayers() <= layer:
                window.SetNumberOfLayers(layer + 1)
        except Exception:
            pass
        window.AddRenderer(renderer)

    def _sync_start_observer(self) -> None:
        # Re-mirror the main camera every time the window renders, so an orbit,
        # a preset button, or a cube snap all keep the cube in lock-step.
        self._start_observer = self._render_window.AddObserver("StartEvent", self._on_render_start)

    # ------------------------------------------------------------------ sync ---

    def _on_render_start(self, *_args) -> None:
        try:
            self.sync()
        except Exception:
            pass
        try:
            self._sync_arrow_camera()
        except Exception:
            pass

    def _sync_arrow_camera(self) -> None:
        """Frame the screen-fixed arrows so they fit the corner viewport at ANY
        pixel aspect. The camera parallel scale sets the world half-HEIGHT; the
        half-width is that times the viewport pixel aspect, so on a tall/narrow
        corner (aspect < 1) the scale is grown by 1/aspect to keep the horizontal
        azimuth arrows on-screen (the miss that hid az_left/az_right on a portrait
        3D pane)."""
        renderer = self._arrow_renderer
        if renderer is None:
            return
        camera = renderer.GetActiveCamera()
        camera.ParallelProjectionOn()
        camera.SetFocalPoint(0.0, 0.0, 0.0)
        camera.SetPosition(0.0, 0.0, 10.0)
        camera.SetViewUp(0.0, 1.0, 0.0)
        try:
            vw, vh = renderer.GetSize()
            aspect = (float(vw) / float(vh)) if vh else 1.0
        except Exception:
            aspect = 1.0
        scale = _ARROW_FIT_HALF / min(1.0, aspect) if aspect > 0 else _ARROW_FIT_HALF
        camera.SetParallelScale(float(scale))

    def sync(self) -> None:
        """Point the cube renderer's camera the same way as the main camera."""
        if self._cube_renderer is None:
            return
        main = self._get_main_camera()
        if main is None:
            return
        pos = np.asarray(main.GetPosition(), dtype=float)
        foc = np.asarray(main.GetFocalPoint(), dtype=float)
        up = np.asarray(main.GetViewUp(), dtype=float)
        view = foc - pos
        norm = float(np.linalg.norm(view))
        if norm <= 1e-9:
            return
        view = view / norm
        cube_cam = self._cube_renderer.GetActiveCamera()
        cube_cam.ParallelProjectionOn()
        cube_cam.SetFocalPoint(0.0, 0.0, 0.0)
        cube_cam.SetPosition(*(-view * 10.0).tolist())
        cube_cam.SetViewUp(*up.tolist())
        cube_cam.SetParallelScale(0.92)  # frame the unit cube with a little margin
        try:
            self._cube_renderer.ResetCameraClippingRange()
        except Exception:
            pass

    # ------------------------------------------------------------------ pick ---

    def _point_in_viewport(self, x: int, y: int) -> bool:
        try:
            w, h = self._render_window.GetSize()
        except Exception:
            return False
        if w <= 0 or h <= 0:
            return False
        x0, y0, x1, y1 = _CUBE_VIEWPORT
        return (x0 * w) <= x <= (x1 * w) and (y0 * h) <= y <= (y1 * h)

    def _arrow_kind_for(self, picked) -> "str | None":
        """Map a picked prop back to its step kind by VTK object identity."""
        if picked is None:
            return None
        try:
            picked_addr = picked.GetAddressAsString("")
        except Exception:
            picked_addr = None
        for actor, kind in self._arrow_actors:
            if actor is picked:
                return kind
            try:
                if picked_addr is not None and actor.GetAddressAsString("") == picked_addr:
                    return kind
            except Exception:
                continue
        return None

    def handle_left_press(self, x: int, y: int) -> bool:
        """Give the cube first refusal on a left-click. Returns True if consumed."""
        if not self.available or not self._point_in_viewport(int(x), int(y)):
            return False
        # Arrows sit on top -- test them first.
        if self._arrow_renderer is not None and self._arrow_picker is not None:
            try:
                self._arrow_picker.Pick(int(x), int(y), 0, self._arrow_renderer)
                actor = self._arrow_picker.GetActor()
            except Exception:
                actor = None
            kind = self._arrow_kind_for(actor)
            if kind is not None:
                self._apply_step(kind)
                return True
        # Then the cube surface -> face/edge/corner orientation.
        if self._cube_renderer is not None and self._cube_picker is not None:
            try:
                hit = self._cube_picker.Pick(int(x), int(y), 0, self._cube_renderer)
                actor = self._cube_picker.GetActor()
            except Exception:
                hit, actor = 0, None
            if hit and actor is self._pick_cube_actor:
                local = np.asarray(self._cube_picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
                sign = classify_pick(local)
                if sign is not None:
                    offset_unit, view_up = orientation_pose(sign)
                    self._apply_orientation(offset_unit, view_up)
                    return True
        return False

    # -------------------------------------------------------------- teardown ---

    def _teardown(self) -> None:
        window = self._render_window
        if window is not None and self._start_observer is not None:
            try:
                window.RemoveObserver(self._start_observer)
            except Exception:
                pass
            self._start_observer = None
        for renderer in (self._arrow_renderer, self._cube_renderer):
            if renderer is None or window is None:
                continue
            try:
                window.RemoveRenderer(renderer)
            except Exception:
                pass
        self._cube_renderer = None
        self._arrow_renderer = None

    def dispose(self) -> None:
        self._teardown()
        self.available = False
