from __future__ import annotations

import itertools
from types import SimpleNamespace

import numpy as np

from KrakenOS.UI import optical_solid_metadata
from KrakenOS.UI.optical_solid_metadata import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    OPTICAL_SOLID_FACE_PORT_DEFAULT,
    OPTICAL_SOLID_FACE_PORT_INPUT,
    OPTICAL_SOLID_FACE_PORT_OUTPUT,
    OPTICAL_SOLID_FACE_PORT_INTERACTION,
    OPTICAL_SOLID_FACE_ROLE_DEFAULT,
    OPTICAL_SOLID_FACE_SIDE_DEFAULT,
    legacy_role_from_optical_solid_face_function,
    normalize_optical_solid_face_function,
    normalize_optical_solid_face_record,
    normalize_optical_solid_face_metadata,
    normalize_optical_solid_face_port_role,
    normalize_optical_solid_face_side,
    optical_solid_face_port_role,
    optical_solid_face_world_records,
    point3_tuple,
    unit_vector_tuple,
)
from KrakenOS.UI.scene_builder import build_scene_boundary_face_index, build_scene_optical_volume_index


def _row_like(row):
    if isinstance(row, dict):
        return SimpleNamespace(
            surface=str(row.get("surface", "") or ""),
            name=str(row.get("name", "") or row.get("Name", "") or ""),
            glass=str(row.get("glass", row.get("Glass", "")) or ""),
            thickness=float(row.get("thickness", 0.0) or 0.0),
            diameter=float(row.get("diameter", 0.0) or 0.0),
            advanced=row.get("advanced", {}) if isinstance(row.get("advanced", {}), dict) else {},
            tilt_x=float(row.get("tilt_x", 0.0) or 0.0),
            tilt_y=float(row.get("tilt_y", 0.0) or 0.0),
            tilt_z=float(row.get("tilt_z", 0.0) or 0.0),
            desp_x=float(row.get("desp_x", 0.0) or 0.0),
            desp_y=float(row.get("desp_y", 0.0) or 0.0),
            desp_z=float(row.get("desp_z", 0.0) or 0.0),
        )
    return row


def _row_surface(row) -> str:
    if isinstance(row, dict):
        return str(row.get("surface", "") or "").strip()
    return str(getattr(row, "surface", "") or "").strip()


def _row_advanced(row) -> dict[str, object]:
    if isinstance(row, dict):
        advanced = row.get("advanced", {})
        return dict(advanced) if isinstance(advanced, dict) else {}
    advanced = getattr(row, "advanced", {})
    return dict(advanced) if isinstance(advanced, dict) else {}


def _row_has_optical_solid(row) -> bool:
    advanced = _row_advanced(row)
    value = advanced.get("Solid_3d_stl")
    return str(value or "").strip() not in {"", "None"}


def row_z_positions(rows) -> list[float]:
    prepared = [_row_like(row) for row in list(rows or [])]
    if not prepared:
        return []
    z_positions: list[float] = [0.0]
    z_pos = 0.0
    for row in prepared[:-1]:
        z_pos += float(getattr(row, "thickness", 0.0) or 0.0)
        z_positions.append(z_pos)
    while len(z_positions) < len(prepared):
        z_positions.append(z_pos)
    return z_positions


def _scene_index_rows(system, rows) -> list[object]:
    prepared = [_row_like(row) for row in list(rows or [])]
    surfaces = list(getattr(system, "SDT", []) or []) if system is not None else []
    for index, row in enumerate(prepared):
        if not (0 <= index < len(surfaces)):
            continue
        surface = surfaces[index]
        if not str(getattr(row, "glass", "") or "").strip():
            try:
                setattr(row, "glass", str(getattr(surface, "Glass", "") or ""))
            except Exception:
                pass
        if not str(getattr(row, "name", "") or "").strip():
            try:
                setattr(row, "name", str(getattr(surface, "Name", "") or ""))
            except Exception:
                pass
    return prepared


def _output_face_sort_key(face: dict[str, object]) -> tuple[float, float]:
    side_priority = {"Down": 6.0, "Up": 5.0, "Right": 4.0, "Back": 3.0, "Front": 2.0, "Left": 1.0}
    return (
        float(side_priority.get(normalize_optical_solid_face_side(face.get("side_2d")), 0.0)),
        float(face.get("area_mm2", 0.0) or 0.0),
    )


def select_optical_solid_explicit_output_face(world_faces: list[dict[str, object]]) -> dict[str, object] | None:
    explicit_output_faces: list[dict[str, object]] = []
    for face in list(world_faces or []):
        if not isinstance(face, dict):
            continue
        if normalize_optical_solid_face_port_role(face.get("port_role", face.get("port"))) != OPTICAL_SOLID_FACE_PORT_OUTPUT:
            continue
        if optical_solid_face_port_role(face) == OPTICAL_SOLID_FACE_PORT_OUTPUT:
            explicit_output_faces.append(face)
    if not explicit_output_faces:
        return None
    return max(explicit_output_faces, key=_output_face_sort_key)


def select_optical_solid_explicit_input_face(world_faces: list[dict[str, object]]) -> dict[str, object] | None:
    explicit_input_faces: list[dict[str, object]] = []
    for face in list(world_faces or []):
        if not isinstance(face, dict):
            continue
        if normalize_optical_solid_face_port_role(face.get("port_role", face.get("port"))) != OPTICAL_SOLID_FACE_PORT_INPUT:
            continue
        if optical_solid_face_port_role(face) == OPTICAL_SOLID_FACE_PORT_INPUT:
            explicit_input_faces.append(face)
    if not explicit_input_faces:
        return None
    return max(explicit_input_faces, key=lambda face: float(face.get("area_mm2", 0.0) or 0.0))


def select_optical_solid_output_face(world_faces: list[dict[str, object]]) -> dict[str, object] | None:
    explicit_output_faces: list[dict[str, object]] = []
    inferred_output_faces: list[dict[str, object]] = []
    for face in list(world_faces or []):
        if not isinstance(face, dict):
            continue
        port_role = optical_solid_face_port_role(face)
        explicit_port = normalize_optical_solid_face_port_role(face.get("port_role", face.get("port")))
        if port_role == OPTICAL_SOLID_FACE_PORT_OUTPUT:
            if explicit_port == OPTICAL_SOLID_FACE_PORT_OUTPUT:
                explicit_output_faces.append(face)
            else:
                inferred_output_faces.append(face)
            continue
        function = normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
        side = normalize_optical_solid_face_side(face.get("side_2d"))
        if (
            function == OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT
            and side != "Left"
            and explicit_port == OPTICAL_SOLID_FACE_PORT_DEFAULT
        ):
            inferred_output_faces.append(face)
    pool = explicit_output_faces or inferred_output_faces
    if not pool:
        return None
    return max(pool, key=_output_face_sort_key)


def _optical_solid_face_function(face: dict[str, object]) -> str:
    return normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))


def _is_uncoated_interaction_function(function: str) -> bool:
    return function in {OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT, "TIR"}


def _is_specular_fold_interaction_face(face: dict[str, object]) -> bool:
    if optical_solid_face_port_role(face) != OPTICAL_SOLID_FACE_PORT_INTERACTION:
        return False
    function = _optical_solid_face_function(face)
    return function == "Mirror" or _is_uncoated_interaction_function(function)


def _interaction_face_priority(face: dict[str, object]) -> float:
    function = _optical_solid_face_function(face)
    if function == "Mirror":
        return 3.0
    if _is_uncoated_interaction_function(function):
        return 2.0
    if function == "Beam Splitter":
        return 1.0
    return 0.0


def select_optical_solid_interaction_face(world_faces: list[dict[str, object]]) -> dict[str, object] | None:
    candidates: list[dict[str, object]] = []
    for face in list(world_faces or []):
        if not isinstance(face, dict):
            continue
        if optical_solid_face_port_role(face) == OPTICAL_SOLID_FACE_PORT_INTERACTION and _interaction_face_priority(face) > 0.0:
            candidates.append(face)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda face: (
            float(_interaction_face_priority(face)),
            float(face.get("area_mm2", 0.0) or 0.0),
        ),
    )


