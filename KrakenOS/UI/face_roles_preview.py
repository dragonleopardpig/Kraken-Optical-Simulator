"""The face-roles editor's 3D preview (docs/design_qt_migration.md phase 5g, bugs/0933).

VTK itself is toolkit-neutral, so the preview scene, the face pick and the fixed-speed drag
rotation live here, fed by a :class:`~KrakenOS.UI.face_roles_session.FaceRolesSession`. A view
supplies the renderer and render window (a Tk ``vtkTkRenderWindowInteractor`` or a Qt
``QVTKRenderWindowInteractor``) and forwards left-button press / motion / release in VTK display
coordinates (origin bottom-left).
"""
from __future__ import annotations

from typing import Any

import numpy as np

DRAG_THRESHOLD_PX = 4
DEGREES_PER_PIXEL = 0.22


class FaceRolesPreview:
    def __init__(self, session: Any, renderer: Any, render_window: Any) -> None:
        le = self.le = session.le
        self.session = session
        self.renderer = renderer
        self.render_window = render_window
        self.actor_map: dict[int, int] = {}
        self.picker = None
        if le.vtkCellPicker is not None:
            self.picker = le.vtkCellPicker()
            self.picker.SetTolerance(0.0008)
        self._face_meshes: dict[int, object] = {}
        self._face_mesh_generation = session.mesh_cache_generation
        # Cache the raw body mesh + its feature edges (both depend only on the path, constant for
        # the dialog's lifetime). The render ran on launch, every face selection AND every field
        # auto-apply, and each call re-read the STL from disk + re-extracted feature edges -- the
        # slow Face Editor the user reported. The rigid pose transform is cheap and stays per
        # render, so a pose change still re-places the body.
        self._base: tuple | None = None
        self._drag: dict[str, object] = {'active': False, 'start': None, 'last': None, 'moved': False}
        renderer.SetBackground(1.0, 1.0, 1.0)
        try:
            points = self._transformed(self._base_body_raw_and_edges()[0]).points
            span = np.max(np.asarray(points, dtype=float), axis=0) - np.min(np.asarray(points, dtype=float), axis=0)
            session.mesh_span = max(float(np.max(span)), 1.0)
        except Exception:
            session.mesh_span = 1.0

    # ---- meshes --------------------------------------------------------------------------------
    def _transformed(self, mesh):
        try:
            mesh = mesh.copy(deep=True)
            pts = np.asarray(mesh.points, dtype=float)
        except Exception:
            return mesh
        if pts.ndim != 2 or pts.shape[0] == 0 or pts.shape[1] < 3:
            return mesh
        mesh.points = self.session.to_world(pts)
        return mesh

    def _base_body_raw_and_edges(self) -> tuple:
        """Raw (untransformed) body surface mesh + its feature edges, read from disk and
        edge-extracted ONCE and cached -- both depend only on the path."""
        if self._base is not None:
            return self._base
        le = self.le
        body = edges = None
        if le.pv is not None:
            try:
                body = le.pv.read(self.session.path).extract_surface(algorithm='dataset_surface').copy(deep=True)
            except Exception as exc:
                self.session.editor.append_debug(f'CAD/STL face preview base mesh read failed: {exc}')
                body = None
        if body is not None and int(getattr(body, 'n_points', 0)) > 0:
            try:
                edges = body.extract_feature_edges(feature_angle=15, boundary_edges=True, feature_edges=True,
                                                   manifold_edges=False)
            except Exception:
                edges = None
        self._base = (body, edges)
        return self._base

    def _mesh_from_triangles(self, triangles):
        if self.le.pv is None:
            return None
        tris = np.asarray(triangles, dtype=float)
        if tris.ndim != 3 or tris.shape[0] == 0 or tris.shape[1:] != (3, 3):
            return None
        faces = np.hstack([np.full((tris.shape[0], 1), 3, dtype=np.int64),
                           np.arange(tris.shape[0] * 3, dtype=np.int64).reshape((-1, 3))]).ravel()
        try:
            return self.le.pv.PolyData(tris.reshape((-1, 3)), faces)
        except Exception:
            return None

    def face_mesh(self, index: int):
        if self._face_mesh_generation != self.session.mesh_cache_generation:
            self._face_meshes.clear()
            self._face_mesh_generation = self.session.mesh_cache_generation
        if index in self._face_meshes:
            return self._face_meshes[index]
        if not 0 <= index < len(self.session.records):
            return None
        try:
            local = self._mesh_from_triangles(self.session.face_source_triangles(index))
            mesh = self._transformed(local) if local is not None else None
        except Exception as exc:
            self.session.editor.append_debug(f'CAD/STL face preview mesh failed for F{index + 1}: {exc}')
            mesh = None
        self._face_meshes[index] = mesh
        return mesh

    def _offset_face_mesh(self, mesh, index: int, selected: bool):
        """Lift a face a hair off the body along its normal so it is never z-fought."""
        if mesh is None:
            return None
        try:
            mesh = mesh.copy(deep=True)
            normal = self.session.face_normal_world(index)
            if normal is None:
                return mesh
            span = self.session.mesh_span
            mesh.points = np.asarray(mesh.points, dtype=float) + normal * max(span * (0.0015 if selected else 0.0007), 0.01)
            return mesh
        except Exception:
            return mesh

    # ---- actors --------------------------------------------------------------------------------
    def _add_actor(self, mesh, *, color, opacity: float, pick_index: int | None = None, line_width: float = 1.0,
                   wireframe: bool = False):
        le = self.le
        if le.vtkActor is None or le.vtkDataSetMapper is None or mesh is None:
            return None
        try:
            if int(getattr(mesh, 'n_points', 0)) <= 0:
                return None
        except Exception:
            return None
        mapper = le.vtkDataSetMapper()
        mapper.SetInputData(mesh)
        actor = le.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(*color)
        prop.SetOpacity(float(opacity))
        prop.SetLineWidth(float(line_width))
        if wireframe:
            prop.SetRepresentationToWireframe()
        else:
            prop.SetInterpolationToFlat()
            prop.SetAmbient(0.45)
            prop.SetDiffuse(0.55)
        if pick_index is None:
            actor.PickableOff()
        else:
            actor.PickableOn()
            key = le.Kraken3DInspector._actor_key(actor)
            if key is not None:
                self.actor_map[key] = int(pick_index)
        self.renderer.AddActor(actor)
        return actor

    def _add_selected_normal_arrow(self, index: int) -> None:
        le, session = self.le, self.session
        if le.pv is None:
            return
        try:
            markers = le.optical_solid_face_world_markers(session.preview_row(single_face=session.records[index]),
                                                          session.z_station, assigned_only=False)
            if not markers:
                return
            marker = markers[0]
            length = le.Kraken3DInspector._face_role_marker_scale(marker, session.mesh_span)
            start = np.asarray(marker.centroid, dtype=float)
            normal = np.asarray(marker.normal, dtype=float)
            self._add_actor(le.pv.Arrow(start=tuple(start[:3]), direction=tuple(normal[:3]), scale=length),
                            color=(1.0, 0.48, 0.02), opacity=0.98, line_width=2.0)
        except Exception as exc:
            session.editor.append_debug(f'CAD/STL selected face normal preview failed: {exc}')

    @staticmethod
    def _anchor(face: dict) -> np.ndarray:
        return np.asarray(face.get('anchor_world', face.get('centroid_world', (np.nan, np.nan, np.nan))),
                          dtype=float).reshape(-1)[:3]

    def _add_selected_input_anchor_marker(self, index: int) -> None:
        le, session = self.le, self.session
        if le.pv is None:
            return
        try:
            face = session.world_face(index)
            if face is None:
                return
            anchor = self._anchor(face)
            if anchor.size < 3 or not np.all(np.isfinite(anchor)):
                return
            self._add_actor(le.pv.Sphere(radius=max(session.mesh_span * 0.012, 0.22), center=tuple(anchor[:3])),
                            color=(0.84, 0.12, 0.08), opacity=0.98)
        except Exception as exc:
            session.editor.append_debug(f'CAD/STL input-anchor preview failed: {exc}')

    def _add_selected_input_uv_gizmo(self, index: int) -> None:
        le, session = self.le, self.session
        if le.pv is None:
            return
        try:
            face = session.world_face(index)
            if face is None:
                return
            anchor = self._anchor(face)
            u_axis = np.asarray(face.get('u_axis_world', (np.nan,) * 3), dtype=float).reshape(-1)[:3]
            v_axis = np.asarray(face.get('v_axis_world', (np.nan,) * 3), dtype=float).reshape(-1)[:3]
            if not (anchor.size >= 3 and u_axis.size >= 3 and v_axis.size >= 3 and np.all(np.isfinite(anchor))
                    and np.all(np.isfinite(u_axis)) and np.all(np.isfinite(v_axis))):
                return
            u_norm, v_norm = float(np.linalg.norm(u_axis)), float(np.linalg.norm(v_axis))
            if u_norm <= 1e-12 or v_norm <= 1e-12:
                return
            scale = max(session.mesh_span * 0.1, 1.2)
            self._add_actor(le.pv.Arrow(start=tuple(anchor), direction=tuple(u_axis / u_norm), scale=scale),
                            color=(0.86, 0.18, 0.18), opacity=0.96, line_width=2.0)
            self._add_actor(le.pv.Arrow(start=tuple(anchor), direction=tuple(v_axis / v_norm), scale=scale),
                            color=(0.15, 0.62, 0.24), opacity=0.96, line_width=2.0)
        except Exception as exc:
            session.editor.append_debug(f'CAD/STL input U/V gizmo preview failed: {exc}')

    def _add_virtual_plane_overlays(self) -> None:
        le, session = self.le, self.session
        if le.pv is None or not session.virtual_planes:
            return
        try:
            for marker in le.optical_solid_virtual_plane_world_markers(session.preview_row(), session.z_station,
                                                                      assigned_only=True):
                center = np.asarray(marker.centroid, dtype=float)
                normal = np.asarray(marker.normal, dtype=float)
                norm = float(np.linalg.norm(normal[:3]))
                if norm <= 1e-12 or not np.isfinite(norm):
                    continue
                normal = normal[:3] / norm
                size = max(float(marker.aperture_mm), max(session.mesh_span * 0.18, 1.0))
                plane = le.pv.Plane(center=tuple(center[:3]), direction=tuple(normal), i_size=size, j_size=size,
                                    i_resolution=1, j_resolution=1)
                self._add_actor(plane, color=marker.color, opacity=0.16)
                try:
                    edges = plane.extract_feature_edges(boundary_edges=True, feature_edges=False, manifold_edges=False)
                    self._add_actor(edges, color=marker.color, opacity=0.98, line_width=2.0)
                except Exception:
                    pass
                self._add_actor(le.pv.Arrow(start=tuple(center[:3]), direction=tuple(normal), scale=max(size * 0.45, 1.0)),
                                color=marker.color, opacity=0.96)
        except Exception as exc:
            session.editor.append_debug(f'CAD/STL virtual plane preview failed: {exc}')

    # ---- the scene -------------------------------------------------------------------------------
    def render(self, *, reset_camera: bool = False) -> int:
        """Redraw the body, every face (the selected one orange and lifted), the per-group edges
        and the selected face's normal / input anchor / U-V gizmo; returns the faces drawn."""
        session = self.session
        self.renderer.RemoveAllViewProps()
        self.actor_map.clear()
        raw_body, raw_edges = self._base_body_raw_and_edges()
        if raw_body is None or int(getattr(raw_body, 'n_points', 0)) <= 0:
            session.render_status('3D preview unavailable: mesh has no points.')
            return 0
        self._add_actor(self._transformed(raw_body), color=(0.12, 0.78, 0.86), opacity=0.18)
        if raw_edges is not None and int(getattr(raw_edges, 'n_points', 0)) > 0:
            try:
                self._add_actor(self._transformed(raw_edges), color=(0.05, 0.18, 0.24), opacity=1.0, line_width=1.2)
            except Exception:
                pass
        selected_index = session.selected_index()
        visible_faces = 0
        offset_meshes: dict[int, object] = {}
        for index in range(len(session.records)):
            mesh = self._offset_face_mesh(self.face_mesh(index), index, selected=index == selected_index)
            if mesh is None:
                continue
            visible_faces += 1
            colour, assigned = session.face_colour(index, selected_index)
            opacity = 0.3 if index == selected_index else 0.08 if assigned else 0.035
            self._add_actor(mesh, color=colour, opacity=opacity, pick_index=index)
            offset_meshes[index] = mesh
        # Feature edges drawn per logical GROUP, not per face: a curved surface the importer split
        # into several faces (a lens rim = several co-axial cylinder faces, or the planar
        # clusterer's ~160 micro candidates) merges into one clean edge instead of a fragmented
        # wireframe, and non-selected groups are drawn faint so the selected face stays the
        # unambiguous highlight (bugs/0013). feature_angle=18 drops a curved surface's interior
        # facets, keeping its real edges.
        edge_groups: dict[object, list[int]] = {}
        for index in offset_meshes:
            gid = session.group_index_by_record_index.get(index, -1)
            edge_groups.setdefault(gid if gid >= 0 else ('solo', index), []).append(index)
        for members in edge_groups.values():
            is_selected_group = selected_index is not None and selected_index in members
            merged = None
            for index in members:
                piece = offset_meshes.get(index)
                if piece is not None:
                    merged = piece.copy(deep=True) if merged is None else merged.merge(piece)
            if merged is None:
                continue
            try:
                welded = merged.clean(tolerance=1.0e-4) if hasattr(merged, 'clean') else merged
                edges = welded.extract_feature_edges(feature_angle=18, boundary_edges=True, feature_edges=True,
                                                     manifold_edges=False)
            except Exception:
                continue
            rep_colour, _assigned = session.face_colour(members[0], None)
            self._add_actor(edges, color=(1.0, 0.28, 0.0) if is_selected_group else rep_colour,
                            opacity=1.0 if is_selected_group else 0.22, line_width=4.0 if is_selected_group else 1.1)
        if selected_index is not None:
            self._add_selected_normal_arrow(selected_index)
            self._add_selected_input_anchor_marker(selected_index)
            self._add_selected_input_uv_gizmo(selected_index)
        self._add_virtual_plane_overlays()
        if reset_camera:
            self.renderer.ResetCamera()
        try:
            self.renderer.ResetCameraClippingRange()
            self.render_window.Render()
        except Exception:
            pass
        session.render_status(session.preview_status_text(visible_faces))
        return visible_faces

    # ---- input -------------------------------------------------------------------------------------
    def pick(self, x: float, y: float) -> tuple:
        """(face index or None, world point) under VTK display point (x, y)."""
        if self.picker is None:
            return None, None
        try:
            self.picker.Pick(float(x), float(y), 0.0, self.renderer)
            key = self.le.Kraken3DInspector._actor_key(self.picker.GetActor())
            index = self.actor_map.get(key) if key is not None else None
            point = np.asarray(self.picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
        except Exception:
            return None, np.asarray((np.nan, np.nan, np.nan), dtype=float)
        return index, point

    def click(self, x: float, y: float) -> None:
        index, point = self.pick(x, y)
        self.session.click_face(index, point, source='3D pick')

    def rotate(self, dx: float, dy: float) -> None:
        """Match Open 3D: a fixed-speed orbit about the focal point, no VTK acceleration."""
        camera = self.renderer.GetActiveCamera()
        if camera is None:
            return
        try:
            dx_f, dy_f = float(dx), float(dy)
        except Exception:
            return
        if abs(dx_f) < 1e-12 and abs(dy_f) < 1e-12:
            return
        try:
            focal = tuple(float(value) for value in camera.GetFocalPoint())
            camera.SetFocalPoint(*focal)
            camera.Azimuth(-dx_f * DEGREES_PER_PIXEL)
            camera.Elevation(dy_f * DEGREES_PER_PIXEL)
            camera.SetFocalPoint(*focal)
            camera.OrthogonalizeViewUp()
            self.renderer.ResetCameraClippingRange()
            self.render_window.Render()
        except Exception as exc:
            self.session.editor.append_debug(f'CAD/STL face preview camera rotate failed: {exc}')

    # A left click (under the drag threshold) picks; a left drag rotates. Positions are VTK display
    # coordinates (y up); the Tk bindings took dy in widget coordinates (y down), so the rotation
    # negates it to turn the camera the same way for the same hand movement.
    def press(self, x: float, y: float) -> None:
        self._drag = {'active': True, 'start': (x, y), 'last': (x, y), 'moved': False}

    def motion(self, x: float, y: float) -> None:
        drag = self._drag
        if not drag['active']:
            return
        start, last = drag['start'] or (x, y), drag['last'] or (x, y)
        if (x - start[0]) ** 2 + (y - start[1]) ** 2 >= DRAG_THRESHOLD_PX ** 2:
            drag['moved'] = True
        if drag['moved']:
            self.rotate(x - last[0], -(y - last[1]))
        drag['last'] = (x, y)

    def release(self, x: float, y: float) -> None:
        should_pick = bool(self._drag['active']) and not bool(self._drag['moved'])
        self._drag = {'active': False, 'start': None, 'last': None, 'moved': False}
        if should_pick:
            self.click(x, y)
