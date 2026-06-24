"""Face-index aware Open 3D edge and outline helpers."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

import numpy as np

try:  # PyVista is optional outside Open 3D.
    import pyvista as pv
except Exception:  # pragma: no cover - exercised in environments without VTK.
    pv = None

from KrakenOS.UI.services.open3d_face_pick import FaceRayPick, pick_face_from_ray


FACE_INDEX_CELL_DATA = "kraken_step_face_index"
SELECTION_FACE_INDEX_CELL_DATA = "kraken_step_selection_face_index"
_FACE_INDEX_CELL_DATA_NAMES = (SELECTION_FACE_INDEX_CELL_DATA, FACE_INDEX_CELL_DATA)


def mesh_has_face_index(mesh) -> bool:
    """Return true when a mesh carries analytic STEP face cell IDs."""
    try:
        surface = pv.wrap(mesh)
        values = np.asarray(
            surface.cell_data.get(SELECTION_FACE_INDEX_CELL_DATA, surface.cell_data.get(FACE_INDEX_CELL_DATA, ())),
            dtype=int,
        )
        return bool(values.size == int(getattr(mesh, "n_cells", 0)) and np.any(values >= 0))
    except Exception:
        return False


def _cell_face_index_values(surface, cell_count: int) -> np.ndarray:
    for name in _FACE_INDEX_CELL_DATA_NAMES:
        try:
            values = np.asarray(surface.cell_data.get(name, ()), dtype=int)
        except Exception:
            values = np.empty((0,), dtype=int)
        if values.shape[0] == int(cell_count):
            return values
    return np.empty((0,), dtype=int)


def _drop_invalid_cell_data(mesh):
    if pv is None or mesh is None:
        return mesh
    try:
        cleaned = pv.wrap(mesh).copy(deep=True)
        cell_count = int(getattr(cleaned, "n_cells", 0))
        cell_data = cleaned.GetCellData()
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
            except Exception:
                try:
                    del cleaned.cell_data[name]
                except Exception:
                    pass
        return cleaned
    except Exception:
        return mesh


# Building the displayed triangle array + face-index map means a full
# ``pv.wrap`` + reshape over every cell. The round-lens cap picker calls
# this twice per analytic group face on every mouse move, so a 114k-cell
# vendor body re-materialised a ~10 MB float array a dozen times per
# hover (~1.8 s stalls). The transformed display mesh is itself memoised
# (one stable object per layout pose), so cache the derived arrays keyed
# on mesh identity plus a content token; a genuine geometry change bumps
# the VTK MTime / cell count and invalidates the entry.
_SURFACE_TRIANGLE_CACHE: dict[int, tuple] = {}
_SURFACE_TRIANGLE_CACHE_ORDER: list[int] = []
_SURFACE_TRIANGLE_CACHE_MAX = 8


def _mesh_cache_token(mesh):
    try:
        mtime = int(mesh.GetMTime())
    except Exception:
        mtime = -1
    return (
        int(getattr(mesh, "n_points", -1)),
        int(getattr(mesh, "n_cells", -1)),
        mtime,
    )


def _surface_triangles_and_face_index(mesh):
    if pv is None or mesh is None:
        return None, np.empty((0, 3, 3), dtype=float), np.empty((0,), dtype=int)
    key = id(mesh)
    token = _mesh_cache_token(mesh)
    cached = _SURFACE_TRIANGLE_CACHE.get(key)
    if cached is not None and cached[0] == token:
        return cached[1]
    result = _surface_triangles_and_face_index_compute(mesh)
    _SURFACE_TRIANGLE_CACHE[key] = (token, result)
    if key in _SURFACE_TRIANGLE_CACHE_ORDER:
        _SURFACE_TRIANGLE_CACHE_ORDER.remove(key)
    _SURFACE_TRIANGLE_CACHE_ORDER.append(key)
    while len(_SURFACE_TRIANGLE_CACHE_ORDER) > _SURFACE_TRIANGLE_CACHE_MAX:
        evicted = _SURFACE_TRIANGLE_CACHE_ORDER.pop(0)
        if evicted != key:
            _SURFACE_TRIANGLE_CACHE.pop(evicted, None)
    return result


def _triangle_only_surface_with_face_index(mesh):
    """Return a triangle-only surface when stray non-triangle cells misalign the
    per-cell face index.

    The analytic STEP display cache occasionally carries a handful of degenerate
    ``VTK_LINE`` cells (a ``clean()`` artifact). VTK numbers the per-cell
    ``kraken_step_face_index`` over *every* cell, so once a line sneaks in the
    polygon count disagrees with the cell-data length and the triangle/
    face-index zip below drops the whole body -- which silently disabled fine
    STEP face hover/pick + outline (the LED clear-aperture window could no longer
    be highlighted). Extracting just the triangle cells, carrying their cell
    data, restores the 1:1 polygon<->face-index alignment. Returns ``None`` when
    there is nothing to repair so the healthy fast path is untouched."""
    if pv is None or mesh is None:
        return None
    try:
        surface = pv.wrap(mesh)
        n_cells = int(getattr(surface, "n_cells", 0))
        if n_cells <= 0:
            return None
        if int(surface.GetNumberOfPolys()) == n_cells:
            return None  # no stray cells -- alignment already holds
        if _cell_face_index_values(surface, n_cells).size != n_cells:
            return None  # face index isn't per-cell here; nothing to realign
        grid = surface.cast_to_unstructured_grid()
        tri_mask = np.asarray(grid.celltypes) == int(pv.CellType.TRIANGLE)
        if not bool(np.any(tri_mask)):
            return None
        extracted = grid.extract_cells(np.flatnonzero(tri_mask)).extract_surface(
            algorithm="dataset_surface"
        )
        if int(getattr(extracted, "n_points", 0)) <= 0:
            return None
        return extracted
    except Exception:
        return None


def _surface_triangles_and_face_index_compute(mesh):
    repaired = _triangle_only_surface_with_face_index(mesh)
    if repaired is not None:
        mesh = repaired
    try:
        surface = pv.wrap(mesh)
        faces = np.asarray(surface.faces, dtype=np.int64).reshape((-1, 4))
        values = _cell_face_index_values(surface, int(faces.shape[0]))
        if values.shape[0] != int(faces.shape[0]):
            return surface, np.empty((0, 3, 3), dtype=float), np.empty((0,), dtype=int)
        if not np.all(faces[:, 0] == 3):
            raise ValueError("not triangle surface")
        points = np.asarray(surface.points, dtype=float)
    except Exception:
        try:
            source = _drop_invalid_cell_data(mesh)
            if _cell_face_index_values(source, int(getattr(source, "n_cells", 0))).size == 0:
                return source, np.empty((0, 3, 3), dtype=float), np.empty((0,), dtype=int)
            surface = source.extract_surface(algorithm="dataset_surface").triangulate().copy(deep=True)
            faces = np.asarray(surface.faces, dtype=np.int64).reshape((-1, 4))
            values = _cell_face_index_values(surface, int(faces.shape[0]))
            points = np.asarray(surface.points, dtype=float)
        except Exception:
            return None, np.empty((0, 3, 3), dtype=float), np.empty((0,), dtype=int)
    if faces.ndim != 2 or faces.shape[0] <= 0 or faces.shape[1] != 4 or not np.all(faces[:, 0] == 3):
        return surface, np.empty((0, 3, 3), dtype=float), np.empty((0,), dtype=int)
    if values.shape[0] != faces.shape[0]:
        return surface, np.empty((0, 3, 3), dtype=float), np.empty((0,), dtype=int)
    if points.ndim != 2 or points.shape[1] < 3:
        return surface, np.empty((0, 3, 3), dtype=float), np.empty((0,), dtype=int)
    triangles = points[faces[:, 1:4], :3]
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or not np.all(np.isfinite(triangles)):
        return surface, np.empty((0, 3, 3), dtype=float), np.empty((0,), dtype=int)
    return surface, np.asarray(triangles, dtype=float), np.asarray(values, dtype=int)


def triangle_array_and_face_index(mesh) -> tuple[np.ndarray, np.ndarray]:
    """Return displayed triangles and analytic face index values."""
    _surface, triangles, face_index = _surface_triangles_and_face_index(mesh)
    return triangles, face_index


def triangles_for_face_indices(mesh, target_face_indices) -> np.ndarray:
    """Return displayed triangles whose selection face index is in the target set."""
    try:
        targets = {int(value) for value in target_face_indices}
    except Exception:
        return np.empty((0, 3, 3), dtype=float)
    if not targets:
        return np.empty((0, 3, 3), dtype=float)
    _surface, triangles, face_index = _surface_triangles_and_face_index(mesh)
    if triangles.size == 0 or face_index.size != triangles.shape[0]:
        return np.empty((0, 3, 3), dtype=float)
    mask = np.isin(np.asarray(face_index, dtype=int), np.asarray(sorted(targets), dtype=int))
    if mask.shape[0] != triangles.shape[0] or not np.any(mask):
        return np.empty((0, 3, 3), dtype=float)
    return np.asarray(triangles[mask], dtype=float)


def _point_key(point: np.ndarray) -> tuple[float, float, float]:
    return tuple(float(value) for value in np.round(np.asarray(point, dtype=float).reshape(3), decimals=8))


def _edge_key(a: np.ndarray, b: np.ndarray) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    first = _point_key(a)
    second = _point_key(b)
    return (first, second) if first <= second else (second, first)


def _edge_records(triangles: np.ndarray, face_index: np.ndarray) -> dict[object, list[tuple[int, np.ndarray, np.ndarray]]]:
    records: dict[object, list[tuple[int, np.ndarray, np.ndarray]]] = {}
    for cell_id, (triangle, face_id) in enumerate(zip(triangles, face_index, strict=False)):
        try:
            face_id = int(face_id)
        except Exception:
            face_id = -1
        if face_id < 0:
            continue
        for i0, i1 in ((0, 1), (1, 2), (2, 0)):
            p0 = np.asarray(triangle[i0], dtype=float).reshape(3)
            p1 = np.asarray(triangle[i1], dtype=float).reshape(3)
            records.setdefault(_edge_key(p0, p1), []).append((face_id, p0, p1))
    return records


def _line_polydata(edges: Iterable[tuple[np.ndarray, np.ndarray]]):
    if pv is None:
        return None
    points: list[tuple[float, float, float]] = []
    point_index: dict[tuple[float, float, float], int] = {}
    lines: list[int] = []

    def add_point(point: np.ndarray) -> int:
        key = _point_key(point)
        existing = point_index.get(key)
        if existing is not None:
            return existing
        point_index[key] = len(points)
        points.append(key)
        return int(point_index[key])

    for p0, p1 in edges:
        i0 = add_point(p0)
        i1 = add_point(p1)
        if i0 == i1:
            continue
        lines.extend((2, i0, i1))
    if not points or not lines:
        return None
    try:
        return pv.PolyData(np.asarray(points, dtype=float), lines=np.asarray(lines, dtype=np.int64))
    except Exception:
        return None


def face_boundary_edges_from_face_index(mesh, *, include_open_boundaries: bool = True):
    """Return true analytic face boundaries from `kraken_step_face_index` data."""
    _surface, triangles, face_index = _surface_triangles_and_face_index(mesh)
    if triangles.size == 0 or face_index.size != triangles.shape[0] or not np.any(face_index >= 0):
        return None
    selected_edges: list[tuple[np.ndarray, np.ndarray]] = []
    for records in _edge_records(triangles, face_index).values():
        faces = {int(face_id) for face_id, _p0, _p1 in records if int(face_id) >= 0}
        if len(faces) > 1 or (include_open_boundaries and len(records) == 1 and faces):
            _face_id, p0, p1 = records[0]
            selected_edges.append((p0, p1))
    return _line_polydata(selected_edges)


# Geometric feature-edge extraction on a heavy vendor body (the 114k-cell
# camera) costs ~0.45 s and yields ~50k edge segments. The display mesh is
# memoised to one stable object per layout pose, so memoise the derived
# edge polydata the same way the surface triangles are (id + content
# token). A genuine pose change rebuilds the mesh, bumps its VTK MTime, and
# invalidates the entry -- so the cost is paid once per layout, never per
# frame, and the heavy-mesh edge skip in the refresh loop is unnecessary.
_DISPLAY_EDGE_CACHE: dict[int, tuple] = {}
_DISPLAY_EDGE_CACHE_ORDER: list[int] = []
_DISPLAY_EDGE_CACHE_MAX = 8


def cached_display_feature_edges(mesh, *, feature_angle: float = 24.0, boundary_edges: bool = True):
    """Memoised :func:`display_feature_edges` keyed on mesh identity + content."""
    if pv is None or mesh is None:
        return None
    key = id(mesh)
    token = (_mesh_cache_token(mesh), round(float(feature_angle), 4), bool(boundary_edges))
    cached = _DISPLAY_EDGE_CACHE.get(key)
    if cached is not None and cached[0] == token:
        return cached[1]
    result = display_feature_edges(mesh, feature_angle=feature_angle, boundary_edges=boundary_edges)
    _DISPLAY_EDGE_CACHE[key] = (token, result)
    if key in _DISPLAY_EDGE_CACHE_ORDER:
        _DISPLAY_EDGE_CACHE_ORDER.remove(key)
    _DISPLAY_EDGE_CACHE_ORDER.append(key)
    while len(_DISPLAY_EDGE_CACHE_ORDER) > _DISPLAY_EDGE_CACHE_MAX:
        evicted = _DISPLAY_EDGE_CACHE_ORDER.pop(0)
        if evicted != key:
            _DISPLAY_EDGE_CACHE.pop(evicted, None)
    return result


def display_feature_edges(mesh, *, feature_angle: float = 24.0, boundary_edges: bool = True):
    """Return face-index boundaries when available, else geometric feature edges."""
    if pv is None or mesh is None:
        return None
    face_edges = face_boundary_edges_from_face_index(mesh, include_open_boundaries=bool(boundary_edges))
    if face_edges is not None and int(getattr(face_edges, "n_points", 0)) > 0:
        return face_edges
    try:
        surface = _drop_invalid_cell_data(mesh).extract_surface(algorithm="dataset_surface").copy(deep=True)
    except Exception:
        try:
            surface = _drop_invalid_cell_data(mesh).copy(deep=True)
        except Exception:
            return None
    try:
        surface = surface.clean(tolerance=1e-6, absolute=True)
    except TypeError:
        try:
            surface = surface.clean(tolerance=1e-6)
        except Exception:
            pass
    except Exception:
        pass
    try:
        edges = surface.extract_feature_edges(
            feature_angle=float(feature_angle),
            boundary_edges=bool(boundary_edges),
            feature_edges=True,
            manifold_edges=False,
        )
    except Exception:
        return None
    try:
        return edges if int(getattr(edges, "n_points", 0)) > 0 else None
    except Exception:
        return None


def face_index_for_record(mesh, face: dict[str, object]) -> int | None:
    """Resolve a normalized face record to its displayed analytic face index."""
    indices = face_indices_for_record(mesh, face)
    return int(indices[0]) if indices else None


def face_indices_for_record(mesh, face: dict[str, object]) -> tuple[int, ...]:
    """Resolve a normalized face record to one or more displayed face indices."""
    _surface, _triangles, face_index = _surface_triangles_and_face_index(mesh)
    if face_index.size == 0:
        return ()
    indices: list[int] = []
    for value in list(face.get("triangle_indices", face.get("cell_indices", ())) or ()):
        try:
            index = int(value)
        except Exception:
            continue
        if 0 <= index < int(face_index.size) and int(face_index[index]) >= 0:
            indices.append(int(face_index[index]))
    if not indices:
        return ()
    return tuple(int(face_id) for face_id, _count in Counter(indices).most_common())


def face_outline_from_face_index(mesh, target_face_index: int):
    """Return only the selected analytic STEP face boundary."""
    return face_outline_from_face_indices(mesh, (target_face_index,))


def face_outline_from_face_indices(mesh, target_face_indices):
    """Return only the selected analytic STEP face-group boundary."""
    try:
        targets = {int(value) for value in target_face_indices}
    except Exception:
        return None
    if not targets:
        return None
    _surface, triangles, face_index = _surface_triangles_and_face_index(mesh)
    if triangles.size == 0 or face_index.size != triangles.shape[0]:
        return None
    selected_edges: list[tuple[np.ndarray, np.ndarray]] = []
    for records in _edge_records(triangles, face_index).values():
        selected_count = sum(1 for face_id, _p0, _p1 in records if int(face_id) in targets)
        if selected_count <= 0:
            continue
        if (
            len(records) == 1
            or selected_count < len(records)
            or any(int(face_id) not in targets for face_id, _p0, _p1 in records)
        ):
            _face_id, p0, p1 = next(
                (record for record in records if int(record[0]) in targets),
                records[0],
            )
            selected_edges.append((p0, p1))
    return _line_polydata(selected_edges)


def face_pick_from_display_mesh(editor, label: str, faces, origin, direction):
    """Pick against the displayed analytic mesh before any STL fallback."""
    try:
        display_mesh = editor._transformed_imported_step_mesh_for_label(str(label).strip().lower())
        triangles, face_index = triangle_array_and_face_index(display_mesh)
        if (
            triangles.ndim == 3
            and triangles.shape[1:] == (3, 3)
            and triangles.shape[0] > 0
            and face_index.shape[0] == triangles.shape[0]
        ):
            return pick_face_from_ray(
                faces,
                triangles,
                origin,
                direction,
                all_points=triangles.reshape((-1, 3)),
                prefer_internal=True,
            )
    except Exception:
        return None
    return None


def face_index_for_display_cell(mesh, cell_id: int) -> int | None:
    """Resolve a VTK-picker cell id straight to its per-cell analytic face index.

    The picker reports ids in the FULL vtkPolyData cell space (verts, then lines,
    then polys) and the ``kraken_step_*face_index`` cell-data arrays are stored in
    that same order, so a direct ``cell_data[cell_id]`` read is picker-aligned even
    when a few stray ``VTK_LINE`` cells (a ``clean()`` artifact) precede the
    polygons. Going through the poly-only triangle array instead would shift every
    id by the stray-line count (the LED clear-aperture window's 14 lines), so the
    cell pick must NOT index the reindexed triangle array. Returns the grouped
    selection face index when present, else the raw face index, else ``None``."""
    if pv is None or mesh is None:
        return None
    try:
        cell_id = int(cell_id)
    except Exception:
        return None
    if cell_id < 0:
        return None
    try:
        surface = pv.wrap(mesh)
        n_cells = int(getattr(surface, "n_cells", 0))
        if cell_id >= n_cells:
            return None
        values = _cell_face_index_values(surface, n_cells)
        if values.shape[0] != n_cells:
            return None
        face_id = int(values[cell_id])
    except Exception:
        return None
    return face_id if face_id >= 0 else None


def _display_cell_centroid(mesh, cell_id: int):
    try:
        points = np.asarray(pv.wrap(mesh).cell_points(int(cell_id)), dtype=float).reshape((-1, 3))
        if points.shape[0] >= 1:
            return np.mean(points, axis=0)
    except Exception:
        return None
    return None


def face_pick_from_display_cell(editor, label: str, faces, cell_id: int, *, pick_point=None) -> FaceRayPick | None:
    """Resolve a VTK-picked displayed cell to its grouped analytic STEP face."""
    try:
        cell_id = int(cell_id)
    except Exception:
        return None
    if cell_id < 0:
        return None
    try:
        display_mesh = editor._transformed_imported_step_mesh_for_label(str(label).strip().lower())
    except Exception:
        return None
    target_face_index = face_index_for_display_cell(display_mesh, cell_id)
    if target_face_index is None:
        return None
    face_record = None
    for face in list(faces or []):
        if not isinstance(face, dict):
            continue
        if target_face_index in set(face_indices_for_record(display_mesh, face)):
            face_record = dict(face)
            break
    if face_record is None:
        return None
    cell_centroid = _display_cell_centroid(display_mesh, cell_id)
    point = None
    try:
        point_candidate = np.asarray(pick_point, dtype=float).reshape(-1)[:3]
        if point_candidate.size >= 3 and np.all(np.isfinite(point_candidate[:3])):
            point = point_candidate[:3]
    except Exception:
        point = None
    if point is None:
        if cell_centroid is None:
            return None
        point = cell_centroid
    try:
        normal = np.asarray(face_record.get("normal_world", face_record.get("normal", ())), dtype=float).reshape(-1)[:3]
    except Exception:
        normal = np.asarray([], dtype=float)
    norm = float(np.linalg.norm(normal[:3])) if normal.size >= 3 else 0.0
    if normal.size < 3 or norm <= 1.0e-12 or not np.isfinite(norm):
        try:
            triangle = np.asarray(pv.wrap(display_mesh).cell_points(int(cell_id)), dtype=float).reshape((-1, 3))[:3]
            normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
            norm = float(np.linalg.norm(normal[:3]))
        except Exception:
            norm = 0.0
    if norm <= 1.0e-12 or not np.isfinite(norm):
        return None
    normal = normal[:3] / norm
    return FaceRayPick(
        face=face_record,
        point_world=tuple(float(value) for value in point[:3]),
        normal_world=tuple(float(value) for value in normal[:3]),
        distance=0.0,
        internal=False,
    )