def _unit_vector(values, fallback=(0.0, 0.0, 1.0)) -> np.ndarray:
    try:
        vector = np.asarray(values, dtype=float).reshape(3)
    except Exception:
        vector = np.asarray(fallback, dtype=float)
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12 or not np.isfinite(norm):
        vector = np.asarray(fallback, dtype=float)
        norm = float(np.linalg.norm(vector))
    return vector / max(norm, 1e-12)


def _frame_rotation_from_normal(normal_world) -> np.ndarray:
    z_axis = _unit_vector(normal_world)
    x_axis = np.asarray((1.0, 0.0, 0.0), dtype=float)
    if abs(float(np.dot(x_axis, z_axis))) > 0.9:
        x_axis = np.asarray((0.0, 0.0, 1.0), dtype=float)
    y_axis = np.cross(z_axis, x_axis)
    y_axis = _unit_vector(y_axis, fallback=(0.0, 0.0, 1.0))
    x_axis = np.cross(y_axis, z_axis)
    x_axis = _unit_vector(x_axis, fallback=(1.0, 0.0, 0.0))
    return np.column_stack((x_axis, y_axis, z_axis))


def _pose_matrix(center: np.ndarray, rotation: np.ndarray) -> np.ndarray:
    matrix = np.eye(4, dtype=float)
    matrix[:3, :3] = np.asarray(rotation, dtype=float).reshape(3, 3)
    matrix[:3, 3] = np.asarray(center, dtype=float).reshape(3)
    return matrix


def _rigid_transform_matrix(source_points: np.ndarray, target_points: np.ndarray) -> np.ndarray | None:
    src = np.asarray(source_points, dtype=float)
    dst = np.asarray(target_points, dtype=float)
    if src.shape != dst.shape or src.ndim != 2 or src.shape[0] < 3 or src.shape[1] != 3:
        return None
    if not (np.all(np.isfinite(src)) and np.all(np.isfinite(dst))):
        return None
    src_center = np.mean(src, axis=0)
    dst_center = np.mean(dst, axis=0)
    src_zero = src - src_center
    dst_zero = dst - dst_center
    if int(np.linalg.matrix_rank(src_zero, tol=1e-7)) < 2 or int(np.linalg.matrix_rank(dst_zero, tol=1e-7)) < 2:
        return None
    try:
        u_matrix, _singular, vt_matrix = np.linalg.svd(src_zero.T @ dst_zero)
        rotation = vt_matrix.T @ u_matrix.T
        if float(np.linalg.det(rotation)) < 0.0:
            vt_matrix[-1, :] *= -1.0
            rotation = vt_matrix.T @ u_matrix.T
    except Exception:
        return None
    if not np.all(np.isfinite(rotation)):
        return None
    translation = np.asarray(dst_center, dtype=float) - (np.asarray(src_center, dtype=float) @ rotation.T)
    return _pose_matrix(translation, rotation)


def _mesh_world_triangles(mesh) -> np.ndarray:
    if mesh is None:
        return np.empty((0, 3, 3), dtype=float)
    try:
        points_world = np.asarray(getattr(mesh, "points", ()), dtype=float)
        faces = np.asarray(getattr(mesh, "faces", ()), dtype=int).ravel()
    except Exception:
        return np.empty((0, 3, 3), dtype=float)
    if points_world.ndim != 2 or points_world.shape[1] < 3 or faces.size == 0:
        return np.empty((0, 3, 3), dtype=float)
    triangles: list[np.ndarray] = []
    cursor = 0
    while cursor < int(faces.size):
        vertex_count = int(faces[cursor])
        indices = faces[cursor + 1: cursor + 1 + vertex_count]
        cursor += vertex_count + 1
        if vertex_count != 3:
            continue
        try:
            tri = np.asarray(points_world[np.asarray(indices, dtype=int), :3], dtype=float)
        except Exception:
            continue
        if tri.shape == (3, 3) and np.all(np.isfinite(tri)):
            triangles.append(tri)
    if not triangles:
        return np.empty((0, 3, 3), dtype=float)
    return np.asarray(triangles, dtype=float)


def _cluster_planar_faces_from_triangles(triangles: np.ndarray, *, max_faces: int = 16) -> list[dict[str, object]]:
    triangle_array = np.asarray(triangles, dtype=float)
    if triangle_array.ndim != 3 or triangle_array.shape[1:] != (3, 3) or triangle_array.shape[0] == 0:
        return []
    flat = triangle_array.reshape((-1, 3))
    extents = np.ptp(flat, axis=0)
    max_extent = max(float(np.max(extents)), 1.0)
    area_tol = max(max_extent * max_extent * 1e-18, 1e-24)
    plane_tol = max(max_extent * 2.0e-3, 0.08)
    normal_tol = 0.995
    groups: list[dict[str, object]] = []
    for tri in triangle_array:
        v0, v1, v2 = (np.asarray(vertex, dtype=float) for vertex in tri)
        cross = np.cross(v1 - v0, v2 - v0)
        area = 0.5 * float(np.linalg.norm(cross))
        if area <= area_tol or not np.isfinite(area):
            continue
        normal = cross / max(float(np.linalg.norm(cross)), 1e-12)
        centroid = (v0 + v1 + v2) / 3.0
        plane_offset = float(np.dot(normal, centroid))
        entry = None
        for candidate in groups:
            candidate_normal = _unit_vector(np.asarray(candidate["normal_weighted"], dtype=float))
            candidate_offset = float(candidate["plane_offset_weighted"]) / max(float(candidate["area"]), 1e-12)
            if float(np.dot(candidate_normal, normal)) < normal_tol:
                continue
            if abs(candidate_offset - plane_offset) > plane_tol:
                continue
            entry = candidate
            break
        if entry is None:
            entry = {
                "normal_weighted": np.zeros(3, dtype=float),
                "centroid_weighted": np.zeros(3, dtype=float),
                "area": 0.0,
                "triangles": 0,
                "plane_offset_weighted": 0.0,
            }
            groups.append(entry)
        entry["normal_weighted"] = np.asarray(entry["normal_weighted"], dtype=float) + normal * area
        entry["centroid_weighted"] = np.asarray(entry["centroid_weighted"], dtype=float) + centroid * area
        entry["area"] = float(entry["area"]) + area
        entry["triangles"] = int(entry["triangles"]) + 1
        entry["plane_offset_weighted"] = float(entry["plane_offset_weighted"]) + plane_offset * area
    records: list[dict[str, object]] = []
    for index, entry in enumerate(sorted(groups, key=lambda item: float(item["area"]), reverse=True)[: max(1, int(max_faces))], start=1):
        area = max(float(entry["area"]), 1e-12)
        records.append(
            {
                "face_id": f"MF{index:03d}",
                "normal": list(unit_vector_tuple(np.asarray(entry["normal_weighted"], dtype=float) / area)),
                "centroid": list(point3_tuple(np.asarray(entry["centroid_weighted"], dtype=float) / area)),
                "area_mm2": float(area),
                "triangle_count": int(entry["triangles"]),
                "plane_offset_mm": float(entry["plane_offset_weighted"]) / area,
            }
        )
    return records


