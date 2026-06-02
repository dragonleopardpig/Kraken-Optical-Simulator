"""2D layout CAD and projected-polyline display helpers.

This mixin owns the file-backed CAD mesh loading, external camera/lens
mechanical overlays, and projected row outline helpers used by the Tk layout
editor.  Keeping this display boundary outside ``layout_editor.py`` makes the
main window class smaller without changing trace or scene state ownership.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from KrakenOS.UI.camera_database import CAMERA_NONE_LABEL, camera_record
from KrakenOS.UI.layout_plot_controller import distance_to_polyline, thin_lens_glyph_polyline
from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_runtime_transform_override
from KrakenOS.UI.services.cad_step_export import (
    _convex_hull_2d,
    _profile_from_section_points,
    _rotation_matrix_xyz,
)
from KrakenOS.UI.services.optical_solid_geometry import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
    OPTICAL_SOLID_FACE_ROLE_DEFAULT,
    OPTICAL_SOLID_FACE_SIDE_DEFAULT,
    _legacy_role_from_optical_solid_face_function,
    _normalize_optical_solid_face_function,
    _normalize_optical_solid_face_side,
    _point3_tuple,
    _read_stl_triangle_vertices,
    _rotation_matrix_from_kraken_tilts,
    _unit_vector_tuple,
    convex_hull_2d,
    normalize_optical_solid_face_metadata,
    optical_solid_face_world_records,
)
from KrakenOS.UI.services.open3d_timing import open3d_timing_event, open3d_timing_span
from KrakenOS.UI.services.step_analytic_geometry import StepAnalyticDocument, load_step_analytic_document
from KrakenOS.UI.services.step_native_reconstruction import axisymmetric_step_selection_face_records
from KrakenOS.UI.trace_intent import BEAM_SPLITTER_SURFACE

pv = None

EXTERNAL_CAMERA_MODELS = {
    "None": None,
    "SHR461xCX": {
        "label": "SHR461xCX",
        "path": Path.home() / "Pictures" / "3D_CAD_shr461xCX.STEP",
        "kind": "step",
        "outer_solids": (0, 1, 2),
        "align_axis": "z",
        "front_face": "min",
        "rotate_xyz_deg": (0.0, 180.0, 0.0),
        "color": (0.62, 0.66, 0.72),
        "opacity_3d": 0.94,
        "line_color_2d": "#6b7280",
    },
}


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


def _load_3d_backends() -> None:
    global pv
    layout_editor_module = _layout_module()
    layout_editor_module._load_3d_backends()
    pv = layout_editor_module.pv


def _load_display_helpers() -> tuple[object | None, object | None, object | None]:
    return _layout_module()._load_display_helpers()


def _external_camera_spec(name: str) -> dict[str, object] | None:
    spec = EXTERNAL_CAMERA_MODELS.get(name)
    return dict(spec) if isinstance(spec, dict) else None


def _cached_cad_mesh_path(path: Path) -> Path:
    return _layout_module()._cached_cad_mesh_path(path)


def _cached_analytic_cad_mesh_path(path: Path, *, largest_component: bool = False) -> Path:
    base_path = _cached_cad_mesh_path(path)
    suffix = ".analytic_largest.vtp" if largest_component else ".analytic.vtp"
    return base_path.with_name(f"{base_path.stem}{suffix}")


def _cached_step_axis_path(path: Path) -> Path:
    base_path = _cached_cad_mesh_path(path)
    return base_path.with_name(f"{base_path.stem}.axis.json")


def _cached_outer_cad_mesh_path(path: Path, solid_indices: tuple[int, ...]) -> Path:
    return _layout_module()._cached_outer_cad_mesh_path(path, solid_indices)


def _cached_cad_reference_path(path: Path, solid_indices: tuple[int, ...]) -> Path:
    return _layout_module()._cached_cad_reference_path(path, solid_indices)


def _cached_cad_section_path(path: Path, solid_indices: tuple[int, ...]) -> Path:
    return _layout_module()._cached_cad_section_path(path, solid_indices)


def _convert_step_to_stl(source_path: Path, target_path: Path) -> None:
    _layout_module()._convert_step_to_stl(source_path, target_path)


def _extract_step_outer_subset_to_stl(source_path: Path, target_path: Path, solid_indices: tuple[int, ...]) -> None:
    _layout_module()._extract_step_outer_subset_to_stl(source_path, target_path, solid_indices)


def _extract_step_reference(source_path: Path, target_path: Path, solid_indices: tuple[int, ...]) -> dict[str, object]:
    return _layout_module()._extract_step_reference(source_path, target_path, solid_indices)


def _extract_step_section_profile(source_path: Path, target_path: Path, solid_indices: tuple[int, ...]) -> dict[str, object]:
    return _layout_module()._extract_step_section_profile(source_path, target_path, solid_indices)


class LayoutPolylineDisplayMixin:
    def _convex_hull_2d(points: np.ndarray) -> np.ndarray:
        pts = np.asarray(points, dtype=float)
        if pts.ndim != 2 or pts.shape[1] != 2:
            return np.empty((0, 2), dtype=float)
        pts = pts[np.all(np.isfinite(pts), axis=1)]
        if pts.shape[0] <= 2:
            return pts
        pts = np.unique(np.round(pts, decimals=6), axis=0)
        if pts.shape[0] <= 2:
            return pts

        def cross(o, a, b) -> float:
            return float((a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]))

        ordered = sorted((float(x), float(y)) for x, y in pts)
        lower: list[tuple[float, float]] = []
        for p in ordered:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0.0:
                lower.pop()
            lower.append(p)
        upper: list[tuple[float, float]] = []
        for p in reversed(ordered):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0.0:
                upper.pop()
            upper.append(p)
        hull = lower[:-1] + upper[:-1]
        return np.asarray(hull, dtype=float)

    def _clear_layout_selection_overlay(self) -> None:
        for artist in self._layout_selection_artists:
            try:
                artist.remove()
            except Exception:
                pass
        self._layout_selection_artists = []

    def _project_layout_points(self, points: np.ndarray) -> np.ndarray:
        pts = np.asarray(points, dtype=float)
        if pts.ndim != 2 or pts.shape[1] < 3:
            return np.empty((0, 2), dtype=float)
        proj_x, proj_y = self._project_xy(pts[:, 2], pts[:, 1])
        return np.column_stack((proj_x, proj_y))

    def _project_layout_polyline(self, z_values, y_values) -> np.ndarray:
        z_arr = np.asarray(z_values, dtype=float).reshape(-1)
        y_arr = np.asarray(y_values, dtype=float).reshape(-1)
        if z_arr.size == 0 or y_arr.size == 0 or z_arr.size != y_arr.size:
            return np.empty((0, 2), dtype=float)
        mask = np.isfinite(z_arr) & np.isfinite(y_arr)
        if not np.any(mask):
            return np.empty((0, 2), dtype=float)
        proj_x, proj_y = self._project_xy(z_arr[mask], y_arr[mask])
        return np.column_stack((proj_x, proj_y))

    def _current_camera_model(self) -> str:
        camera_model_var = self.__dict__.get("camera_model_var")
        if camera_model_var is None:
            return CAMERA_NONE_LABEL
        name = camera_model_var.get().strip()
        return name if name == CAMERA_NONE_LABEL or camera_record(name) is not None else CAMERA_NONE_LABEL

    def _current_camera_record(self) -> dict[str, object] | None:
        return camera_record(self._current_camera_model())

    def _current_camera_front_to_sensor_mm(self) -> float:
        record = self._current_camera_record()
        if record is None:
            return 0.0
        try:
            value = float(record.get("camera_front_to_sensor_mm", 0.0))
        except Exception:
            return 0.0
        return max(value, 0.0) if np.isfinite(value) else 0.0

    def _current_external_camera_name(self) -> str:
        if not hasattr(self, "external_camera_var"):
            return "None"
        name = self.external_camera_var.get().strip()
        return name if name in EXTERNAL_CAMERA_MODELS else "None"

    def _current_external_camera_spec(self) -> dict[str, object] | None:
        return _external_camera_spec(self._current_external_camera_name())

    def _load_external_camera_mesh(self) -> pv.DataSet | None:
        _load_3d_backends()
        if pv is None:
            raise RuntimeError("PyVista is required for CAD mesh import")
        spec = self._current_external_camera_spec()
        if spec is None:
            return None
        source_path = Path(spec["path"])
        if not source_path.exists():
            raise FileNotFoundError(f"External camera file not found: {source_path}")
        solid_indices = tuple(int(index) for index in spec.get("outer_solids", ()) if isinstance(index, (int, float)))
        cache_key = f"{source_path}|{solid_indices}"
        cached = self._external_cad_mesh_cache.get(cache_key)
        if cached is not None:
            return cached.copy(deep=True)
        mesh_path = source_path
        kind = str(spec.get("kind", "")).lower()
        if kind == "step":
            if solid_indices:
                mesh_path = _cached_outer_cad_mesh_path(source_path, solid_indices)
                if not mesh_path.exists():
                    _extract_step_outer_subset_to_stl(source_path, mesh_path, solid_indices)
            else:
                mesh_path = _cached_cad_mesh_path(source_path)
                if not mesh_path.exists():
                    _convert_step_to_stl(source_path, mesh_path)
        mesh = pv.read(mesh_path)
        try:
            mesh = mesh.extract_surface().copy(deep=True)
        except Exception:
            mesh = mesh.copy(deep=True)
        self._external_cad_mesh_cache[cache_key] = mesh
        return mesh.copy(deep=True)

    def _load_external_camera_reference(self) -> dict[str, object] | None:
        spec = self._current_external_camera_spec()
        if spec is None:
            return None
        source_path = Path(spec["path"])
        if not source_path.exists():
            raise FileNotFoundError(f"External camera file not found: {source_path}")
        solid_indices = tuple(int(index) for index in spec.get("outer_solids", ()) if isinstance(index, (int, float)))
        if str(spec.get("kind", "")).lower() != "step" or not solid_indices:
            return None
        cache_key = f"{source_path}|ref|{solid_indices}"
        cached = self._external_cad_reference_cache.get(cache_key)
        if cached is not None:
            return dict(cached)
        ref_path = _cached_cad_reference_path(source_path, solid_indices)
        if ref_path.exists():
            ref_data = json.loads(ref_path.read_text(encoding="utf-8"))
        else:
            ref_data = _extract_step_reference(source_path, ref_path, solid_indices)
        self._external_cad_reference_cache[cache_key] = dict(ref_data)
        return dict(ref_data)

    def _load_external_camera_section_profile(self) -> dict[str, object] | None:
        spec = self._current_external_camera_spec()
        if spec is None:
            return None
        source_path = Path(spec["path"])
        if not source_path.exists():
            raise FileNotFoundError(f"External camera file not found: {source_path}")
        solid_indices = tuple(int(index) for index in spec.get("outer_solids", ()) if isinstance(index, (int, float)))
        if str(spec.get("kind", "")).lower() != "step" or not solid_indices:
            return None
        cache_key = f"{source_path}|section|{solid_indices}"
        cached = self._external_cad_section_cache.get(cache_key)
        if cached is not None:
            return dict(cached)
        section_path = _cached_cad_section_path(source_path, solid_indices)
        if section_path.exists():
            section_data = json.loads(section_path.read_text(encoding="utf-8"))
        else:
            section_data = _extract_step_section_profile(source_path, section_path, solid_indices)
        self._external_cad_section_cache[cache_key] = dict(section_data)
        return dict(section_data)

    def _current_image_plane_z(self) -> float:
        if not self.rows:
            return 0.0
        z_pos = 0.0
        for row in self.rows[:-1]:
            z_pos += float(row.thickness)
        return z_pos + float(self.rows[-1].desp_z) if self.rows[-1].surface == "Image" else z_pos

    def _row_z_positions(self) -> list[float]:
        z_positions: list[float] = [0.0]
        z_pos = 0.0
        for row in self.rows[:-1]:
            z_pos += float(row.thickness)
            z_positions.append(z_pos)
        while len(z_positions) < len(self.rows):
            z_positions.append(z_pos)
        return z_positions

    def _lens_front_datum_z(self) -> float:
        z_positions = self._row_z_positions()
        for index, row in enumerate(self.rows):
            name = (row.name or "").strip().lower()
            if "front" in name and ("datum" in name or "edge" in name):
                return float(z_positions[index])
        for index, row in enumerate(self.rows):
            if row.surface not in {"Object", "Image", "Aperture"}:
                return float(z_positions[index])
        return 0.0

    @staticmethod
    def _polydata_from_triangle_array(triangles: np.ndarray):
        if pv is None:
            _load_3d_backends()
        if pv is None:
            return None
        triangle_array = np.asarray(triangles, dtype=float)
        if triangle_array.ndim != 3 or triangle_array.shape[1:] != (3, 3) or triangle_array.shape[0] <= 0:
            return None
        points = triangle_array.reshape((-1, 3))
        faces = np.empty((int(triangle_array.shape[0]), 4), dtype=np.int64)
        faces[:, 0] = 3
        faces[:, 1] = np.arange(0, int(points.shape[0]), 3, dtype=np.int64)
        faces[:, 2] = faces[:, 1] + 1
        faces[:, 3] = faces[:, 1] + 2
        return pv.PolyData(points, faces.reshape(-1))

    @staticmethod
    def _triangle_array_from_polydata(mesh) -> tuple[np.ndarray, object | None]:
        if mesh is None:
            return np.empty((0, 3, 3), dtype=float), None
        try:
            faces = np.asarray(getattr(mesh, "faces", ()), dtype=np.int64).reshape((-1, 4))
            if faces.shape[0] > 0 and np.all(faces[:, 0] == 3):
                surface = mesh.copy(deep=True)
            else:
                surface = mesh.extract_surface(algorithm="dataset_surface").triangulate().copy(deep=True)
        except Exception:
            try:
                surface = mesh.triangulate().copy(deep=True)
            except Exception:
                return np.empty((0, 3, 3), dtype=float), None
        try:
            faces = np.asarray(surface.faces, dtype=np.int64).reshape((-1, 4))
            if faces.shape[0] <= 0 or not np.all(faces[:, 0] == 3):
                return np.empty((0, 3, 3), dtype=float), surface
            points = np.asarray(surface.points, dtype=float)
            triangles = points[faces[:, 1:4]]
        except Exception:
            return np.empty((0, 3, 3), dtype=float), surface
        if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or not np.all(np.isfinite(triangles)):
            return np.empty((0, 3, 3), dtype=float), surface
        return np.asarray(triangles, dtype=float), surface

    def _load_step_analytic_document(self, source_path: Path) -> StepAnalyticDocument:
        source_path = Path(source_path).expanduser()
        cache_key = f"step-analytic-document:{source_path.resolve()}"
        cached = self._external_cad_mesh_cache.get(cache_key)
        if isinstance(cached, StepAnalyticDocument):
            return cached
        # Negative-existence cache: the analytic-document loader is the
        # one that took 1.1 seconds per probe on missing files in the
        # live log (it walks pythonocc-core's STEP reader before the
        # exists() check inside step_analytic_geometry). One extra
        # exists() check up front turns that into a syscall.
        try:
            is_missing_cached = self._path_is_missing_cached(str(source_path))
        except Exception:
            is_missing_cached = False
        if is_missing_cached:
            raise FileNotFoundError(f"STEP file not found: {source_path}")
        with open3d_timing_span("load_step_analytic_document", source_path=str(source_path)):
            try:
                document = load_step_analytic_document(source_path)
            except FileNotFoundError:
                try:
                    self._record_missing_path(str(source_path))
                except Exception:
                    pass
                raise
        self._external_cad_mesh_cache[cache_key] = document
        open3d_timing_event(
            "load_step_analytic_document_cached",
            source_path=str(source_path),
            solids=int(document.solid_count),
            source_faces=int(document.source_face_count),
            outer_faces=int(len(document.outer_faces)),
            triangles=int(document.triangles.shape[0]),
            interior_duplicates=int(document.interior_duplicate_count),
        )
        return document

    def _mesh_from_step_analytic_document(self, document: StepAnalyticDocument):
        with open3d_timing_span(
            "build_step_analytic_mesh",
            source_path=str(document.source_path),
            triangles=int(document.triangles.shape[0]),
            outer_faces=int(len(document.outer_faces)),
        ):
            mesh = self._polydata_from_triangle_array(document.triangles)
            if mesh is None:
                return None
            face_index_by_triangle = np.full(int(document.triangles.shape[0]), -1, dtype=np.int32)
            selection_face_index_by_triangle = np.full(int(document.triangles.shape[0]), -1, dtype=np.int32)
            source_face_index_by_triangle = np.full(int(document.triangles.shape[0]), -1, dtype=np.int32)
            solid_index_by_triangle = np.full(int(document.triangles.shape[0]), -1, dtype=np.int32)
            for face_index, face in enumerate(document.outer_faces):
                for value in face.triangle_indices:
                    triangle_index = int(value)
                    if 0 <= triangle_index < int(face_index_by_triangle.size):
                        face_index_by_triangle[triangle_index] = int(face_index)
                        selection_face_index_by_triangle[triangle_index] = int(face_index)
                        source_face_index_by_triangle[triangle_index] = int(face.source_face_index)
                        solid_index_by_triangle[triangle_index] = int(face.solid_index)
            try:
                face_index_by_id = {
                    str(face.face_id): int(face_index)
                    for face_index, face in enumerate(document.outer_faces)
                }
                for grouped in axisymmetric_step_selection_face_records(document):
                    source_ids = [str(value) for value in list(grouped.get("source_face_ids", ())) if str(value)]
                    raw_indices = [face_index_by_id[value] for value in source_ids if value in face_index_by_id]
                    if not raw_indices:
                        continue
                    grouped_index = int(min(raw_indices))
                    for value in list(grouped.get("triangle_indices", ())) or ():
                        triangle_index = int(value)
                        if 0 <= triangle_index < int(selection_face_index_by_triangle.size):
                            selection_face_index_by_triangle[triangle_index] = grouped_index
            except Exception:
                pass
            try:
                mesh.cell_data["kraken_step_selection_face_index"] = selection_face_index_by_triangle
                mesh.cell_data["kraken_step_face_index"] = face_index_by_triangle
                mesh.cell_data["kraken_step_source_face_index"] = source_face_index_by_triangle
                mesh.cell_data["kraken_step_solid_index"] = solid_index_by_triangle
                mesh.field_data["kraken_step_analytic"] = np.asarray([1], dtype=np.int8)
                mesh.field_data["kraken_step_outer_face_count"] = np.asarray([len(document.outer_faces)], dtype=np.int32)
                mesh.field_data["kraken_step_source_face_count"] = np.asarray([document.source_face_count], dtype=np.int32)
            except Exception:
                pass
            return mesh

    def _open3d_step_cache_warmup_active(self) -> bool:
        if bool(getattr(self, "_open3d_step_cache_warmup_pending", False)):
            return True
        process = getattr(self, "_open3d_step_cache_warmup_process", None)
        try:
            return bool(process is not None and process.poll() is None)
        except Exception:
            return False

    def _load_step_mesh(
        self,
        source_path: Path,
        *,
        largest_component: bool = False,
        allow_slow_import: bool = True,
    ):
        source_path = Path(source_path).expanduser()
        # Negative cache: a layout that references a missing STEP file
        # used to get this path probed up to 18 times per refresh (every
        # analytic-fit lookup, every face-metadata pass, every body STL
        # load). The cache short-circuits the second-and-subsequent hits
        # with the same FileNotFoundError so callers see consistent
        # behaviour without paying the syscall.
        try:
            is_missing_cached = self._path_is_missing_cached(str(source_path))
        except Exception:
            is_missing_cached = False
        if is_missing_cached:
            raise FileNotFoundError(f"STEP file not found: {source_path}")
        with open3d_timing_span(
            "load_step_mesh",
            source_path=str(source_path),
            source_size=int(source_path.stat().st_size) if source_path.exists() else None,
            largest_component=bool(largest_component),
        ):
            _load_3d_backends()
            if pv is None:
                raise RuntimeError("PyVista is required for STEP import")
            if not source_path.exists():
                try:
                    self._record_missing_path(str(source_path))
                except Exception:
                    pass
                raise FileNotFoundError(f"STEP file not found: {source_path}")
            cache_prefix = "step-largest" if largest_component else "step"
            cache_key = f"{cache_prefix}:{source_path.resolve()}"
            cached = self._external_cad_mesh_cache.get(cache_key)
            if cached is not None:
                open3d_timing_event(
                    "load_step_mesh_memory_cache_hit",
                    source_path=str(source_path),
                    points=int(getattr(cached, "n_points", 0)),
                    cells=int(getattr(cached, "n_cells", 0)),
                )
                return cached.copy(deep=True)
            if source_path.suffix.lower() in {".step", ".stp"}:
                analytic_cache_path = _cached_analytic_cad_mesh_path(
                    source_path,
                    largest_component=bool(largest_component),
                )
                if analytic_cache_path.exists() and analytic_cache_path.stat().st_size > 0:
                    try:
                        with open3d_timing_span(
                            "read_step_analytic_mesh_cache",
                            source_path=str(source_path),
                            cache_path=str(analytic_cache_path),
                            largest_component=bool(largest_component),
                        ):
                            mesh = pv.read(str(analytic_cache_path)).extract_surface(
                                algorithm="dataset_surface"
                            ).copy(deep=True)
                        if mesh is not None and int(getattr(mesh, "n_points", 0)) > 0:
                            if not self._step_display_mesh_cell_data_valid(mesh):
                                raise RuntimeError("cached analytic STEP mesh has invalid cell-data lengths")
                            self._external_cad_mesh_cache[cache_key] = mesh.copy(deep=True)
                            open3d_timing_event(
                                "load_step_mesh_analytic_disk_cache_hit",
                                source_path=str(source_path),
                                cache_path=str(analytic_cache_path),
                                largest_component=bool(largest_component),
                                points=int(getattr(mesh, "n_points", 0)),
                                cells=int(getattr(mesh, "n_cells", 0)),
                            )
                            return mesh
                    except Exception as exc:
                        try:
                            analytic_cache_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        self.append_debug(
                            f"Analytic STEP display cache ignored for {source_path.name}: {exc}"
                        )
                if not bool(allow_slow_import):
                    open3d_timing_event(
                        "load_step_mesh_slow_import_deferred",
                        source_path=str(source_path),
                        cache_path=str(analytic_cache_path),
                        largest_component=bool(largest_component),
                    )
                    return None
                try:
                    document = self._load_step_analytic_document(source_path)
                    mesh = self._mesh_from_step_analytic_document(document)
                    if mesh is not None and int(getattr(mesh, "n_points", 0)) > 0:
                        with open3d_timing_span(
                            "clean_step_analytic_mesh",
                            source_path=str(source_path),
                            largest_component=bool(largest_component),
                        ):
                            mesh = self._clean_step_display_mesh(mesh)
                        if largest_component:
                            with open3d_timing_span("largest_step_component", source_path=str(source_path)):
                                mesh = self._largest_connected_step_component(mesh)
                        try:
                            _cached_cad_mesh_path(source_path).unlink(missing_ok=True)
                        except Exception:
                            pass
                        try:
                            analytic_cache_path.parent.mkdir(parents=True, exist_ok=True)
                            mesh.save(str(analytic_cache_path))
                        except Exception as exc:
                            self.append_debug(
                                f"Analytic STEP display cache write skipped for {source_path.name}: {exc}"
                            )
                        self._external_cad_mesh_cache[cache_key] = mesh.copy(deep=True)
                        open3d_timing_event(
                            "load_step_mesh_analytic_cached",
                            source_path=str(source_path),
                            largest_component_requested=bool(largest_component),
                            cache_path=str(analytic_cache_path),
                            points=int(getattr(mesh, "n_points", 0)),
                            cells=int(getattr(mesh, "n_cells", 0)),
                            outer_faces=int(len(document.outer_faces)),
                            interior_duplicates=int(document.interior_duplicate_count),
                        )
                        return mesh
                except Exception as exc:
                    self.append_debug(f"Analytic STEP display import fell back to STL for {source_path.name}: {exc}")
            stl_path = _cached_cad_mesh_path(source_path)
            converted = False
            if not stl_path.exists() or stl_path.stat().st_size <= 0:
                if not bool(allow_slow_import):
                    open3d_timing_event(
                        "load_step_mesh_stl_import_deferred",
                        source_path=str(source_path),
                        stl_path=str(stl_path),
                        largest_component=bool(largest_component),
                    )
                    return None
                with open3d_timing_span("convert_step_to_stl", source_path=str(source_path), stl_path=str(stl_path)):
                    _convert_step_to_stl(source_path, stl_path)
                converted = True
            with open3d_timing_span("read_step_stl_mesh", stl_path=str(stl_path), converted=converted):
                mesh = pv.read(stl_path).extract_surface(algorithm="dataset_surface").copy(deep=True)
            if largest_component:
                with open3d_timing_span("largest_step_component", source_path=str(source_path)):
                    mesh = self._largest_connected_step_component(mesh)
            self._external_cad_mesh_cache[cache_key] = mesh.copy(deep=True)
            open3d_timing_event(
                "load_step_mesh_cached",
                source_path=str(source_path),
                stl_path=str(stl_path),
                converted=converted,
                points=int(getattr(mesh, "n_points", 0)),
                cells=int(getattr(mesh, "n_cells", 0)),
            )
            return mesh

    @staticmethod
    def _step_display_mesh_cell_data_valid(mesh) -> bool:
        if mesh is None:
            return False
        try:
            cell_count = int(getattr(mesh, "n_cells", 0))
            cell_data = mesh.GetCellData()
            for index in range(int(cell_data.GetNumberOfArrays())):
                array = cell_data.GetArray(index)
                if array is None:
                    continue
                try:
                    tuples = int(array.GetNumberOfTuples())
                except Exception:
                    return False
                if tuples not in {0, cell_count}:
                    return False
        except Exception:
            return False
        return True

    def _clean_step_display_mesh(self, mesh):
        if mesh is None or int(getattr(mesh, "n_points", 0)) == 0:
            return mesh
        try:
            cleaned = mesh.clean(tolerance=1.0e-9, absolute=True)
            cleaned = cleaned.extract_surface(algorithm="dataset_surface").copy(deep=True)
            cleaned = self._drop_invalid_step_cell_data(cleaned, context="clean")
            if int(getattr(cleaned, "n_points", 0)) > 0 and self._step_display_mesh_cell_data_valid(cleaned):
                return cleaned
        except Exception as exc:
            self.append_debug(f"STEP display mesh clean skipped: {exc}")
        return mesh

    def _drop_invalid_step_cell_data(self, mesh, *, context: str):
        if mesh is None:
            return mesh
        try:
            cell_count = int(getattr(mesh, "n_cells", 0))
            dropped: list[str] = []
            cell_data = mesh.GetCellData()
            removals: list[tuple[int, str]] = []
            for index in range(int(cell_data.GetNumberOfArrays())):
                array = cell_data.GetArray(index)
                if array is None:
                    continue
                name = str(array.GetName() or f"#{index}")
                try:
                    if int(array.GetNumberOfTuples()) in {0, cell_count}:
                        continue
                except Exception:
                    pass
                removals.append((index, name))
            for index, name in reversed(removals):
                try:
                    if not name.startswith("#"):
                        cell_data.RemoveArray(name)
                    else:
                        cell_data.RemoveArray(int(index))
                    dropped.append(str(name))
                except Exception:
                    pass
            if dropped:
                self.append_debug(
                    "STEP display mesh {context} dropped invalid cell-data arrays: {names}".format(
                        context=str(context),
                        names=", ".join(dropped),
                    )
                )
        except Exception:
            pass
        return mesh

    def _largest_connected_step_component(self, mesh):
        if mesh is None or int(getattr(mesh, "n_points", 0)) == 0:
            return mesh
        try:
            connected = mesh.connectivity("all")
            region_ids = np.asarray(connected.cell_data.get("RegionId", []), dtype=int)
            if region_ids.size == 0:
                return mesh
            counts = np.bincount(region_ids)
            if counts.size <= 1:
                return mesh
            largest_region = int(np.argmax(counts))
            part = connected.threshold(
                [largest_region, largest_region],
                scalars="RegionId",
                preference="cell",
            )
            part = part.extract_surface(algorithm="dataset_surface").copy(deep=True)
            part = self._drop_invalid_step_cell_data(part, context="largest-component")
            if int(getattr(part, "n_points", 0)) > 0:
                self.append_debug(
                    f"STEP CAD component filter | kept region {largest_region} "
                    f"({int(counts[largest_region])}/{int(np.sum(counts))} cells)"
                )
                return part
        except Exception as exc:
            self.append_debug(f"STEP CAD component filter skipped: {exc}")
        return mesh

    def _step_primary_cylinder_axis(self, source_path: Path) -> np.ndarray | None:
        source_path = Path(source_path).expanduser()
        cache_key = f"step-axis:{source_path.resolve()}"
        cached = self._external_cad_mesh_cache.get(cache_key)
        if cached is not None:
            return np.asarray(cached, dtype=float).copy()
        axis_cache_path = _cached_step_axis_path(source_path)
        if axis_cache_path.exists() and axis_cache_path.stat().st_size > 0:
            try:
                payload = json.loads(axis_cache_path.read_text(encoding="utf-8"))
                axis = np.asarray(payload.get("axis", ()), dtype=float).reshape(-1)[:3]
                norm = float(np.linalg.norm(axis[:3])) if axis.size >= 3 else 0.0
                if axis.size >= 3 and norm > 1.0e-12 and np.isfinite(norm):
                    axis = axis[:3] / norm
                    self._external_cad_mesh_cache[cache_key] = axis.copy()
                    open3d_timing_event(
                        "load_step_axis_disk_cache_hit",
                        source_path=str(source_path),
                        cache_path=str(axis_cache_path),
                    )
                    return axis.copy()
            except Exception:
                try:
                    axis_cache_path.unlink(missing_ok=True)
                except Exception:
                    pass
        try:
            from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
            from OCC.Core.GeomAbs import GeomAbs_Cylinder
            from OCC.Core.STEPControl import STEPControl_Reader
            from OCC.Core.TopAbs import TopAbs_FACE
            from OCC.Core.TopExp import TopExp_Explorer
        except Exception as exc:
            self.append_debug(f"STEP cylinder-axis extraction unavailable: {exc}")
            return None
        try:
            reader = STEPControl_Reader()
            if reader.ReadFile(str(source_path)) != 1:
                return None
            reader.TransferRoots()
            shape = reader.OneShape()
            explorer = TopExp_Explorer(shape, TopAbs_FACE)
            axes: list[tuple[float, np.ndarray]] = []
            while explorer.More():
                face = explorer.Current()
                surface = BRepAdaptor_Surface(face)
                if surface.GetType() == GeomAbs_Cylinder:
                    cylinder = surface.Cylinder()
                    direction = cylinder.Axis().Direction()
                    vector = np.array([direction.X(), direction.Y(), direction.Z()], dtype=float)
                    norm = float(np.linalg.norm(vector))
                    radius = float(cylinder.Radius())
                    if norm > 1e-12 and np.isfinite(radius) and radius > 1.0:
                        axes.append((radius, vector / norm))
                explorer.Next()
            if not axes:
                return None
            reference = axes[0][1]
            weighted = np.zeros(3, dtype=float)
            for radius, vector in axes:
                if float(np.dot(reference, vector)) < 0.0:
                    vector = -vector
                weighted += max(radius, 1.0) * vector
            norm = float(np.linalg.norm(weighted))
            if norm <= 1e-12:
                return None
            axis = weighted / norm
            self._external_cad_mesh_cache[cache_key] = axis.copy()
            try:
                axis_cache_path.parent.mkdir(parents=True, exist_ok=True)
                axis_cache_path.write_text(
                    json.dumps(
                        {
                            "axis": [float(value) for value in axis[:3]],
                            "source_path": str(source_path),
                            "cylinder_count": int(len(axes)),
                        },
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            except Exception as exc:
                self.append_debug(f"STEP cylinder-axis cache write skipped for {source_path.name}: {exc}")
            self.append_debug(
                "STEP CAD cylinder axis | {name} | axis=({x:.6f},{y:.6f},{z:.6f}) | cylinders={count}".format(
                    name=source_path.name,
                    x=float(axis[0]),
                    y=float(axis[1]),
                    z=float(axis[2]),
                    count=len(axes),
                )
            )
            return axis
        except Exception as exc:
            self.append_debug(f"STEP cylinder-axis extraction failed: {exc}")
            return None

    def _cad_mesh_aligned_to_optical_axis(
        self,
        mesh,
        *,
        source_axis,
        front_face: str,
        target_front_z: float,
        label: str,
        roll_deg: float = 0.0,
        x_rotation_deg: float = 0.0,
        y_rotation_deg: float = 0.0,
        axis_offset_xy: tuple[float, float] | None = None,
        placement_offset_xyz: tuple[float, float, float] | None = None,
    ):
        if mesh is None or int(getattr(mesh, "n_points", 0)) == 0:
            return None
        mesh = mesh.copy(deep=True)
        pts = np.asarray(mesh.points, dtype=float)
        if pts.ndim != 2 or pts.shape[0] == 0 or pts.shape[1] < 3:
            return None
        axis_vector = None
        try:
            vector_candidate = np.asarray(source_axis, dtype=float)
            if vector_candidate.shape == (3,):
                norm = float(np.linalg.norm(vector_candidate))
                if norm > 1e-12:
                    axis_vector = vector_candidate / norm
        except Exception:
            axis_vector = None
        axis_text = "vector" if axis_vector is not None else str(source_axis).strip().lower()
        working_pts = pts
        if axis_vector is not None:
            reference = np.array([0.0, 0.0, 1.0], dtype=float)
            if abs(float(np.dot(reference, axis_vector))) > 0.9:
                reference = np.array([0.0, 1.0, 0.0], dtype=float)
            transverse_u = np.cross(reference, axis_vector)
            transverse_u /= max(float(np.linalg.norm(transverse_u)), 1e-12)
            transverse_v = np.cross(axis_vector, transverse_u)
            transverse_v /= max(float(np.linalg.norm(transverse_v)), 1e-12)
            centered = pts - np.mean(pts, axis=0)
            working_pts = np.column_stack(
                [
                    centered @ transverse_u,
                    centered @ transverse_v,
                    centered @ axis_vector,
                ]
            )
            axis_index = 2
        elif axis_text.startswith("pca"):
            centered = pts - np.mean(pts, axis=0)
            cov = centered.T @ centered / max(int(centered.shape[0]), 1)
            eig_vals, eig_vecs = np.linalg.eigh(cov)
            order = np.argsort(eig_vals)[::-1]
            eig_vecs = eig_vecs[:, order]
            working_pts = centered @ eig_vecs
            try:
                axis_index = int(axis_text.replace("pca", "") or "0")
            except ValueError:
                axis_index = 0
            axis_index = max(0, min(axis_index, 2))
        else:
            axis_index = {"x": 0, "y": 1, "z": 2}.get(axis_text, 2)
        transverse_axes = [index for index in (0, 1, 2) if index != axis_index]
        src_min = np.min(pts, axis=0)
        src_max = np.max(pts, axis=0)
        work_min = np.min(working_pts, axis=0)
        work_max = np.max(working_pts, axis=0)
        transverse_center = 0.5 * (work_min[transverse_axes] + work_max[transverse_axes])
        optical_values = working_pts[:, axis_index]
        face = str(front_face).strip().lower()
        front_value = float(np.min(optical_values) if face == "min" else np.max(optical_values))
        aligned = np.empty_like(pts)
        aligned[:, 0] = working_pts[:, transverse_axes[0]] - float(transverse_center[0])
        aligned[:, 1] = working_pts[:, transverse_axes[1]] - float(transverse_center[1])
        if face == "min":
            aligned[:, 2] = optical_values - front_value
        else:
            aligned[:, 2] = front_value - optical_values
        offset_x = offset_y = 0.0
        if axis_offset_xy is not None:
            try:
                offset_x = float(axis_offset_xy[0])
                offset_y = float(axis_offset_xy[1])
            except Exception:
                offset_x = offset_y = 0.0
            aligned[:, 0] -= offset_x
            aligned[:, 1] -= offset_y
        try:
            x_rotation = float(x_rotation_deg)
        except Exception:
            x_rotation = 0.0
        if abs(x_rotation) > 1e-9:
            angle = np.deg2rad(x_rotation)
            cos_a = float(np.cos(angle))
            sin_a = float(np.sin(angle))
            # X flips should turn the imported component in place, not hinge it
            # around the datum/front edge used for optical placement.
            pivot_y = 0.5 * (float(np.min(aligned[:, 1])) + float(np.max(aligned[:, 1])))
            pivot_z = 0.5 * (float(np.min(aligned[:, 2])) + float(np.max(aligned[:, 2])))
            y_vals = aligned[:, 1].copy() - pivot_y
            z_vals = aligned[:, 2].copy() - pivot_z
            aligned[:, 1] = pivot_y + (cos_a * y_vals) - (sin_a * z_vals)
            aligned[:, 2] = pivot_z + (sin_a * y_vals) + (cos_a * z_vals)
        try:
            y_rotation = float(y_rotation_deg)
        except Exception:
            y_rotation = 0.0
        if abs(y_rotation) > 1e-9:
            angle = np.deg2rad(y_rotation)
            cos_a = float(np.cos(angle))
            sin_a = float(np.sin(angle))
            pivot_x = 0.5 * (float(np.min(aligned[:, 0])) + float(np.max(aligned[:, 0])))
            pivot_z = 0.5 * (float(np.min(aligned[:, 2])) + float(np.max(aligned[:, 2])))
            x_vals = aligned[:, 0].copy() - pivot_x
            z_vals = aligned[:, 2].copy() - pivot_z
            aligned[:, 0] = pivot_x + (cos_a * x_vals) + (sin_a * z_vals)
            aligned[:, 2] = pivot_z + (-sin_a * x_vals) + (cos_a * z_vals)
        try:
            roll = float(roll_deg)
        except Exception:
            roll = 0.0
        if abs(roll) > 1e-9:
            angle = np.deg2rad(roll)
            cos_a = float(np.cos(angle))
            sin_a = float(np.sin(angle))
            x_vals = aligned[:, 0].copy()
            y_vals = aligned[:, 1].copy()
            aligned[:, 0] = (cos_a * x_vals) - (sin_a * y_vals)
            aligned[:, 1] = (sin_a * x_vals) + (cos_a * y_vals)
        aligned[:, 2] += float(target_front_z)
        placement_offset = np.zeros(3, dtype=float)
        if placement_offset_xyz is not None:
            try:
                placement_offset = np.asarray(placement_offset_xyz, dtype=float).reshape(-1)[:3]
                if placement_offset.size < 3 or not np.all(np.isfinite(placement_offset)):
                    placement_offset = np.zeros(3, dtype=float)
            except Exception:
                placement_offset = np.zeros(3, dtype=float)
            aligned[:, :3] += placement_offset[:3]
        mesh.points = aligned
        try:
            axis_label = (
                "vector=({:.6f},{:.6f},{:.6f})".format(*[float(value) for value in axis_vector])
                if axis_vector is not None
                else axis_text
            )
            self.append_debug(
                "STEP CAD transform | {label} | axis={axis} | front={front} | rot_x={rot_x:.1f} | rot_y={rot_y:.1f} | roll_z={roll:.1f} | target_front_z={front_z:.3f} | "
                "axis_offset=({ox:.3f},{oy:.3f}) | placement_offset=({px:.3f},{py:.3f},{pz:.3f}) | raw_span=({sx:.3f},{sy:.3f},{sz:.3f}) | "
                "aligned_bounds=({x0:.3f},{x1:.3f},{y0:.3f},{y1:.3f},{z0:.3f},{z1:.3f})".format(
                    label=label,
                    axis=axis_label,
                    front=face,
                    rot_x=x_rotation,
                    rot_y=y_rotation,
                    roll=roll,
                    front_z=float(target_front_z),
                    ox=float(offset_x),
                    oy=float(offset_y),
                    px=float(placement_offset[0]),
                    py=float(placement_offset[1]),
                    pz=float(placement_offset[2]),
                    sx=float(src_max[0] - src_min[0]),
                    sy=float(src_max[1] - src_min[1]),
                    sz=float(src_max[2] - src_min[2]),
                    x0=float(np.min(aligned[:, 0])),
                    x1=float(np.max(aligned[:, 0])),
                    y0=float(np.min(aligned[:, 1])),
                    y1=float(np.max(aligned[:, 1])),
                    z0=float(np.min(aligned[:, 2])),
                    z1=float(np.max(aligned[:, 2])),
                )
            )
        except Exception:
            pass
        return mesh

    def _heavy_step_display_proxy(self, mesh, *, label: str, max_cells: int = 50000):
        if mesh is None or int(getattr(mesh, "n_points", 0)) == 0:
            return mesh
        try:
            cell_count = int(getattr(mesh, "n_cells", 0))
        except Exception:
            cell_count = 0
        if cell_count <= int(max_cells):
            return mesh
        _load_3d_backends()
        if pv is None:
            return mesh
        try:
            bounds = tuple(float(value) for value in mesh.bounds)
            proxy = pv.Box(bounds=bounds).triangulate()
            proxy.field_data["kraken_step_display_proxy"] = np.asarray([1], dtype=np.int8)
            proxy.field_data["kraken_step_display_proxy_source_cells"] = np.asarray([cell_count], dtype=np.int32)
            self.append_debug(
                f"STEP CAD display proxy | {label} | source_cells={cell_count} | proxy_cells={int(proxy.n_cells)}"
            )
            return proxy
        except Exception as exc:
            self.append_debug(f"STEP CAD display proxy skipped for {label}: {exc}")
            return mesh

    @staticmethod
    def _step_overlay_stat_key(path) -> tuple:
        """Stable identity for a STEP file: resolved path + mtime + size."""
        try:
            resolved = Path(path).expanduser()
            st = resolved.stat()
            return (str(resolved), int(st.st_mtime_ns), int(st.st_size))
        except Exception:
            return (str(path), 0, 0)

    def _display_overlay_rebuild_suppressed(self) -> bool:
        """While a transient analysis sweep is running, heavy display-only
        STEP CAD overlays (camera body, vendor lens housing) are served
        from cache instead of being re-transformed every step."""
        return bool(self.__dict__.get("_suppress_display_step_overlay_rebuild", False))

    @contextmanager
    def _suppress_display_step_overlay_rebuilds(self):
        previous = bool(self.__dict__.get("_suppress_display_step_overlay_rebuild", False))
        self.__dict__["_suppress_display_step_overlay_rebuild"] = True
        try:
            yield
        finally:
            self.__dict__["_suppress_display_step_overlay_rebuild"] = previous

    def _cached_transformed_step_overlay(self, label, signature, builder):
        """Memoize a transformed display STEP overlay mesh.

        The heavy non-optical CAD overlays (e.g. a 113k-cell camera body)
        were re-transformed and re-proxied at every call site -- 3D
        refresh, 2D projection, placement, trace, step-overlay refresh --
        so a single ``Refresh`` or focus diagnostic re-transformed the
        full mesh many times. Cache the transformed result keyed on every
        input that affects it (file identity, pose, design-driven datum),
        so unchanged state is reused and only a genuine change rebuilds.
        ``None`` results are never cached, so an overlay that was not ready
        during STEP-cache warm-up still appears once the cache is warm.
        """
        cache = self.__dict__.get("_transformed_step_overlay_cache")
        if cache is None:
            cache = {}
            self.__dict__["_transformed_step_overlay_cache"] = cache
        entry = cache.get(label)
        if entry is not None:
            cached_signature, cached_mesh = entry
            if cached_signature == signature or self._display_overlay_rebuild_suppressed():
                return cached_mesh
        mesh = builder()
        if mesh is not None:
            cache[label] = (signature, mesh)
        return mesh

    def _transformed_imported_lens_step_mesh(self):
        if self.imported_lens_step_path is None:
            return None
        largest = bool(getattr(self, "lens_step_largest_component_only", True))
        signature = (
            self._step_overlay_stat_key(self.imported_lens_step_path),
            largest,
            round(float(self._lens_front_datum_z()), 6),
            round(float(getattr(self, "lens_step_rotation_z_deg", 0.0)), 6),
            round(float(getattr(self, "lens_step_rotation_x_deg", 0.0)), 6),
            round(float(getattr(self, "lens_step_rotation_y_deg", 0.0)), 6),
            tuple(round(float(v), 6) for v in self._step_axis_offset_xy("lens")),
            tuple(round(float(v), 6) for v in self._step_placement_offset_xyz("lens")),
        )

        def build():
            allow_slow_import = not self._open3d_step_cache_warmup_active()
            mesh = self._load_step_mesh(
                self.imported_lens_step_path,
                largest_component=largest,
                allow_slow_import=allow_slow_import,
            )
            if mesh is None:
                return None
            cylinder_axis = self._step_primary_cylinder_axis(self.imported_lens_step_path)
            return self._cad_mesh_aligned_to_optical_axis(
                mesh,
                source_axis=cylinder_axis if cylinder_axis is not None else "pca0",
                front_face="max",
                target_front_z=self._lens_front_datum_z(),
                label="Lens STEP",
                roll_deg=float(getattr(self, "lens_step_rotation_z_deg", 0.0)),
                x_rotation_deg=float(getattr(self, "lens_step_rotation_x_deg", 0.0)),
                y_rotation_deg=float(getattr(self, "lens_step_rotation_y_deg", 0.0)),
                axis_offset_xy=self._step_axis_offset_xy("lens"),
                placement_offset_xyz=self._step_placement_offset_xyz("lens"),
            )

        return self._cached_transformed_step_overlay("lens", signature, build)

    def _transformed_imported_optical_step_mesh(self):
        if self.imported_optical_step_path is None:
            return None
        signature = (
            self._step_overlay_stat_key(self.imported_optical_step_path),
            round(float(getattr(self, "optical_step_rotation_z_deg", 0.0)), 6),
            round(float(getattr(self, "optical_step_rotation_x_deg", 0.0)), 6),
            round(float(getattr(self, "optical_step_rotation_y_deg", 0.0)), 6),
            tuple(round(float(v), 6) for v in self._step_axis_offset_xy("optical")),
            tuple(round(float(v), 6) for v in self._step_placement_offset_xyz("optical")),
        )

        def build():
            mesh = self._load_step_mesh(
                self.imported_optical_step_path,
                largest_component=False,
                allow_slow_import=not self._open3d_step_cache_warmup_active(),
            )
            if mesh is None:
                return None
            return self._cad_mesh_aligned_to_optical_axis(
                mesh,
                source_axis="z",
                front_face="min",
                target_front_z=0.0,
                label="Optical STEP",
                roll_deg=float(getattr(self, "optical_step_rotation_z_deg", 0.0)),
                x_rotation_deg=float(getattr(self, "optical_step_rotation_x_deg", 0.0)),
                y_rotation_deg=float(getattr(self, "optical_step_rotation_y_deg", 0.0)),
                axis_offset_xy=self._step_axis_offset_xy("optical"),
                placement_offset_xyz=self._step_placement_offset_xyz("optical"),
            )

        return self._cached_transformed_step_overlay("optical", signature, build)

    def _transformed_imported_camera_step_mesh(self):
        if self.imported_camera_step_path is None:
            return None
        camera_front_z = self._current_image_plane_z() - self._current_camera_front_to_sensor_mm()
        signature = (
            self._step_overlay_stat_key(self.imported_camera_step_path),
            round(float(camera_front_z), 6),
            round(float(getattr(self, "camera_step_rotation_z_deg", 0.0)), 6),
            round(float(getattr(self, "camera_step_rotation_x_deg", 0.0)), 6),
            round(float(getattr(self, "camera_step_rotation_y_deg", 0.0)), 6),
            tuple(round(float(v), 6) for v in self._step_axis_offset_xy("camera")),
            tuple(round(float(v), 6) for v in self._step_placement_offset_xyz("camera")),
        )

        def build():
            mesh = self._load_step_mesh(
                self.imported_camera_step_path,
                largest_component=True,
                allow_slow_import=not self._open3d_step_cache_warmup_active(),
            )
            if mesh is None:
                return None
            aligned = self._cad_mesh_aligned_to_optical_axis(
                mesh,
                source_axis="z",
                front_face="max",
                target_front_z=camera_front_z,
                label="Camera STEP",
                roll_deg=float(getattr(self, "camera_step_rotation_z_deg", 0.0)),
                x_rotation_deg=float(getattr(self, "camera_step_rotation_x_deg", 0.0)),
                y_rotation_deg=float(getattr(self, "camera_step_rotation_y_deg", 0.0)),
                axis_offset_xy=self._step_axis_offset_xy("camera"),
                placement_offset_xyz=self._step_placement_offset_xyz("camera"),
            )
            return self._heavy_step_display_proxy(aligned, label="Camera STEP")

        return self._cached_transformed_step_overlay("camera", signature, build)

    def _transformed_imported_led_step_mesh(self):
        if self.imported_led_step_path is None:
            return None
        signature = (
            self._step_overlay_stat_key(self.imported_led_step_path),
            round(float(self._led_step_z_translation()), 6),
            round(float(getattr(self, "led_step_rotation_z_deg", 0.0)), 6),
            round(float(getattr(self, "led_step_rotation_x_deg", 0.0)), 6),
            round(float(getattr(self, "led_step_rotation_y_deg", 0.0)), 6),
            tuple(round(float(v), 6) for v in self._step_axis_offset_xy("led")),
            tuple(round(float(v), 6) for v in self._step_placement_offset_xyz("led")),
        )

        def build():
            mesh = self._load_step_mesh(
                self.imported_led_step_path,
                largest_component=False,
                allow_slow_import=not self._open3d_step_cache_warmup_active(),
            )
            if mesh is None:
                return None
            return self._cad_mesh_aligned_to_optical_axis(
                mesh,
                source_axis="z",
                front_face="min",
                target_front_z=self._led_step_z_translation(),
                label="LED STEP",
                roll_deg=float(getattr(self, "led_step_rotation_z_deg", 0.0)),
                x_rotation_deg=float(getattr(self, "led_step_rotation_x_deg", 0.0)),
                y_rotation_deg=float(getattr(self, "led_step_rotation_y_deg", 0.0)),
                axis_offset_xy=self._step_axis_offset_xy("led"),
                placement_offset_xyz=self._step_placement_offset_xyz("led"),
            )

        return self._cached_transformed_step_overlay("led", signature, build)

    def _transformed_external_camera_mesh(self) -> pv.DataSet | None:
        spec = self._current_external_camera_spec()
        if spec is None:
            return None
        mesh = self._load_external_camera_mesh()
        if mesh is None or int(getattr(mesh, "n_points", 0)) == 0:
            return None
        pts = np.asarray(mesh.points, dtype=float)
        if pts.size == 0:
            return None
        reference = None
        try:
            reference = self._load_external_camera_reference()
        except Exception as exc:
            self.append_debug(f"Camera CAD reference error: {exc}")
        if isinstance(reference, dict):
            ref_xy = reference.get("reference_xy")
            if isinstance(ref_xy, (list, tuple)) and len(ref_xy) >= 2:
                pts[:, 0] -= float(ref_xy[0])
                pts[:, 1] -= float(ref_xy[1])
        else:
            bounds = np.array(mesh.bounds, dtype=float)
            pts[:, 0] -= 0.5 * (bounds[0] + bounds[1])
            pts[:, 1] -= 0.5 * (bounds[2] + bounds[3])
        rotate_xyz_deg = spec.get("rotate_xyz_deg")
        if rotate_xyz_deg is not None:
            rot = _rotation_matrix_xyz(rotate_xyz_deg)
            pts = pts @ rot.T
        bounds_min = np.min(pts, axis=0)
        bounds_max = np.max(pts, axis=0)
        front_face = str(spec.get("front_face", "min")).lower()
        front_z = float(bounds_min[2] if front_face == "min" else bounds_max[2])
        image_z = self._current_image_plane_z()
        pts[:, 2] += image_z - front_z
        mesh.points = pts
        try:
            self.append_debug(
                "Camera CAD transform | model={label} | raw_bounds=({rx0:.3f},{rx1:.3f},{ry0:.3f},{ry1:.3f},{rz0:.3f},{rz1:.3f}) | "
                "shifted_bounds=({sx0:.3f},{sx1:.3f},{sy0:.3f},{sy1:.3f},{sz0:.3f},{sz1:.3f}) | image_z={iz:.3f} | front_z={fz:.3f}".format(
                    label=str(spec.get("label", self._current_external_camera_name())),
                    rx0=float(bounds_min[0]),
                    rx1=float(bounds_max[0]),
                    ry0=float(bounds_min[1]),
                    ry1=float(bounds_max[1]),
                    rz0=float(bounds_min[2]),
                    rz1=float(bounds_max[2]),
                    sx0=float(np.min(pts[:, 0])),
                    sx1=float(np.max(pts[:, 0])),
                    sy0=float(np.min(pts[:, 1])),
                    sy1=float(np.max(pts[:, 1])),
                    sz0=float(np.min(pts[:, 2])),
                    sz1=float(np.max(pts[:, 2])),
                    iz=float(image_z),
                    fz=float(front_z),
                )
            )
            if isinstance(reference, dict):
                self.append_debug(
                    "Camera CAD reference | method={method} | ref_xy=({x:.3f},{y:.3f})".format(
                        method=str(reference.get("method", "unknown")),
                        x=float(reference.get("reference_xy", [0.0, 0.0])[0]),
                        y=float(reference.get("reference_xy", [0.0, 0.0])[1]),
                    )
                )
        except Exception:
            pass
        return mesh

    def _external_camera_overlay_polylines(self) -> list[np.ndarray]:
        spec = self._current_external_camera_spec()
        if spec is None:
            return []
        try:
            section_data = self._load_external_camera_section_profile()
        except Exception as exc:
            self.append_debug(f"Camera CAD section profile error: {exc}")
            section_data = None
        if isinstance(section_data, dict):
            profile_points = np.asarray(section_data.get("profile_points", []), dtype=float)
            ref_xy = np.asarray(section_data.get("reference_xy", [0.0, 0.0]), dtype=float)
            if profile_points.ndim == 2 and profile_points.shape[0] >= 4 and profile_points.shape[1] >= 3 and ref_xy.size >= 2:
                pts = profile_points[:, :3].copy()
                pts[:, 0] -= float(ref_xy[0])
                pts[:, 1] -= float(ref_xy[1])
                rotate_xyz_deg = spec.get("rotate_xyz_deg")
                if rotate_xyz_deg is not None:
                    rot = _rotation_matrix_xyz(rotate_xyz_deg)
                    pts = pts @ rot.T
                front_face = str(spec.get("front_face", "min")).lower()
                front_z = float(np.min(pts[:, 2]) if front_face == "min" else np.max(pts[:, 2]))
                pts[:, 2] += self._current_image_plane_z() - front_z
                poly = self._project_layout_polyline(pts[:, 2], pts[:, 1])
                if int(poly.shape[0]) >= 2:
                    self.append_debug(f"Camera CAD OCC section profile used | points={int(poly.shape[0])}")
                    return [poly]
        mesh = self._transformed_external_camera_mesh()
        if mesh is None or int(getattr(mesh, "n_points", 0)) == 0:
            return []
        bounds = tuple(float(v) for v in mesh.bounds)
        mesh_pts = np.asarray(mesh.points, dtype=float)
        full_outline = _profile_from_section_points(np.column_stack((mesh_pts[:, 2], mesh_pts[:, 1])))
        if int(full_outline.shape[0]) >= 4:
            poly = self._project_layout_polyline(full_outline[:, 0], full_outline[:, 1])
            if int(poly.shape[0]) >= 2:
                self.append_debug(f"Camera CAD silhouette outline | points={int(poly.shape[0])}")
                return [poly]
        try:
            center_x = 0.5 * (bounds[0] + bounds[1])
            section = mesh.slice(normal=(1.0, 0.0, 0.0), origin=(center_x, 0.0, 0.0))
            self.append_debug(
                "Camera CAD section | center_x={cx:.3f} | bounds=({x0:.3f},{x1:.3f},{y0:.3f},{y1:.3f},{z0:.3f},{z1:.3f}) | "
                "section_points={pts} | section_cells={cells}".format(
                    cx=float(center_x),
                    x0=bounds[0],
                    x1=bounds[1],
                    y0=bounds[2],
                    y1=bounds[3],
                    z0=bounds[4],
                    z1=bounds[5],
                    pts=int(getattr(section, "n_points", 0)),
                    cells=int(getattr(section, "n_cells", 0)),
                )
            )
        except Exception:
            section = None
        if section is not None and int(getattr(section, "n_points", 0)) >= 2:
            pts = np.asarray(section.points, dtype=float)
            outline = _profile_from_section_points(np.column_stack((pts[:, 2], pts[:, 1])))
            if int(outline.shape[0]) >= 4:
                poly = self._project_layout_polyline(outline[:, 0], outline[:, 1])
                if int(poly.shape[0]) >= 2:
                    self.append_debug(f"Camera CAD section outline | points={int(poly.shape[0])}")
                    return [poly]
            self.append_debug("Camera CAD section produced no usable outline; falling back to silhouette hull.")
        pts = mesh_pts
        if pts.shape[0] < 8:
            self.append_debug("Camera CAD fallback silhouette skipped: insufficient mesh points.")
            return []
        stride = max(1, pts.shape[0] // 3000)
        yz = np.column_stack((pts[::stride, 2], pts[::stride, 1]))
        yz = yz[np.all(np.isfinite(yz), axis=1)]
        if yz.shape[0] < 3:
            return []
        hull = _convex_hull_2d(yz)
        if hull.shape[0] < 3:
            self.append_debug("Camera CAD fallback silhouette skipped: hull extraction failed.")
            return []
        hull = np.vstack([hull, hull[0]])
        poly = self._project_layout_polyline(hull[:, 0], hull[:, 1])
        if int(poly.shape[0]) >= 2:
            self.append_debug("Camera CAD fallback silhouette used.")
            return [poly]
        self.append_debug("Camera CAD fallback silhouette produced no drawable polyline.")
        return []

    def _draw_external_camera_overlay(self) -> None:
        spec = self._current_external_camera_spec()
        if spec is None:
            return
        overlay_mode = self.camera_overlay_mode_var.get().strip() if hasattr(self, "camera_overlay_mode_var") else "Rough envelope"
        if overlay_mode == "Off":
            return
        try:
            polylines = self._external_camera_overlay_polylines()
        except Exception as exc:
            self.append_debug(f"Camera CAD overlay error: {exc}")
            return
        if not polylines:
            return
        color = str(spec.get("line_color_2d", "#6b7280"))
        for poly in polylines:
            self.ax.plot(poly[:, 0], poly[:, 1], color="white", linewidth=3.6, alpha=0.94, zorder=54)
            self.ax.plot(poly[:, 0], poly[:, 1], color=color, linewidth=1.35, alpha=0.98, zorder=55)

    def _supported_lens_mech_profile(self) -> dict[str, object] | None:
        if self.current_layout_file is None:
            return None
        stem = self.current_layout_file.stem.lower()
        if stem not in {
            "machine_vision_150mm_datasheet_1x",
            "machine_vision_150mm_datasheet_0_5x",
            "machine_vision_150mm_measured",
        }:
            return None
        if len(self.rows) < 4:
            return None
        front_z = float(self.rows[0].thickness)
        rear_z = None
        z_cursor = 0.0
        for row in self.rows:
            if row.name == "Lens Rear Datum":
                rear_z = z_cursor
                break
            z_cursor += float(row.thickness)
        if rear_z is None:
            mech_length = float(self.rows[1].thickness) + float(self.rows[2].thickness)
            rear_z = front_z + mech_length
        else:
            mech_length = max(float(rear_z) - front_z, 1e-9)
        # Approximate the housing from the datasheet front/knurled/rear barrel drawing.
        z_knurl_start = front_z + 0.24 * mech_length
        z_knurl_end = front_z + 0.70 * mech_length
        z_rear_step = front_z + 0.83 * mech_length
        r_front = 21.0
        r_body = 25.0
        r_rear = 19.5
        top = np.array(
            [
                [front_z, r_front],
                [z_knurl_start, r_front],
                [z_knurl_start, r_body],
                [z_knurl_end, r_body],
                [z_knurl_end, r_front + 1.5],
                [z_rear_step, r_front + 1.5],
                [z_rear_step, r_rear],
                [rear_z, r_rear],
            ],
            dtype=float,
        )
        bottom = top[::-1].copy()
        bottom[:, 1] *= -1.0
        outline = np.vstack([top, bottom, top[:1]])
        return {
            "outline": outline,
            "knurl_start": z_knurl_start,
            "knurl_end": z_knurl_end,
            "front_z": front_z,
            "rear_z": rear_z,
            "radius": r_body,
        }

    def _draw_lens_mech_overlay(self) -> None:
        profile = self._supported_lens_mech_profile()
        if not isinstance(profile, dict):
            return
        outline = np.asarray(profile["outline"], dtype=float)
        poly = self._project_layout_polyline(outline[:, 0], outline[:, 1])
        if int(poly.shape[0]) < 2:
            return
        self.ax.plot(poly[:, 0], poly[:, 1], color="white", linewidth=4.2, alpha=0.95, zorder=54)
        self.ax.plot(poly[:, 0], poly[:, 1], color="#6b7280", linewidth=1.4, alpha=0.98, zorder=55)
        z_knurl_start = float(profile["knurl_start"])
        z_knurl_end = float(profile["knurl_end"])
        radius = float(profile["radius"])
        knurl_count = 11
        tooth_width = (z_knurl_end - z_knurl_start) / max(knurl_count * 2, 1)
        for idx in range(knurl_count):
            z0 = z_knurl_start + idx * 2.0 * tooth_width
            z1 = min(z0 + tooth_width, z_knurl_end)
            z2 = min(z1 + tooth_width, z_knurl_end)
            top_pts = self._project_layout_polyline(
                [z0, z1, z2],
                [radius - 1.6, radius, radius - 1.6],
            )
            bot_pts = self._project_layout_polyline(
                [z0, z1, z2],
                [-(radius - 1.6), -radius, -(radius - 1.6)],
            )
            if int(top_pts.shape[0]) >= 2:
                self.ax.plot(top_pts[:, 0], top_pts[:, 1], color="#9ca3af", linewidth=0.9, alpha=0.9, zorder=56)
            if int(bot_pts.shape[0]) >= 2:
                self.ax.plot(bot_pts[:, 0], bot_pts[:, 1], color="#9ca3af", linewidth=0.9, alpha=0.9, zorder=56)

    @staticmethod
    def _system_transform_list(system):
        if system is None:
            return None
        pr3d = getattr(system, "Pr3D", None)
        for owner in (pr3d, system):
            transforms = getattr(owner, "TRANS_2A", None) if owner is not None else None
            if transforms is not None:
                return transforms
        return None

    def _row_layout_polylines(self, system, row_index: int, z_pos: float) -> list[np.ndarray]:
        if not (0 <= row_index < len(self.rows)):
            return []
        row = self.rows[row_index]
        polylines: list[np.ndarray] = []
        if row.surface in {"Mirror", BEAM_SPLITTER_SURFACE}:
            half_length = max(float(row.diameter) / 2.0, 0.5)
            transforms = self._system_transform_list(system)
            if transforms is not None and row_index < len(transforms):
                try:
                    transform = np.asarray(transforms[row_index], dtype=float)
                    center = np.asarray(transform[:3, 3], dtype=float)
                    tangent = np.asarray(transform[:3, 1], dtype=float)
                    norm = float(np.linalg.norm(tangent))
                    if norm > 1e-12:
                        tangent /= norm
                        poly = np.vstack((center - tangent * half_length, center + tangent * half_length))
                        if poly.size > 0:
                            polylines.append(poly)
                            return polylines
                except Exception:
                    pass
            angle = np.deg2rad(float(row.tilt_x))
            dz = np.sin(angle) * half_length
            dy = np.cos(angle) * half_length
            center_z = z_pos + float(row.desp_z)
            center_y = float(row.desp_y)
            poly = self._project_layout_polyline(
                [center_z - dz, center_z + dz],
                [center_y - dy, center_y + dy],
            )
            if poly.size > 0:
                polylines.append(poly)
            return polylines
        if row.surface in {"Object", "Image", "Aperture"}:
            half_height = max(float(row.diameter) / 2.0, 0.5)
            if row.surface == "Aperture":
                transforms = self._system_transform_list(system)
                if transforms is not None and row_index < len(transforms):
                    try:
                        transform = np.asarray(transforms[row_index], dtype=float)
                        center = np.asarray(transform[:3, 3], dtype=float)
                        tangent = np.asarray(transform[:3, 1], dtype=float)
                        norm = float(np.linalg.norm(tangent))
                        if norm > 1e-12:
                            tangent /= norm
                            poly = np.vstack((center - tangent * half_height, center + tangent * half_height))
                            if poly.size > 0:
                                polylines.append(poly)
                                return polylines
                    except Exception:
                        pass
            center_z = z_pos + float(row.desp_z)
            center_y = float(row.desp_y)
            poly = self._project_layout_polyline(
                [center_z, center_z],
                [center_y - half_height, center_y + half_height],
            )
            if poly.size > 0:
                polylines.append(poly)
            return polylines
        if row.surface == "Thin Lens":
            transforms = self._system_transform_list(system)
            transform = None
            if transforms is not None and row_index < len(transforms):
                transform = transforms[row_index]
            poly = thin_lens_glyph_polyline(
                row,
                z_pos,
                transform=transform,
                project_fn=self._project_xy,
            )
            if poly is not None and int(poly.shape[0]) >= 2:
                return [poly]
        surface_data = getattr(system, "SDT_0", None)
        surface_tools = getattr(system, "SuTo", None)
        transforms = getattr(getattr(system, "Pr3D", None), "TRANS_2A", None)
        if surface_data is None:
            return polylines
        if row_index >= len(surface_data):
            return polylines
        surface = surface_data[row_index]
        if int(getattr(surface, "Drawing", 1)) != 1:
            return polylines
        if str(getattr(surface, "Glass", "") or "").upper() == "NULL":
            return polylines
        solid = 1 if getattr(surface, "Solid_3d_stl", "None") != "None" else 0
        if solid:
            stl_polylines = self._stl_mesh_layout_polylines(system, row_index, z_pos)
            if stl_polylines:
                return stl_polylines
        if surface_tools is not None and transforms is not None and row_index < len(transforms):
            try:
                half_height = max(float(row.diameter) / 2.0, 0.5)
                transform = np.asarray(transforms[row_index], dtype=float)
                inner_half = min(max(float(row.in_diameter) / 2.0, 0.0), max(half_height - 1e-6, 0.0))
                local_y_segments = [np.linspace(-half_height, half_height, 181, dtype=float)]
                if inner_half > 1e-6:
                    local_y_segments = []
                    if -half_height < -inner_half:
                        local_y_segments.append(np.linspace(-half_height, -inner_half, 91, dtype=float))
                    if inner_half < half_height:
                        local_y_segments.append(np.linspace(inner_half, half_height, 91, dtype=float))
                for local_y in local_y_segments:
                    if local_y.size < 2:
                        continue
                    local_x = np.zeros_like(local_y)
                    local_z = np.asarray(surface_tools.SurfaceShape(local_x, local_y, row_index), dtype=float)
                    local_pts = np.column_stack(
                        (
                            local_x,
                            local_y,
                            local_z,
                            np.ones_like(local_y),
                        )
                    )
                    world_pts = (transform @ local_pts.T).T
                    finite = np.all(np.isfinite(world_pts[:, :3]), axis=1)
                    if not np.any(finite):
                        continue
                    poly = np.asarray(world_pts[finite, :3], dtype=float)
                    if int(poly.shape[0]) >= 2:
                        polylines.append(poly)
                if polylines:
                    return polylines
            except Exception:
                pass
        surfaces = getattr(system, "AAA", None)
        try:
            surface_block_count = int(getattr(surfaces, "n_blocks", len(surfaces)))
        except Exception:
            surface_block_count = 0
        if surfaces is None or row_index >= surface_block_count:
            return polylines
        mesh = surfaces[row_index]
        edge_3d_func, filter_face_2dplot_func, _color_func = _load_display_helpers()
        if edge_3d_func is None or filter_face_2dplot_func is None:
            return polylines
        for direction in (1, -1):
            try:
                _ax, ay, az = edge_3d_func(mesh, direction, 0, 0, solid)
                az, ay = filter_face_2dplot_func(np.asarray(az, dtype=float), np.asarray(ay, dtype=float), solid)
            except Exception:
                continue
            poly = self._project_layout_polyline(az, ay)
            if int(poly.shape[0]) >= 2:
                polylines.append(poly)
        return polylines

    def _optical_solid_face_layout_polylines(self, row, z_pos: float, transform=None) -> list[np.ndarray]:
        if transform is None:
            try:
                faces = optical_solid_face_world_records(row, z_pos, assigned_only=True)
            except Exception:
                return []
        else:
            try:
                metadata = normalize_optical_solid_face_metadata(
                    getattr(row, "advanced", {}).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
                )
                matrix = np.asarray(transform, dtype=float).reshape(4, 4)
            except Exception:
                return []
            faces = []
            for face in list(metadata.get("faces", []) or []):
                if not isinstance(face, dict):
                    continue
                function = _normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
                side = _normalize_optical_solid_face_side(face.get("side_2d"))
                role = _legacy_role_from_optical_solid_face_function(function)
                if (
                    role == OPTICAL_SOLID_FACE_ROLE_DEFAULT
                    and function == OPTICAL_SOLID_FACE_FUNCTION_DEFAULT
                    and side == OPTICAL_SOLID_FACE_SIDE_DEFAULT
                ):
                    continue
                centroid_local = np.asarray(_point3_tuple(face.get("centroid", (0.0, 0.0, 0.0))), dtype=float)
                normal_local = np.asarray(_unit_vector_tuple(face.get("normal", (0.0, 0.0, 1.0))), dtype=float)
                if bool(face.get("flip_normal", False)):
                    normal_local = -normal_local
                centroid_world = matrix @ np.asarray(
                    (float(centroid_local[0]), float(centroid_local[1]), float(centroid_local[2]), 1.0),
                    dtype=float,
                )
                normal_world = np.asarray(matrix[:3, :3], dtype=float) @ normal_local[:3]
                normal_norm = float(np.linalg.norm(normal_world))
                if normal_norm <= 1e-12:
                    continue
                world_face = dict(face)
                world_face["role"] = role
                world_face["function"] = function
                world_face["side_2d"] = side
                world_face["centroid_world"] = tuple(float(value) for value in centroid_world[:3])
                world_face["normal_world"] = tuple(float(value) for value in normal_world[:3] / normal_norm)
                faces.append(world_face)
        polylines: list[np.ndarray] = []
        for face in list(faces or []):
            if not isinstance(face, dict):
                continue
            function = _normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
            if function == OPTICAL_SOLID_FACE_FUNCTION_DEFAULT:
                continue
            centroid = np.asarray(face.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
            normal = np.asarray(face.get("normal_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
            if centroid.size < 3 or normal.size < 3:
                continue
            if not (np.all(np.isfinite(centroid[:3])) and np.all(np.isfinite(normal[:3]))):
                continue
            x0, y0 = self._project_xy([float(centroid[2])], [float(centroid[1])])
            x1, y1 = self._project_xy(
                [float(centroid[2] + normal[2])],
                [float(centroid[1] + normal[1])],
            )
            center = np.asarray((float(x0[0]), float(y0[0])), dtype=float)
            normal_2d = np.asarray((float(x1[0] - x0[0]), float(y1[0] - y0[0])), dtype=float)
            normal_norm = float(np.linalg.norm(normal_2d))
            if normal_norm <= 1e-12:
                continue
            tangent = np.asarray((-normal_2d[1], normal_2d[0]), dtype=float) / normal_norm
            try:
                clear_aperture = float(face.get("clear_aperture_mm", 0.0) or 0.0)
            except Exception:
                clear_aperture = 0.0
            try:
                area_length = float(np.sqrt(max(float(face.get("area_mm2", 0.0) or 0.0), 0.0)))
            except Exception:
                area_length = 0.0
            try:
                row_length = max(float(getattr(row, "diameter", 0.0) or 0.0), 1.0)
            except Exception:
                row_length = 1.0
            length = clear_aperture if clear_aperture > 1e-9 else area_length
            if length <= 1e-9:
                length = row_length
            half_length = max(0.5, min(float(length), row_length * 1.25) * 0.5)
            polylines.append(np.vstack((center - tangent * half_length, center + tangent * half_length)))
        return polylines

    def _stl_mesh_layout_polylines(self, system, row_index: int, z_pos: float) -> list[np.ndarray]:
        face_polylines: list[np.ndarray] = []
        transform = None
        runtime_transform = optical_solid_output_port_runtime_transform_override(system, self.rows, row_index)
        transforms = getattr(system, "TRANS_2A", None)
        if runtime_transform is not None:
            transform = runtime_transform
        elif transforms is not None and 0 <= row_index < len(transforms):
            try:
                transform = np.asarray(transforms[row_index], dtype=float)
            except Exception:
                transform = None
        if 0 <= row_index < len(self.rows):
            face_polylines = self._optical_solid_face_layout_polylines(self.rows[row_index], z_pos, transform=transform)
        points = None
        runtime_meshes = getattr(system, "EEE", None)
        try:
            runtime_mesh_count = len(runtime_meshes) if runtime_meshes is not None else 0
        except Exception:
            runtime_mesh_count = 0
        if runtime_meshes is not None and row_index < runtime_mesh_count:
            try:
                mesh = runtime_meshes[row_index]
                points = np.asarray(mesh.points, dtype=float)
            except Exception:
                points = None
        if points is None and runtime_transform is not None:
            try:
                row = self.rows[row_index]
                path = self._stl_path_from_row(row)
                if path is not None:
                    _fmt, triangles = _read_stl_triangle_vertices(path)
                    local_points = triangles.reshape((-1, 3))
                    local_h = np.column_stack((local_points[:, 0], local_points[:, 1], local_points[:, 2], np.ones(local_points.shape[0])))
                    world_points = (np.asarray(runtime_transform, dtype=float).reshape(4, 4) @ local_h.T).T
                    points = np.asarray(world_points[:, :3], dtype=float)
            except Exception:
                points = None
        surfaces = getattr(system, "AAA", None)
        try:
            surface_block_count = int(getattr(surfaces, "n_blocks", len(surfaces)))
        except Exception:
            surface_block_count = 0
        if points is None and surfaces is not None and row_index < surface_block_count:
            try:
                mesh = surfaces[row_index]
                points = np.asarray(mesh.points, dtype=float)
            except Exception:
                points = None
        if points is None or points.ndim != 2 or points.shape[1] < 3 or points.shape[0] < 2:
            try:
                row = self.rows[row_index]
                path = self._stl_path_from_row(row)
                if path is None:
                    return []
                _fmt, triangles = _read_stl_triangle_vertices(path)
                local_points = triangles.reshape((-1, 3))
                rotation = _rotation_matrix_from_kraken_tilts(row.tilt_x, row.tilt_y, row.tilt_z)
                points = local_points @ rotation.T
                points[:, 0] += float(row.desp_x)
                points[:, 1] += float(row.desp_y)
                points[:, 2] += float(z_pos) + float(row.desp_z)
            except Exception:
                return face_polylines
        if points.ndim != 2 or points.shape[1] < 3 or points.shape[0] < 2:
            return face_polylines
        projected = self._project_layout_polyline(points[:, 2], points[:, 1])
        hull = convex_hull_2d(projected)
        if hull.shape[0] >= 2:
            return [hull]
        return face_polylines

    # _rebuild_layout_pick_regions removed in Phase 3 — pick regions
    # are now built from the SceneBundle in refresh_plot().

    @staticmethod
    def _distance_to_polyline(point_xy: np.ndarray, polyline_xy: np.ndarray) -> float:
        return distance_to_polyline(point_xy, polyline_xy)
