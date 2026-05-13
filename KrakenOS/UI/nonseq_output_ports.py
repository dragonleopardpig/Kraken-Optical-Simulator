from __future__ import annotations

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
    normalize_optical_solid_face_metadata,
    normalize_optical_solid_face_port_role,
    normalize_optical_solid_face_side,
    optical_solid_face_port_role,
    optical_solid_face_world_records,
    point3_tuple,
    unit_vector_tuple,
)


def _row_like(row):
    if isinstance(row, dict):
        return SimpleNamespace(
            surface=str(row.get("surface", "") or ""),
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
    return str(getattr(row, "surface", "") or "").strip()


def _row_advanced(row) -> dict[str, object]:
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
        if function == OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT and side != "Left":
            inferred_output_faces.append(face)
    pool = explicit_output_faces or inferred_output_faces
    if not pool:
        return None
    return max(pool, key=lambda face: float(face.get("area_mm2", 0.0) or 0.0))


def select_optical_solid_interaction_face(world_faces: list[dict[str, object]]) -> dict[str, object] | None:
    candidates: list[dict[str, object]] = []
    for face in list(world_faces or []):
        if not isinstance(face, dict):
            continue
        function = normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
        port_role = optical_solid_face_port_role(face)
        if port_role == OPTICAL_SOLID_FACE_PORT_INTERACTION and function in {"Mirror", "TIR", "Beam Splitter"}:
            candidates.append(face)
    if not candidates:
        return None
    priority = {"Mirror": 3.0, "TIR": 2.0, "Beam Splitter": 1.0}
    return max(
        candidates,
        key=lambda face: (
            float(priority.get(normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role")), 0.0)),
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


def optical_solid_output_port_pose_overrides(system, rows) -> dict[int, dict[str, object]]:
    """Return the active output-port pose graph for a row list.

    The built KrakenOS system may already carry overrides applied by
    ``apply_optical_solid_output_port_system_overrides``. If not, compute them
    directly from the rows. Callers should use this instead of reading
    ``TRANS_2A`` for chained CAD/STL placement decisions.
    """
    overrides = getattr(system, "_optical_solid_output_port_pose_overrides", None) if system is not None else None
    if not isinstance(overrides, dict):
        overrides = build_optical_solid_output_port_pose_overrides(rows)
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


def _downstream_pose_from_frame(row, frame_origin: np.ndarray, frame_rotation: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
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
    function = normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
    if function not in {"Mirror", "TIR"}:
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


def build_optical_solid_output_port_pose_overrides(rows) -> dict[int, dict[str, object]]:
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
        if output_face is None:
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
        else:
            output_center = np.asarray(output_face.get("centroid_world", (0.0, 0.0, 0.0)), dtype=float).reshape(3)
            output_normal = _unit_vector(output_face.get("normal_world", (0.0, 0.0, 1.0)))
            frame_origin = output_center + output_normal * float(getattr(current, "thickness", 0.0) or 0.0)
            frame_rotation = _frame_rotation_from_normal(output_normal)
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
            }
            if _row_has_optical_solid(follower):
                follower_faces = _optical_solid_faces_at_pose(
                    follower,
                    np.asarray(center, dtype=float),
                    np.asarray(rotation, dtype=float),
                    assigned_only=True,
                )
                follower_output_face = select_optical_solid_output_face(follower_faces)
                if follower_output_face is not None:
                    output_face = follower_output_face
                    output_center = np.asarray(output_face.get("centroid_world", (0.0, 0.0, 0.0)), dtype=float).reshape(3)
                    output_normal = _unit_vector(output_face.get("normal_world", (0.0, 0.0, 1.0)))
                    frame_origin = output_center + output_normal * float(getattr(follower, "thickness", 0.0) or 0.0)
                    frame_rotation = _frame_rotation_from_normal(output_normal)
                    row_index = follower_index
                else:
                    reflected_frame = _reflected_frame_from_interaction_face(
                        follower_faces,
                        frame_origin,
                        frame_rotation,
                        float(getattr(follower, "thickness", 0.0) or 0.0),
                    )
                    if reflected_frame is None:
                        break
                    frame_origin, frame_rotation = reflected_frame
                    row_index = follower_index
            else:
                frame_origin = center + (rotation[:, 2] * float(getattr(follower, "thickness", 0.0) or 0.0))
                frame_rotation = rotation
            follower_index += 1
        row_index = max(follower_index, row_index + 1)
    return overrides


def _transform_mesh_in_place(mesh, delta: np.ndarray) -> bool:
    if mesh is None:
        return False
    try:
        mesh.transform(delta, inplace=True)
        return True
    except Exception:
        return False


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
) -> dict[int, dict[str, object]]:
    if not overrides:
        return {}
    pr3d = getattr(system, "Pr3D", None)
    transformed_mesh_lists: set[tuple[int, int]] = set()
    for row_index, pose in overrides.items():
        transforms = getattr(system, "TRANS_2A", None)
        if transforms is None or not (0 <= int(row_index) < len(transforms)):
            continue
        current = np.asarray(transforms[int(row_index)], dtype=float)
        target = _pose_matrix(np.asarray(pose["center"], dtype=float), np.asarray(pose["rotation"], dtype=float))
        try:
            delta = target @ np.linalg.inv(current)
        except Exception:
            continue
        for owner in (system, pr3d, getattr(system, "INORM", None)):
            _update_owner_transform(owner, int(row_index), target)
        for mesh_name in ("EEE",):
            mesh_list = getattr(system, mesh_name, None)
            if mesh_list is None or not (0 <= int(row_index) < len(mesh_list)):
                continue
            key = (id(mesh_list), int(row_index))
            if key in transformed_mesh_lists:
                continue
            try:
                mesh = mesh_list[int(row_index)]
            except Exception:
                continue
            if _transform_mesh_in_place(mesh, delta):
                transformed_mesh_lists.add(key)
        side_numbers = list(getattr(system, "side_number", []) or [])
        bodies = getattr(system, "BBB", None)
        if bodies is not None:
            for body_index, side_row_index in enumerate(side_numbers):
                try:
                    if int(side_row_index) != int(row_index):
                        continue
                except Exception:
                    continue
                key = (id(bodies), int(body_index))
                if key in transformed_mesh_lists:
                    continue
                try:
                    body = bodies[int(body_index)]
                except Exception:
                    continue
                if _transform_mesh_in_place(body, delta):
                    transformed_mesh_lists.add(key)
    cache = getattr(system, "_optical_solid_face_world_cache", None)
    if isinstance(cache, dict):
        cache.clear()
    setattr(system, "_optical_solid_output_port_pose_overrides", overrides)
    if pr3d is not None:
        setattr(pr3d, "_optical_solid_output_port_pose_overrides", overrides)
    return overrides


def _install_build_hook(system) -> None:
    if system is None or hasattr(system, "_optical_solid_output_port_original_build"):
        return
    original_build = getattr(system, "build", None)
    if not callable(original_build):
        return

    def build_with_output_ports(*args, **kwargs):
        result = original_build(*args, **kwargs)
        rows = getattr(system, "_optical_solid_output_port_rows", None)
        overrides = build_optical_solid_output_port_pose_overrides(rows)
        _apply_optical_solid_output_port_system_overrides_built(system, overrides)
        return result

    setattr(system, "_optical_solid_output_port_original_build", original_build)
    setattr(system, "build", build_with_output_ports)


def apply_optical_solid_output_port_system_overrides(system, rows) -> dict[int, dict[str, object]]:
    if system is None:
        return {}
    overrides = build_optical_solid_output_port_pose_overrides(rows)
    setattr(system, "_optical_solid_output_port_rows", list(rows or []))
    _install_build_hook(system)
    if not overrides:
        return {}
    pr3d = getattr(system, "Pr3D", None)
    try:
        transforms = getattr(system, "TRANS_2A", None)
        meshes = getattr(system, "EEE", None)
        needs_build = (
            pr3d is None
            or transforms is None
            or meshes is None
            or len(transforms) <= max(overrides)
            or len(meshes) <= max(overrides)
            or not hasattr(meshes[max(overrides)], "ray_trace")
        )
        if needs_build:
            system.build()
            return getattr(system, "_optical_solid_output_port_pose_overrides", overrides)
    except Exception:
        try:
            system.build()
            return getattr(system, "_optical_solid_output_port_pose_overrides", overrides)
        except Exception:
            return {}
    return _apply_optical_solid_output_port_system_overrides_built(system, overrides)
