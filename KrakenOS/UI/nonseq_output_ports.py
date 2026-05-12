from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from KrakenOS.UI import optical_solid_metadata
from KrakenOS.UI.optical_solid_metadata import (
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    normalize_optical_solid_face_function,
    normalize_optical_solid_face_side,
    optical_solid_face_world_records,
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
    transmit_faces: list[dict[str, object]] = []
    non_left_transmit_faces: list[dict[str, object]] = []
    for face in list(world_faces or []):
        if not isinstance(face, dict):
            continue
        function = normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
        if function != OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT:
            continue
        transmit_faces.append(face)
        side = normalize_optical_solid_face_side(face.get("side_2d"))
        if side != "Left":
            non_left_transmit_faces.append(face)
    pool = non_left_transmit_faces or transmit_faces
    if not pool:
        return None
    return max(pool, key=lambda face: float(face.get("area_mm2", 0.0) or 0.0))


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
            row_index += 1
            continue
        output_center = np.asarray(output_face.get("centroid_world", (0.0, 0.0, 0.0)), dtype=float).reshape(3)
        output_normal = _unit_vector(output_face.get("normal_world", (0.0, 0.0, 1.0)))
        frame_origin = output_center + output_normal * float(getattr(current, "thickness", 0.0) or 0.0)
        frame_rotation = _frame_rotation_from_normal(-output_normal)
        follower_index = row_index + 1
        while follower_index < len(prepared):
            follower = prepared[follower_index]
            if _row_has_optical_solid(follower):
                break
            if _row_surface(follower) == "Object":
                follower_index += 1
                continue
            local_rotation = optical_solid_metadata.rotation_matrix_from_kraken_tilts(
                float(getattr(follower, "tilt_x", 0.0) or 0.0),
                float(getattr(follower, "tilt_y", 0.0) or 0.0),
                float(getattr(follower, "tilt_z", 0.0) or 0.0),
            )
            rotation = frame_rotation @ local_rotation
            center = (
                frame_origin
                + (frame_rotation[:, 0] * float(getattr(follower, "desp_x", 0.0) or 0.0))
                + (frame_rotation[:, 1] * float(getattr(follower, "desp_y", 0.0) or 0.0))
                + (frame_rotation[:, 2] * float(getattr(follower, "desp_z", 0.0) or 0.0))
            )
            overrides[follower_index] = {
                "center": np.asarray(center, dtype=float),
                "rotation": np.asarray(rotation, dtype=float),
                "normal": np.asarray(rotation[:, 2], dtype=float),
                "output_face": dict(output_face),
                "source_index": int(row_index),
            }
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