def _source_to_runtime_world_transform(row, mesh) -> np.ndarray | None:
    advanced = _row_advanced(row)
    metadata = normalize_optical_solid_face_metadata(advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
    source_faces = [
        normalize_optical_solid_face_record(face)
        for face in list(metadata.get("faces", []) or [])
        if isinstance(face, dict)
    ]
    if len(source_faces) < 3:
        return None
    mesh_triangles = _mesh_world_triangles(mesh)
    mesh_faces = _cluster_planar_faces_from_triangles(mesh_triangles, max_faces=max(8, len(source_faces) + 2))
    if len(mesh_faces) < len(source_faces):
        return None
    source_faces = sorted(source_faces, key=lambda face: float(face.get("area_mm2", 0.0) or 0.0), reverse=True)
    mesh_faces = sorted(mesh_faces, key=lambda face: float(face.get("area_mm2", 0.0) or 0.0), reverse=True)
    source_count = len(source_faces)
    extra_candidate_faces = 1 if source_count <= 7 else 0
    mesh_pool = mesh_faces[: min(len(mesh_faces), source_count + extra_candidate_faces)]
    if len(mesh_pool) < source_count or source_count > 8:
        return None
    source_centroids = np.asarray([point3_tuple(face.get("centroid", (0.0, 0.0, 0.0))) for face in source_faces], dtype=float)
    source_normals = np.asarray([unit_vector_tuple(face.get("normal", (0.0, 0.0, 1.0))) for face in source_faces], dtype=float)
    best_transform: np.ndarray | None = None
    best_score = float("inf")
    mesh_indices = range(len(mesh_pool))
    for candidate_indices in itertools.permutations(mesh_indices, source_count):
        candidate_faces = [mesh_pool[index] for index in candidate_indices]
        area_penalty = 0.0
        for source_face, mesh_face in zip(source_faces, candidate_faces):
            source_area = max(float(source_face.get("area_mm2", 0.0) or 0.0), 1e-9)
            mesh_area = max(float(mesh_face.get("area_mm2", 0.0) or 0.0), 1e-9)
            area_penalty += abs(mesh_area - source_area) / source_area
        if area_penalty > max(0.18 * float(source_count), 0.35):
            continue
        target_centroids = np.asarray([point3_tuple(face.get("centroid", (0.0, 0.0, 0.0))) for face in candidate_faces], dtype=float)
        transform = _rigid_transform_matrix(source_centroids, target_centroids)
        if transform is None:
            continue
        rotation = np.asarray(transform[:3, :3], dtype=float)
        translation = np.asarray(transform[:3, 3], dtype=float)
        mapped_centroids = source_centroids @ rotation.T + translation
        mapped_normals = source_normals @ rotation.T
        centroid_error = float(np.mean(np.linalg.norm(mapped_centroids - target_centroids, axis=1)))
        normal_error = 0.0
        for mapped, target_face in zip(mapped_normals, candidate_faces):
            target_normal = np.asarray(unit_vector_tuple(target_face.get("normal", (0.0, 0.0, 1.0))), dtype=float)
            normal_error += 1.0 - float(np.clip(np.dot(_unit_vector(mapped), target_normal), -1.0, 1.0))
        score = centroid_error + (8.0 * normal_error) + area_penalty
        if score < best_score:
            best_score = score
            best_transform = transform
    if best_transform is None or best_score > 6.0:
        return None
    return best_transform


def _side_direction_world(side: object, frame_rotation: np.ndarray) -> np.ndarray | None:
    side_name = normalize_optical_solid_face_side(side)
    local_vectors = {
        "Right": np.asarray((0.0, 0.0, 1.0), dtype=float),
        "Left": np.asarray((0.0, 0.0, -1.0), dtype=float),
        "Up": np.asarray((0.0, 1.0, 0.0), dtype=float),
        "Down": np.asarray((0.0, -1.0, 0.0), dtype=float),
        "Front": np.asarray((-1.0, 0.0, 0.0), dtype=float),
        "Back": np.asarray((1.0, 0.0, 0.0), dtype=float),
    }
    local = local_vectors.get(side_name)
    if local is None:
        return None
    return _unit_vector(np.asarray(frame_rotation, dtype=float).reshape(3, 3) @ local)


def _rotation_with_roll(
    local_anchor_normal: np.ndarray,
    target_anchor_normal: np.ndarray,
    *,
    local_guide_normal: np.ndarray | None = None,
    target_guide_normal: np.ndarray | None = None,
) -> np.ndarray:
    target = _unit_vector(target_anchor_normal)
    rotation = optical_solid_metadata.rotation_matrix_aligning_vectors(_unit_vector(local_anchor_normal), target)
    if local_guide_normal is None or target_guide_normal is None:
        return rotation
    guide_world = rotation @ _unit_vector(local_guide_normal)
    desired_world = _unit_vector(target_guide_normal)
    guide_proj = guide_world - target * float(np.dot(guide_world, target))
    desired_proj = desired_world - target * float(np.dot(desired_world, target))
    guide_norm = float(np.linalg.norm(guide_proj))
    desired_norm = float(np.linalg.norm(desired_proj))
    if guide_norm <= 1e-9 or desired_norm <= 1e-9:
        return rotation
    guide_proj = guide_proj / guide_norm
    desired_proj = desired_proj / desired_norm
    angle = float(
        np.arctan2(
            float(np.dot(target, np.cross(guide_proj, desired_proj))),
            float(np.clip(np.dot(guide_proj, desired_proj), -1.0, 1.0)),
        )
    )
    return optical_solid_metadata.rotation_matrix_about_axis(target, angle) @ rotation


def _guide_has_roll_signal(
    local_anchor_normal: np.ndarray,
    target_anchor_normal: np.ndarray,
    local_guide_normal: np.ndarray,
    target_guide_normal: np.ndarray,
) -> bool:
    target = _unit_vector(target_anchor_normal)
    rotation = optical_solid_metadata.rotation_matrix_aligning_vectors(_unit_vector(local_anchor_normal), target)
    guide_world = rotation @ _unit_vector(local_guide_normal)
    desired_world = _unit_vector(target_guide_normal)
    guide_proj = guide_world - target * float(np.dot(guide_world, target))
    desired_proj = desired_world - target * float(np.dot(desired_world, target))
    return float(np.linalg.norm(guide_proj)) > 1e-9 and float(np.linalg.norm(desired_proj)) > 1e-9


def _interaction_fold_roll_guides(
    metadata: dict[str, object],
    anchor_face_id: str,
    *,
    output_face: dict[str, object] | None,
    desired_outgoing: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray, str]]:
    normalized = normalize_optical_solid_face_metadata(metadata)
    faces = [
        face
        for face in list(normalized.get("faces", []) or [])
        if isinstance(face, dict)
        and str(face.get("face_id", "") or "").strip() != str(anchor_face_id or "").strip()
    ]
    priority = {"+Y normal": 6.0, "-Y normal": 5.0, "+Z normal": 4.0, "-Z normal": 3.0, "+X normal": 2.0, "-X normal": 1.0}
    explicit_guides: list[tuple[float, float, np.ndarray, np.ndarray, str]] = []
    for face in faces:
        reference = optical_solid_metadata.normalize_optical_solid_face_fit_reference(face.get("fit_reference"))
        if reference == optical_solid_metadata.OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT:
            continue
        target = optical_solid_metadata.optical_solid_face_fit_reference_axis(reference)
        if target is None:
            continue
        try:
            local = optical_solid_metadata.optical_solid_face_local_normal(face)
        except Exception:
            continue
        explicit_guides.append(
            (
                float(priority.get(reference, 0.0)),
                float(face.get("area_mm2", 0.0) or 0.0),
                np.asarray(local, dtype=float).reshape(3),
                np.asarray(target, dtype=float).reshape(3),
                reference,
            )
        )
    guides = [
        (local, target, label)
        for _priority, _area, local, target, label in sorted(explicit_guides, key=lambda item: (item[0], item[1]), reverse=True)
    ]
    if isinstance(output_face, dict):
        try:
            guides.append(
                (
                    optical_solid_metadata.optical_solid_face_local_normal(output_face),
                    np.asarray(desired_outgoing, dtype=float).reshape(3),
                    "Output side",
                )
            )
        except Exception:
            pass
    return guides


