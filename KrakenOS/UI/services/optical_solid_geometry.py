"""Optical-solid STL geometry helpers for the layout editor.

This module contains the non-Tk face clustering, face metadata, and STL
transform helpers used by the main layout editor and Open 3D inspector.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI import optical_solid_metadata, stl_geometry
from KrakenOS.UI.surface_table_model import SurfaceRow

StlMeshDiagnostics = stl_geometry.StlMeshDiagnostics


@dataclass(frozen=True)
class OpticalSolidFaceCandidate:
    face_id: str
    normal: tuple[float, float, float]
    centroid: tuple[float, float, float]
    area_mm2: float
    triangle_count: int
    plane_offset_mm: float
    triangle_indices: tuple[int, ...] = ()


@dataclass(frozen=True)
class OpticalSolidFaceMarker:
    face_id: str
    role: str
    centroid: tuple[float, float, float]
    normal: tuple[float, float, float]
    area_mm2: float
    split_ratio: float
    color: tuple[float, float, float]


@dataclass(frozen=True)
class OpticalSolidVirtualPlaneMarker:
    plane_id: str
    kind: str
    centroid: tuple[float, float, float]
    normal: tuple[float, float, float]
    aperture_mm: float
    split_ratio: float
    color: tuple[float, float, float]


def _read_stl_triangle_vertices(path: Path) -> tuple[str, np.ndarray]:
    return stl_geometry.read_stl_triangle_vertices(path)


def inspect_stl_mesh(path: Path) -> StlMeshDiagnostics:
    return stl_geometry.inspect_stl_mesh(path)


def format_stl_mesh_diagnostics(report: StlMeshDiagnostics) -> str:
    return stl_geometry.format_stl_mesh_diagnostics(report)


def short_stl_mesh_diagnostics(report: StlMeshDiagnostics) -> str:
    return stl_geometry.short_stl_mesh_diagnostics(report)


OPTICAL_SOLID_FACES_ADVANCED_ATTR = "OpticalSolidFaces"
OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER = "Beam Splitter"
OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y = "Left + Up (reflect +Y)"
OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_NEG_Y = "Left + Down (reflect -Y)"
OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_VALUES = (
    OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y,
    OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_NEG_Y,
)
OPTICAL_SOLID_FACE_ROLE_DEFAULT = "Unassigned"
OPTICAL_SOLID_FACE_ROLE_VALUES = (
    OPTICAL_SOLID_FACE_ROLE_DEFAULT,
    "Input",
    "Output",
    "TIR",
    "Mirror",
    "Beam Splitter",
    "Absorber/Mechanical",
)
OPTICAL_SOLID_FACE_SIDE_DEFAULT = "Auto"
OPTICAL_SOLID_FACE_SIDE_VALUES = (
    OPTICAL_SOLID_FACE_SIDE_DEFAULT,
    "Left",
    "Right",
    "Up",
    "Down",
    "Front",
    "Back",
)
OPTICAL_SOLID_FACE_FUNCTION_DEFAULT = OPTICAL_SOLID_FACE_ROLE_DEFAULT
OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT = "Transmit/Port"
OPTICAL_SOLID_FACE_FUNCTION_VALUES = optical_solid_metadata.OPTICAL_SOLID_FACE_FUNCTION_UI_VALUES
OPTICAL_SOLID_FACE_PORT_DEFAULT = "Auto"
OPTICAL_SOLID_FACE_PORT_INPUT = "Input Port"
OPTICAL_SOLID_FACE_PORT_OUTPUT = "Output Port"
OPTICAL_SOLID_FACE_PORT_INTERACTION = "Interaction Surface"
OPTICAL_SOLID_FACE_PORT_VALUES = (
    OPTICAL_SOLID_FACE_PORT_DEFAULT,
    OPTICAL_SOLID_FACE_PORT_INPUT,
    OPTICAL_SOLID_FACE_PORT_OUTPUT,
    OPTICAL_SOLID_FACE_PORT_INTERACTION,
)
OPTICAL_SOLID_FACE_ASSIGNMENT_DEFAULT_UNCOATED = "default_uncoated"
OPTICAL_SOLID_FACE_ASSIGNMENT_MANUAL = "manual"
OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT = "Auto side labels"
OPTICAL_SOLID_FACE_FIT_ROLL_NONE = "No roll constraint"
OPTICAL_SOLID_FACE_FIT_ROLL_VALUES = (
    OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT,
    OPTICAL_SOLID_FACE_FIT_ROLL_NONE,
)
OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT = "Auto"
OPTICAL_SOLID_FACE_FIT_REFERENCE_VALUES = (
    OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT,
    "+Y normal",
    "-Y normal",
    "+Z normal",
    "-Z normal",
    "+X normal",
    "-X normal",
)
OPTICAL_SOLID_FACE_ROLE_COLORS = {
    OPTICAL_SOLID_FACE_ROLE_DEFAULT: (0.42, 0.45, 0.50),
    "Input": (0.08, 0.62, 0.24),
    "Output": (0.08, 0.36, 0.88),
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT: (0.08, 0.36, 0.88),
    "TIR": (0.08, 0.36, 0.88),
    "Mirror": (0.66, 0.70, 0.76),
    "Beam Splitter": (0.88, 0.18, 0.22),
    "Absorber/Mechanical": (0.12, 0.14, 0.18),
}
OPTICAL_SOLID_VIRTUAL_PLANE_KIND_VALUES = (OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER,)
OPTICAL_SOLID_VIRTUAL_PLANE_KIND_COLORS = {
    OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER: (0.88, 0.18, 0.22),
}


def _normalize_optical_solid_face_side(value: object) -> str:
    return optical_solid_metadata.normalize_optical_solid_face_side(value)


def _normalize_optical_solid_face_function(value: object, *, legacy_role: object = None) -> str:
    return optical_solid_metadata.normalize_optical_solid_face_function(value, legacy_role=legacy_role)


def _optical_solid_face_function_from_ui_value(value: object, *, legacy_role: object = None) -> str:
    return optical_solid_metadata.optical_solid_face_function_from_ui_value(value, legacy_role=legacy_role)


def _optical_solid_face_function_display(value: object, *, legacy_role: object = None) -> str:
    return optical_solid_metadata.optical_solid_face_function_display(value, legacy_role=legacy_role)


def _normalize_optical_solid_face_port_role(value: object) -> str:
    return optical_solid_metadata.normalize_optical_solid_face_port_role(value)


def _normalize_optical_solid_face_fit_reference(value: object) -> str:
    return optical_solid_metadata.normalize_optical_solid_face_fit_reference(value)


def _optical_solid_face_port_role(face: dict[str, object]) -> str:
    return optical_solid_metadata.optical_solid_face_port_role(face)


def _optical_solid_face_authored_port_role(face: dict[str, object]) -> str:
    return optical_solid_metadata.normalize_optical_solid_face_port_role(face.get("port_role", face.get("port")))


def _legacy_role_from_optical_solid_face_function(function: object) -> str:
    return optical_solid_metadata.legacy_role_from_optical_solid_face_function(function)


def _normalize_optical_solid_virtual_plane_kind(value: object) -> str:
    return optical_solid_metadata.normalize_optical_solid_virtual_plane_kind(value)


def _normalize_optical_solid_virtual_plane_diagonal(value: object) -> str:
    return optical_solid_metadata.normalize_optical_solid_virtual_plane_diagonal(value)


def optical_solid_virtual_plane_color(kind: object) -> tuple[float, float, float]:
    return optical_solid_metadata.optical_solid_virtual_plane_color(kind)


def _optical_solid_face_marker_label(face: dict[str, object]) -> str:
    return optical_solid_metadata.optical_solid_face_marker_label(face)


def optical_solid_face_role_color(role: object) -> tuple[float, float, float]:
    return optical_solid_metadata.optical_solid_face_role_color(role)


def _float_or_default(value, default: float = 0.0) -> float:
    return optical_solid_metadata.float_or_default(value, default)


def _unit_vector_tuple(value) -> tuple[float, float, float]:
    return optical_solid_metadata.unit_vector_tuple(value)


def _point3_tuple(value) -> tuple[float, float, float]:
    return optical_solid_metadata.point3_tuple(value)


def _canonical_optical_solid_plane(normal, plane_offset: float) -> tuple[np.ndarray, float]:
    """Return a sign-stable plane normal/offset pair for face grouping."""
    plane_normal = np.asarray(_unit_vector_tuple(normal), dtype=float).reshape(3)
    offset = _float_or_default(plane_offset, 0.0)
    pivot = int(np.argmax(np.abs(plane_normal)))
    if float(plane_normal[pivot]) < 0.0:
        plane_normal = -plane_normal
        offset = -offset
    return plane_normal, float(offset)


def _optical_solid_face_records_share_plane(
    face: dict[str, object],
    target: dict[str, object],
    *,
    extent_mm: float,
) -> bool:
    face_normal, face_offset = _canonical_optical_solid_plane(
        face.get("normal", (0.0, 0.0, 1.0)),
        _float_or_default(face.get("plane_offset_mm"), 0.0),
    )
    target_normal, target_offset = _canonical_optical_solid_plane(
        target.get("normal", (0.0, 0.0, 1.0)),
        _float_or_default(target.get("plane_offset_mm"), 0.0),
    )
    normal_alignment = abs(float(np.dot(face_normal, target_normal)))
    plane_tolerance = max(abs(float(extent_mm)) * 2.0e-4, 0.02)
    return normal_alignment >= 0.999 and abs(float(face_offset - target_offset)) <= plane_tolerance


def _optical_solid_face_metadata_extent(faces: list[dict[str, object]], row: SurfaceRow | None = None) -> float:
    extents: list[float] = [1.0]
    centroids: list[np.ndarray] = []
    for face in faces:
        try:
            centroid = np.asarray(face.get("centroid", (0.0, 0.0, 0.0)), dtype=float).reshape(-1)[:3]
        except Exception:
            continue
        if centroid.size == 3 and np.all(np.isfinite(centroid)):
            centroids.append(centroid)
        area = _float_or_default(face.get("area_mm2"), 0.0)
        if area > 0.0:
            extents.append(float(np.sqrt(area)))
    if centroids:
        points = np.asarray(centroids, dtype=float)
        extents.append(float(np.max(np.ptp(points, axis=0))))
    if row is not None:
        for value in (
            getattr(row, "diameter", 0.0),
            getattr(row, "thickness", 0.0),
            getattr(row, "desp_x", 0.0),
            getattr(row, "desp_y", 0.0),
            getattr(row, "desp_z", 0.0),
        ):
            parsed = abs(_float_or_default(value, 0.0))
            if parsed > 0.0:
                extents.append(parsed)
    finite = [value for value in extents if np.isfinite(float(value)) and float(value) > 0.0]
    return max(finite, default=1.0)


def cluster_optical_solid_planar_faces(path: Path, *, max_faces: int = 160) -> list[OpticalSolidFaceCandidate]:
    """Cluster STL triangles into approximate planar face candidates."""
    _file_format, triangles = _read_stl_triangle_vertices(Path(path).expanduser())
    if triangles.size == 0:
        return []
    flat = triangles.reshape((-1, 3))
    extents = np.ptp(flat, axis=0)
    max_extent = max(float(np.max(extents)), 1.0)
    area_tol = max(max_extent * max_extent * 1e-18, 1e-24)
    plane_decimals = 4 if max_extent < 100.0 else 3
    normal_decimals = 4
    groups: dict[tuple[tuple[float, float, float], float], dict[str, object]] = {}
    for triangle_index, tri in enumerate(triangles):
        v0, v1, v2 = (np.asarray(vertex, dtype=float) for vertex in tri)
        cross = np.cross(v1 - v0, v2 - v0)
        area = 0.5 * float(np.linalg.norm(cross))
        if area <= area_tol or not np.isfinite(area):
            continue
        normal = cross / max(float(np.linalg.norm(cross)), 1e-12)
        centroid = (v0 + v1 + v2) / 3.0
        plane_offset = float(np.dot(normal, centroid))
        canonical_normal, canonical_plane_offset = _canonical_optical_solid_plane(normal, plane_offset)
        key = (
            tuple(float(v) for v in np.round(canonical_normal, normal_decimals)),
            float(np.round(canonical_plane_offset, plane_decimals)),
        )
        entry = groups.setdefault(
            key,
            {
                "normal_weighted": np.zeros(3, dtype=float),
                "centroid_weighted": np.zeros(3, dtype=float),
                "area": 0.0,
                "triangles": 0,
                "plane_offset_weighted": 0.0,
                "triangle_indices": [],
                "reference_normal": np.asarray(normal, dtype=float),
            },
        )
        reference_normal = np.asarray(entry.get("reference_normal", normal), dtype=float).reshape(3)
        oriented_normal = np.asarray(normal, dtype=float)
        if float(np.dot(oriented_normal, reference_normal)) < 0.0:
            oriented_normal = -oriented_normal
        oriented_plane_offset = float(np.dot(oriented_normal, centroid))
        entry["normal_weighted"] = np.asarray(entry["normal_weighted"], dtype=float) + oriented_normal * area
        entry["centroid_weighted"] = np.asarray(entry["centroid_weighted"], dtype=float) + centroid * area
        entry["area"] = float(entry["area"]) + area
        entry["triangles"] = int(entry["triangles"]) + 1
        entry["plane_offset_weighted"] = float(entry["plane_offset_weighted"]) + oriented_plane_offset * area
        entry["triangle_indices"].append(int(triangle_index))

    candidates: list[OpticalSolidFaceCandidate] = []
    sorted_entries = sorted(groups.values(), key=lambda item: float(item["area"]), reverse=True)
    for index, entry in enumerate(sorted_entries[: max(1, int(max_faces))], start=1):
        area = max(float(entry["area"]), 1e-12)
        normal = _unit_vector_tuple(np.asarray(entry["normal_weighted"], dtype=float) / area)
        centroid = _point3_tuple(np.asarray(entry["centroid_weighted"], dtype=float) / area)
        plane_offset = float(entry["plane_offset_weighted"]) / area
        candidates.append(
            OpticalSolidFaceCandidate(
                face_id=f"F{index:03d}",
                normal=normal,
                centroid=centroid,
                area_mm2=float(area),
                triangle_count=int(entry["triangles"]),
                plane_offset_mm=float(plane_offset),
                triangle_indices=tuple(int(value) for value in list(entry.get("triangle_indices", []) or [])),
            )
        )
    return candidates


def group_optical_solid_face_candidates(path: Path, faces, *, angle_deg: float = 35.0) -> list[int]:
    """Assign a display group id to each planar face candidate by mesh
    connectivity + normal continuity.

    ``cluster_optical_solid_planar_faces`` fragments a *curved* surface (an
    aspheric/spherical lens face) into one micro-cluster per triangle, so a
    single lens can list ~160 candidates. Connectivity region-growing -- add an
    edge-adjacent triangle to the same region when its normal is within
    ``angle_deg`` of its neighbour -- collapses each smooth surface into one
    region while still splitting at sharp dihedral edges (face boundaries). This
    is **display-only**: the candidates and their planar fits are unchanged; the
    returned ids just let the face editor group rows so a whole curved surface
    can be role-assigned at once. Returns a list of group ids parallel to
    ``faces`` (each item is an ``OpticalSolidFaceCandidate`` or a record dict
    carrying ``triangle_indices``), renumbered 0..k-1 by descending member count.
    """
    faces = list(faces or [])
    if not faces:
        return []
    _file_format, triangles = _read_stl_triangle_vertices(Path(path).expanduser())
    n_tris = int(triangles.shape[0]) if triangles.size else 0
    if n_tris == 0:
        return list(range(len(faces)))

    v0, v1, v2 = triangles[:, 0, :], triangles[:, 1, :], triangles[:, 2, :]
    cross = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(cross, axis=1)
    valid = norms > 1e-12
    normals = np.zeros((n_tris, 3), dtype=float)
    normals[valid] = cross[valid] / norms[valid][:, None]

    flat = triangles.reshape((-1, 3))
    max_extent = max(float(np.max(np.ptp(flat, axis=0))), 1.0)
    merge_decimals = 5 if max_extent < 100.0 else 4
    quantized = np.round(flat, merge_decimals)
    _unique, inverse = np.unique(quantized, axis=0, return_inverse=True)
    tri_vertex_ids = np.asarray(inverse, dtype=np.int64).reshape(n_tris, 3)

    from collections import defaultdict

    edge_triangles: dict[tuple[int, int], list[int]] = defaultdict(list)
    for tri_index in range(n_tris):
        if not valid[tri_index]:
            continue
        a, b, c = (int(v) for v in tri_vertex_ids[tri_index])
        for u, w in ((a, b), (b, c), (c, a)):
            edge_triangles[(min(u, w), max(u, w))].append(tri_index)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for shared in edge_triangles.values():
        for i in range(len(shared)):
            for j in range(i + 1, len(shared)):
                adjacency[shared[i]].add(shared[j])
                adjacency[shared[j]].add(shared[i])

    cos_threshold = float(np.cos(np.deg2rad(angle_deg)))
    region = np.full(n_tris, -1, dtype=int)
    next_region = 0
    for seed in range(n_tris):
        if region[seed] != -1 or not valid[seed]:
            continue
        region[seed] = next_region
        stack = [seed]
        while stack:
            current = stack.pop()
            for neighbour in adjacency.get(current, ()):  # type: ignore[arg-type]
                if region[neighbour] != -1 or not valid[neighbour]:
                    continue
                if float(np.dot(normals[current], normals[neighbour])) >= cos_threshold:
                    region[neighbour] = next_region
                    stack.append(neighbour)
        next_region += 1

    def _triangle_indices(face) -> list[int]:
        raw = getattr(face, "triangle_indices", None)
        if raw is None and isinstance(face, dict):
            raw = face.get("triangle_indices", face.get("cell_indices"))
        out: list[int] = []
        for value in raw or ():
            try:
                idx = int(value)
            except Exception:
                continue
            if 0 <= idx < n_tris and region[idx] >= 0:
                out.append(idx)
        return out

    raw_group_per_face: list[int] = []
    for face in faces:
        indices = _triangle_indices(face)
        if not indices:
            raw_group_per_face.append(-1)
            continue
        values, counts = np.unique(region[np.asarray(indices, dtype=int)], return_counts=True)
        raw_group_per_face.append(int(values[int(np.argmax(counts))]))

    # Renumber groups 0..k-1 by descending number of member faces so the
    # biggest logical surfaces get the lowest, stable labels (-1 stays -1).
    from collections import Counter

    order = [g for g, _ in Counter(g for g in raw_group_per_face if g >= 0).most_common()]
    remap = {g: i for i, g in enumerate(order)}
    return [remap.get(g, -1) for g in raw_group_per_face]


def optical_solid_face_candidate_triangles(path: Path, candidate: OpticalSolidFaceCandidate) -> np.ndarray:
    """Return STL triangles that belong to a clustered planar face candidate."""
    _file_format, triangles = _read_stl_triangle_vertices(Path(path).expanduser())
    if triangles.size == 0:
        return np.empty((0, 3, 3), dtype=float)
    triangle_indices_list: list[int] = []
    for value in getattr(candidate, "triangle_indices", ()) or ():
        try:
            triangle_index = int(value)
        except Exception:
            continue
        if 0 <= triangle_index < int(triangles.shape[0]):
            triangle_indices_list.append(triangle_index)
    triangle_indices = tuple(triangle_indices_list)
    if triangle_indices:
        return np.asarray(triangles[np.asarray(triangle_indices, dtype=int)], dtype=float)
    flat = triangles.reshape((-1, 3))
    extents = np.ptp(flat, axis=0)
    max_extent = max(float(np.max(extents)), 1.0)
    area_tol = max(max_extent * max_extent * 1e-18, 1e-24)
    plane_tol = max(max_extent * 1e-4, 0.02)
    normal_tol = 0.999
    candidate_normal = np.asarray(_unit_vector_tuple(candidate.normal), dtype=float)
    candidate_offset = float(candidate.plane_offset_mm)
    selected: list[np.ndarray] = []
    for tri in triangles:
        v0, v1, v2 = (np.asarray(vertex, dtype=float) for vertex in tri)
        cross = np.cross(v1 - v0, v2 - v0)
        norm = float(np.linalg.norm(cross))
        area = 0.5 * norm
        if area <= area_tol or not np.isfinite(area) or norm <= 1e-12:
            continue
        normal = cross / norm
        centroid = (v0 + v1 + v2) / 3.0
        if float(np.dot(normal, candidate_normal)) < normal_tol:
            continue
        if abs(float(np.dot(candidate_normal, centroid)) - candidate_offset) > plane_tol:
            continue
        selected.append(np.asarray(tri, dtype=float))
    if not selected:
        return np.empty((0, 3, 3), dtype=float)
    return np.asarray(selected, dtype=float)


def optical_solid_face_record_triangles(path: Path, record: dict[str, object]) -> np.ndarray:
    """Return STL triangles for a face record via its ``triangle_indices``.

    The B-Rep path writes the displayed STL from the same OCC tessellation that
    produced the face metadata, so a face's ``triangle_indices`` select that
    face's exact triangles -- no plane re-derivation, unlike the cluster path.
    """
    _file_format, triangles = _read_stl_triangle_vertices(Path(path).expanduser())
    if triangles.size == 0:
        return np.empty((0, 3, 3), dtype=float)
    count = int(triangles.shape[0])
    indices: list[int] = []
    for value in (record or {}).get("triangle_indices", ()) or ():
        try:
            index = int(value)
        except Exception:
            continue
        if 0 <= index < count:
            indices.append(index)
    if not indices:
        return np.empty((0, 3, 3), dtype=float)
    return np.asarray(triangles[np.asarray(indices, dtype=int)], dtype=float)


def optical_solid_metadata_is_brep(metadata: dict[str, object] | None) -> bool:
    """True if face metadata carries native B-Rep faces (any face has a surface_type).

    Cluster candidates never set ``surface_type``; the OCC analytic path always
    does, and ``surface_type`` survives metadata normalization, so its presence
    is the durable marker that the editor should trust the saved faces verbatim
    instead of re-clustering the STL.
    """
    if not isinstance(metadata, dict):
        return False
    faces = metadata.get("faces")
    if not isinstance(faces, (list, tuple)):
        return False
    return any(
        isinstance(face, dict) and str(face.get("surface_type") or "").strip()
        for face in faces
    )


def optical_solid_face_record_from_candidate(candidate: OpticalSolidFaceCandidate) -> dict[str, object]:
    return optical_solid_metadata.optical_solid_face_record_from_candidate(candidate)


def normalize_optical_solid_face_record(record: dict[str, object]) -> dict[str, object]:
    return optical_solid_metadata.normalize_optical_solid_face_record(record)


def normalize_optical_solid_virtual_plane_record(record: dict[str, object]) -> dict[str, object]:
    return optical_solid_metadata.normalize_optical_solid_virtual_plane_record(record)


def normalize_optical_solid_face_metadata(
    value,
    candidates: list[OpticalSolidFaceCandidate] | None = None,
    *,
    source_stl: str = "",
) -> dict[str, object]:
    return optical_solid_metadata.normalize_optical_solid_face_metadata(value, candidates, source_stl=source_stl)


def auto_assign_optical_solid_face_roles(records: list[dict[str, object]]) -> list[dict[str, object]]:
    return optical_solid_metadata.auto_assign_optical_solid_face_roles(records)


def suggest_optical_solid_face_roles(
    records: list[dict[str, object]],
    *,
    incoming_direction=(0.0, 0.0, 1.0),
    ray_points=None,
) -> list[dict[str, object]]:
    return optical_solid_metadata.suggest_optical_solid_face_roles(
        records,
        incoming_direction=incoming_direction,
        ray_points=ray_points,
    )


def apply_optical_solid_face_suggestions(
    records: list[dict[str, object]],
    *,
    incoming_direction=(0.0, 0.0, 1.0),
    ray_points=None,
    overwrite: bool = False,
) -> list[dict[str, object]]:
    return optical_solid_metadata.apply_optical_solid_face_suggestions(
        records,
        incoming_direction=incoming_direction,
        ray_points=ray_points,
        overwrite=overwrite,
    )


def _optical_solid_face_suggestion_label(face: dict[str, object]) -> str:
    return optical_solid_metadata.optical_solid_face_suggestion_label(face)


def _optical_solid_face_by_side(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
    side: str,
) -> dict[str, object] | None:
    return optical_solid_metadata.optical_solid_face_by_side(metadata, side)


def _optical_solid_virtual_plane_center_from_faces(faces: list[dict[str, object]]) -> np.ndarray:
    return optical_solid_metadata.optical_solid_virtual_plane_center_from_faces(faces)


def build_optical_solid_cube_splitter_virtual_plane(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    diagonal_mode: str = OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y,
    split_ratio: float = 0.5,
    loss: float = 0.0,
    phase_deg: float = 0.0,
    aperture_mm: float = 0.0,
    notes: str = "",
    plane_id: str = "VP001",
) -> dict[str, object]:
    return optical_solid_metadata.build_optical_solid_cube_splitter_virtual_plane(
        metadata,
        diagonal_mode=diagonal_mode,
        split_ratio=split_ratio,
        loss=loss,
        phase_deg=phase_deg,
        aperture_mm=aperture_mm,
        notes=notes,
        plane_id=plane_id,
    )


def optical_solid_has_virtual_splitter_plane(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...]
) -> bool:
    return optical_solid_metadata.optical_solid_has_virtual_splitter_plane(metadata)


STL_AXIS_TO_LAYOUT_Z_TILTS = {
    "+Z": (0.0, 0.0, 0.0),
    "-Z": (180.0, 0.0, 0.0),
    "+Y": (90.0, 0.0, 0.0),
    "-Y": (-90.0, 0.0, 0.0),
    "+X": (0.0, -90.0, 0.0),
    "-X": (0.0, 90.0, 0.0),
}


def _rotation_matrix_from_kraken_tilts(tilt_x: float, tilt_y: float, tilt_z: float) -> np.ndarray:
    return optical_solid_metadata.rotation_matrix_from_kraken_tilts(tilt_x, tilt_y, tilt_z)


def optical_solid_face_world_markers(
    row: SurfaceRow,
    z_station: float,
    *,
    assigned_only: bool = True,
) -> list[OpticalSolidFaceMarker]:
    """Return saved CAD/STL face roles transformed into layout coordinates."""
    world_faces = optical_solid_face_world_records(row, z_station, assigned_only=assigned_only)
    markers: list[OpticalSolidFaceMarker] = []
    for face in world_faces:
        role = _legacy_role_from_optical_solid_face_function(face.get("function", face.get("role")))
        markers.append(
            OpticalSolidFaceMarker(
                face_id=str(face.get("face_id", "") or ""),
                role=_optical_solid_face_marker_label(face),
                centroid=tuple(float(v) for v in np.asarray(face.get("centroid_world", (0.0, 0.0, 0.0)), dtype=float)[:3]),
                normal=tuple(float(v) for v in np.asarray(face.get("normal_world", (0.0, 0.0, 1.0)), dtype=float)[:3]),
                area_mm2=max(_float_or_default(face.get("area_mm2"), 0.0), 0.0),
                split_ratio=float(np.clip(_float_or_default(face.get("split_ratio"), 0.5), 0.0, 1.0)),
                color=optical_solid_face_role_color(role),
            )
        )
    return markers


def optical_solid_face_world_records(
    row: SurfaceRow,
    z_station: float,
    *,
    assigned_only: bool = True,
) -> list[dict[str, object]]:
    """Return saved CAD/STL face-role records transformed into layout coordinates."""
    return optical_solid_metadata.optical_solid_face_world_records(row, z_station, assigned_only=assigned_only)


def optical_solid_virtual_plane_world_markers(
    row: SurfaceRow,
    z_station: float,
    *,
    assigned_only: bool = True,
) -> list[OpticalSolidVirtualPlaneMarker]:
    world_planes = optical_solid_virtual_plane_world_records(row, z_station, assigned_only=assigned_only)
    markers: list[OpticalSolidVirtualPlaneMarker] = []
    for plane in world_planes:
        kind = _normalize_optical_solid_virtual_plane_kind(plane.get("kind"))
        markers.append(
            OpticalSolidVirtualPlaneMarker(
                plane_id=str(plane.get("plane_id", "") or ""),
                kind=kind,
                centroid=tuple(float(v) for v in np.asarray(plane.get("point_world", (0.0, 0.0, 0.0)), dtype=float)[:3]),
                normal=tuple(float(v) for v in np.asarray(plane.get("normal_world", (0.0, 0.0, 1.0)), dtype=float)[:3]),
                aperture_mm=max(_float_or_default(plane.get("aperture_mm"), 0.0), 0.0),
                split_ratio=float(np.clip(_float_or_default(plane.get("split_ratio"), 0.5), 0.0, 1.0)),
                color=optical_solid_virtual_plane_color(kind),
            )
        )
    return markers


def optical_solid_virtual_plane_world_records(
    row: SurfaceRow,
    z_station: float,
    *,
    assigned_only: bool = True,
) -> list[dict[str, object]]:
    return optical_solid_metadata.optical_solid_virtual_plane_world_records(row, z_station, assigned_only=assigned_only)


def _optical_solid_face_effective_radius_mm(face: dict[str, object]) -> float:
    return optical_solid_metadata.optical_solid_face_effective_radius_mm(face)


def match_optical_solid_world_face(
    world_faces: list[dict[str, object]],
    point_world,
    normal_world=None,
) -> dict[str, object] | None:
    return optical_solid_metadata.match_optical_solid_world_face(world_faces, point_world, normal_world)


def _optical_solid_plane_basis(normal_world) -> tuple[np.ndarray, np.ndarray]:
    return optical_solid_metadata.optical_solid_plane_basis(normal_world)


def optical_solid_virtual_plane_segment_events(
    world_planes: list[dict[str, object]],
    start_point_world,
    end_point_world,
    *,
    tolerance_mm: float = 1e-6,
) -> list[dict[str, object]]:
    return optical_solid_metadata.optical_solid_virtual_plane_segment_events(
        world_planes,
        start_point_world,
        end_point_world,
        tolerance_mm=tolerance_mm,
    )


def optical_solid_trace_sequence_records(
    row: SurfaceRow,
    z_station: float,
    hit_points_world,
    hit_normals_world=None,
    *,
    assigned_only: bool = True,
    include_virtual_planes: bool = True,
) -> list[dict[str, object]]:
    return optical_solid_metadata.optical_solid_trace_sequence_records(
        row,
        z_station,
        hit_points_world,
        hit_normals_world,
        assigned_only=assigned_only,
        include_virtual_planes=include_virtual_planes,
    )


def _rotation_matrix_about_axis(axis: np.ndarray, angle_rad: float) -> np.ndarray:
    return optical_solid_metadata.rotation_matrix_about_axis(axis, angle_rad)


def _rotation_matrix_aligning_vectors(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    return optical_solid_metadata.rotation_matrix_aligning_vectors(source, target)


def _optical_solid_face_local_normal(face: dict[str, object]) -> np.ndarray:
    return optical_solid_metadata.optical_solid_face_local_normal(face)


def _optical_solid_face_fit_priority(face: dict[str, object]) -> tuple[float, float, float]:
    return optical_solid_metadata.optical_solid_face_fit_priority(face)


def select_optical_solid_anchor_face(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    face_id: str = "",
) -> dict[str, object] | None:
    return optical_solid_metadata.select_optical_solid_anchor_face(metadata, face_id=face_id)


def _select_optical_solid_roll_reference_face(
    metadata: dict[str, object],
    anchor_face_id: str,
) -> tuple[dict[str, object], str] | None:
    return optical_solid_metadata.select_optical_solid_roll_reference_face(metadata, anchor_face_id)


def solve_optical_solid_face_fit(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    face_id: str = "",
    target_normal: tuple[float, float, float] = (0.0, 0.0, 1.0),
    target_point: tuple[float, float, float] = (0.0, 0.0, 0.0),
    roll_mode: str = OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT,
) -> dict[str, object] | None:
    return optical_solid_metadata.solve_optical_solid_face_fit(
        metadata,
        face_id=face_id,
        target_normal=target_normal,
        target_point=target_point,
        roll_mode=roll_mode,
    )


def solve_optical_solid_two_face_fit(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    anchor_face_id: str,
    guide_face_id: str,
    target_anchor_normal,
    target_guide_normal,
    target_point=(0.0, 0.0, 0.0),
) -> dict[str, object] | None:
    return optical_solid_metadata.solve_optical_solid_two_face_fit(
        metadata,
        anchor_face_id=anchor_face_id,
        guide_face_id=guide_face_id,
        target_anchor_normal=target_anchor_normal,
        target_guide_normal=target_guide_normal,
        target_point=target_point,
    )


def solve_optical_solid_left_input_pose(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    target_point: tuple[float, float, float] = (0.0, 0.0, 0.0),
    roll_mode: str = OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT,
) -> dict[str, object] | None:
    return optical_solid_metadata.solve_optical_solid_left_input_pose(
        metadata,
        target_point=target_point,
        roll_mode=roll_mode,
    )


def rotated_stl_bounds(path: Path, tilts: tuple[float, float, float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return stl_geometry.rotated_stl_bounds(path, tilts)


def transformed_stl_points(
    path: Path,
    tilts: tuple[float, float, float],
    desp: tuple[float, float, float],
    z_station: float,
) -> np.ndarray:
    return stl_geometry.transformed_stl_points(path, tilts, desp, z_station)


def transformed_stl_bounds(
    path: Path,
    tilts: tuple[float, float, float],
    desp: tuple[float, float, float],
    z_station: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return stl_geometry.transformed_stl_bounds(path, tilts, desp, z_station)


def convex_hull_2d(points: np.ndarray) -> np.ndarray:
    return stl_geometry.convex_hull_2d(points)