def _rotation_from_explicit_fit_references(metadata: dict[str, object], anchor_face_id: str) -> np.ndarray | None:
    normalized = normalize_optical_solid_face_metadata(metadata)
    local_vectors: list[np.ndarray] = []
    target_vectors: list[np.ndarray] = []
    for face in list(normalized.get("faces", []) or []):
        if not isinstance(face, dict):
            continue
        if str(face.get("face_id", "") or "").strip() == str(anchor_face_id or "").strip():
            continue
        reference = optical_solid_metadata.normalize_optical_solid_face_fit_reference(face.get("fit_reference"))
        if reference == optical_solid_metadata.OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT:
            continue
        target = optical_solid_metadata.optical_solid_face_fit_reference_axis(reference)
        if target is None:
            continue
        try:
            local = optical_solid_metadata.optical_solid_face_local_normal(face)
        except Exception:
            continue
        local_vectors.append(_unit_vector(local))
        target_vectors.append(_unit_vector(target))
    if len(local_vectors) < 2:
        return None
    local_rank = np.linalg.matrix_rank(np.asarray(local_vectors, dtype=float), tol=1e-7)
    target_rank = np.linalg.matrix_rank(np.asarray(target_vectors, dtype=float), tol=1e-7)
    if min(int(local_rank), int(target_rank)) < 2:
        return None
    local_matrix = np.asarray(local_vectors, dtype=float)
    target_matrix = np.asarray(target_vectors, dtype=float)
    try:
        u_matrix, _singular, vt_matrix = np.linalg.svd(local_matrix.T @ target_matrix)
        rotation = vt_matrix.T @ u_matrix.T
        if float(np.linalg.det(rotation)) < 0.0:
            vt_matrix[-1, :] *= -1.0
            rotation = vt_matrix.T @ u_matrix.T
    except Exception:
        return None
    if not np.all(np.isfinite(rotation)):
        return None
    return rotation


def _interaction_fold_prefers_explicit_fit_pose(row) -> bool:
    if not _row_has_optical_solid(row):
        return False
    metadata = normalize_optical_solid_face_metadata(_row_advanced(row).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
    if optical_solid_metadata.optical_solid_face_by_port_role(metadata, OPTICAL_SOLID_FACE_PORT_INPUT) is not None:
        return False
    faces = [
        face
        for face in list(metadata.get("faces", []) or [])
        if isinstance(face, dict)
    ]
    for face in faces:
        if not _is_specular_fold_interaction_face(face):
            continue
        face_id = str(face.get("face_id", "") or "").strip()
        if not face_id:
            continue
        if _rotation_from_explicit_fit_references(metadata, face_id) is not None:
            return True
    return False


def pose_matrix_from_override(pose: dict[str, object] | None) -> np.ndarray | None:
    """Return a world transform for one optical-solid output-port pose override."""
    if not isinstance(pose, dict):
        return None
    try:
        center = np.asarray(pose.get("center"), dtype=float).reshape(3)
        rotation = np.asarray(pose.get("rotation"), dtype=float).reshape(3, 3)
    except Exception:
        return None
    if not (np.all(np.isfinite(center)) and np.all(np.isfinite(rotation))):
        return None
    return _pose_matrix(center, rotation)


def runtime_pose_matrix_from_override(pose: dict[str, object] | None) -> np.ndarray | None:
    if not isinstance(pose, dict):
        return None
    try:
        matrix = np.asarray(pose.get("runtime_transform"), dtype=float).reshape(4, 4)
    except Exception:
        return pose_matrix_from_override(pose)
    if not np.all(np.isfinite(matrix)):
        return pose_matrix_from_override(pose)
    return matrix


def optical_solid_output_port_pose_overrides(system, rows) -> dict[int, dict[str, object]]:
    """Return the active output-port pose graph for a row list.

    The built KrakenOS system may already carry overrides applied by
    ``apply_optical_solid_output_port_system_overrides``. If not, compute them
    directly from the rows. Callers should use this instead of reading
    ``TRANS_2A`` for chained CAD/STL placement decisions.
    """
    overrides = getattr(system, "_optical_solid_output_port_pose_overrides", None) if system is not None else None
    if not isinstance(overrides, dict):
        overrides = build_optical_solid_output_port_pose_overrides(rows, system=system)
    normalized: dict[int, dict[str, object]] = {}
    for key, value in dict(overrides or {}).items():
        try:
            row_index = int(key)
        except Exception:
            continue
        if isinstance(value, dict):
            normalized[row_index] = value
    return normalized


def optical_solid_output_port_transform_override(system, rows, row_index: int) -> np.ndarray | None:
    """Return the authoritative world transform for a chained CAD/STL row."""
    try:
        pose = optical_solid_output_port_pose_overrides(system, rows).get(int(row_index))
    except Exception:
        pose = None
    return pose_matrix_from_override(pose)


def optical_solid_output_port_runtime_transform_override(system, rows, row_index: int) -> np.ndarray | None:
    """Return the runtime world transform for a chained CAD/STL row."""
    try:
        pose = optical_solid_output_port_pose_overrides(system, rows).get(int(row_index))
    except Exception:
        pose = None
    return runtime_pose_matrix_from_override(pose)


def _optical_solid_faces_at_pose(
    row,
    center: np.ndarray,
    rotation: np.ndarray,
    *,
    assigned_only: bool = True,
) -> list[dict[str, object]]:
    advanced = _row_advanced(row)
    metadata = normalize_optical_solid_face_metadata(advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
    pose_center = np.asarray(center, dtype=float).reshape(3)
    pose_rotation = np.asarray(rotation, dtype=float).reshape(3, 3)
    world_faces: list[dict[str, object]] = []
    for face in list(metadata.get("faces", []) or []):
        if not isinstance(face, dict):
            continue
        role = legacy_role_from_optical_solid_face_function(face.get("function", face.get("role")))
        function = normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
        side = normalize_optical_solid_face_side(face.get("side_2d"))
        if (
            assigned_only
            and role == OPTICAL_SOLID_FACE_ROLE_DEFAULT
            and function == OPTICAL_SOLID_FACE_FUNCTION_DEFAULT
            and side == OPTICAL_SOLID_FACE_SIDE_DEFAULT
        ):
            continue
        centroid_local = np.asarray(point3_tuple(face.get("centroid", (0.0, 0.0, 0.0))), dtype=float)
        normal_local = np.asarray(unit_vector_tuple(face.get("normal", (0.0, 0.0, 1.0))), dtype=float)
        if bool(face.get("flip_normal", False)):
            normal_local = -normal_local
        centroid_world = centroid_local @ pose_rotation.T + pose_center
        normal_world = np.asarray(unit_vector_tuple(normal_local @ pose_rotation.T), dtype=float)
        if not (np.all(np.isfinite(centroid_world)) and np.all(np.isfinite(normal_world))):
            continue
        world_face = dict(face)
        world_face["role"] = role
        world_face["function"] = function
        world_face["side_2d"] = side
        world_face["centroid_world"] = tuple(float(v) for v in centroid_world[:3])
        world_face["normal_world"] = tuple(float(v) for v in normal_world[:3])
        world_faces.append(world_face)
    return world_faces


def _canonical_left_input_solution(row) -> dict[str, object] | None:
    if not _row_has_optical_solid(row):
        return None
    metadata = normalize_optical_solid_face_metadata(_row_advanced(row).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
    input_face = optical_solid_metadata.optical_solid_face_by_port_role(metadata, OPTICAL_SOLID_FACE_PORT_INPUT)
    if input_face is None:
        return None
    face_id = str(input_face.get("face_id", "") or "").strip()
    try:
        return optical_solid_metadata.solve_optical_solid_face_fit(
            metadata,
            face_id=face_id,
            target_normal=(0.0, 0.0, -1.0),
        )
    except Exception:
        return None


def _trace_row_exit_frame(
    system,
    row_index: int,
    *,
    thickness: float,
    wavelength_um: float = 0.55,
) -> tuple[np.ndarray, np.ndarray] | None:
    if system is None:
        return None
    energy_probability = getattr(system, "energy_probability", None)
    try:
        if energy_probability is not None:
            setattr(system, "energy_probability", 0)
        system.NsTrace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], float(wavelength_um))
    except Exception:
        return None
    finally:
        if energy_probability is not None:
            try:
                setattr(system, "energy_probability", energy_probability)
            except Exception:
                pass
    if list(getattr(system, "NS_BRANCH_RESULTS", []) or []):
        return None
    try:
        surface_ids = np.asarray(getattr(system, "SURFACE", ()), dtype=int).ravel()
    except Exception:
        return None
    if surface_ids.size == 0:
        return None
    hit_positions = np.flatnonzero(surface_ids == int(row_index))
    if hit_positions.size == 0:
        return None
    last_hit = int(hit_positions[-1])
    hit_points = getattr(system, "XYZ", None)
    if hit_points is None or len(hit_points) <= last_hit + 1:
        hit_points = getattr(system, "RAY", None)
    if hit_points is None or len(hit_points) <= last_hit + 1:
        return None
    try:
        exit_point = np.asarray(hit_points[last_hit + 1], dtype=float).reshape(3)
    except Exception:
        return None
    if not np.all(np.isfinite(exit_point)):
        return None
    outgoing = None
    try:
        directions = getattr(system, "R_LMN", None)
        if directions is not None and len(directions) > last_hit:
            outgoing = np.asarray(directions[last_hit], dtype=float).reshape(3)
    except Exception:
        outgoing = None
    if outgoing is None or not np.all(np.isfinite(outgoing)) or float(np.linalg.norm(outgoing)) <= 1e-12:
        try:
            if len(hit_points) > last_hit + 2:
                outgoing = np.asarray(hit_points[last_hit + 2], dtype=float).reshape(3) - exit_point
        except Exception:
            outgoing = None
    if outgoing is None or not np.all(np.isfinite(outgoing)):
        return None
    outgoing = _unit_vector(outgoing)
    center = exit_point + outgoing * float(thickness or 0.0)
    return center, _frame_rotation_from_normal(outgoing)


def _interaction_fold_pose_from_frame(
    row,
    frame_origin: np.ndarray,
    frame_rotation: np.ndarray,
) -> tuple[np.ndarray, np.ndarray] | None:
    if not _row_has_optical_solid(row):
        return None
    metadata = normalize_optical_solid_face_metadata(_row_advanced(row).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
    if optical_solid_metadata.optical_solid_face_by_port_role(metadata, OPTICAL_SOLID_FACE_PORT_INPUT) is not None:
        return None
    faces = [
        face
        for face in list(metadata.get("faces", []) or [])
        if isinstance(face, dict)
    ]
    interaction_faces = [
        face
        for face in faces
        if _is_specular_fold_interaction_face(face)
    ]
    if not interaction_faces:
        return None
    side_priority = {"Left": 4.0, "Right": 3.0, "Down": 2.0, "Up": 2.0}
    interaction_face = max(
        interaction_faces,
        key=lambda face: (
            float(side_priority.get(normalize_optical_solid_face_side(face.get("side_2d")), 0.0)),
            float(face.get("area_mm2", 0.0) or 0.0),
        ),
    )
    output_faces = [
        face
        for face in faces
        if optical_solid_face_port_role(face) == OPTICAL_SOLID_FACE_PORT_OUTPUT
    ]
    output_side_priority = {"Down": 6.0, "Up": 5.0, "Right": 4.0, "Back": 3.0, "Front": 2.0, "Left": 1.0}
    output_face = max(
        output_faces,
        key=lambda face: (
            float(output_side_priority.get(normalize_optical_solid_face_side(face.get("side_2d")), 0.0)),
            float(face.get("area_mm2", 0.0) or 0.0),
        ),
        default=None,
    )
    desired_outgoing = None
    if output_face is not None:
        desired_outgoing = _side_direction_world(output_face.get("side_2d"), frame_rotation)
    if desired_outgoing is None:
        desired_outgoing = _side_direction_world("Down", frame_rotation)
    incoming = _unit_vector(np.asarray(frame_rotation, dtype=float).reshape(3, 3)[:, 2])
    desired_outgoing = _unit_vector(desired_outgoing)
    target_normal = incoming - desired_outgoing
    if float(np.linalg.norm(target_normal)) <= 1e-9:
        target_normal = incoming + desired_outgoing
    target_normal = _unit_vector(target_normal)
    try:
        local_anchor = optical_solid_metadata.optical_solid_face_local_normal(interaction_face)
        anchor_face_id = str(interaction_face.get("face_id", "") or "").strip()
        rotation = _rotation_from_explicit_fit_references(metadata, anchor_face_id)
        if rotation is None:
            rotation = optical_solid_metadata.rotation_matrix_aligning_vectors(_unit_vector(local_anchor), target_normal)
            for local_guide, target_guide, _label in _interaction_fold_roll_guides(
                metadata,
                anchor_face_id,
                output_face=output_face,
                desired_outgoing=desired_outgoing,
            ):
                if not _guide_has_roll_signal(local_anchor, target_normal, local_guide, target_guide):
                    continue
                rotation = _rotation_with_roll(
                    local_anchor,
                    target_normal,
                    local_guide_normal=local_guide,
                    target_guide_normal=target_guide,
                )
                break
        else:
            rotation = np.asarray(rotation, dtype=float).reshape(3, 3)
        centroid = np.asarray(
            optical_solid_metadata.point3_tuple(interaction_face.get("centroid", (0.0, 0.0, 0.0))),
            dtype=float,
        )
        center = np.asarray(frame_origin, dtype=float).reshape(3) - (centroid @ rotation.T)
    except Exception:
        return None
    if not (np.all(np.isfinite(center)) and np.all(np.isfinite(rotation))):
        return None
    return center, rotation


def _inferred_interaction_input_pose_from_frame(
    row,
    frame_origin: np.ndarray,
    frame_rotation: np.ndarray,
) -> tuple[np.ndarray, np.ndarray] | None:
    if not _row_has_optical_solid(row):
        return None
    metadata = normalize_optical_solid_face_metadata(_row_advanced(row).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
    if optical_solid_metadata.optical_solid_face_by_port_role(metadata, OPTICAL_SOLID_FACE_PORT_INPUT) is not None:
        return None
    faces = [
        face
        for face in list(metadata.get("faces", []) or [])
        if isinstance(face, dict)
    ]
    interaction_faces = [
        face
        for face in faces
        if _is_specular_fold_interaction_face(face)
    ]
    if not interaction_faces:
        return None
    output_faces = [
        face
        for face in faces
        if optical_solid_face_port_role(face) == OPTICAL_SOLID_FACE_PORT_OUTPUT
    ]
    output_side_priority = {"Down": 6.0, "Up": 5.0, "Right": 4.0, "Back": 3.0, "Front": 2.0, "Left": 1.0}
    output_face = max(
        output_faces,
        key=lambda face: (
            float(output_side_priority.get(normalize_optical_solid_face_side(face.get("side_2d")), 0.0)),
            float(face.get("area_mm2", 0.0) or 0.0),
        ),
        default=None,
    )
    if output_face is None:
        return None
    desired_outgoing = _side_direction_world(output_face.get("side_2d"), frame_rotation)
    if desired_outgoing is None:
        return None
    incoming = _unit_vector(np.asarray(frame_rotation, dtype=float).reshape(3, 3)[:, 2])
    interaction_face = max(
        interaction_faces,
        key=lambda face: float(face.get("area_mm2", 0.0) or 0.0),
    )
    output_face_id = str(output_face.get("face_id", "") or "").strip()
    interaction_face_id = str(interaction_face.get("face_id", "") or "").strip()
    best_score = -np.inf
    best_pose: tuple[np.ndarray, np.ndarray] | None = None
    for candidate in faces:
        candidate_id = str(candidate.get("face_id", "") or "").strip()
        if not candidate_id or candidate_id in {interaction_face_id, output_face_id}:
            continue
        try:
            solution = optical_solid_metadata.solve_optical_solid_face_fit(
                metadata,
                face_id=candidate_id,
                target_normal=tuple((-incoming).tolist()),
                target_point=tuple(np.asarray(frame_origin, dtype=float).reshape(3).tolist()),
            )
        except Exception:
            continue
        if not isinstance(solution, dict):
            continue
        try:
            center = np.asarray(solution.get("desp"), dtype=float).reshape(3)
            rotation = np.asarray(solution.get("rotation"), dtype=float).reshape(3, 3)
        except Exception:
            continue
        if not (np.all(np.isfinite(center)) and np.all(np.isfinite(rotation))):
            continue
        world_faces = _optical_solid_faces_at_pose(row, center, rotation, assigned_only=False)
        world_by_id = {
            str(face.get("face_id", "") or "").strip(): face
            for face in world_faces
            if isinstance(face, dict)
        }
        interaction_world = world_by_id.get(interaction_face_id)
        output_world = world_by_id.get(output_face_id)
        anchor_world = world_by_id.get(candidate_id)
        if interaction_world is None or output_world is None or anchor_world is None:
            continue
        interaction_normal = _unit_vector(interaction_world.get("normal_world", (0.0, 0.0, 1.0)))
        reflected = incoming - 2.0 * float(np.dot(incoming, interaction_normal)) * interaction_normal
        reflected = _unit_vector(reflected)
        reflect_score = float(np.dot(reflected, _unit_vector(desired_outgoing)))
        output_normal = _unit_vector(output_world.get("normal_world", (0.0, 0.0, 1.0)))
        output_score = float(np.dot(output_normal, _unit_vector(desired_outgoing)))
        anchor_centroid = np.asarray(anchor_world.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(3)
        interaction_centroid = np.asarray(interaction_world.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(3)
        if not (np.all(np.isfinite(anchor_centroid)) and np.all(np.isfinite(interaction_centroid))):
            continue
        upstream_span = float(np.dot(interaction_centroid - anchor_centroid, incoming))
        if upstream_span <= 1e-6:
            continue
        score = reflect_score + (0.35 * output_score) + (0.01 * min(upstream_span, 50.0))
        if score > best_score:
            best_score = score
            best_pose = (center, rotation)
    if best_pose is None or best_score < 0.8:
        return None
    return best_pose


def _row_uses_interaction_fold_pose(
    row,
    frame_origin: np.ndarray,
    frame_rotation: np.ndarray,
) -> bool:
    return _interaction_fold_pose_from_frame(row, frame_origin, frame_rotation) is not None


def _downstream_pose_from_frame(row, frame_origin: np.ndarray, frame_rotation: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    fold_pose = _interaction_fold_pose_from_frame(row, frame_origin, frame_rotation)
    if fold_pose is not None and _interaction_fold_prefers_explicit_fit_pose(row):
        return fold_pose
    inferred_input_pose = _inferred_interaction_input_pose_from_frame(row, frame_origin, frame_rotation)
    if inferred_input_pose is not None:
        return inferred_input_pose
    if fold_pose is not None:
        return fold_pose
    local_solution = _canonical_left_input_solution(row)
    if local_solution is not None:
        local_rotation = np.asarray(local_solution["rotation"], dtype=float).reshape(3, 3)
        local_offset = np.asarray(local_solution["desp"], dtype=float).reshape(3)
    else:
        local_rotation = optical_solid_metadata.rotation_matrix_from_kraken_tilts(
            float(getattr(row, "tilt_x", 0.0) or 0.0),
            float(getattr(row, "tilt_y", 0.0) or 0.0),
            float(getattr(row, "tilt_z", 0.0) or 0.0),
        )
        local_offset = np.asarray(
            (
                float(getattr(row, "desp_x", 0.0) or 0.0),
                float(getattr(row, "desp_y", 0.0) or 0.0),
                float(getattr(row, "desp_z", 0.0) or 0.0),
            ),
            dtype=float,
        )
    rotation = np.asarray(frame_rotation, dtype=float).reshape(3, 3) @ local_rotation
    center = np.asarray(frame_origin, dtype=float).reshape(3) + (
        np.asarray(frame_rotation, dtype=float).reshape(3, 3) @ local_offset
    )
    return center, rotation


def _reflected_frame_from_interaction_face(
    world_faces: list[dict[str, object]],
    frame_origin: np.ndarray,
    frame_rotation: np.ndarray,
    thickness: float,
) -> tuple[np.ndarray, np.ndarray] | None:
    face = select_optical_solid_interaction_face(world_faces)
    if face is None:
        return None
    if not _is_specular_fold_interaction_face(face):
        return None
    origin = np.asarray(frame_origin, dtype=float).reshape(3)
    incoming = _unit_vector(np.asarray(frame_rotation, dtype=float).reshape(3, 3)[:, 2])
    point = np.asarray(face.get("centroid_world", (0.0, 0.0, 0.0)), dtype=float).reshape(3)
    normal = _unit_vector(face.get("normal_world", (0.0, 0.0, 1.0)))
    reflected = incoming - 2.0 * float(np.dot(incoming, normal)) * normal
    reflected = _unit_vector(reflected)
    denominator = float(np.dot(incoming, normal))
    if abs(denominator) > 1e-12:
        distance = float(np.dot(point - origin, normal) / denominator)
        hit = origin + incoming * distance if np.isfinite(distance) else point
    else:
        hit = point
    center = hit + reflected * float(thickness or 0.0)
    return center, _frame_rotation_from_normal(reflected)


def _exit_frame_is_non_folding(
    frame_rotation: np.ndarray,
    incoming_axis: np.ndarray,
    *,
    direction_tol: float = 1e-6,
) -> bool:
    """True when an exit frame does NOT fold the incoming beam (codirectional).

    Only a *fold* -- a change of propagation direction (reflection/bend) --
    relocates the beam and the downstream image/detector it lands on. A
    non-folding *inferred* exit leaves the beam travelling the same direction it
    arrived, so the existing downstream rows already sit on that path at their
    authored spacing and must not be repositioned onto the solid's exit face.

    bugs/0022: this used to also require the exit to be laterally *centred* on
    the incoming axis. That wrongly fired when the user shifted a beam-splitter
    cube sideways "out of the beam": the cube's exit FACE moved off-axis (still
    codirectional), the lateral test failed, the skip stopped applying, and the
    override snapped the Image plane onto the displaced face -- dragging the
    focus ~400 mm off its real station. Moving the cube laterally does not bend
    the beam, so nothing downstream may move; the focus is the lens's, fixed in
    space, and the beam simply propagates to it whether or not the cube is in
    the path. (A genuine codirectional beam *displacer* must be authored with an
    explicit output port, which is not gated by this skip.)
    """
    incoming = _unit_vector(incoming_axis)
    forward = _unit_vector(np.asarray(frame_rotation, dtype=float).reshape(3, 3)[:, 2])
    return float(np.dot(forward, incoming)) >= 1.0 - float(direction_tol)


def build_optical_solid_output_port_pose_overrides(rows, *, system=None) -> dict[int, dict[str, object]]:
    prepared = [_row_like(row) for row in list(rows or [])]
    if len(prepared) < 2:
        return {}
    z_positions = row_z_positions(prepared)
    overrides: dict[int, dict[str, object]] = {}
    row_index = 0
    while row_index < len(prepared):
        current = prepared[row_index]
        if not _row_has_optical_solid(current):
            row_index += 1
            continue
        try:
            world_faces = optical_solid_face_world_records(
                current,
                float(z_positions[row_index]) if row_index < len(z_positions) else 0.0,
                assigned_only=True,
            )
        except Exception:
            row_index += 1
            continue
        output_face = select_optical_solid_output_face(world_faces)
        explicit_output_face = select_optical_solid_explicit_output_face(world_faces)
        explicit_input_face = select_optical_solid_explicit_input_face(world_faces)
        frame_origin = None
        frame_rotation = None
        frame_source = ""
        if system is not None and explicit_output_face is None and explicit_input_face is not None:
            traced_frame = _trace_row_exit_frame(
                system,
                int(row_index),
                thickness=float(getattr(current, "thickness", 0.0) or 0.0),
            )
            if traced_frame is not None:
                frame_origin, frame_rotation = traced_frame
                frame_source = "physics_exit_trace"
        if frame_origin is None or frame_rotation is None:
            if output_face is None:
                if explicit_input_face is None:
                    row_index += 1
                    continue
                z_station = float(z_positions[row_index]) if row_index < len(z_positions) else 0.0
                reflected_frame = _reflected_frame_from_interaction_face(
                    world_faces,
                    np.asarray((0.0, 0.0, z_station), dtype=float),
                    _frame_rotation_from_normal((0.0, 0.0, 1.0)),
                    float(getattr(current, "thickness", 0.0) or 0.0),
                )
                if reflected_frame is None:
                    row_index += 1
                    continue
                frame_origin, frame_rotation = reflected_frame
                frame_source = "interaction_reflection_fallback"
            else:
                output_center = np.asarray(output_face.get("centroid_world", (0.0, 0.0, 0.0)), dtype=float).reshape(3)
                output_normal = _unit_vector(output_face.get("normal_world", (0.0, 0.0, 1.0)))
                frame_origin = output_center + output_normal * float(getattr(current, "thickness", 0.0) or 0.0)
                frame_rotation = _frame_rotation_from_normal(output_normal)
                frame_source = (
                    f"explicit_output:{str(output_face.get('face_id', '') or '').strip()}"
                    if explicit_output_face is not None
                    else f"inferred_output:{str(output_face.get('face_id', '') or '').strip()}"
                )
        # A purely inferred (auto-suggested, not user-authored) exit that does
        # not FOLD the beam must not reposition the existing downstream rows:
        # the beam keeps travelling the incoming direction, so they already lie
        # on its path. This keeps an Image/Object plane at its authored station
        # instead of snapping it onto the solid's exit face -- including when
        # the solid is shifted laterally off the beam (bugs/0022: a beam-splitter
        # cube moved sideways must not drag the focus onto its displaced face).
        # Folded inferred exits, explicit output ports, and physics-traced exits
        # still drive the follower-row workflow normally.
        if str(frame_source or "").startswith("inferred_output") and _exit_frame_is_non_folding(
            frame_rotation,
            np.asarray((0.0, 0.0, 1.0), dtype=float),
        ):
            row_index += 1
            continue
        follower_index = row_index + 1
        while follower_index < len(prepared):
            follower = prepared[follower_index]
            if _row_surface(follower) == "Object":
                follower_index += 1
                continue
            center, rotation = _downstream_pose_from_frame(follower, frame_origin, frame_rotation)
            overrides[follower_index] = {
                "center": np.asarray(center, dtype=float),
                "rotation": np.asarray(rotation, dtype=float),
                "normal": np.asarray(rotation[:, 2], dtype=float),
                "output_face": dict(output_face) if isinstance(output_face, dict) else {},
                "source_index": int(row_index),
                "frame_source": frame_source,
            }
            if system is not None:
                _apply_optical_solid_output_port_system_overrides_built(
                    system,
                    {int(follower_index): overrides[follower_index]},
                    merge=True,
                )
            if _row_has_optical_solid(follower):
                used_interaction_fold = _row_uses_interaction_fold_pose(follower, frame_origin, frame_rotation)
                follower_faces = _optical_solid_faces_at_pose(
                    follower,
                    np.asarray(center, dtype=float),
                    np.asarray(rotation, dtype=float),
                    assigned_only=True,
                )
                follower_output_face = select_optical_solid_output_face(follower_faces)
                explicit_follower_output = select_optical_solid_explicit_output_face(follower_faces)
                explicit_follower_input = select_optical_solid_explicit_input_face(follower_faces)
                traced_frame = None
                follower_prefers_traced_exit = (
                    (explicit_follower_output is None and explicit_follower_input is not None)
                )
                if system is not None and follower_prefers_traced_exit:
                    traced_frame = _trace_row_exit_frame(
                        system,
                        int(follower_index),
                        thickness=float(getattr(follower, "thickness", 0.0) or 0.0),
                    )
                if traced_frame is not None:
                    frame_origin, frame_rotation = traced_frame
                    output_face = follower_output_face
                    frame_source = "physics_exit_trace"
                    row_index = follower_index
                else:
                    reflected_frame = (
                        _reflected_frame_from_interaction_face(
                            follower_faces,
                            frame_origin,
                            frame_rotation,
                            float(getattr(follower, "thickness", 0.0) or 0.0),
                        )
                        if used_interaction_fold
                        else None
                    )
                    if reflected_frame is not None:
                        frame_origin, frame_rotation = reflected_frame
                        output_face = None
                        frame_source = "interaction_reflection_fallback"
                        row_index = follower_index
                    elif follower_output_face is not None:
                        output_face = follower_output_face
                        output_center = np.asarray(output_face.get("centroid_world", (0.0, 0.0, 0.0)), dtype=float).reshape(3)
                        output_normal = _unit_vector(output_face.get("normal_world", (0.0, 0.0, 1.0)))
                        frame_origin = output_center + output_normal * float(getattr(follower, "thickness", 0.0) or 0.0)
                        frame_rotation = _frame_rotation_from_normal(output_normal)
                        frame_source = (
                            f"explicit_output:{str(output_face.get('face_id', '') or '').strip()}"
                            if explicit_follower_output is not None
                            else f"inferred_output:{str(output_face.get('face_id', '') or '').strip()}"
                        )
                        row_index = follower_index
                    else:
                        reflected_frame = (
                            _reflected_frame_from_interaction_face(
                                follower_faces,
                                frame_origin,
                                frame_rotation,
                                float(getattr(follower, "thickness", 0.0) or 0.0),
                            )
                            if explicit_follower_input is not None
                            else None
                        )
                        if reflected_frame is None:
                            break
                        frame_origin, frame_rotation = reflected_frame
                        output_face = None
                        frame_source = "interaction_reflection_fallback"
                        row_index = follower_index
            else:
                frame_origin = center + (rotation[:, 2] * float(getattr(follower, "thickness", 0.0) or 0.0))
                frame_rotation = rotation
                output_face = None
                frame_source = "downstream_row_frame"
            follower_index += 1
        row_index = max(follower_index, row_index + 1)
    return overrides


def _transformed_mesh_copy(mesh, delta: np.ndarray):
    if mesh is None:
        return None
    try:
        transformed = mesh.copy(deep=True)
        transformed.transform(delta, inplace=True)
        # PyVista can keep a stale ray_trace locator after in-place point
        # transforms. Rebuilding a clean PolyData gives the tracer a fresh
        # acceleration structure while keeping the same visible geometry.
        try:
            transformed = transformed.clean()
        except Exception:
            pass
        return transformed
    except Exception:
        return None


def _replace_transformed_mesh(owner, mesh_name: str, index: int, delta: np.ndarray, transformed_mesh_lists: set[tuple[int, int]]) -> None:
    mesh_list = getattr(owner, mesh_name, None) if owner is not None else None
    if mesh_list is None or not (0 <= int(index) < len(mesh_list)):
        return
    key = (id(mesh_list), int(index))
    if key in transformed_mesh_lists:
        return
    try:
        transformed = _transformed_mesh_copy(mesh_list[int(index)], delta)
    except Exception:
        transformed = None
    if transformed is None:
        return
    try:
        mesh_list[int(index)] = transformed
    except Exception:
        return
    transformed_mesh_lists.add(key)


def _update_owner_transform(owner, row_index: int, world_transform: np.ndarray) -> None:
    if owner is None:
        return
    for transform_name, matrix in (
        ("TRANS_2A", np.matrix(world_transform)),
        ("TRANS_1A", np.matrix(np.linalg.inv(world_transform))),
    ):
        transforms = getattr(owner, transform_name, None)
        if transforms is None or not (0 <= int(row_index) < len(transforms)):
            continue
        transforms[int(row_index)] = matrix


def _apply_optical_solid_output_port_system_overrides_built(
    system,
    overrides: dict[int, dict[str, object]],
    *,
    merge: bool = False,
) -> dict[int, dict[str, object]]:
    if not overrides:
        return {}
    if merge:
        active_overrides = dict(getattr(system, "_optical_solid_output_port_pose_overrides", {}) or {})
        active_overrides.update(overrides)
    else:
        active_overrides = dict(overrides)
    pr3d = getattr(system, "Pr3D", None)
    transformed_mesh_lists: set[tuple[int, int]] = set()
    for row_index, pose in overrides.items():
        transforms = getattr(system, "TRANS_2A", None)
        if transforms is None or not (0 <= int(row_index) < len(transforms)):
            continue
        current = np.asarray(transforms[int(row_index)], dtype=float)
        target = _pose_matrix(np.asarray(pose["center"], dtype=float), np.asarray(pose["rotation"], dtype=float))
        runtime_target = target
        source_to_runtime_world = None
        try:
            mesh_list = getattr(system, "EEE", None)
            mesh = mesh_list[int(row_index)] if mesh_list is not None and 0 <= int(row_index) < len(mesh_list) else None
        except Exception:
            mesh = None
        try:
            rows = getattr(system, "_optical_solid_output_port_rows", None)
            row = rows[int(row_index)] if rows is not None and 0 <= int(row_index) < len(rows) else None
        except Exception:
            row = None
        if row is not None and mesh is not None:
            source_to_runtime_world = _source_to_runtime_world_transform(row, mesh)
        pose["runtime_transform"] = np.asarray(runtime_target, dtype=float)
        if source_to_runtime_world is not None:
            pose["source_to_runtime_world"] = np.asarray(source_to_runtime_world, dtype=float)
        else:
            pose.pop("source_to_runtime_world", None)
        try:
            current_mesh_world = (
                np.asarray(source_to_runtime_world, dtype=float).reshape(4, 4)
                if source_to_runtime_world is not None
                else current
            )
            delta = runtime_target @ np.linalg.inv(current_mesh_world)
        except Exception:
            continue
        for owner in (system, pr3d, getattr(system, "INORM", None)):
            _update_owner_transform(owner, int(row_index), runtime_target)
        mesh_owners = (system, pr3d, getattr(system, "INORM", None), getattr(getattr(system, "INORM", None), "Pr3D", None))
        for owner in mesh_owners:
            _replace_transformed_mesh(owner, "EEE", int(row_index), delta, transformed_mesh_lists)
        side_numbers = list(getattr(system, "side_number", []) or [])
        for owner in mesh_owners:
            bodies = getattr(owner, "BBB", None) if owner is not None else None
            if bodies is None:
                continue
            for body_index, side_row_index in enumerate(side_numbers):
                try:
                    if int(side_row_index) != int(row_index):
                        continue
                except Exception:
                    continue
                _replace_transformed_mesh(owner, "BBB", int(body_index), delta, transformed_mesh_lists)
    cache = getattr(system, "_optical_solid_face_world_cache", None)
    if isinstance(cache, dict):
        cache.clear()
    setattr(system, "_optical_solid_output_port_pose_overrides", active_overrides)
    if pr3d is not None:
        setattr(pr3d, "_optical_solid_output_port_pose_overrides", active_overrides)
    rows = getattr(system, "_optical_solid_output_port_rows", None)
    if rows is not None:
        attach_scene_boundary_face_index(system, rows)
        attach_scene_optical_volume_index(system, rows)
    return active_overrides


def attach_scene_boundary_face_index(system, rows) -> dict[int, list[dict[str, object]]]:
    if system is None:
        return {}
    prepared_rows = _scene_index_rows(system, rows)
    try:
        index = build_scene_boundary_face_index(prepared_rows, system=system)
    except Exception:
        index = {}
    setattr(system, "_scene_boundary_faces_by_surface", index)
    cache = getattr(system, "_optical_solid_face_world_cache", None)
    if isinstance(cache, dict):
        cache.clear()
    return index


def attach_scene_optical_volume_index(system, rows) -> dict[int, dict[str, object]]:
    if system is None:
        return {}
    prepared_rows = _scene_index_rows(system, rows)
    try:
        index = build_scene_optical_volume_index(prepared_rows, system=system)
    except Exception:
        index = {}
    setattr(system, "_scene_optical_volumes_by_surface", index)
    return index


def _install_build_hook(system) -> None:
    if system is None or hasattr(system, "_optical_solid_output_port_original_build"):
        return
    original_build = getattr(system, "build", None)
    if not callable(original_build):
        return

    def build_with_output_ports(*args, **kwargs):
        result = original_build(*args, **kwargs)
        rows = getattr(system, "_optical_solid_output_port_rows", None)
        attach_scene_boundary_face_index(system, rows)
        attach_scene_optical_volume_index(system, rows)
        overrides = build_optical_solid_output_port_pose_overrides(rows, system=system)
        _apply_optical_solid_output_port_system_overrides_built(system, overrides)
        return result

    setattr(system, "_optical_solid_output_port_original_build", original_build)
    setattr(system, "build", build_with_output_ports)


def apply_optical_solid_output_port_system_overrides(system, rows) -> dict[int, dict[str, object]]:
    if system is None:
        return {}
    row_list = list(rows or [])
    setattr(system, "_optical_solid_output_port_rows", row_list)
    _install_build_hook(system)
    attach_scene_boundary_face_index(system, row_list)
    attach_scene_optical_volume_index(system, row_list)
    solid_indices = [
        int(index)
        for index, row in enumerate(row_list)
        if _row_has_optical_solid(row)
    ]
    if not solid_indices:
        setattr(system, "_scene_boundary_faces_by_surface", {})
        setattr(system, "_scene_optical_volumes_by_surface", {})
        setattr(system, "_optical_solid_output_port_pose_overrides", {})
        pr3d = getattr(system, "Pr3D", None)
        if pr3d is not None:
            setattr(pr3d, "_optical_solid_output_port_pose_overrides", {})
        return {}
    max_solid_index = max(solid_indices)
    pr3d = getattr(system, "Pr3D", None)
    try:
        transforms = getattr(system, "TRANS_2A", None)
        meshes = getattr(system, "EEE", None)
        needs_build = (
            pr3d is None
            or transforms is None
            or meshes is None
            or len(transforms) <= max_solid_index
            or len(meshes) <= max_solid_index
            or not hasattr(meshes[max_solid_index], "ray_trace")
        )
        if needs_build:
            original_build_flag = getattr(system, "BUILD", None)
            try:
                setattr(system, "BUILD", 1)
                system.build()
            finally:
                if original_build_flag is not None:
                    try:
                        setattr(system, "BUILD", original_build_flag)
                    except Exception:
                        pass
            settled = build_optical_solid_output_port_pose_overrides(row_list, system=system)
            if settled:
                return _apply_optical_solid_output_port_system_overrides_built(system, settled)
            setattr(system, "_optical_solid_output_port_pose_overrides", {})
            if pr3d is not None:
                setattr(pr3d, "_optical_solid_output_port_pose_overrides", {})
            return {}
    except Exception:
        try:
            original_build_flag = getattr(system, "BUILD", None)
            try:
                setattr(system, "BUILD", 1)
                system.build()
            finally:
                if original_build_flag is not None:
                    try:
                        setattr(system, "BUILD", original_build_flag)
                    except Exception:
                        pass
            settled = build_optical_solid_output_port_pose_overrides(row_list, system=system)
            if settled:
                return _apply_optical_solid_output_port_system_overrides_built(system, settled)
            setattr(system, "_optical_solid_output_port_pose_overrides", {})
            if pr3d is not None:
                setattr(pr3d, "_optical_solid_output_port_pose_overrides", {})
            return {}
        except Exception:
            return {}
    overrides = build_optical_solid_output_port_pose_overrides(row_list, system=system)
    if not overrides:
        setattr(system, "_optical_solid_output_port_pose_overrides", {})
        if pr3d is not None:
            setattr(pr3d, "_optical_solid_output_port_pose_overrides", {})
        return {}
    return _apply_optical_solid_output_port_system_overrides_built(system, overrides)
