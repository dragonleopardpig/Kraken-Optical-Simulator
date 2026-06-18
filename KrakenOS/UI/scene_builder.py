"""Build a SceneBundle from KrakenOS system data and surface rows.

This module has no dependency on matplotlib, VTK, or tkinter.
It converts KrakenOS tracing results and surface descriptions into
the scene geometry dataclasses defined in ``scene_geometry``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable

import numpy as np

from .optical_solid_metadata import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
    OPTICAL_SOLID_FACE_ROLE_DEFAULT,
    OPTICAL_SOLID_FACE_SIDE_DEFAULT,
    float_or_default,
    legacy_role_from_optical_solid_face_function,
    nonnegative_int_list,
    normalize_optical_solid_face_function,
    normalize_optical_solid_face_side,
    optical_solid_face_local_anchor_point,
    optical_solid_face_plane_basis,
    optical_solid_face_world_records,
    point3_tuple,
    unit_vector_tuple,
)
from .scene_placement import (
    SCENE_PLACEMENT_ADVANCED_ATTR,
    normalize_scene_placement_settings,
    row_has_scene_placement_metadata,
    row_scene_placement_settings,
)
from .scene_geometry import (
    BoundaryFace3D,
    BoundsRect,
    LabelSpec,
    OpticalVolume3D,
    PickRegion,
    PlaneMarker,
    RayBranch3D,
    RayEvent3D,
    RayHit3D,
    RayPath3D,
    SceneBundle,
    ScenePlacement3D,
    SceneSource3D,
    SceneTarget3D,
    StyleHint,
    SurfaceCurve3D,
)
from .scene_row_mapping import build_scene_row_mapping
from ..TraceEvents import TRACE_EVENT_SOURCE_RAYKEEPER, trace_event_to_record

FOLDED_TERMINAL_POLICY_TRACE_EVENTS = "trace_events"
FOLDED_TERMINAL_POLICY_DISPLAY_COMPATIBILITY = "display_compatibility"
FOLDED_TERMINAL_POLICIES = {
    FOLDED_TERMINAL_POLICY_TRACE_EVENTS,
    FOLDED_TERMINAL_POLICY_DISPLAY_COMPATIBILITY,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _runtime_optical_solid_transform(system: Any | None, row_index: int) -> np.ndarray | None:
    if system is None:
        return None
    overrides = getattr(system, "_optical_solid_output_port_pose_overrides", None)
    if not isinstance(overrides, dict):
        return None
    pose = overrides.get(int(row_index))
    if pose is None:
        pose = overrides.get(str(int(row_index)))
    if not isinstance(pose, dict):
        return None
    for key in ("source_to_runtime_world", "runtime_transform"):
        try:
            matrix = np.asarray(pose.get(key), dtype=float).reshape(4, 4)
        except Exception:
            continue
        if np.all(np.isfinite(matrix)):
            return matrix
    return None


def _optical_solid_face_world_records_from_transform(
    row: Any,
    transform: np.ndarray,
    *,
    assigned_only: bool = True,
) -> list[dict[str, object]]:
    advanced = getattr(row, "advanced", {}) or {}
    if not isinstance(advanced, dict):
        return []
    metadata = advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
    if not isinstance(metadata, dict):
        return []
    try:
        matrix = np.asarray(transform, dtype=float).reshape(4, 4)
    except Exception:
        return []
    if not np.all(np.isfinite(matrix)):
        return []
    rotation = np.asarray(matrix[:3, :3], dtype=float)
    offset = np.asarray(matrix[:3, 3], dtype=float)
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
        anchor_local = np.asarray(optical_solid_face_local_anchor_point(face), dtype=float)
        normal_local = np.asarray(unit_vector_tuple(face.get("normal", (0.0, 0.0, 1.0))), dtype=float)
        if bool(face.get("flip_normal", False)):
            normal_local = -normal_local
        centroid_world = centroid_local @ rotation.T + offset
        anchor_world = anchor_local @ rotation.T + offset
        normal_world = np.asarray(unit_vector_tuple(normal_local @ rotation.T), dtype=float)
        u_axis_local, v_axis_local, _normal_axis_local = optical_solid_face_plane_basis(face)
        u_axis_world = np.asarray(unit_vector_tuple(np.asarray(u_axis_local, dtype=float) @ rotation.T), dtype=float)
        v_axis_world = np.asarray(unit_vector_tuple(np.asarray(v_axis_local, dtype=float) @ rotation.T), dtype=float)
        if not (
            np.all(np.isfinite(centroid_world))
            and np.all(np.isfinite(anchor_world))
            and np.all(np.isfinite(normal_world))
        ):
            continue
        world_face = dict(face)
        world_face["role"] = role
        world_face["function"] = function
        world_face["side_2d"] = side
        world_face["centroid_world"] = tuple(float(v) for v in centroid_world[:3])
        world_face["anchor_world"] = tuple(float(v) for v in anchor_world[:3])
        world_face["normal_world"] = tuple(float(v) for v in normal_world[:3])
        world_face["u_axis_world"] = tuple(float(v) for v in u_axis_world[:3])
        world_face["v_axis_world"] = tuple(float(v) for v in v_axis_world[:3])
        world_faces.append(world_face)
    return world_faces


def build_scene_boundary_faces(rows: list, system: Any | None = None) -> list[BoundaryFace3D]:
    boundary_faces: list[BoundaryFace3D] = []
    z_pos = 0.0
    for row_index, row in enumerate(rows):
        runtime_transform = _runtime_optical_solid_transform(system, row_index)
        try:
            if runtime_transform is not None:
                world_faces = _optical_solid_face_world_records_from_transform(
                    row,
                    runtime_transform,
                    assigned_only=False,
                )
            else:
                world_faces = optical_solid_face_world_records(row, z_pos, assigned_only=False)
        except Exception:
            world_faces = []
        source_stl = _row_optical_solid_source_stl(row)
        for face in world_faces:
            if not isinstance(face, dict):
                continue
            face_id = str(face.get("face_id", "") or "").strip()
            triangle_indices = tuple(nonnegative_int_list(face.get("triangle_indices", face.get("cell_indices"))))
            triangle_count = max(
                int(round(float_or_default(face.get("triangle_count"), 0.0))),
                len(triangle_indices),
                0,
            )
            normal_local = np.asarray(unit_vector_tuple(face.get("normal", (0.0, 0.0, 1.0))), dtype=float)
            if bool(face.get("flip_normal", False)):
                normal_local = -normal_local
            boundary_faces.append(
                BoundaryFace3D(
                    object_id=f"surface:{int(row_index)}",
                    row_index=int(row_index),
                    trace_surface=int(row_index),
                    face_id=face_id,
                    side_2d=str(face.get("side_2d", "") or "").strip(),
                    function=str(face.get("function", "") or "").strip(),
                    port_role=str(face.get("port_role", "") or "").strip(),
                    material=str(face.get("material", "") or getattr(row, "glass", "") or "").strip(),
                    coating=str(face.get("coating", "") or "").strip(),
                    split_ratio=float_or_default(face.get("split_ratio"), 0.5),
                    loss=float_or_default(face.get("loss"), 0.0),
                    phase_deg=float_or_default(face.get("phase_deg"), 0.0),
                    area_mm2=max(float_or_default(face.get("area_mm2"), 0.0), 0.0),
                    triangle_count=triangle_count,
                    triangle_indices=triangle_indices,
                    centroid_local=np.asarray(point3_tuple(face.get("centroid", (0.0, 0.0, 0.0))), dtype=float),
                    normal_local=normal_local,
                    centroid_world=np.asarray(point3_tuple(face.get("centroid_world", (0.0, 0.0, 0.0))), dtype=float),
                    normal_world=np.asarray(unit_vector_tuple(face.get("normal_world", (0.0, 0.0, 1.0))), dtype=float),
                    source_stl=source_stl,
                    diagnostics=tuple(_boundary_face_diagnostics(face_id, triangle_count, triangle_indices)),
                    metadata=dict(face),
                )
            )
        z_pos += float(getattr(row, "thickness", 0.0))
    return boundary_faces


def boundary_face_to_runtime_record(face: BoundaryFace3D) -> dict[str, object]:
    metadata = dict(face.metadata or {})
    record = dict(metadata)
    record.update(
        {
            "object_id": str(face.object_id),
            "row_index": int(face.row_index),
            "trace_surface": None if face.trace_surface is None else int(face.trace_surface),
            "face_id": str(face.face_id),
            "side_2d": str(face.side_2d),
            "function": str(face.function),
            "port_role": str(face.port_role),
            "material": str(face.material),
            "coating": str(face.coating),
            "split_ratio": None if face.split_ratio is None else float(face.split_ratio),
            "loss": None if face.loss is None else float(face.loss),
            "phase_deg": None if face.phase_deg is None else float(face.phase_deg),
            "area_mm2": float(face.area_mm2),
            "triangle_count": int(face.triangle_count),
            "triangle_indices": [int(index) for index in face.triangle_indices],
            "centroid": np.asarray(
                metadata.get("centroid", face.centroid_local),
                dtype=float,
            ).reshape(-1)[:3].tolist(),
            "normal": np.asarray(
                metadata.get("normal", face.normal_local),
                dtype=float,
            ).reshape(-1)[:3].tolist(),
            "centroid_local": np.asarray(face.centroid_local, dtype=float).reshape(-1)[:3].tolist(),
            "normal_local": np.asarray(face.normal_local, dtype=float).reshape(-1)[:3].tolist(),
            "centroid_world": np.asarray(face.centroid_world, dtype=float).reshape(-1)[:3].tolist(),
            "normal_world": np.asarray(face.normal_world, dtype=float).reshape(-1)[:3].tolist(),
            "source_stl": str(face.source_stl),
            "diagnostics": [str(item) for item in face.diagnostics],
            "boundary_source": "scene_boundary_index",
        }
    )
    return record


def build_scene_boundary_face_index(rows: list, system: Any | None = None) -> dict[int, list[dict[str, object]]]:
    index: dict[int, list[dict[str, object]]] = {}
    for face in build_scene_boundary_faces(rows, system=system):
        trace_surface = face.trace_surface if face.trace_surface is not None else face.row_index
        try:
            surface_index = int(trace_surface)
        except Exception:
            continue
        index.setdefault(surface_index, []).append(boundary_face_to_runtime_record(face))
    return index


def build_scene_optical_volumes(
    rows: list,
    boundary_faces: list[BoundaryFace3D] | None = None,
    system: Any | None = None,
) -> list[OpticalVolume3D]:
    faces = list(boundary_faces) if boundary_faces is not None else build_scene_boundary_faces(rows, system=system)
    faces_by_row: dict[int, list[BoundaryFace3D]] = {}
    for face in faces:
        try:
            faces_by_row.setdefault(int(face.row_index), []).append(face)
        except Exception:
            continue
    volumes: list[OpticalVolume3D] = []
    for row_index, row in enumerate(rows):
        source_stl = _row_optical_solid_source_stl(row)
        if not source_stl:
            continue
        row_faces = faces_by_row.get(int(row_index), [])
        face_ids = tuple(
            str(face.face_id)
            for face in row_faces
            if str(getattr(face, "face_id", "") or "").strip()
        )
        centroids = np.asarray(
            [
                np.asarray(face.centroid_world, dtype=float).reshape(-1)[:3]
                for face in row_faces
                if np.asarray(face.centroid_world, dtype=float).reshape(-1).size >= 3
            ],
            dtype=float,
        )
        finite_centroids = (
            centroids[np.all(np.isfinite(centroids[:, :3]), axis=1), :3]
            if centroids.ndim == 2 and centroids.shape[1] >= 3
            else np.empty((0, 3), dtype=float)
        )
        if finite_centroids.size:
            centroid_world = np.mean(finite_centroids, axis=0)
            bounds_min_world = np.min(finite_centroids, axis=0)
            bounds_max_world = np.max(finite_centroids, axis=0)
        else:
            centroid_world = np.full(3, np.nan)
            bounds_min_world = np.full(3, np.nan)
            bounds_max_world = np.full(3, np.nan)
        material = str(getattr(row, "glass", "") or "").strip()
        diagnostics = _optical_volume_diagnostics(material, row_faces)
        volumes.append(
            OpticalVolume3D(
                volume_id=f"volume:{int(row_index)}",
                object_id=f"surface:{int(row_index)}",
                row_index=int(row_index),
                trace_surface=int(row_index),
                volume_type="optical_solid",
                material=material,
                ambient_material="AIR",
                source_stl=source_stl,
                boundary_face_ids=face_ids,
                boundary_face_count=len(row_faces),
                centroid_world=np.asarray(centroid_world, dtype=float),
                bounds_min_world=np.asarray(bounds_min_world, dtype=float),
                bounds_max_world=np.asarray(bounds_max_world, dtype=float),
                diagnostics=tuple(diagnostics),
                metadata={
                    "surface": str(getattr(row, "surface", "") or ""),
                    "name": str(getattr(row, "name", "") or ""),
                    "row_material": material,
                },
            )
        )
    return volumes


def optical_volume_to_runtime_record(volume: OpticalVolume3D) -> dict[str, object]:
    return {
        "volume_id": str(volume.volume_id),
        "object_id": str(volume.object_id),
        "row_index": int(volume.row_index),
        "trace_surface": None if volume.trace_surface is None else int(volume.trace_surface),
        "volume_type": str(volume.volume_type),
        "material": str(volume.material),
        "ambient_material": str(volume.ambient_material),
        "source_stl": str(volume.source_stl),
        "boundary_face_ids": [str(face_id) for face_id in volume.boundary_face_ids],
        "boundary_face_count": int(volume.boundary_face_count),
        "centroid_world": np.asarray(volume.centroid_world, dtype=float).reshape(-1)[:3].tolist(),
        "bounds_min_world": np.asarray(volume.bounds_min_world, dtype=float).reshape(-1)[:3].tolist(),
        "bounds_max_world": np.asarray(volume.bounds_max_world, dtype=float).reshape(-1)[:3].tolist(),
        "diagnostics": [str(item) for item in volume.diagnostics],
        "metadata": dict(volume.metadata or {}),
    }


def build_scene_optical_volume_index(rows: list, system: Any | None = None) -> dict[int, dict[str, object]]:
    index: dict[int, dict[str, object]] = {}
    for volume in build_scene_optical_volumes(rows, system=system):
        trace_surface = volume.trace_surface if volume.trace_surface is not None else volume.row_index
        try:
            surface_index = int(trace_surface)
        except Exception:
            continue
        index[surface_index] = optical_volume_to_runtime_record(volume)
    return index


def build_scene_targets(
    rows: list,
    *,
    target_surface: int | None = None,
    detector_surface_indices: set[int] | None = None,
    detector_active_dims_overrides: dict[int, tuple[float, float]] | None = None,
) -> list[SceneTarget3D]:
    """Return explicit scene target records derived from table rows.

    These records do not add KrakenOS surfaces. They make object/reference,
    detector, aperture, and selected target roles visible to scene consumers
    instead of forcing every analysis to rediscover those roles from table rows.
    """
    detector_indices = _normalized_detector_surface_indices(rows, detector_surface_indices)
    targets: list[SceneTarget3D] = []
    z_pos = 0.0
    for row_index, row in enumerate(rows):
        surface = str(getattr(row, "surface", "") or "").strip()
        scene_target_settings = _row_scene_target_settings(row)
        scene_target_role = _normalize_scene_target_role(scene_target_settings.get("role"))
        is_detector = scene_target_role == "detector" or (
            not scene_target_role
            and (
                int(row_index) in detector_indices
                or _row_has_detector_metadata(row)
                or surface == "Image"
            )
        )
        is_object = surface == "Object" or scene_target_role == "object_reference"
        is_active_target = target_surface is not None and int(row_index) == int(target_surface)
        role = _scene_target_role(
            surface,
            is_detector=is_detector,
            is_active_target=is_active_target,
            scene_target_role=scene_target_role,
        )
        if role is None:
            z_pos += float(getattr(row, "thickness", 0.0) or 0.0)
            continue
        detector_settings = _row_detector_settings(row)
        active_width_mm = max(_safe_float(detector_settings.get("active_width_mm")), 0.0)
        active_height_mm = max(_safe_float(detector_settings.get("active_height_mm")), 0.0)
        if is_detector:
            override_w, override_h = _detector_override_dims(detector_active_dims_overrides, row_index)
            if active_width_mm <= 1e-12 and override_w > 1e-12:
                active_width_mm = override_w
            if active_height_mm <= 1e-12 and override_h > 1e-12:
                active_height_mm = override_h
        center, normal, tangent = _scene_target_frame(row_index, row, z_pos)
        targets.append(
            SceneTarget3D(
                target_id=f"surface:{int(row_index)}",
                name=str(getattr(row, "name", "") or surface or f"S{row_index}"),
                role=role,
                row_index=int(row_index),
                trace_surface=int(row_index),
                surface=surface,
                material=str(getattr(row, "glass", "") or ""),
                center_world=center,
                normal_world=normal,
                tangent_world=tangent,
                diameter=max(_safe_float(getattr(row, "diameter", 0.0)), 0.0),
                active_width_mm=active_width_mm,
                active_height_mm=active_height_mm,
                detector_bins=str(detector_settings.get("bins", "") or ""),
                pixel_pitch_um=max(_safe_float(detector_settings.get("pixel_pitch_um")), 0.0),
                is_detector=bool(is_detector),
                is_object=bool(is_object),
                is_active_target=bool(is_active_target),
                metadata={
                    "target_source": "table_row",
                    "element_role": _row_element_role(row),
                    "scene_target_settings": scene_target_settings,
                    "detector_settings": detector_settings,
                },
            )
        )
        z_pos += float(getattr(row, "thickness", 0.0) or 0.0)
    return targets


def scene_target_to_runtime_record(target: SceneTarget3D) -> dict[str, object]:
    center = np.asarray(target.center_world, dtype=float).reshape(-1)
    normal = np.asarray(target.normal_world, dtype=float).reshape(-1)
    tangent = np.asarray(target.tangent_world, dtype=float).reshape(-1)
    return {
        "target_id": str(target.target_id),
        "name": str(target.name),
        "role": str(target.role),
        "row_index": int(target.row_index),
        "trace_surface": None if target.trace_surface is None else int(target.trace_surface),
        "surface": str(target.surface),
        "material": str(target.material),
        "center_world": center[:3].tolist() if center.size >= 3 else [np.nan, np.nan, np.nan],
        "normal_world": normal[:3].tolist() if normal.size >= 3 else [np.nan, np.nan, np.nan],
        "tangent_world": tangent[:3].tolist() if tangent.size >= 3 else [np.nan, np.nan, np.nan],
        "diameter": float(target.diameter),
        "active_width_mm": float(target.active_width_mm),
        "active_height_mm": float(target.active_height_mm),
        "detector_bins": str(target.detector_bins),
        "pixel_pitch_um": float(target.pixel_pitch_um),
        "is_detector": bool(target.is_detector),
        "is_object": bool(target.is_object),
        "is_active_target": bool(target.is_active_target),
        "metadata": dict(target.metadata or {}),
    }


def build_scene_placements(
    rows: list,
    *,
    targets: list[SceneTarget3D] | None = None,
) -> list[ScenePlacement3D]:
    """Return row-backed 3-D placement records for targets and CAD/STL solids."""
    target_by_row = {
        int(target.row_index): target
        for target in list(targets or [])
        if getattr(target, "row_index", None) is not None
    }
    placements: list[ScenePlacement3D] = []
    z_pos = 0.0
    for row_index, row in enumerate(rows):
        settings = row_scene_placement_settings(row)
        if not bool(settings.get("enabled", True)):
            z_pos += float(getattr(row, "thickness", 0.0) or 0.0)
            continue
        target = target_by_row.get(int(row_index))
        has_solid = bool(_row_optical_solid_source_stl(row))
        explicit = row_has_scene_placement_metadata(row)
        surface = str(getattr(row, "surface", "") or "").strip()
        if target is not None and surface in {"Object", "Image"} and not has_solid:
            z_pos += float(getattr(row, "thickness", 0.0) or 0.0)
            continue
        if target is None and not has_solid and not explicit:
            z_pos += float(getattr(row, "thickness", 0.0) or 0.0)
            continue
        center, normal, tangent = _scene_target_frame(row_index, row, z_pos)
        source_kind = "surface_row"
        target_id = ""
        if target is not None:
            center = np.asarray(target.center_world, dtype=float).reshape(-1)[:3]
            normal = np.asarray(target.normal_world, dtype=float).reshape(-1)[:3]
            tangent = np.asarray(target.tangent_world, dtype=float).reshape(-1)[:3]
            target_id = str(target.target_id)
            source_kind = "scene_target"
        if has_solid:
            source_kind = "optical_solid" if not target_id else "targeted_optical_solid"
        center = _point3_or_default(center, (0.0, 0.0, z_pos))
        normal = _unit_vector_or_default(normal, (0.0, 0.0, 1.0))
        tangent = _unit_vector_or_default(tangent, (0.0, 1.0, 0.0))
        placements.append(
            ScenePlacement3D(
                placement_id=f"surface:{int(row_index)}",
                row_index=int(row_index),
                trace_surface=int(row_index),
                target_id=target_id,
                object_id=f"surface:{int(row_index)}",
                source_kind=source_kind,
                center_world=np.asarray(center, dtype=float),
                normal_world=np.asarray(normal, dtype=float),
                tangent_world=np.asarray(tangent, dtype=float),
                pose_translation=np.asarray(
                    (
                        _safe_float(getattr(row, "desp_x", 0.0)),
                        _safe_float(getattr(row, "desp_y", 0.0)),
                        _safe_float(getattr(row, "desp_z", 0.0)),
                    ),
                    dtype=float,
                ),
                pose_rotation_deg=np.asarray(
                    (
                        _safe_float(getattr(row, "tilt_x", 0.0)),
                        _safe_float(getattr(row, "tilt_y", 0.0)),
                        _safe_float(getattr(row, "tilt_z", 0.0)),
                    ),
                    dtype=float,
                ),
                anchor=str(settings.get("anchor", "row_pose") or "row_pose"),
                snap_enabled=bool(settings.get("snap_enabled", False)),
                snap_mm=float(settings.get("snap_mm", 1.0) or 1.0),
                snap_deg=float(settings.get("snap_deg", 5.0) or 5.0),
                grid_visible=bool(settings.get("grid_visible", True)),
                grid_spacing_mm=float(settings.get("grid_spacing_mm", 10.0) or 10.0),
                grid_extent_mm=float(settings.get("grid_extent_mm", 100.0) or 100.0),
                metadata={
                    "surface": str(getattr(row, "surface", "") or ""),
                    "name": str(getattr(row, "name", "") or ""),
                    "source_stl": _row_optical_solid_source_stl(row),
                    "scene_placement_settings": normalize_scene_placement_settings(settings),
                    "placement_source": (
                        SCENE_PLACEMENT_ADVANCED_ATTR
                        if explicit
                        else "scene_target"
                        if target is not None
                        else "optical_solid"
                    ),
                },
            )
        )
        z_pos += float(getattr(row, "thickness", 0.0) or 0.0)
    return placements


def scene_placement_to_runtime_record(placement: ScenePlacement3D) -> dict[str, object]:
    center = np.asarray(placement.center_world, dtype=float).reshape(-1)
    normal = np.asarray(placement.normal_world, dtype=float).reshape(-1)
    tangent = np.asarray(placement.tangent_world, dtype=float).reshape(-1)
    translation = np.asarray(placement.pose_translation, dtype=float).reshape(-1)
    rotation = np.asarray(placement.pose_rotation_deg, dtype=float).reshape(-1)
    return {
        "placement_id": str(placement.placement_id),
        "row_index": int(placement.row_index),
        "trace_surface": None if placement.trace_surface is None else int(placement.trace_surface),
        "target_id": str(placement.target_id),
        "object_id": str(placement.object_id),
        "source_kind": str(placement.source_kind),
        "center_world": center[:3].tolist() if center.size >= 3 else [np.nan, np.nan, np.nan],
        "normal_world": normal[:3].tolist() if normal.size >= 3 else [np.nan, np.nan, np.nan],
        "tangent_world": tangent[:3].tolist() if tangent.size >= 3 else [np.nan, np.nan, np.nan],
        "pose_translation": translation[:3].tolist() if translation.size >= 3 else [0.0, 0.0, 0.0],
        "pose_rotation_deg": rotation[:3].tolist() if rotation.size >= 3 else [0.0, 0.0, 0.0],
        "anchor": str(placement.anchor),
        "snap_enabled": bool(placement.snap_enabled),
        "snap_mm": float(placement.snap_mm),
        "snap_deg": float(getattr(placement, "snap_deg", 5.0)),
        "grid_visible": bool(placement.grid_visible),
        "grid_spacing_mm": float(placement.grid_spacing_mm),
        "grid_extent_mm": float(placement.grid_extent_mm),
        "metadata": dict(placement.metadata or {}),
    }


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except Exception:
        return float(default)
    return number if np.isfinite(number) else float(default)


def _row_advanced(row: Any) -> dict[str, object]:
    advanced = getattr(row, "advanced", {}) or {}
    return advanced if isinstance(advanced, dict) else {}


def _row_element_role(row: Any) -> str:
    element = _row_advanced(row).get("Element", {})
    if not isinstance(element, dict):
        return ""
    return str(element.get("arm_role", "") or "").strip()


def _row_has_detector_metadata(row: Any) -> bool:
    advanced = _row_advanced(row)
    if isinstance(advanced.get("Detector"), dict):
        return True
    if _row_element_role(row) == "Detector":
        return True
    display_settings = advanced.get("Display2D", {})
    if isinstance(display_settings, dict) and isinstance(display_settings.get("branch_output_targets"), dict):
        return True
    return isinstance(advanced.get("Interferogram"), dict)


def _row_detector_settings(row: Any) -> dict[str, object]:
    settings = {
        "active_width_mm": 0.0,
        "active_height_mm": 0.0,
        "bins": "",
        "pixel_pitch_um": 0.0,
    }
    detector_settings = _row_advanced(row).get("Detector", {})
    if isinstance(detector_settings, dict):
        settings.update(detector_settings)
    settings["active_width_mm"] = max(_safe_float(settings.get("active_width_mm")), 0.0)
    settings["active_height_mm"] = max(_safe_float(settings.get("active_height_mm")), 0.0)
    settings["pixel_pitch_um"] = max(_safe_float(settings.get("pixel_pitch_um")), 0.0)
    bins = str(settings.get("bins", "") or "").strip()
    if bins.lower() in {"auto", "default", "none"}:
        bins = ""
    if bins:
        try:
            bins = str(int(np.clip(int(float(bins)), 4, 512)))
        except Exception:
            bins = ""
    settings["bins"] = bins
    return settings


def _detector_override_dims(
    detector_active_dims_overrides: dict[int, tuple[float, float]] | None,
    row_index: int,
) -> tuple[float, float]:
    """Vendor ``(width, height)`` active dims for a detector row, else ``(0, 0)``.

    These come from the selected camera's datasheet sensor size and take
    precedence over the bare-diameter fallback so the detector footprint is
    drawn (and ray hits classified) at the real sensor, not the image-surface
    clear aperture.
    """
    if not detector_active_dims_overrides:
        return 0.0, 0.0
    override = detector_active_dims_overrides.get(int(row_index))
    if not override:
        return 0.0, 0.0
    try:
        width = max(float(override[0]), 0.0)
        height = max(float(override[1]), 0.0)
    except (TypeError, ValueError, IndexError):
        return 0.0, 0.0
    return width, height


def _row_scene_target_settings(row: Any) -> dict[str, object]:
    settings = {"role": "", "label": ""}
    advanced = _row_advanced(row)
    raw = advanced.get("SceneTarget", {})
    if isinstance(raw, dict):
        settings.update(raw)
    settings["role"] = _normalize_scene_target_role(settings.get("role"))
    settings["label"] = str(settings.get("label", "") or "").strip()
    return settings


def _normalize_scene_target_role(value: object) -> str:
    role = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "auto": "",
        "from_surface": "",
        "analysis": "analysis_target",
        "target": "analysis_target",
        "object": "object_reference",
        "object_ref": "object_reference",
        "diffuse_object": "object_target",
    }
    role = aliases.get(role, role)
    return role if role in {"", "analysis_target", "aperture", "detector", "object_reference", "object_target"} else ""


def _scene_target_role(
    surface: str,
    *,
    is_detector: bool,
    is_active_target: bool,
    scene_target_role: str = "",
) -> str | None:
    if is_detector:
        return "detector"
    if scene_target_role:
        return scene_target_role
    if surface == "Object":
        return "object_reference"
    if surface in {"Object Target", "Diffuse Object"}:
        return "object_target"
    if surface == "Aperture":
        return "aperture"
    if is_active_target:
        return "analysis_target"
    return None


def _unit_vector_or_default(value: object, default: tuple[float, float, float]) -> np.ndarray:
    try:
        vector = np.asarray(value, dtype=float).reshape(-1)
    except Exception:
        vector = np.asarray(default, dtype=float)
    if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
        vector = np.asarray(default, dtype=float)
    else:
        vector = vector[:3]
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12:
        vector = np.asarray(default, dtype=float)
        norm = float(np.linalg.norm(vector))
    return vector / max(norm, 1e-12)


def _point3_or_default(value: object, default: tuple[float, float, float]) -> np.ndarray:
    try:
        vector = np.asarray(value, dtype=float).reshape(-1)
    except Exception:
        vector = np.asarray(default, dtype=float)
    if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
        vector = np.asarray(default, dtype=float)
    else:
        vector = vector[:3]
    return np.asarray(vector, dtype=float)


def _scene_target_frame(row_index: int, row: Any, z_pos: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    display_settings = _row_display_settings(row)
    center_value = display_settings.get("plane_center")
    tangent_value = display_settings.get("plane_tangent")
    center = None
    tangent = None
    if center_value is not None:
        try:
            raw_center = np.asarray(center_value, dtype=float).reshape(-1)
            if raw_center.size >= 3 and np.all(np.isfinite(raw_center[:3])):
                center = raw_center[:3]
            elif raw_center.size >= 2 and np.all(np.isfinite(raw_center[:2])):
                center = np.asarray((0.0, raw_center[1], raw_center[0]), dtype=float)
        except Exception:
            center = None
    if tangent_value is not None:
        try:
            raw_tangent = np.asarray(tangent_value, dtype=float).reshape(-1)
            if raw_tangent.size >= 3 and np.all(np.isfinite(raw_tangent[:3])):
                tangent = raw_tangent[:3]
            elif raw_tangent.size >= 2 and np.all(np.isfinite(raw_tangent[:2])):
                tangent = np.asarray((0.0, raw_tangent[1], raw_tangent[0]), dtype=float)
        except Exception:
            tangent = None
    if center is None:
        center_z = float(z_pos) + _safe_float(getattr(row, "desp_z", 0.0))
        if str(getattr(row, "surface", "") or "") == "Image" and abs(_safe_float(getattr(row, "thickness", 0.0))) > 1e-12:
            center_z += _safe_float(getattr(row, "thickness", 0.0))
        center = np.asarray(
            (
                _safe_float(getattr(row, "desp_x", 0.0)),
                _safe_float(getattr(row, "desp_y", 0.0)),
                center_z,
            ),
            dtype=float,
        )
    tangent = _unit_vector_or_default(
        tangent if tangent is not None else (0.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
    )
    normal = np.cross(np.asarray((1.0, 0.0, 0.0), dtype=float), tangent)
    if np.linalg.norm(normal) <= 1e-12:
        normal = np.asarray((0.0, 0.0, 1.0), dtype=float)
    normal = _unit_vector_or_default(normal, (0.0, 0.0, 1.0))
    return np.asarray(center, dtype=float), normal, tangent


def _superseded_image_row_indices(rows) -> set:
    """Row indices of sequential Image surfaces (bugs/0093 supersession)."""
    return {
        int(i)
        for i, r in enumerate(rows or [])
        if str(getattr(r, "surface", "") or "") == "Image"
    }


def drop_superseded_image_display(targets, surface_curves, labels, rows, *, has_branch_detector):
    """bugs/0093: hide the sequential Image's target + plane curve + label when a
    branch detector supersedes it.

    A beam-splitter split derives a branch detector at the transmit arm's true
    focus (= bare focus + plate shift). Inserting the splitter also pushes the
    sequential Image surface back by the element's *full* thickness (not the plate
    shift), so the Image lingers BEHIND the (correct) detector. 0092 hid only the
    3-D aperture disk; this also drops:
      * the Image **target** -- otherwise its ``is_detector`` footprint still draws
        as an orange detector marker at the stale location (the leftover the user
        kept flagging). The branch detector(s) hard-stop the rays before it, so
        nothing needs the superseded Image plane.
      * the Image plane **curve** + **label** (drawn by both the 2-D and 3-D views).
    No-op without a branch detector, so plain sequential/folded scenes are
    unaffected. Returns ``(targets, curves, labels)``.
    """
    if not has_branch_detector:
        return targets, surface_curves, labels
    rows_idx = _superseded_image_row_indices(rows)
    if not rows_idx:
        return targets, surface_curves, labels
    kept_targets = [t for t in targets if int(getattr(t, "row_index", -1)) not in rows_idx]
    curves = [c for c in surface_curves if int(getattr(c, "row_index", -1)) not in rows_idx]
    kept_labels = [lbl for lbl in labels if int(getattr(lbl, "row_index", -1)) not in rows_idx]
    return kept_targets, curves, kept_labels


def build_scene_bundle(
    *,
    rows: list,
    system: Any | None,
    rays: Any | None,
    display_orientation: str = "YZ",
    show_clipped_rays: bool = True,
    field_count: int = 1,
    ray_count_per_field: int = 5,
    field_colors: list[str] | None = None,
    folded_geometry: Any | None = None,
    row_polylines_fn: Callable | None = None,
    surface_meshes_fn: Callable | None = None,
    project_fn: Callable | None = None,
    reference_plane_overrides: dict | None = None,
    folded_ray_display_paths: list[np.ndarray] | None = None,
    folded_terminal_policy: str = FOLDED_TERMINAL_POLICY_TRACE_EVENTS,
    trace_mode_requested: str = "Auto",
    trace_mode_active: str = "Sequential",
    trace_mode_note: str = "",
    target_surface: int | None = None,
    detector_surface_indices: set[int] | None = None,
    detector_active_dims_overrides: dict[int, tuple[float, float]] | None = None,
    allow_target_plane_contact: bool = False,
    sources: list[SceneSource3D] | None = None,
    source_row_order: str = "after_object",
    branch_camera_sensors: dict | None = None,
) -> SceneBundle:
    """Construct a complete :class:`SceneBundle` from tracing data.

    Parameters
    ----------
    rows : list[SurfaceRow]
        The surface table rows.
    system : KrakenOS system object (may be *None* for fallback).
    rays : KrakenOS raykeeper (may be *None*).
    display_orientation : ``"YZ"``, ``"XZ"``, or ``"XY"``.
    folded_geometry :
        Pre-computed folded geometry tuple from the editor, or *None*
        for sequential layouts.  When provided the tuple is
        ``(point, direction, max_half, extent_points, elements)``.
    row_polylines_fn :
        Callback ``(system, row_index, z_pos) -> list[np.ndarray]``
        used to extract 2-D polylines for sequential surfaces.  This
        bridges the KrakenOS mesh API without importing it here.
    surface_meshes_fn :
        Optional callback ``(system) -> list[SurfaceMesh3D]`` used by 3-D
        renderers.  It is intentionally callback-based so this builder stays
        independent of PyVista/VTK.
    project_fn :
        Callback ``(z_array, y_array) -> (x_display, y_display)``.
    reference_plane_overrides :
        Mapping ``{row_index: (center, along)}`` for folded plane display.
    folded_ray_display_paths :
        Pre-computed folded ray display override paths (list of Nx2 arrays).
    folded_terminal_policy :
        ``"trace_events"`` keeps KrakenOS ray events authoritative and records
        folded display detector reach only as diagnostics.
        ``"display_compatibility"`` lets folded display paths rewrite terminal
        detector reach for legacy folded-preview workflows.
    """
    scene_sources = list(sources or [])
    scene_row_mapping = build_scene_row_mapping(
        rows,
        scene_sources,
        include_sources=True,
        source_row_order=source_row_order,
    )
    if not rows:
        return SceneBundle(
            sources=scene_sources,
            scene_row_mapping=scene_row_mapping,
            display_orientation=display_orientation,
        )

    max_half = max((max(row.diameter / 2.0, 0.5) for row in rows), default=1.0)
    has_off_axis = _has_off_axis_geometry(rows)
    colors = field_colors or _default_field_colors(field_count)
    detector_surface_indices = _normalized_detector_surface_indices(rows, detector_surface_indices)
    boundary_faces = build_scene_boundary_faces(rows, system=system)
    optical_volumes = build_scene_optical_volumes(rows, boundary_faces, system=system)
    scene_targets = build_scene_targets(
        rows,
        target_surface=target_surface,
        detector_surface_indices=detector_surface_indices,
        detector_active_dims_overrides=detector_active_dims_overrides,
    )
    scene_placements = build_scene_placements(rows, targets=scene_targets)

    # --- surfaces ---
    extent_points: list[np.ndarray] = []
    elements = None
    if folded_geometry is not None:
        _point, _direction, max_half, extent_points_raw, elements = folded_geometry
        extent_points = list(extent_points_raw)
        surface_curves = _build_folded_surface_curves(rows, elements)
    else:
        surface_curves = _build_sequential_surface_curves(
            rows, system, row_polylines_fn,
        )
    surface_curves.extend(
        _build_reference_plane_curves(
            rows,
            project_fn=project_fn,
            overrides=reference_plane_overrides or {},
            detector_surface_indices=detector_surface_indices,
        )
    )
    surface_curves.extend(
        _build_display_overlay_curves(
            rows,
            project_fn=project_fn,
        )
    )
    source_curves, source_labels = _build_source_markers(
        scene_sources,
        display_orientation=display_orientation,
        project_fn=project_fn,
    )
    surface_curves.extend(source_curves)

    # --- rays ---
    ray_paths = _build_ray_paths(
        rows,
        system,
        rays,
        field_count,
        ray_count_per_field,
        colors,
        target_surface=target_surface,
        detector_surface_indices=detector_surface_indices,
        allow_target_plane_contact=allow_target_plane_contact,
        detector_active_dims_overrides=detector_active_dims_overrides,
    )
    if folded_ray_display_paths is not None and elements:
        _sync_folded_terminal_events(
            ray_paths,
            folded_ray_display_paths,
            elements,
            detector_surface_indices,
            folded_terminal_policy=folded_terminal_policy,
        )
    ray_events = [event for path in ray_paths for event in list(getattr(path, "events", []) or [])]

    # --- branch detectors (bugs/0088 Phase B1) ---
    # Derive a detector per TERMINAL leaf branch of the traced ray tree (beam
    # splitter arms etc.), so reflected/leaf branches get a hard-stop detector at
    # their focus. Display-only: these are is_detector SceneTarget3D appended to
    # the target list so they (a) draw as a plane and (b) feed Phase A's
    # detector_planes_for_hard_stop. Pure sequential/folded scenes produce only a
    # leaf that reaches the Image, so they get NONE (no behaviour change). The
    # transmit/sequential Image detector is untouched (not duplicated).
    branch_detectors: list = []
    try:
        from KrakenOS.UI.services.branch_detectors import (
            derive_branch_detectors,
            branch_detector_scene_target,
            branch_detector_plane_curve,
        )

        branch_detectors = derive_branch_detectors(
            ray_paths,
            existing_targets=scene_targets,
            scene_radius=float(max_half) * 2.0,
            branch_camera_sensors=branch_camera_sensors,
        )
        for offset, branch_detector in enumerate(branch_detectors):
            scene_targets.append(
                branch_detector_scene_target(branch_detector, row_index=100000 + offset)
            )
            surface_curves.append(branch_detector_plane_curve(branch_detector))
    except Exception:
        branch_detectors = []

    # --- 3-D surface/body meshes ---
    surface_meshes = []
    if surface_meshes_fn is not None and system is not None:
        try:
            surface_meshes = list(surface_meshes_fn(system) or [])
        except Exception:
            surface_meshes = []

    # --- labels ---
    labels = _build_reference_plane_labels(
        rows,
        project_fn=project_fn,
        overrides=reference_plane_overrides or {},
        detector_surface_indices=detector_surface_indices,
    )
    labels.extend(source_labels)
    labels.extend(_build_key_optic_labels(rows, surface_curves))

    # bugs/0093: drop the superseded sequential Image's target + plane curve + label
    # when a split derived a branch detector at the true focus (see helper docstring).
    scene_targets, surface_curves, labels = drop_superseded_image_display(
        scene_targets, surface_curves, labels, rows, has_branch_detector=bool(branch_detectors)
    )

    # --- pick regions ---
    pick_regions = _build_pick_regions(rows, surface_curves)

    # --- bounds ---
    all_points = list(extent_points)
    for curve in surface_curves:
        pts = _curve_points_yz_display(curve.points_world)
        if pts.shape[0] >= 2:
            all_points.append(pts)
    bounds = BoundsRect.from_points(all_points)

    return SceneBundle(
        sources=scene_sources,
        targets=scene_targets,
        placements=scene_placements,
        scene_row_mapping=scene_row_mapping,
        surface_curves=surface_curves,
        surface_meshes=surface_meshes,
        optical_volumes=optical_volumes,
        boundary_faces=boundary_faces,
        ray_paths=ray_paths,
        ray_events=ray_events,
        planes=[],
        labels=labels,
        pick_regions=pick_regions,
        bounds=bounds,
        has_off_axis=has_off_axis,
        max_half=max_half,
        display_orientation=display_orientation,
        extra={
            "elements": elements,
            "folded_ray_display_paths": folded_ray_display_paths,
            "trace_mode_requested": trace_mode_requested,
            "trace_mode_active": trace_mode_active,
            "trace_mode_note": trace_mode_note,
            "folded_terminal_policy": _normalize_folded_terminal_policy(folded_terminal_policy),
            "sources": scene_sources,
            "scene_row_mapping": scene_row_mapping,
            "scene_row_records": scene_row_mapping.to_jsonable()["records"],
            "scene_target_records": [scene_target_to_runtime_record(target) for target in scene_targets],
            "scene_placement_records": [
                scene_placement_to_runtime_record(placement) for placement in scene_placements
            ],
            "optical_volume_records": [optical_volume_to_runtime_record(volume) for volume in optical_volumes],
            "boundary_face_records": [boundary_face_to_runtime_record(face) for face in boundary_faces],
            "trace_surface_to_scene_row": scene_row_mapping.trace_surface_to_scene,
            "scene_row_to_trace_surface": scene_row_mapping.scene_to_trace_surface,
            "detector_surface_indices": sorted(int(index) for index in detector_surface_indices),
        },
    )


# ---------------------------------------------------------------------------
# Optical-solid boundary face builders
# ---------------------------------------------------------------------------

def _row_optical_solid_source_stl(row: Any) -> str:
    advanced = getattr(row, "advanced", {}) or {}
    if not isinstance(advanced, dict):
        return ""
    metadata = advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
    source_stl = ""
    if isinstance(metadata, dict):
        source_stl = str(metadata.get("source_stl", "") or "").strip()
    if not source_stl:
        source_stl = str(advanced.get("Solid_3d_stl", "") or "").strip()
    return "" if source_stl == "None" else source_stl


def _boundary_face_diagnostics(
    face_id: str,
    triangle_count: int,
    triangle_indices: tuple[int, ...],
) -> list[str]:
    diagnostics: list[str] = []
    if not face_id:
        diagnostics.append("missing optical solid face id")
    if int(triangle_count) > 0 and not triangle_indices:
        diagnostics.append(
            "missing exact triangle membership; runtime will fall back to face-plane inference"
        )
    return diagnostics


def _optical_volume_diagnostics(material: str, boundary_faces: list[BoundaryFace3D]) -> list[str]:
    diagnostics: list[str] = []
    material_text = str(material or "").strip()
    if not material_text:
        diagnostics.append("optical volume has no material")
    if material_text.upper() == "AIR":
        diagnostics.append("optical volume material is AIR")
    if not boundary_faces:
        diagnostics.append("optical volume has no boundary faces")
    elif any(tuple(getattr(face, "diagnostics", ()) or ()) for face in boundary_faces):
        diagnostics.append("one or more boundary faces have diagnostics")
    return diagnostics


# ---------------------------------------------------------------------------
# Surface curve builders
# ---------------------------------------------------------------------------

def _is_inpath_trailing_spacer_row(row: Any) -> bool:
    """bugs/0093: the AIR gap-carrier the in-path promote (bugs/0079) inserts after a
    promoted solid. It keeps the solid's large diameter so the trace never clips, but
    it is NOT a physical surface, so the display must not draw its clear-aperture ring
    (the "big circle" at the cube's transmit output)."""
    advanced = getattr(row, "advanced", {}) or {}
    return isinstance(advanced, dict) and bool(advanced.get("InPathTrailingSpacer"))


def _build_sequential_surface_curves(
    rows: list,
    system: Any | None,
    row_polylines_fn: Callable | None,
) -> list[SurfaceCurve3D]:
    curves: list[SurfaceCurve3D] = []
    curve_map: dict[int, np.ndarray] = {}
    z_pos = 0.0
    for row_index, row in enumerate(rows):
        if row.surface in {"Object", "Image"}:
            z_pos += float(row.thickness)
            continue
        if _is_inpath_trailing_spacer_row(row):
            z_pos += float(row.thickness)
            continue
        color, linewidth, alpha = surface_style_for_row(row)
        style = StyleHint(color=color, linewidth=linewidth, alpha=alpha)
        polylines: list[np.ndarray] = []
        if row_polylines_fn is not None and system is not None:
            polylines = row_polylines_fn(system, row_index, z_pos)
        for polyline in polylines:
            points = _surface_polyline_world_points(polyline)
            if points.ndim != 2 or points.shape[0] < 2:
                continue
            kind = row.surface.lower().replace(" ", "_")
            advanced = getattr(row, "advanced", {}) or {}
            if isinstance(advanced, dict) and advanced.get("Solid_3d_stl") not in (None, "", "None"):
                kind = "stl_solid"
            curves.append(SurfaceCurve3D(
                row_index=row_index,
                kind=kind,
                points_world=points,
                style=style,
            ))
            if row_index not in curve_map:
                curve_map[row_index] = points
        z_pos += float(row.thickness)
    curves.extend(_build_lens_edge_curves(rows, curve_map))
    return curves


def _surface_polyline_world_points(polyline: object) -> np.ndarray:
    """Return native scene points for a surface polyline.

    Newer row adapters return world ``(X, Y, Z)`` points directly.  Legacy
    display builders still return YZ display points as ``(Z, Y)``; lift those
    into the scene at ``X=0`` so auxiliary XZ/XY views use the same projector
    path instead of a second 2-D drawing convention.
    """
    try:
        points = np.asarray(polyline, dtype=float)
    except Exception:
        return np.empty((0, 3), dtype=float)
    if points.ndim != 2 or points.shape[0] < 2:
        return np.empty((0, 3), dtype=float)
    if points.shape[1] >= 3:
        return np.asarray(points[:, :3], dtype=float)
    if points.shape[1] >= 2:
        z_values = np.asarray(points[:, 0], dtype=float)
        y_values = np.asarray(points[:, 1], dtype=float)
        x_values = np.zeros_like(z_values, dtype=float)
        return np.column_stack((x_values, y_values, z_values))
    return np.empty((0, 3), dtype=float)


def _curve_points_yz_display(points: object) -> np.ndarray:
    """Return YZ display coordinates from a 3-D or legacy 2-D curve."""
    try:
        pts = np.asarray(points, dtype=float)
    except Exception:
        return np.empty((0, 2), dtype=float)
    if pts.ndim != 2 or pts.shape[0] == 0:
        return np.empty((0, 2), dtype=float)
    if pts.shape[1] >= 3:
        return np.column_stack((pts[:, 2], pts[:, 1]))
    if pts.shape[1] >= 2:
        return np.asarray(pts[:, :2], dtype=float)
    return np.empty((0, 2), dtype=float)


def _build_folded_surface_curves(
    rows: list,
    elements: list,
) -> list[SurfaceCurve3D]:
    curves: list[SurfaceCurve3D] = []
    curve_map: dict[int, np.ndarray] = {}
    for idx, elem in enumerate(elements):
        # Elements may be 4-tuples (legacy) or 5-tuples (with mirror_tangent).
        surface_type, center, row, branch_dir = elem[0], elem[1], elem[2], elem[3]
        mirror_tangent = elem[4] if len(elem) > 4 else None
        row_index = idx + 1
        if _is_inpath_trailing_spacer_row(row):  # bugs/0093: gap-carrier, no ring
            continue
        if surface_type in {"Mirror", "Object Target", "Diffuse Object"}:
            half = max(row.diameter / 2.0, 0.5)
            if mirror_tangent is not None:
                tangent = np.asarray(mirror_tangent, dtype=float).copy()
                tn = np.linalg.norm(tangent)
                if tn > 1e-12:
                    tangent /= tn
                else:
                    theta = np.deg2rad(-float(row.tilt_x))
                    tangent = np.array([np.cos(theta), np.sin(theta)], dtype=float)
            else:
                theta = np.deg2rad(-float(row.tilt_x))
                tangent = np.array([np.cos(theta), np.sin(theta)], dtype=float)
                tangent /= max(np.linalg.norm(tangent), 1e-12)
            points = np.vstack((center - tangent * half, center + tangent * half))
            if surface_type == "Object Target":
                kind = "object_target"
                style = StyleHint(color="#202020", linewidth=2.2, alpha=0.95)
            elif surface_type == "Diffuse Object":
                kind = "diffuse_object"
                style = StyleHint(color="#16a34a", linewidth=2.2, alpha=0.95)
            else:
                kind = "mirror"
                style = StyleHint(color="#202020", linewidth=2.2, alpha=0.95)
            curves.append(SurfaceCurve3D(
                row_index=row_index,
                kind=kind,
                points_world=points,
                style=style,
                coordinate_space="folded_yz_display",
            ))
        elif surface_type == "Standard":
            axis = branch_dir / max(np.linalg.norm(branch_dir), 1e-12)
            tangent = np.array([-axis[1], axis[0]], dtype=float)
            half = max(row.diameter / 2.0, 0.5)
            yy = np.linspace(-half, half, 128)
            if abs(float(row.rc)) <= half + 1e-9:
                xx = np.zeros_like(yy)
            else:
                rr = abs(float(row.rc))
                sign = 1.0 if float(row.rc) >= 0.0 else -1.0
                xx = float(row.rc) - sign * np.sqrt(np.maximum(rr * rr - yy * yy, 0.0))
            points = center[None, :] + np.outer(xx, axis) + np.outer(yy, tangent)
            curve_map[row_index] = np.asarray(points, dtype=float)
            curves.append(SurfaceCurve3D(
                row_index=row_index,
                kind="standard",
                points_world=points,
                style=StyleHint(color="#2563eb", linewidth=1.8, alpha=0.95),
                coordinate_space="folded_yz_display",
            ))
        elif surface_type == "Aperture":
            tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
            tangent /= max(np.linalg.norm(tangent), 1e-12)
            half = max(row.diameter / 2.0, 0.5)
            points = np.vstack((center - tangent * half, center + tangent * half))
            curves.append(SurfaceCurve3D(
                row_index=row_index,
                kind="aperture",
                points_world=points,
                style=StyleHint(color="#b45309", linewidth=1.6, alpha=0.95),
                coordinate_space="folded_yz_display",
            ))
    curves.extend(_build_lens_edge_curves(rows, curve_map, coordinate_space="folded_yz_display"))
    return curves


def _build_reference_plane_curves(
    rows: list,
    *,
    project_fn: Callable | None,
    overrides: dict,
    detector_surface_indices: set[int],
) -> list[SurfaceCurve3D]:
    curves: list[SurfaceCurve3D] = []
    z_pos = 0.0
    for row_index, row in enumerate(rows):
        display_settings = _row_display_settings(row)
        if display_settings.get("show_reference_plane") is False:
            z_pos += float(row.thickness)
            continue
        if row.surface == "Image" and int(row_index) not in detector_surface_indices:
            z_pos += float(row.thickness)
            continue
        if row.surface in {"Object", "Image"}:
            points = _reference_plane_world_points(row_index, row, z_pos, overrides)
            if points is not None and points.shape[0] >= 2:
                curves.append(SurfaceCurve3D(
                    row_index=row_index,
                    kind=row.surface.lower(),
                    points_world=points,
                    style=StyleHint(color="#202020", linewidth=1.2, alpha=0.9),
                ))
        z_pos += float(row.thickness)
    return curves


def _build_display_overlay_curves(
    rows: list,
    *,
    project_fn: Callable | None,
) -> list[SurfaceCurve3D]:
    del project_fn
    curves: list[SurfaceCurve3D] = []
    for row_index, row in enumerate(rows):
        display_settings = _row_display_settings(row)
        raw_polylines = display_settings.get("overlay_polylines", display_settings.get("extra_polylines", ()))
        if not isinstance(raw_polylines, (list, tuple)):
            continue
        for item in raw_polylines:
            if isinstance(item, dict):
                raw_points = item.get("points")
                color = str(item.get("color", "#b45309") or "#b45309")
                try:
                    linewidth = float(item.get("linewidth", 1.6))
                except Exception:
                    linewidth = 1.6
                try:
                    alpha = float(item.get("alpha", 0.95))
                except Exception:
                    alpha = 0.95
            else:
                raw_points = item
                color = "#b45309"
                linewidth = 1.6
                alpha = 0.95
            try:
                points_zy = np.asarray(raw_points, dtype=float)
            except Exception:
                continue
            if points_zy.ndim != 2 or points_zy.shape[0] < 2 or points_zy.shape[1] < 2:
                continue
            points = _surface_polyline_world_points(points_zy[:, :2])
            if points.ndim != 2 or points.shape[0] < 2:
                continue
            curves.append(
                SurfaceCurve3D(
                    row_index=row_index,
                    kind="display_overlay",
                    points_world=points,
                    style=StyleHint(color=color, linewidth=linewidth, alpha=alpha),
                )
            )
    return curves


def _build_lens_edge_curves(
    rows: list,
    curve_map: dict[int, np.ndarray],
    color: str = "#6b7280",
    linewidth: float = 1.2,
    alpha: float = 0.9,
    coordinate_space: str = "world",
) -> list[SurfaceCurve3D]:
    groups = _build_row_surface_groups(rows, curve_map)
    edge_curves: list[SurfaceCurve3D] = []
    for group in groups:
        first, last = group[0], group[-1]
        curve_a = np.asarray(curve_map.get(first), dtype=float)
        curve_b = np.asarray(curve_map.get(last), dtype=float)
        if curve_a.shape[0] < 2 or curve_b.shape[0] < 2:
            continue
        base_row = rows[first] if 0 <= first < len(rows) else None
        if base_row is not None:
            edge_color, edge_width, edge_alpha = surface_style_for_row(base_row)
            style = StyleHint(
                color=edge_color,
                linewidth=max(linewidth, edge_width),
                alpha=max(alpha, edge_alpha),
            )
        else:
            style = StyleHint(color=color, linewidth=linewidth, alpha=alpha)
        aperture_axis = _curve_group_aperture_axis(curve_a, curve_b)
        a0, a1 = _curve_edge_points(curve_a, aperture_axis)
        b0, b1 = _curve_edge_points(curve_b, aperture_axis)
        if a0 is None or b0 is None:
            continue
        for start, end in ((a0, b0), (a1, b1)):
            edge_curves.append(SurfaceCurve3D(
                row_index=first,
                kind="lens_edge",
                points_world=np.vstack((start, end)),
                style=style,
                coordinate_space=coordinate_space,
            ))
    return edge_curves


# ---------------------------------------------------------------------------
# Ray path builder
# ---------------------------------------------------------------------------

def _build_ray_paths(
    rows: list,
    system: Any | None,
    rays: Any | None,
    field_count: int,
    ray_count_per_field: int,
    colors: list[str],
    *,
    target_surface: int | None = None,
    detector_surface_indices: set[int] | None = None,
    allow_target_plane_contact: bool = False,
    detector_active_dims_overrides: dict[int, tuple[float, float]] | None = None,
) -> list[RayPath3D]:
    if rays is None:
        return []
    final_surface_index = max(0, len(rows) - 1)
    detector_surface_indices = _normalized_detector_surface_indices(rows, detector_surface_indices)
    target_surface_index = final_surface_index if target_surface is None else int(target_surface)
    paths: list[RayPath3D] = []
    ray_waves = getattr(rays, "RayWave", ())
    wavelengths = list(ray_waves) if ray_waves is not None else []
    for ray_index, ray in enumerate(getattr(rays, "CC", ())):
        points_world = np.asarray(ray, dtype=float)
        if points_world.shape[0] < 2:
            continue
        hits = _build_ray_hit_records(rows, rays, ray_index)
        if hits:
            surface_ids = np.asarray(
                [hit.surface_id for hit in hits if hit.surface_id is not None],
                dtype=int,
            )
        else:
            surface_ids = _raykeeper_array(rays, "SURFACE", ray_index, dtype=int)
        points_world, hits, surface_ids = _strip_nonterminal_image_hits(
            rows,
            points_world,
            hits,
            surface_ids,
            detector_surface_indices=detector_surface_indices,
        )
        last_surface = int(surface_ids[-1]) if surface_ids.size else None
        terminal_continuation = _has_terminal_continuation(points_world, surface_ids)
        if surface_ids.size and points_world.shape[0] > surface_ids.size + 1:
            # Kraken raykeeper may include an extrapolated continuation point
            # after the last surface hit. Preserve that point for non-absorbed
            # non-sequential rays so reflected/refracted rays do not appear to
            # stop inside prisms or optical solids. Image and absorber hits are
            # true terminal interactions and should remain clipped to the hit.
            last_surface_type = ""
            if last_surface is not None and 0 <= last_surface < len(rows):
                last_surface_type = str(getattr(rows[last_surface], "surface", "") or "")
            last_interaction = str(getattr(hits[-1], "interaction", "") or "").strip().lower() if hits else ""
            if last_surface_type == "Image" or last_interaction in {"absorb", "absorption"}:
                points_world = points_world[: surface_ids.size + 1]
                terminal_continuation = False
        source_ray_index = _raykeeper_metadata_scalar(rays, "SOURCE_RAY", ray_index)
        if source_ray_index is None:
            source_ray_index = ray_index
        source_position_arr = _raykeeper_xyz_array(rays, "SOURCE_XYZ", ray_index)
        source_direction_arr = _raykeeper_xyz_array(rays, "SOURCE_LMN", ray_index)
        source_position = source_position_arr[0] if source_position_arr.shape[0] else np.full(3, np.nan, dtype=float)
        source_direction = source_direction_arr[0] if source_direction_arr.shape[0] else np.full(3, np.nan, dtype=float)
        source_power = _raykeeper_metadata_scalar(rays, "SOURCE_POWER", ray_index)
        source_weight = _raykeeper_metadata_scalar(rays, "SOURCE_WEIGHT", ray_index)
        source_id = _raykeeper_metadata_text(rays, "SOURCE_ID", ray_index)
        source_name = _raykeeper_metadata_text(rays, "SOURCE_NAME", ray_index)
        source_role = _raykeeper_metadata_text(rays, "SOURCE_ROLE", ray_index)
        source_model = _raykeeper_metadata_text(rays, "SOURCE_MODEL", ray_index)
        field_index = min(int(source_ray_index) // max(ray_count_per_field, 1), field_count - 1)
        reaches_image = last_surface in detector_surface_indices
        if reaches_image:
            termination_reason = "image"
        elif last_surface is None:
            termination_reason = "no_hit"
        elif terminal_continuation:
            termination_reason = "missed_image" if detector_surface_indices else "no_next_intersection"
        else:
            termination_reason = f"stopped_at_surface_{last_surface}"
        branch_id = _raykeeper_metadata_scalar(rays, "BRANCH_ID", ray_index)
        parent_branch_id = _raykeeper_metadata_scalar(rays, "PARENT_BRANCH_ID", ray_index)
        branch_power = _raykeeper_metadata_scalar(rays, "BRANCH_POWER", ray_index)
        branch_phase = _raykeeper_metadata_scalar(rays, "BRANCH_PHASE", ray_index)
        branch_jones_p = _raykeeper_metadata_complex(rays, "BRANCH_JONES_P", ray_index, complex(1.0, 0.0))
        branch_jones_s = _raykeeper_metadata_complex(rays, "BRANCH_JONES_S", ray_index, complex(0.0, 0.0))
        branch_polarization_arr = _raykeeper_complex_xyz_array(rays, "BRANCH_POLARIZATION_XYZ", ray_index)
        branch_termination_reason = _raykeeper_metadata_text(rays, "BRANCH_TERMINATION_REASON", ray_index)
        branch_termination_diagnostic = _raykeeper_metadata_text(rays, "BRANCH_TERMINATION_DIAGNOSTIC", ray_index)
        branch_tree_diagnostic = _raykeeper_metadata_text(rays, "BRANCH_TREE_DIAGNOSTIC", ray_index)
        if branch_termination_reason and termination_reason not in {"image", "missed_image"}:
            termination_reason = branch_termination_reason
        termination_diagnostic = branch_termination_diagnostic or _ray_path_termination_diagnostic(
            rows,
            points_world,
            surface_ids,
            termination_reason,
            target_surface_index,
            detector_surface_indices,
            branch_tree_diagnostic,
        )
        branch_polarization = (
            branch_polarization_arr[0]
            if branch_polarization_arr.shape[0]
            else np.asarray((1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j), dtype=np.complex128)
        )
        branch_label = _raykeeper_metadata_text(rays, "BRANCH_LABEL", ray_index)
        branch_path = _raykeeper_metadata_text(rays, "BRANCH_PATH", ray_index)
        if branch_id is not None:
            for hit in hits:
                hit.branch_id = int(branch_id)
            branches = [
                RayBranch3D(
                    branch_id=int(branch_id),
                    parent_branch_id=None if parent_branch_id is None or int(parent_branch_id) < 0 else int(parent_branch_id),
                    start_step=0,
                    end_step=max(0, len(hits) - 1),
                    surface_ids=surface_ids,
                    termination_reason=termination_reason,
                    termination_diagnostic=termination_diagnostic,
                )
            ] if hits else []
        else:
            branches = _build_ray_branches(hits, termination_reason, termination_diagnostic)
            branch_id = branches[-1].branch_id if branches else 0
        path = RayPath3D(
            ray_index=ray_index,
            source_ray_index=int(source_ray_index) if source_ray_index is not None else None,
            source_id=source_id or "",
            source_name=source_name or "",
            source_role=source_role or "",
            source_model=source_model or "",
            source_position=np.asarray(source_position, dtype=float),
            source_direction=np.asarray(source_direction, dtype=float),
            source_power=float(source_power) if source_power is not None else None,
            source_weight=float(source_weight) if source_weight is not None else None,
            field_index=field_index,
            wavelength=float(wavelengths[ray_index]) if ray_index < len(wavelengths) else None,
            color=colors[field_index % len(colors)],
            points_world=points_world,
            surface_ids=surface_ids,
            reaches_image=reaches_image,
            branch_id=int(branch_id),
            branch_power=float(branch_power) if branch_power is not None else None,
            branch_phase_deg=float(branch_phase) if branch_phase is not None else None,
            branch_jones_p=branch_jones_p,
            branch_jones_s=branch_jones_s,
            branch_polarization_xyz=np.asarray(branch_polarization, dtype=np.complex128),
            branch_label=branch_label or "",
            branch_path=branch_path or branch_label or "",
            target_surface=target_surface_index,
            termination_reason=termination_reason,
            termination_diagnostic=termination_diagnostic,
            branch_tree_diagnostic=branch_tree_diagnostic,
            hits=hits,
            branches=branches,
        )
        path.events = build_ray_events_from_raykeeper(rows, rays, ray_index, path)
        path.events = _sync_detector_miss_terminal_event(
            rows,
            system,
            path,
            path.events,
            detector_surface_indices,
            allow_target_plane_contact=allow_target_plane_contact,
            detector_active_dims_overrides=detector_active_dims_overrides,
        )
        _sync_path_terminal_state_from_events(path)
        _sync_path_display_geometry_from_events(path)
        paths.append(path)
    return paths


RAY_EVENT_RECORD_COLUMNS = (
    "event_id",
    "event_source",
    "event_kind",
    "event_type",
    "ray_index",
    "source_ray_index",
    "source_id",
    "source_name",
    "source_role",
    "source_model",
    "wavelength",
    "launch_field_requested",
    "launch_field_effective",
    "launch_field_basis",
    "launch_field_unit",
    "launch_field_min",
    "launch_field_max",
    "launch_field_active",
    "launch_ray_count",
    "launch_pupil_pattern",
    "launch_trace_intent",
    "launch_sampling_mode",
    "branch_id",
    "branch_path",
    "branch_power",
    "branch_phase_deg",
    "step",
    "surface",
    "surface_name",
    "material",
    "x",
    "y",
    "z",
    "l",
    "m",
    "n",
    "out_l",
    "out_m",
    "out_n",
    "normal_l",
    "normal_m",
    "normal_n",
    "n0",
    "n1",
    "rp",
    "rs",
    "tp",
    "ts",
    "distance",
    "op",
    "ttbe",
    "interaction_model",
    "interaction_target_surface",
    "interaction_in_power",
    "interaction_coeff",
    "interaction_out_power",
    "interaction_loss_power",
    "interaction_bulk",
    "volume_id",
    "media_transition",
    "media_in",
    "media_out",
    "media_state_method",
    "media_state_diagnostic",
    "inside_volumes_before",
    "inside_volumes_after",
    "terminal_media",
    "terminal_index",
    "terminal_inside_volumes",
    "terminal_media_state",
    "mesh_cell_id",
    "mesh_original_cell_id",
    "mesh_face_id",
    "mesh_face_match_method",
    "mesh_face_match_score",
    "mesh_face_match_warning",
    "termination_reason",
    "terminal_policy_source",
    "terminal_target_surface",
    "terminal_detector_surfaces",
    "reaches_target",
    "reaches_detector",
    "terminal_geometry_source",
    "terminal_direction_source",
    "terminal_trace_surface",
    "terminal_surface_source",
    "detector_miss_surface",
    "detector_miss_status",
    "detector_miss_distance_mm",
    "detector_miss_radial_mm",
    "detector_miss_half_mm",
    "detector_miss_x_mm",
    "detector_miss_y_mm",
    "detector_miss_active_width_mm",
    "detector_miss_active_height_mm",
    "detector_miss_normal_error_mm",
    "folded_detector_policy",
    "folded_display_authoritative",
    "folded_display_reaches_detector",
    "folded_terminal_source",
    "folded_display_status",
    "folded_detector_surface",
    "folded_display_normal_error",
    "folded_display_along",
    "folded_display_half",
    "diagnostic",
)

RAY_ANALYSIS_CONTRACT_COLUMNS = (
    "launch_field_requested",
    "launch_field_effective",
    "launch_field_basis",
    "launch_field_unit",
    "launch_field_min",
    "launch_field_max",
    "launch_field_active",
    "launch_ray_count",
    "launch_pupil_pattern",
    "launch_trace_intent",
    "launch_sampling_mode",
    "terminal_policy_source",
    "terminal_target_surface",
    "terminal_detector_surfaces",
    "reaches_target",
    "reaches_detector",
    "terminal_geometry_source",
    "terminal_direction_source",
    "terminal_trace_surface",
    "terminal_surface_source",
    "detector_miss_surface",
    "detector_miss_status",
    "detector_miss_distance_mm",
    "detector_miss_radial_mm",
    "detector_miss_half_mm",
    "detector_miss_x_mm",
    "detector_miss_y_mm",
    "detector_miss_active_width_mm",
    "detector_miss_active_height_mm",
    "detector_miss_normal_error_mm",
    "folded_detector_policy",
    "folded_display_authoritative",
    "folded_display_reaches_detector",
    "folded_terminal_source",
    "folded_display_status",
    "folded_detector_surface",
    "folded_display_normal_error",
    "folded_display_along",
    "folded_display_half",
)


def build_ray_events_for_path(path: RayPath3D) -> list[RayEvent3D]:
    """Mirror one traced path into canonical read-only ray events."""
    events: list[RayEvent3D] = []
    branch_path = str(getattr(path, "branch_path", "") or getattr(path, "branch_label", "") or "")
    for hit in list(getattr(path, "hits", []) or []):
        diagnostic = _join_diagnostics(
            getattr(hit, "media_state_diagnostic", ""),
            getattr(hit, "mesh_face_match_warning", ""),
        )
        events.append(
            RayEvent3D(
                event_id=f"ray:{int(path.ray_index)}:hit:{int(hit.step)}",
                event_kind="surface",
                event_type=str(getattr(hit, "interaction", "") or getattr(hit, "media_transition", "") or "surface"),
                ray_index=int(path.ray_index),
                source_ray_index=path.source_ray_index,
                source_id=str(path.source_id or ""),
                source_name=str(path.source_name or ""),
                source_role=str(path.source_role or ""),
                source_model=str(path.source_model or ""),
                wavelength=path.wavelength,
                branch_id=int(getattr(hit, "branch_id", getattr(path, "branch_id", 0))),
                branch_path=branch_path,
                branch_power=path.branch_power,
                branch_phase_deg=path.branch_phase_deg,
                step=int(hit.step),
                surface_id=hit.surface_id,
                surface_name=str(getattr(hit, "name", "") or ""),
                material=str(getattr(hit, "material", "") or ""),
                point_world=np.asarray(getattr(hit, "point_world", np.full(3, np.nan)), dtype=float),
                incoming_direction=np.asarray(getattr(hit, "incoming_direction", np.full(3, np.nan)), dtype=float),
                outgoing_direction=np.asarray(getattr(hit, "outgoing_direction", np.full(3, np.nan)), dtype=float),
                surface_normal=np.asarray(getattr(hit, "surface_normal", np.full(3, np.nan)), dtype=float),
                n0=hit.n0,
                n1=hit.n1,
                distance=hit.distance,
                optical_path=hit.optical_path,
                rp=hit.rp,
                rs=hit.rs,
                tp=hit.tp,
                ts=hit.ts,
                ttbe=hit.ttbe,
                interaction_model=str(getattr(hit, "interaction_model", "") or ""),
                interaction_target_surface=hit.interaction_target_surface,
                interaction_in_power=hit.interaction_in_power,
                interaction_coeff=hit.interaction_coeff,
                interaction_out_power=hit.interaction_out_power,
                interaction_loss_power=hit.interaction_loss_power,
                interaction_bulk=hit.interaction_bulk,
                volume_id=str(getattr(hit, "volume_id", "") or ""),
                media_in=str(getattr(hit, "media_in", "") or ""),
                media_out=str(getattr(hit, "media_out", "") or ""),
                media_transition=str(getattr(hit, "media_transition", "") or ""),
                media_state_method=str(getattr(hit, "media_state_method", "") or ""),
                media_state_diagnostic=str(getattr(hit, "media_state_diagnostic", "") or ""),
                inside_volumes_before=str(getattr(hit, "inside_volumes_before", "") or ""),
                inside_volumes_after=str(getattr(hit, "inside_volumes_after", "") or ""),
                mesh_cell_id=hit.mesh_cell_id,
                mesh_original_cell_id=hit.mesh_original_cell_id,
                mesh_face_id=str(getattr(hit, "mesh_face_id", "") or ""),
                mesh_face_match_method=str(getattr(hit, "mesh_face_match_method", "") or ""),
                mesh_face_match_score=hit.mesh_face_match_score,
                mesh_face_match_warning=str(getattr(hit, "mesh_face_match_warning", "") or ""),
                diagnostic=diagnostic,
                metadata={"event_source": "ray_path_fallback"},
            )
        )

    terminal_event = _ray_path_terminal_event(path, step=len(events), event_source="ray_path_fallback")
    if terminal_event is not None:
        events.append(terminal_event)
    return events


def _launch_event_kwargs(record: dict[str, object] | None) -> dict[str, object]:
    record = dict(record or {})
    return {
        "launch_field_requested": _optional_int(record.get("launch_field_requested")),
        "launch_field_effective": _optional_int(record.get("launch_field_effective")),
        "launch_field_basis": str(record.get("launch_field_basis", "") or ""),
        "launch_field_unit": str(record.get("launch_field_unit", "") or ""),
        "launch_field_min": _optional_float(record.get("launch_field_min")),
        "launch_field_max": _optional_float(record.get("launch_field_max")),
        "launch_field_active": _optional_bool(record.get("launch_field_active")),
        "launch_ray_count": _optional_int(record.get("launch_ray_count")),
        "launch_pupil_pattern": str(record.get("launch_pupil_pattern", "") or ""),
        "launch_trace_intent": str(record.get("launch_trace_intent", "") or ""),
        "launch_sampling_mode": str(record.get("launch_sampling_mode", "") or ""),
    }


def build_ray_events_from_raykeeper(rows: list, rays: Any | None, ray_index: int, path: RayPath3D) -> list[RayEvent3D]:
    """Build canonical scene events from raykeeper trace-event records."""
    trace_event_sets = getattr(rays, "TRACE_EVENTS", ()) if rays is not None else ()
    trace_records = []
    try:
        if trace_event_sets is not None and ray_index < len(trace_event_sets):
            trace_records = [
                trace_event_to_record(event)
                for event in list(trace_event_sets[ray_index] or [])
            ]
    except Exception:
        trace_records = []
    terminal_records = [
        record
        for record in trace_records
        if str(record.get("event_kind", "") or "") == "terminal"
    ]
    events: list[RayEvent3D] = []
    retained_steps = {
        int(getattr(hit, "step", -1))
        for hit in list(getattr(path, "hits", []) or [])
        if getattr(hit, "step", None) is not None
    }
    for record in trace_records:
        if str(record.get("event_kind", "") or "") != "surface":
            continue
        step = _optional_int(record.get("step"))
        if retained_steps and step is not None and int(step) not in retained_steps:
            continue
        surface_id = _optional_int(record.get("surface_id"))
        n0 = _optional_float(record.get("n0"))
        n1 = _optional_float(record.get("n1"))
        event_type = _interaction_event_label(rows, surface_id, str(record.get("event_type", "") or ""), n0, n1)
        events.append(
            RayEvent3D(
                event_id=str(record.get("event_id", "") or f"ray:{int(ray_index)}:hit:{len(events)}"),
                event_kind="surface",
                event_type=event_type,
                ray_index=int(record.get("ray_index", ray_index) or ray_index),
                source_ray_index=_optional_int(record.get("source_ray_index")),
                source_id=str(record.get("source_id", "") or ""),
                source_name=str(record.get("source_name", "") or ""),
                source_role=str(record.get("source_role", "") or ""),
                source_model=str(record.get("source_model", "") or ""),
                wavelength=_optional_float(record.get("wavelength")),
                **_launch_event_kwargs(record),
                branch_id=_optional_int(record.get("branch_id")) or 0,
                branch_path=str(record.get("branch_path", "") or ""),
                branch_power=_optional_float(record.get("branch_power")),
                branch_phase_deg=_optional_float(record.get("branch_phase_deg")),
                step=step if step is not None else len(events),
                surface_id=surface_id,
                surface_name=str(record.get("surface_name", "") or ""),
                material=str(record.get("material", "") or ""),
                point_world=np.asarray(_vector3(record.get("point_world")), dtype=float),
                incoming_direction=np.asarray(_vector3(record.get("incoming_direction")), dtype=float),
                outgoing_direction=np.asarray(_vector3(record.get("outgoing_direction")), dtype=float),
                surface_normal=np.asarray(_vector3(record.get("surface_normal")), dtype=float),
                n0=n0,
                n1=n1,
                distance=_optional_float(record.get("distance")),
                optical_path=_optional_float(record.get("optical_path")),
                rp=_optional_float(record.get("rp")),
                rs=_optional_float(record.get("rs")),
                tp=_optional_float(record.get("tp")),
                ts=_optional_float(record.get("ts")),
                ttbe=_optional_float(record.get("ttbe")),
                interaction_model=str(record.get("interaction_model", "") or ""),
                interaction_target_surface=_optional_int(record.get("interaction_target_surface")),
                interaction_in_power=_optional_float(record.get("interaction_in_power")),
                interaction_coeff=_optional_float(record.get("interaction_coeff")),
                interaction_out_power=_optional_float(record.get("interaction_out_power")),
                interaction_loss_power=_optional_float(record.get("interaction_loss_power")),
                interaction_bulk=_optional_float(record.get("interaction_bulk")),
                volume_id=str(record.get("volume_id", "") or ""),
                media_in=str(record.get("media_in", "") or ""),
                media_out=str(record.get("media_out", "") or ""),
                media_transition=str(record.get("media_transition", "") or ""),
                media_state_method=str(record.get("media_state_method", "") or ""),
                media_state_diagnostic=str(record.get("media_state_diagnostic", "") or ""),
                inside_volumes_before=str(record.get("inside_volumes_before", "") or ""),
                inside_volumes_after=str(record.get("inside_volumes_after", "") or ""),
                mesh_cell_id=_optional_int(record.get("mesh_cell_id")),
                mesh_original_cell_id=_optional_int(record.get("mesh_original_cell_id")),
                mesh_face_id=str(record.get("mesh_face_id", "") or ""),
                mesh_face_match_method=str(record.get("mesh_face_match_method", "") or ""),
                mesh_face_match_score=_optional_float(record.get("mesh_face_match_score")),
                mesh_face_match_warning=str(record.get("mesh_face_match_warning", "") or ""),
                termination_reason="",
                diagnostic=str(record.get("diagnostic", "") or ""),
                metadata={
                    "event_source": str(record.get("event_source", "") or TRACE_EVENT_SOURCE_RAYKEEPER),
                },
            )
        )
    terminal_record = terminal_records[-1] if terminal_records else None
    if not events:
        if terminal_record is not None:
            fallback_events = [
                event
                for event in build_ray_events_for_path(path)
                if str(getattr(event, "event_kind", "") or "") != "terminal"
            ]
            return _sync_path_terminal_event(path, fallback_events, terminal_record=terminal_record)
        return build_ray_events_for_path(path)
    return _sync_path_terminal_event(path, events, terminal_record=terminal_record)


def _sync_path_terminal_event(
    path: RayPath3D,
    events: list[RayEvent3D],
    *,
    terminal_record: dict[str, object] | None = None,
) -> list[RayEvent3D]:
    surface_events = [
        event
        for event in events
        if str(getattr(event, "event_kind", "") or "") != "terminal"
    ]
    event_source = "scene_path_terminal"
    event_id = ""
    extra_metadata: dict[str, object] = {}
    if terminal_record:
        event_source = str(terminal_record.get("event_source", "") or TRACE_EVENT_SOURCE_RAYKEEPER)
        event_id = str(terminal_record.get("event_id", "") or "")
        trace_surface = _optional_int(terminal_record.get("surface_id"))
        extra_metadata = {
            "terminal_policy_source": str(terminal_record.get("terminal_policy_source", "") or ""),
            "terminal_target_surface": terminal_record.get("terminal_target_surface"),
            "terminal_detector_surfaces": terminal_record.get("terminal_detector_surfaces", ()),
            "reaches_target": bool(terminal_record.get("reaches_target", False)),
            "reaches_detector": bool(terminal_record.get("reaches_detector", False)),
            "terminal_trace_surface": trace_surface,
        }
    terminal = _ray_path_terminal_event(
        path,
        step=len(surface_events),
        event_source=event_source,
        event_id=event_id,
        terminal_record=terminal_record,
        extra_metadata=extra_metadata,
    )
    if terminal is not None:
        surface_events.append(terminal)
    return surface_events


def _ray_path_terminal_event(
    path: RayPath3D,
    *,
    step: int,
    event_source: str,
    event_id: str = "",
    terminal_record: dict[str, object] | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> RayEvent3D | None:
    path_termination_reason = str(getattr(path, "termination_reason", "") or "")
    path_termination_diagnostic = _join_diagnostics(
        getattr(path, "termination_diagnostic", ""),
        getattr(path, "branch_tree_diagnostic", ""),
    )
    record_termination_reason = ""
    record_diagnostic = ""
    if terminal_record:
        record_termination_reason = str(
            terminal_record.get("termination_reason", "")
            or terminal_record.get("event_type", "")
            or ""
        )
        record_diagnostic = str(terminal_record.get("diagnostic", "") or "")
    trace_surface_id = _optional_int(terminal_record.get("surface_id")) if terminal_record else None
    surface_id, surface_source = _terminal_surface_id_for_event(path, trace_surface_id, terminal_record)
    if surface_source == "ray_path_filtered" and path_termination_reason:
        termination_reason = path_termination_reason
    else:
        termination_reason = record_termination_reason or path_termination_reason
    termination_diagnostic = _join_diagnostics(record_diagnostic, path_termination_diagnostic)
    if not termination_reason and not termination_diagnostic:
        return None
    point_world, point_source = _terminal_record_vector_or_fallback(
        terminal_record,
        "point_world",
        _last_path_point(path),
    )
    incoming_direction, incoming_source = _terminal_record_vector_or_fallback(
        terminal_record,
        "incoming_direction",
        _last_path_direction(path, incoming=True),
    )
    outgoing_direction, outgoing_source = _terminal_record_vector_or_fallback(
        terminal_record,
        "outgoing_direction",
        _last_path_direction(path, incoming=False),
    )
    direction_source = "missing"
    if incoming_source == "trace_event" or outgoing_source == "trace_event":
        direction_source = "trace_event"
    elif incoming_source == "ray_path" or outgoing_source == "ray_path":
        direction_source = "ray_path"
    metadata = {
        "event_source": event_source,
        "target_surface": path.target_surface,
        "reaches_image": bool(path.reaches_image),
        "terminal_geometry_source": point_source,
        "terminal_direction_source": direction_source,
        "terminal_surface_source": surface_source,
    }
    metadata.update(dict(extra_metadata or {}))
    source_ray_index = _optional_int(terminal_record.get("source_ray_index")) if terminal_record else None
    ray_index = _optional_int(terminal_record.get("ray_index")) if terminal_record else None
    wavelength = _optional_float(terminal_record.get("wavelength")) if terminal_record else None
    branch_id = _optional_int(terminal_record.get("branch_id")) if terminal_record else None
    branch_power = _optional_float(terminal_record.get("branch_power")) if terminal_record else None
    branch_phase = _optional_float(terminal_record.get("branch_phase_deg")) if terminal_record else None
    terminal_n1 = _optional_float(terminal_record.get("n1")) if terminal_record else None
    return RayEvent3D(
        event_id=event_id or f"ray:{int(path.ray_index)}:terminal",
        event_kind="terminal",
        event_type=termination_reason or "terminal",
        ray_index=ray_index if ray_index is not None else int(path.ray_index),
        source_ray_index=source_ray_index if source_ray_index is not None else path.source_ray_index,
        source_id=str((terminal_record or {}).get("source_id", "") or path.source_id or ""),
        source_name=str((terminal_record or {}).get("source_name", "") or path.source_name or ""),
        source_role=str((terminal_record or {}).get("source_role", "") or path.source_role or ""),
        source_model=str((terminal_record or {}).get("source_model", "") or path.source_model or ""),
        wavelength=wavelength if wavelength is not None else path.wavelength,
        **_launch_event_kwargs(terminal_record),
        branch_id=branch_id if branch_id is not None else int(getattr(path, "branch_id", 0)),
        branch_path=str((terminal_record or {}).get("branch_path", "") or getattr(path, "branch_path", "") or getattr(path, "branch_label", "") or ""),
        branch_power=branch_power if branch_power is not None else path.branch_power,
        branch_phase_deg=branch_phase if branch_phase is not None else path.branch_phase_deg,
        step=int(step),
        surface_id=surface_id,
        point_world=point_world,
        incoming_direction=incoming_direction,
        outgoing_direction=outgoing_direction,
        n1=terminal_n1,
        media_in=str((terminal_record or {}).get("media_in", "") or ""),
        media_out=str((terminal_record or {}).get("media_out", "") or ""),
        media_transition=str((terminal_record or {}).get("media_transition", "") or ""),
        media_state_method=str((terminal_record or {}).get("media_state_method", "") or ""),
        media_state_diagnostic=str((terminal_record or {}).get("media_state_diagnostic", "") or ""),
        inside_volumes_before=str((terminal_record or {}).get("inside_volumes_before", "") or ""),
        inside_volumes_after=str((terminal_record or {}).get("inside_volumes_after", "") or ""),
        termination_reason=termination_reason,
        diagnostic=termination_diagnostic,
        metadata=metadata,
    )


def scene_bundle_ray_event_records(bundle: SceneBundle) -> list[dict[str, object]]:
    """Return flat CSV-ready records for the bundle's canonical ray events."""
    events = list(getattr(bundle, "ray_events", []) or [])
    if not events:
        for path in list(getattr(bundle, "ray_paths", []) or []):
            events.extend(build_ray_events_for_path(path))
    return [ray_event_to_record(event) for event in events]


def _ray_event_launch_record(event: RayEvent3D | None) -> dict[str, object]:
    if event is None:
        return {
            "launch_field_requested": "",
            "launch_field_effective": "",
            "launch_field_basis": "",
            "launch_field_unit": "",
            "launch_field_min": "",
            "launch_field_max": "",
            "launch_field_active": "",
            "launch_ray_count": "",
            "launch_pupil_pattern": "",
            "launch_trace_intent": "",
            "launch_sampling_mode": "",
        }
    return {
        "launch_field_requested": "" if event.launch_field_requested is None else event.launch_field_requested,
        "launch_field_effective": "" if event.launch_field_effective is None else event.launch_field_effective,
        "launch_field_basis": event.launch_field_basis,
        "launch_field_unit": event.launch_field_unit,
        "launch_field_min": "" if event.launch_field_min is None else event.launch_field_min,
        "launch_field_max": "" if event.launch_field_max is None else event.launch_field_max,
        "launch_field_active": "" if event.launch_field_active is None else bool(event.launch_field_active),
        "launch_ray_count": "" if event.launch_ray_count is None else event.launch_ray_count,
        "launch_pupil_pattern": event.launch_pupil_pattern,
        "launch_trace_intent": event.launch_trace_intent,
        "launch_sampling_mode": event.launch_sampling_mode,
    }


def scene_bundle_ray_analysis_records(bundle: SceneBundle) -> list[dict[str, object]]:
    """Return ray-level analysis records derived from canonical scene events."""
    records: list[dict[str, object]] = []
    if bundle is None:
        return records
    for path in list(getattr(bundle, "ray_paths", []) or []):
        events = list(getattr(path, "events", []) or [])
        if not events:
            events = build_ray_events_for_path(path)
        surface_events = [
            event
            for event in events
            if str(getattr(event, "event_kind", "") or "") == "surface"
        ]
        terminal_events = [
            event
            for event in events
            if str(getattr(event, "event_kind", "") or "") == "terminal"
        ]
        hits = [_ray_event_analysis_hit(event) for event in surface_events]
        terminal_event = terminal_events[-1] if terminal_events else None
        launch_event = surface_events[0] if surface_events else terminal_event
        last_event = surface_events[-1] if surface_events else terminal_event
        last_surface = getattr(last_event, "surface_id", None) if last_event is not None else _last_surface_id(path)
        last_name = str(getattr(last_event, "surface_name", "") or "") if last_event is not None else ""
        total_distance = _sum_event_values(surface_events, "distance")
        total_op = _sum_event_values(surface_events, "optical_path")
        last_ttbe = _last_event_value(surface_events, "ttbe")
        branch_path = str(getattr(path, "branch_path", "") or getattr(path, "branch_label", "") or "")
        source_position = _vector3(getattr(path, "source_position", None))
        source_direction = _vector3(getattr(path, "source_direction", None))
        branch_polarization = _complex_vector3(getattr(path, "branch_polarization_xyz", None))
        branch_jones_p = getattr(path, "branch_jones_p", complex(1.0, 0.0))
        branch_jones_s = getattr(path, "branch_jones_s", complex(0.0, 0.0))
        branch_p_fraction, branch_s_fraction = _branch_jones_fractions(branch_jones_p, branch_jones_s)
        termination = str(getattr(path, "termination_reason", "") or "")
        if not termination and terminal_event is not None:
            termination = str(
                getattr(terminal_event, "termination_reason", "")
                or getattr(terminal_event, "event_type", "")
                or ""
            )
        termination_diagnostic = str(getattr(path, "termination_diagnostic", "") or "")
        if not termination_diagnostic and terminal_event is not None:
            termination_diagnostic = str(getattr(terminal_event, "diagnostic", "") or "")
        terminal_metadata = dict(getattr(terminal_event, "metadata", {}) or {}) if terminal_event is not None else {}
        terminal_media = ""
        terminal_index = ""
        terminal_inside_volumes = ""
        terminal_media_state = ""
        if terminal_event is not None:
            terminal_media = str(getattr(terminal_event, "media_out", "") or "")
            terminal_index = getattr(terminal_event, "n1", None)
            terminal_index = "" if terminal_index is None else terminal_index
            terminal_inside_volumes = str(getattr(terminal_event, "inside_volumes_after", "") or "")
            terminal_media_state = str(getattr(terminal_event, "media_state_method", "") or "")
        reaches_image = bool(getattr(path, "reaches_image", False))
        records.append(
            {
                "ray_index": int(getattr(path, "ray_index", 0)),
                "source_ray_index": getattr(path, "source_ray_index", None),
                "source_id": str(getattr(path, "source_id", "") or ""),
                "source_name": str(getattr(path, "source_name", "") or ""),
                "source_role": str(getattr(path, "source_role", "") or ""),
                "source_model": str(getattr(path, "source_model", "") or ""),
                "source_x": source_position[0],
                "source_y": source_position[1],
                "source_z": source_position[2],
                "source_l": source_direction[0],
                "source_m": source_direction[1],
                "source_n": source_direction[2],
                "source_power": getattr(path, "source_power", None),
                "source_weight": getattr(path, "source_weight", None),
                "field_index": int(getattr(path, "field_index", 0)),
                "wavelength": getattr(path, "wavelength", None),
                **_ray_event_launch_record(launch_event),
                "branch_id": int(getattr(path, "branch_id", 0)),
                "branch_path": branch_path,
                "branch_power": getattr(path, "branch_power", None),
                "branch_phase": getattr(path, "branch_phase_deg", None),
                "branch_jones_p": branch_jones_p,
                "branch_jones_s": branch_jones_s,
                "branch_polarization_xyz": np.asarray(branch_polarization, dtype=np.complex128),
                "branch_p_fraction": branch_p_fraction,
                "branch_s_fraction": branch_s_fraction,
                "branch_count": len(list(getattr(path, "branches", []) or [])) or 1,
                "target_surface": getattr(path, "target_surface", None),
                "termination": termination,
                "status": _ray_analysis_status_text(termination, last_surface, reaches_image),
                "termination_diagnostic": termination_diagnostic,
                "terminal_media": terminal_media,
                "terminal_index": terminal_index,
                "terminal_inside_volumes": terminal_inside_volumes,
                "terminal_media_state": terminal_media_state,
                "terminal_policy_source": str(terminal_metadata.get("terminal_policy_source", "") or ""),
                "terminal_target_surface": (
                    ""
                    if terminal_metadata.get("terminal_target_surface") is None
                    else terminal_metadata.get("terminal_target_surface")
                ),
                "terminal_detector_surfaces": _metadata_int_list_text(
                    terminal_metadata.get("terminal_detector_surfaces")
                ),
                "reaches_target": bool(terminal_metadata.get("reaches_target", False)),
                "reaches_detector": bool(terminal_metadata.get("reaches_detector", False)),
                "terminal_geometry_source": str(terminal_metadata.get("terminal_geometry_source", "") or ""),
                "terminal_direction_source": str(terminal_metadata.get("terminal_direction_source", "") or ""),
                "terminal_trace_surface": (
                    ""
                    if terminal_metadata.get("terminal_trace_surface") is None
                    else terminal_metadata.get("terminal_trace_surface")
                ),
                "terminal_surface_source": str(terminal_metadata.get("terminal_surface_source", "") or ""),
                "detector_miss_surface": (
                    ""
                    if terminal_metadata.get("detector_miss_surface") is None
                    else terminal_metadata.get("detector_miss_surface")
                ),
                "detector_miss_status": str(terminal_metadata.get("detector_miss_status", "") or ""),
                "detector_miss_distance_mm": (
                    ""
                    if terminal_metadata.get("detector_miss_distance_mm") is None
                    else terminal_metadata.get("detector_miss_distance_mm")
                ),
                "detector_miss_radial_mm": (
                    ""
                    if terminal_metadata.get("detector_miss_radial_mm") is None
                    else terminal_metadata.get("detector_miss_radial_mm")
                ),
                "detector_miss_half_mm": (
                    ""
                    if terminal_metadata.get("detector_miss_half_mm") is None
                    else terminal_metadata.get("detector_miss_half_mm")
                ),
                "detector_miss_x_mm": (
                    ""
                    if terminal_metadata.get("detector_miss_x_mm") is None
                    else terminal_metadata.get("detector_miss_x_mm")
                ),
                "detector_miss_y_mm": (
                    ""
                    if terminal_metadata.get("detector_miss_y_mm") is None
                    else terminal_metadata.get("detector_miss_y_mm")
                ),
                "detector_miss_active_width_mm": (
                    ""
                    if terminal_metadata.get("detector_miss_active_width_mm") is None
                    else terminal_metadata.get("detector_miss_active_width_mm")
                ),
                "detector_miss_active_height_mm": (
                    ""
                    if terminal_metadata.get("detector_miss_active_height_mm") is None
                    else terminal_metadata.get("detector_miss_active_height_mm")
                ),
                "detector_miss_normal_error_mm": (
                    ""
                    if terminal_metadata.get("detector_miss_normal_error_mm") is None
                    else terminal_metadata.get("detector_miss_normal_error_mm")
                ),
                "folded_detector_policy": str(terminal_metadata.get("folded_detector_policy", "") or ""),
                "folded_display_authoritative": bool(terminal_metadata.get("folded_display_authoritative", False)),
                "folded_display_reaches_detector": (
                    ""
                    if terminal_metadata.get("folded_display_reaches_detector") is None
                    else bool(terminal_metadata.get("folded_display_reaches_detector", False))
                ),
                "folded_terminal_source": str(terminal_metadata.get("folded_terminal_source", "") or ""),
                "folded_display_status": str(terminal_metadata.get("folded_display_status", "") or ""),
                "folded_detector_surface": (
                    ""
                    if terminal_metadata.get("folded_detector_surface") is None
                    else terminal_metadata.get("folded_detector_surface")
                ),
                "folded_display_normal_error": (
                    ""
                    if terminal_metadata.get("folded_display_normal_error") is None
                    else terminal_metadata.get("folded_display_normal_error")
                ),
                "folded_display_along": (
                    ""
                    if terminal_metadata.get("folded_display_along") is None
                    else terminal_metadata.get("folded_display_along")
                ),
                "folded_display_half": (
                    ""
                    if terminal_metadata.get("folded_display_half") is None
                    else terminal_metadata.get("folded_display_half")
                ),
                "branch_tree_diagnostic": str(getattr(path, "branch_tree_diagnostic", "") or ""),
                "last_surface": last_surface,
                "last_name": last_name,
                "distance": total_distance,
                "op": total_op,
                "top": total_op,
                "transmission": last_ttbe if last_ttbe is not None else "",
                "reaches_image": reaches_image,
                "hit_count": len(hits),
                "event_count": len(events),
                "terminal_event_id": str(getattr(terminal_event, "event_id", "") or "") if terminal_event is not None else "",
                "analysis_source": "ray_events",
                "hits": hits,
            }
        )
    return records


def ray_event_to_record(event: RayEvent3D) -> dict[str, object]:
    point = _vector3(getattr(event, "point_world", None))
    incoming = _vector3(getattr(event, "incoming_direction", None))
    outgoing = _vector3(getattr(event, "outgoing_direction", None))
    normal = _vector3(getattr(event, "surface_normal", None))
    metadata = dict(getattr(event, "metadata", {}) or {})
    is_terminal = str(getattr(event, "event_kind", "") or "") == "terminal"
    return {
        "event_id": event.event_id,
        "event_source": str(metadata.get("event_source", "") or ""),
        "event_kind": event.event_kind,
        "event_type": event.event_type,
        "ray_index": event.ray_index,
        "source_ray_index": "" if event.source_ray_index is None else event.source_ray_index,
        "source_id": event.source_id,
        "source_name": event.source_name,
        "source_role": event.source_role,
        "source_model": event.source_model,
        "wavelength": "" if event.wavelength is None else event.wavelength,
        **_ray_event_launch_record(event),
        "branch_id": event.branch_id,
        "branch_path": event.branch_path,
        "branch_power": "" if event.branch_power is None else event.branch_power,
        "branch_phase_deg": "" if event.branch_phase_deg is None else event.branch_phase_deg,
        "step": event.step,
        "surface": "" if event.surface_id is None else event.surface_id,
        "surface_name": event.surface_name,
        "material": event.material,
        "x": point[0],
        "y": point[1],
        "z": point[2],
        "l": incoming[0],
        "m": incoming[1],
        "n": incoming[2],
        "out_l": outgoing[0],
        "out_m": outgoing[1],
        "out_n": outgoing[2],
        "normal_l": normal[0],
        "normal_m": normal[1],
        "normal_n": normal[2],
        "n0": "" if event.n0 is None else event.n0,
        "n1": "" if event.n1 is None else event.n1,
        "rp": "" if event.rp is None else event.rp,
        "rs": "" if event.rs is None else event.rs,
        "tp": "" if event.tp is None else event.tp,
        "ts": "" if event.ts is None else event.ts,
        "distance": "" if event.distance is None else event.distance,
        "op": "" if event.optical_path is None else event.optical_path,
        "ttbe": "" if event.ttbe is None else event.ttbe,
        "interaction_model": event.interaction_model,
        "interaction_target_surface": "" if event.interaction_target_surface is None else event.interaction_target_surface,
        "interaction_in_power": "" if event.interaction_in_power is None else event.interaction_in_power,
        "interaction_coeff": "" if event.interaction_coeff is None else event.interaction_coeff,
        "interaction_out_power": "" if event.interaction_out_power is None else event.interaction_out_power,
        "interaction_loss_power": "" if event.interaction_loss_power is None else event.interaction_loss_power,
        "interaction_bulk": "" if event.interaction_bulk is None else event.interaction_bulk,
        "volume_id": event.volume_id,
        "media_transition": event.media_transition,
        "media_in": event.media_in,
        "media_out": event.media_out,
        "media_state_method": event.media_state_method,
        "media_state_diagnostic": event.media_state_diagnostic,
        "inside_volumes_before": event.inside_volumes_before,
        "inside_volumes_after": event.inside_volumes_after,
        "terminal_media": event.media_out if is_terminal else "",
        "terminal_index": "" if not is_terminal or event.n1 is None else event.n1,
        "terminal_inside_volumes": event.inside_volumes_after if is_terminal else "",
        "terminal_media_state": event.media_state_method if is_terminal else "",
        "mesh_cell_id": "" if event.mesh_cell_id is None else event.mesh_cell_id,
        "mesh_original_cell_id": "" if event.mesh_original_cell_id is None else event.mesh_original_cell_id,
        "mesh_face_id": event.mesh_face_id,
        "mesh_face_match_method": event.mesh_face_match_method,
        "mesh_face_match_score": "" if event.mesh_face_match_score is None else event.mesh_face_match_score,
        "mesh_face_match_warning": event.mesh_face_match_warning,
        "termination_reason": event.termination_reason,
        "terminal_policy_source": str(metadata.get("terminal_policy_source", "") or ""),
        "terminal_target_surface": "" if metadata.get("terminal_target_surface") is None else metadata.get("terminal_target_surface"),
        "terminal_detector_surfaces": _metadata_int_list_text(metadata.get("terminal_detector_surfaces")),
        "reaches_target": bool(metadata.get("reaches_target", False)),
        "reaches_detector": bool(metadata.get("reaches_detector", False)),
        "terminal_geometry_source": str(metadata.get("terminal_geometry_source", "") or ""),
        "terminal_direction_source": str(metadata.get("terminal_direction_source", "") or ""),
        "terminal_trace_surface": "" if metadata.get("terminal_trace_surface") is None else metadata.get("terminal_trace_surface"),
        "terminal_surface_source": str(metadata.get("terminal_surface_source", "") or ""),
        "detector_miss_surface": "" if metadata.get("detector_miss_surface") is None else metadata.get("detector_miss_surface"),
        "detector_miss_status": str(metadata.get("detector_miss_status", "") or ""),
        "detector_miss_distance_mm": "" if metadata.get("detector_miss_distance_mm") is None else metadata.get("detector_miss_distance_mm"),
        "detector_miss_radial_mm": "" if metadata.get("detector_miss_radial_mm") is None else metadata.get("detector_miss_radial_mm"),
        "detector_miss_half_mm": "" if metadata.get("detector_miss_half_mm") is None else metadata.get("detector_miss_half_mm"),
        "detector_miss_x_mm": "" if metadata.get("detector_miss_x_mm") is None else metadata.get("detector_miss_x_mm"),
        "detector_miss_y_mm": "" if metadata.get("detector_miss_y_mm") is None else metadata.get("detector_miss_y_mm"),
        "detector_miss_active_width_mm": "" if metadata.get("detector_miss_active_width_mm") is None else metadata.get("detector_miss_active_width_mm"),
        "detector_miss_active_height_mm": "" if metadata.get("detector_miss_active_height_mm") is None else metadata.get("detector_miss_active_height_mm"),
        "detector_miss_normal_error_mm": "" if metadata.get("detector_miss_normal_error_mm") is None else metadata.get("detector_miss_normal_error_mm"),
        "folded_detector_policy": str(metadata.get("folded_detector_policy", "") or ""),
        "folded_display_authoritative": bool(metadata.get("folded_display_authoritative", False)),
        "folded_display_reaches_detector": (
            ""
            if metadata.get("folded_display_reaches_detector") is None
            else bool(metadata.get("folded_display_reaches_detector", False))
        ),
        "folded_terminal_source": str(metadata.get("folded_terminal_source", "") or ""),
        "folded_display_status": str(metadata.get("folded_display_status", "") or ""),
        "folded_detector_surface": "" if metadata.get("folded_detector_surface") is None else metadata.get("folded_detector_surface"),
        "folded_display_normal_error": "" if metadata.get("folded_display_normal_error") is None else metadata.get("folded_display_normal_error"),
        "folded_display_along": "" if metadata.get("folded_display_along") is None else metadata.get("folded_display_along"),
        "folded_display_half": "" if metadata.get("folded_display_half") is None else metadata.get("folded_display_half"),
        "diagnostic": event.diagnostic,
    }


def _ray_event_analysis_hit(event: RayEvent3D) -> dict[str, object]:
    point = _vector3(getattr(event, "point_world", None))
    incoming = _vector3(getattr(event, "incoming_direction", None))
    outgoing = _vector3(getattr(event, "outgoing_direction", None))
    normal = _vector3(getattr(event, "surface_normal", None))
    metadata = dict(getattr(event, "metadata", {}) or {})
    record = {
        "step": int(getattr(event, "step", 0)),
        "branch": int(getattr(event, "branch_id", 0)),
        "surface": "" if event.surface_id is None else event.surface_id,
        "event": event.event_type,
        "name": event.surface_name,
        "glass": event.material,
        "x": point[0],
        "y": point[1],
        "z": point[2],
        "distance": "" if event.distance is None else event.distance,
        "op": "" if event.optical_path is None else event.optical_path,
        "l": incoming[0],
        "m": incoming[1],
        "n": incoming[2],
        "out_l": outgoing[0],
        "out_m": outgoing[1],
        "out_n": outgoing[2],
        "normal_l": normal[0],
        "normal_m": normal[1],
        "normal_n": normal[2],
        "n0": "" if event.n0 is None else event.n0,
        "n1": "" if event.n1 is None else event.n1,
        "rp": "" if event.rp is None else event.rp,
        "rs": "" if event.rs is None else event.rs,
        "tp": "" if event.tp is None else event.tp,
        "ts": "" if event.ts is None else event.ts,
        "ttbe": "" if event.ttbe is None else event.ttbe,
        "interaction_model": event.interaction_model,
        "interaction_target_surface": "" if event.interaction_target_surface is None else event.interaction_target_surface,
        "interaction_in_power": "" if event.interaction_in_power is None else event.interaction_in_power,
        "interaction_coeff": "" if event.interaction_coeff is None else event.interaction_coeff,
        "interaction_out_power": "" if event.interaction_out_power is None else event.interaction_out_power,
        "interaction_loss_power": "" if event.interaction_loss_power is None else event.interaction_loss_power,
        "interaction_bulk": "" if event.interaction_bulk is None else event.interaction_bulk,
        "volume_id": event.volume_id,
        "media_transition": event.media_transition,
        "media_in": event.media_in,
        "media_out": event.media_out,
        "media_state_method": event.media_state_method,
        "media_state_diagnostic": event.media_state_diagnostic,
        "inside_volumes_before": event.inside_volumes_before,
        "inside_volumes_after": event.inside_volumes_after,
        "mesh_cell_id": "" if event.mesh_cell_id is None else event.mesh_cell_id,
        "mesh_original_cell_id": "" if event.mesh_original_cell_id is None else event.mesh_original_cell_id,
        "mesh_face_id": event.mesh_face_id,
        "mesh_face_match_method": event.mesh_face_match_method,
        "mesh_face_match_score": "" if event.mesh_face_match_score is None else event.mesh_face_match_score,
        "mesh_face_match_warning": event.mesh_face_match_warning,
        "event_id": event.event_id,
        "event_source": str(metadata.get("event_source", "") or ""),
        "event_kind": event.event_kind,
        "diagnostic": event.diagnostic,
    }
    record.update(_ray_event_gaussian_frame_fields(incoming, outgoing, normal))
    return record


def _ray_analysis_status_text(termination: str, last_surface, reaches_image: bool = False) -> str:
    if reaches_image or termination == "image":
        return "Image"
    try:
        surface_text = f"S{int(last_surface)}"
    except Exception:
        surface_text = ""
    if termination == "missed_image":
        return f"Missed image after {surface_text}" if surface_text else "Missed image"
    if termination == "missed_folded_image":
        return "Missed image"
    if termination == "no_next_intersection":
        return f"Continues after {surface_text}" if surface_text else "Continues"
    if termination in {"no_hit", "no_folded_display_path"}:
        return "No hit"
    if str(termination or "").startswith("stopped_at_surface_"):
        return f"Stop @ {surface_text}" if surface_text else "Stopped"
    return str(termination or "").strip() or "No hit"


def _safe_complex_scalar(value, default: complex) -> complex:
    try:
        result = complex(value)
    except Exception:
        return default
    if not np.isfinite(result.real) or not np.isfinite(result.imag):
        return default
    return result


def _branch_jones_fractions(p_value, s_value) -> tuple[float, float]:
    p_component = _safe_complex_scalar(p_value, complex(1.0, 0.0))
    s_component = _safe_complex_scalar(s_value, complex(0.0, 0.0))
    norm_sq = float((abs(p_component) ** 2.0) + (abs(s_component) ** 2.0))
    if not np.isfinite(norm_sq) or norm_sq <= 1e-30:
        return 1.0, 0.0
    return float(abs(p_component) ** 2.0 / norm_sq), float(abs(s_component) ** 2.0 / norm_sq)


def _unit_ray_frame_vector(value) -> np.ndarray | None:
    try:
        vector = np.asarray(value, dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    if vector.size < 3 or not np.all(np.isfinite(vector)):
        return None
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 1e-12:
        return None
    return vector / norm


def _ray_event_gaussian_frame_fields(incoming, outgoing, normal) -> dict[str, object]:
    incoming_unit = _unit_ray_frame_vector(incoming)
    outgoing_unit = _unit_ray_frame_vector(outgoing)
    normal_unit = _unit_ray_frame_vector(normal)
    k_axis = outgoing_unit if outgoing_unit is not None else incoming_unit
    if k_axis is None:
        return {
            "gb_frame_valid": False,
            "gb_incidence_deg": np.nan,
            "gb_k_l": np.nan,
            "gb_k_m": np.nan,
            "gb_k_n": np.nan,
            "gb_t_l": np.nan,
            "gb_t_m": np.nan,
            "gb_t_n": np.nan,
            "gb_s_l": np.nan,
            "gb_s_m": np.nan,
            "gb_s_n": np.nan,
        }

    incidence_deg = np.nan
    if incoming_unit is not None and normal_unit is not None:
        cos_i = float(np.clip(abs(float(np.dot(incoming_unit, normal_unit))), 0.0, 1.0))
        incidence_deg = float(np.rad2deg(np.arccos(cos_i)))

    reference = normal_unit
    if reference is None or float(np.linalg.norm(reference - (np.dot(reference, k_axis) * k_axis))) <= 1e-10:
        candidates = (
            np.asarray((0.0, 1.0, 0.0), dtype=float),
            np.asarray((1.0, 0.0, 0.0), dtype=float),
            np.asarray((0.0, 0.0, 1.0), dtype=float),
        )
        reference = max(
            candidates,
            key=lambda candidate: float(np.linalg.norm(candidate - (np.dot(candidate, k_axis) * k_axis))),
        )

    t_axis = reference - (float(np.dot(reference, k_axis)) * k_axis)
    t_norm = float(np.linalg.norm(t_axis))
    if not np.isfinite(t_norm) or t_norm <= 1e-12:
        return {
            "gb_frame_valid": False,
            "gb_incidence_deg": incidence_deg,
            "gb_k_l": float(k_axis[0]),
            "gb_k_m": float(k_axis[1]),
            "gb_k_n": float(k_axis[2]),
            "gb_t_l": np.nan,
            "gb_t_m": np.nan,
            "gb_t_n": np.nan,
            "gb_s_l": np.nan,
            "gb_s_m": np.nan,
            "gb_s_n": np.nan,
        }
    t_axis = t_axis / t_norm
    s_axis = np.cross(k_axis, t_axis)
    s_norm = float(np.linalg.norm(s_axis))
    if not np.isfinite(s_norm) or s_norm <= 1e-12:
        return {
            "gb_frame_valid": False,
            "gb_incidence_deg": incidence_deg,
            "gb_k_l": float(k_axis[0]),
            "gb_k_m": float(k_axis[1]),
            "gb_k_n": float(k_axis[2]),
            "gb_t_l": float(t_axis[0]),
            "gb_t_m": float(t_axis[1]),
            "gb_t_n": float(t_axis[2]),
            "gb_s_l": np.nan,
            "gb_s_m": np.nan,
            "gb_s_n": np.nan,
        }
    s_axis = s_axis / s_norm
    t_axis = np.cross(s_axis, k_axis)
    t_axis = t_axis / max(float(np.linalg.norm(t_axis)), 1e-12)
    return {
        "gb_frame_valid": True,
        "gb_incidence_deg": incidence_deg,
        "gb_k_l": float(k_axis[0]),
        "gb_k_m": float(k_axis[1]),
        "gb_k_n": float(k_axis[2]),
        "gb_t_l": float(t_axis[0]),
        "gb_t_m": float(t_axis[1]),
        "gb_t_n": float(t_axis[2]),
        "gb_s_l": float(s_axis[0]),
        "gb_s_m": float(s_axis[1]),
        "gb_s_n": float(s_axis[2]),
    }


def _sum_event_values(events: list[RayEvent3D], attr: str) -> float:
    total = 0.0
    for event in events:
        value = getattr(event, attr, None)
        try:
            numeric = float(value)
        except Exception:
            continue
        if np.isfinite(numeric):
            total += numeric
    return float(total)


def _last_event_value(events: list[RayEvent3D], attr: str) -> float | None:
    for event in reversed(events):
        value = getattr(event, attr, None)
        try:
            numeric = float(value)
        except Exception:
            continue
        if np.isfinite(numeric):
            return float(numeric)
    return None


def _join_diagnostics(*values: object) -> str:
    return "; ".join(str(value).strip() for value in values if str(value or "").strip())


def _optional_float(value: object) -> float | None:
    try:
        numeric = float(value)
    except Exception:
        return None
    return float(numeric) if np.isfinite(numeric) else None


def _optional_int(value: object) -> int | None:
    numeric = _optional_float(value)
    if numeric is None:
        return None
    return int(round(float(numeric)))


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    numeric = _optional_float(value)
    if numeric is not None:
        return bool(numeric)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "active"}:
        return True
    if text in {"0", "false", "no", "off", "inactive"}:
        return False
    return None


def _metadata_int_list_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    try:
        values = np.asarray(value, dtype=object).reshape(-1)
    except Exception:
        values = (value,)
    result: list[str] = []
    for item in values:
        text = str(item or "").strip()
        if not text:
            continue
        try:
            result.append(str(int(float(text))))
        except Exception:
            result.append(text)
    return ",".join(result)


def _vector3(value: object) -> tuple[float, float, float]:
    try:
        arr = np.asarray(value, dtype=float).reshape(-1)
        if arr.size >= 3 and np.isfinite(arr[:3]).all():
            return float(arr[0]), float(arr[1]), float(arr[2])
    except Exception:
        pass
    return (np.nan, np.nan, np.nan)


def _complex_vector3(value: object) -> tuple[complex, complex, complex]:
    try:
        arr = np.asarray(value, dtype=np.complex128).reshape(-1)
        if arr.size >= 3 and np.isfinite(arr[:3].real).all() and np.isfinite(arr[:3].imag).all():
            return complex(arr[0]), complex(arr[1]), complex(arr[2])
    except Exception:
        pass
    return (complex(1.0, 0.0), complex(0.0, 0.0), complex(0.0, 0.0))


def _last_path_point(path: RayPath3D) -> np.ndarray:
    try:
        points = np.asarray(path.points_world, dtype=float)
        if points.ndim == 2 and points.shape[0] > 0:
            return np.asarray(points[-1, :3], dtype=float)
    except Exception:
        pass
    return np.full(3, np.nan, dtype=float)


def _finite_vector_array(value: object) -> np.ndarray | None:
    vector = np.asarray(_vector3(value), dtype=float)
    if vector.shape == (3,) and np.isfinite(vector).all():
        return vector
    return None


def _terminal_record_vector_or_fallback(
    record: dict[str, object] | None,
    key: str,
    fallback: object,
) -> tuple[np.ndarray, str]:
    if record:
        vector = _finite_vector_array(record.get(key))
        if vector is not None:
            return vector, "trace_event"
    fallback_vector = _finite_vector_array(fallback)
    if fallback_vector is not None:
        return fallback_vector, "ray_path"
    return np.full(3, np.nan, dtype=float), "missing"


def _terminal_surface_id_for_event(
    path: RayPath3D,
    trace_surface_id: int | None,
    terminal_record: dict[str, object] | None,
) -> tuple[int | None, str]:
    path_surface_id = _last_surface_id(path)
    if trace_surface_id is None:
        return path_surface_id, "ray_path"
    path_surface_ids: set[int] = set()
    try:
        path_surface_ids = {int(value) for value in np.asarray(path.surface_ids, dtype=int).reshape(-1)}
    except Exception:
        path_surface_ids = set()
    reaches_trace_terminal = False
    if terminal_record:
        reaches_trace_terminal = bool(terminal_record.get("reaches_target", False)) or bool(
            terminal_record.get("reaches_detector", False)
        )
    if trace_surface_id in path_surface_ids or reaches_trace_terminal or bool(getattr(path, "reaches_image", False)):
        return int(trace_surface_id), "trace_event"
    if path_surface_id is not None:
        return path_surface_id, "ray_path_filtered"
    return int(trace_surface_id), "trace_event"


def _last_path_direction(path: RayPath3D, *, incoming: bool) -> np.ndarray:
    hits = list(getattr(path, "hits", []) or [])
    if hits:
        attr = "incoming_direction" if incoming else "outgoing_direction"
        return np.asarray(getattr(hits[-1], attr, np.full(3, np.nan)), dtype=float)
    return np.asarray(getattr(path, "source_direction", np.full(3, np.nan)), dtype=float)


def _system_transform_for_surface(system: Any | None, surface_index: int) -> np.ndarray | None:
    if system is None:
        return None
    for owner in (getattr(system, "Pr3D", None), system):
        transforms = getattr(owner, "TRANS_2A", None) if owner is not None else None
        if transforms is None:
            continue
        try:
            if 0 <= int(surface_index) < len(transforms):
                transform = np.asarray(transforms[int(surface_index)], dtype=float).reshape(4, 4)
                if np.all(np.isfinite(transform)):
                    return transform
        except Exception:
            continue
    return None


def _row_axial_z_before(rows: list, row_index: int) -> float:
    z_pos = 0.0
    for prior in list(rows or [])[: max(0, int(row_index))]:
        try:
            z_pos += float(getattr(prior, "thickness", 0.0) or 0.0)
        except Exception:
            pass
    return float(z_pos)


def _detector_surface_frame(
    rows: list,
    system: Any | None,
    surface_index: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    if not (0 <= int(surface_index) < len(rows)):
        return None
    transform = _system_transform_for_surface(system, int(surface_index))
    if transform is not None:
        center = np.asarray(transform[:3, 3], dtype=float)
        normal = _unit_vector_or_default(transform[:3, 2], (0.0, 0.0, 1.0))
        tangent = _unit_vector_or_default(transform[:3, 1], (0.0, 1.0, 0.0))
        return center, normal, tangent
    row = rows[int(surface_index)]
    return _scene_target_frame(int(surface_index), row, _row_axial_z_before(rows, int(surface_index)))


def _terminal_direction_for_detector_miss(path: RayPath3D, terminal_event: RayEvent3D) -> np.ndarray | None:
    for candidate in (
        getattr(terminal_event, "outgoing_direction", None),
        getattr(terminal_event, "incoming_direction", None),
        _last_path_direction(path, incoming=False),
    ):
        vector = _finite_vector_array(candidate)
        if vector is not None and np.linalg.norm(vector) > 1e-12:
            return vector / np.linalg.norm(vector)
    points = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
    if points.ndim == 2 and points.shape[0] >= 2:
        vector = points[-1, :3] - points[-2, :3]
        norm = float(np.linalg.norm(vector))
        if np.isfinite(norm) and norm > 1e-12:
            return vector / norm
    return None


# An escaped ray is only meaningfully "imaged" onto a detector plane when it
# actually propagates toward that plane. A ray traveling nearly parallel to the
# plane -- e.g. the reflected branch of a beam-splitter cube, which folds ~90 deg
# away toward its own (second) port -- would only "reach" the image plane
# hundreds of metres off-axis. Projecting it there is non-physical and the
# resulting ~10^5 mm coordinates wreck both the VTK scene extent (rays render
# bent / vanish on zoom) and the 2D layout auto-scale. Require the ray to lie
# within this cone of the detector normal (|cos| >= cos(80 deg)) before
# projecting; otherwise it stays escaped with its sane traced length.
_DETECTOR_MISS_MIN_AXIAL_COS = 0.17364817766693041  # cos(80 deg)


def _detector_plane_miss_intersection(
    rows: list,
    system: Any | None,
    detector_surface_indices: set[int],
    origin: np.ndarray,
    direction: np.ndarray,
    detector_active_dims_overrides: dict[int, tuple[float, float]] | None = None,
) -> dict[str, object] | None:
    best: dict[str, object] | None = None
    for detector_index in sorted(int(index) for index in detector_surface_indices):
        frame = _detector_surface_frame(rows, system, detector_index)
        if frame is None:
            continue
        center, normal, tangent = frame
        tangent = np.asarray(tangent, dtype=float).reshape(3)
        tangent = tangent - normal * float(np.dot(tangent, normal))
        tangent_norm = float(np.linalg.norm(tangent))
        if not np.isfinite(tangent_norm) or tangent_norm <= 1e-12:
            fallback = np.asarray((1.0, 0.0, 0.0), dtype=float)
            if abs(float(np.dot(fallback, normal))) > 0.95:
                fallback = np.asarray((0.0, 1.0, 0.0), dtype=float)
            tangent = fallback - normal * float(np.dot(fallback, normal))
            tangent_norm = float(np.linalg.norm(tangent))
        tangent = tangent / max(tangent_norm, 1e-12)
        bitangent = np.cross(normal, tangent)
        bitangent_norm = float(np.linalg.norm(bitangent))
        if not np.isfinite(bitangent_norm) or bitangent_norm <= 1e-12:
            continue
        bitangent = bitangent / bitangent_norm
        denom = float(np.dot(direction, normal))
        if not np.isfinite(denom) or abs(denom) < _DETECTOR_MISS_MIN_AXIAL_COS:
            # parallel to / grazing the detector plane: not heading toward it.
            continue
        distance = float(np.dot(center - origin, normal) / denom)
        if not np.isfinite(distance) or distance <= 1e-9:
            continue
        point = origin + direction * distance
        offset = point - center
        normal_error = float(abs(np.dot(offset, normal)))
        in_plane = offset - normal * float(np.dot(offset, normal))
        radial = float(np.linalg.norm(in_plane))
        row = rows[detector_index]
        settings = _row_detector_settings(row)
        try:
            diameter = max(float(getattr(row, "diameter", 0.0) or 0.0), 0.0)
        except Exception:
            diameter = 0.0
        active_width = float(settings.get("active_width_mm", 0.0) or 0.0)
        active_height = float(settings.get("active_height_mm", 0.0) or 0.0)
        override_w, override_h = _detector_override_dims(detector_active_dims_overrides, detector_index)
        if active_width <= 1e-12:
            active_width = override_w if override_w > 1e-12 else diameter
        if active_height <= 1e-12:
            active_height = override_h if override_h > 1e-12 else diameter
        half = 0.5 * max(active_width, active_height)
        local_x = float(np.dot(offset, tangent))
        local_y = float(np.dot(offset, bitangent))
        candidate = {
            "surface": int(detector_index),
            "point": np.asarray(point, dtype=float),
            "distance": float(distance),
            "radial": float(radial),
            "half": float(half),
            "x": float(local_x),
            "y": float(local_y),
            "active_width": float(active_width),
            "active_height": float(active_height),
            "normal_error": float(normal_error),
        }
        if best is None or float(candidate["distance"]) < float(best["distance"]):
            best = candidate
    return best


def _detector_plane_contact(
    rows: list,
    system: Any | None,
    detector_surface_indices: set[int],
    point: np.ndarray,
    detector_active_dims_overrides: dict[int, tuple[float, float]] | None = None,
) -> dict[str, object] | None:
    try:
        point = np.asarray(point, dtype=float).reshape(3)
    except Exception:
        return None
    if not np.all(np.isfinite(point)):
        return None
    for detector_index in sorted(int(index) for index in detector_surface_indices):
        frame = _detector_surface_frame(rows, system, detector_index)
        if frame is None:
            continue
        center, normal, tangent = frame
        tangent = np.asarray(tangent, dtype=float).reshape(3)
        tangent = tangent - normal * float(np.dot(tangent, normal))
        tangent_norm = float(np.linalg.norm(tangent))
        if not np.isfinite(tangent_norm) or tangent_norm <= 1e-12:
            fallback = np.asarray((1.0, 0.0, 0.0), dtype=float)
            if abs(float(np.dot(fallback, normal))) > 0.95:
                fallback = np.asarray((0.0, 1.0, 0.0), dtype=float)
            tangent = fallback - normal * float(np.dot(fallback, normal))
            tangent_norm = float(np.linalg.norm(tangent))
        tangent = tangent / max(tangent_norm, 1e-12)
        bitangent = np.cross(normal, tangent)
        bitangent_norm = float(np.linalg.norm(bitangent))
        if not np.isfinite(bitangent_norm) or bitangent_norm <= 1e-12:
            continue
        bitangent = bitangent / bitangent_norm
        offset = point - center
        normal_error = float(abs(np.dot(offset, normal)))
        in_plane = offset - normal * float(np.dot(offset, normal))
        radial = float(np.linalg.norm(in_plane))
        row = rows[detector_index]
        settings = _row_detector_settings(row)
        try:
            diameter = max(float(getattr(row, "diameter", 0.0) or 0.0), 0.0)
        except Exception:
            diameter = 0.0
        active_width = float(settings.get("active_width_mm", 0.0) or 0.0)
        active_height = float(settings.get("active_height_mm", 0.0) or 0.0)
        override_w, override_h = _detector_override_dims(detector_active_dims_overrides, detector_index)
        if active_width <= 1e-12:
            active_width = override_w if override_w > 1e-12 else diameter
        if active_height <= 1e-12:
            active_height = override_h if override_h > 1e-12 else diameter
        half = 0.5 * max(active_width, active_height)
        local_x = float(np.dot(offset, tangent))
        local_y = float(np.dot(offset, bitangent))
        if normal_error <= 1e-5 and radial <= half + 1e-6:
            return {
                "surface": int(detector_index),
                "point": np.asarray(point, dtype=float),
                "radial": float(radial),
                "half": float(half),
                "x": float(local_x),
                "y": float(local_y),
                "active_width": float(active_width),
                "active_height": float(active_height),
                "normal_error": float(normal_error),
            }
    return None


def _sync_detector_miss_terminal_event(
    rows: list,
    system: Any | None,
    path: RayPath3D,
    events: list[RayEvent3D],
    detector_surface_indices: set[int],
    *,
    allow_target_plane_contact: bool = False,
    detector_active_dims_overrides: dict[int, tuple[float, float]] | None = None,
) -> list[RayEvent3D]:
    if not events:
        return events
    contact_surface_indices = set(int(index) for index in detector_surface_indices)
    try:
        target_surface = int(getattr(path, "target_surface", -1))
    except Exception:
        target_surface = -1
    if allow_target_plane_contact and 0 <= target_surface < len(rows):
        if str(getattr(rows[target_surface], "surface", "") or "") == "Image":
            contact_surface_indices.add(int(target_surface))
    if not contact_surface_indices and not detector_surface_indices:
        return events
    terminal_index = None
    for index in range(len(events) - 1, -1, -1):
        if str(getattr(events[index], "event_kind", "") or "") == "terminal":
            terminal_index = index
            break
    if terminal_index is None:
        return events
    terminal = events[terminal_index]
    metadata = dict(getattr(terminal, "metadata", {}) or {})
    if bool(metadata.get("reaches_detector", False)) or bool(getattr(path, "reaches_image", False)):
        return events
    reason = str(getattr(terminal, "termination_reason", "") or getattr(terminal, "event_type", "") or "").strip().lower()
    if reason not in {"no_next_intersection", "missed_image", "missed_detector", "escaped"}:
        return events
    surface_events = [
        event
        for event in events[:terminal_index]
        if str(getattr(event, "event_kind", "") or "") == "surface"
    ]
    if not surface_events:
        return events
    origin = _finite_vector_array(getattr(surface_events[-1], "point_world", None))
    if origin is None:
        return events
    direction = _terminal_direction_for_detector_miss(path, terminal)
    if direction is None:
        return events
    terminal_point = _finite_vector_array(getattr(terminal, "point_world", None))
    contact = _detector_plane_contact(
        rows,
        system,
        contact_surface_indices,
        terminal_point if terminal_point is not None else origin,
        detector_active_dims_overrides=detector_active_dims_overrides,
    )
    if contact is not None:
        detector_surface = int(contact["surface"])
        reaches_detector = detector_surface in detector_surface_indices
        metadata.update(
            {
                "terminal_geometry_source": "detector_plane_contact",
                "detector_miss_surface": detector_surface,
                "detector_miss_status": "",
                "detector_miss_distance_mm": 0.0,
                "detector_miss_radial_mm": float(contact["radial"]),
                "detector_miss_half_mm": float(contact["half"]),
                "detector_miss_x_mm": float(contact["x"]),
                "detector_miss_y_mm": float(contact["y"]),
                "detector_miss_active_width_mm": float(contact["active_width"]),
                "detector_miss_active_height_mm": float(contact["active_height"]),
                "detector_miss_normal_error_mm": float(contact["normal_error"]),
                "detector_miss_kernel_reason": reason or "no_next_intersection",
                "terminal_detector_surfaces": sorted(int(index) for index in detector_surface_indices),
                "terminal_trace_surface": detector_surface,
                "terminal_surface_source": "detector_plane_contact",
                "reaches_image": True,
                "reaches_detector": bool(reaches_detector),
                "reaches_target": True,
            }
        )
        updated = replace(
            terminal,
            event_type="image",
            surface_id=detector_surface,
            termination_reason="image",
            point_world=np.asarray(contact["point"], dtype=float),
            diagnostic="",
            metadata=metadata,
        )
        return [*events[:terminal_index], updated, *events[terminal_index + 1:]]
    intersection = _detector_plane_miss_intersection(
        rows, system, detector_surface_indices, origin, direction,
        detector_active_dims_overrides=detector_active_dims_overrides,
    )
    if intersection is None:
        return events
    detector_surface = int(intersection["surface"])
    kernel_reason = reason or "no_next_intersection"
    metadata.update(
        {
            "terminal_geometry_source": "detector_miss_plane",
            "detector_miss_surface": detector_surface,
            "detector_miss_status": "missed_detector",
            "detector_miss_distance_mm": float(intersection["distance"]),
            "detector_miss_radial_mm": float(intersection["radial"]),
            "detector_miss_half_mm": float(intersection["half"]),
            "detector_miss_x_mm": float(intersection["x"]),
            "detector_miss_y_mm": float(intersection["y"]),
            "detector_miss_active_width_mm": float(intersection["active_width"]),
            "detector_miss_active_height_mm": float(intersection["active_height"]),
            "detector_miss_normal_error_mm": float(intersection["normal_error"]),
            "detector_miss_kernel_reason": kernel_reason,
            "terminal_detector_surfaces": sorted(int(index) for index in detector_surface_indices),
            "reaches_detector": False,
        }
    )
    diagnostic = _join_diagnostics(
        getattr(terminal, "diagnostic", ""),
        (
            "Ray escaped modeled geometry and was projected to detector plane "
            f"S{detector_surface} as a miss: radial={float(intersection['radial']):.6g} mm, "
            f"active half={float(intersection['half']):.6g} mm, "
            f"local=({float(intersection['x']):.6g}, {float(intersection['y']):.6g}) mm."
        ),
    )
    updated = replace(
        terminal,
        event_type="missed_image",
        termination_reason="missed_image",
        point_world=np.asarray(intersection["point"], dtype=float),
        diagnostic=diagnostic,
        metadata=metadata,
    )
    return [*events[:terminal_index], updated, *events[terminal_index + 1:]]


def _last_surface_id(path: RayPath3D) -> int | None:
    try:
        surfaces = np.asarray(path.surface_ids, dtype=int).reshape(-1)
        if surfaces.size:
            return int(surfaces[-1])
    except Exception:
        pass
    return None


def _sync_path_display_geometry_from_events(path: RayPath3D) -> None:
    """Make display path points follow the canonical event table when possible."""
    raw_points = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
    raw_surface_ids = np.asarray(
        getattr(path, "surface_ids", np.empty(0, dtype=int)),
        dtype=int,
    ).reshape(-1)
    events = list(getattr(path, "events", []) or [])
    if not events:
        path.display_geometry_source = path.display_geometry_source or "raykeeper_path"
        path.display_geometry_diagnostic = path.display_geometry_diagnostic or "no canonical events available"
        return
    surface_events = [
        event
        for event in events
        if str(getattr(event, "event_kind", "") or "") == "surface"
    ]
    if not surface_events:
        path.display_geometry_source = "raykeeper_path"
        path.display_geometry_diagnostic = "canonical events contain no surface geometry"
        return
    launch = _finite_vector_array(getattr(path, "source_position", None))
    if launch is None:
        if raw_points.ndim == 2 and raw_points.shape[0] > 0:
            launch = _finite_vector_array(raw_points[0, :3])
    if launch is None:
        path.display_geometry_source = "raykeeper_path"
        path.display_geometry_diagnostic = "canonical events cannot recover a finite launch point"
        return
    points: list[np.ndarray] = [launch]
    surface_ids: list[int] = []
    for event in surface_events:
        point = _finite_vector_array(getattr(event, "point_world", None))
        if point is None:
            path.display_geometry_source = "raykeeper_path"
            path.display_geometry_diagnostic = "canonical surface event has no finite point"
            return
        points.append(point)
        surface_id = getattr(event, "surface_id", None)
        if surface_id is not None:
            surface_ids.append(int(surface_id))
    terminal_events = [
        event
        for event in events
        if str(getattr(event, "event_kind", "") or "") == "terminal"
    ]
    terminal_point_source = ""
    if terminal_events:
        terminal_event = terminal_events[-1]
        terminal_point = _finite_vector_array(getattr(terminal_event, "point_world", None))
        terminal_metadata = dict(getattr(terminal_event, "metadata", {}) or {})
        terminal_reason = str(
            getattr(terminal_event, "termination_reason", "")
            or getattr(terminal_event, "event_type", "")
            or ""
        ).strip().lower()
        terminal_surface_id = getattr(terminal_event, "surface_id", None)
        terminal_is_detector_hit = bool(terminal_metadata.get("reaches_detector", False)) or terminal_reason == "image"
        if terminal_point is not None and not _same_point(points[-1], terminal_point):
            points.append(terminal_point)
            terminal_point_source = str(
                terminal_metadata.get("terminal_geometry_source", "") or ""
            )
            if terminal_is_detector_hit and terminal_surface_id is not None:
                surface_ids.append(int(terminal_surface_id))
    elif _has_terminal_continuation(raw_points, raw_surface_ids):
        continuation_point = _finite_vector_array(raw_points[-1, :3])
        if continuation_point is not None and not _same_point(points[-1], continuation_point):
            points.append(continuation_point)
            terminal_point_source = "raykeeper_terminal_continuation"
    event_sources = sorted({
        str((getattr(event, "metadata", {}) or {}).get("event_source", "") or "")
        for event in events
        if str((getattr(event, "metadata", {}) or {}).get("event_source", "") or "").strip()
    })
    raw_surface_count = 0
    try:
        raw_surface_count = int(np.asarray(path.surface_ids, dtype=int).reshape(-1).size)
    except Exception:
        raw_surface_count = 0
    path.points_world = np.asarray(points, dtype=float)
    path.surface_ids = np.asarray(surface_ids, dtype=int)
    path.display_geometry_source = "ray_events"
    details = [f"events={','.join(event_sources) or 'unknown'}"]
    if terminal_point_source:
        details.append(f"terminal_point={terminal_point_source}")
    if raw_surface_count != len(surface_ids):
        details.append(f"raw_surface_count={raw_surface_count}, event_surface_count={len(surface_ids)}")
    path.display_geometry_diagnostic = "; ".join(details)


def _same_point(a: object, b: object, *, atol: float = 1e-9) -> bool:
    first = _finite_vector_array(a)
    second = _finite_vector_array(b)
    if first is None or second is None:
        return False
    return bool(np.allclose(first, second, rtol=0.0, atol=atol))


def _has_terminal_continuation(points_world: np.ndarray, surface_ids: np.ndarray) -> bool:
    return bool(
        surface_ids.size
        and points_world.ndim == 2
        and points_world.shape[0] > int(surface_ids.size) + 1
    )


def _normalized_detector_surface_indices(rows: list, detector_surface_indices: set[int] | None) -> set[int]:
    if detector_surface_indices is None:
        return {
            int(index)
            for index, row in enumerate(rows)
            if str(getattr(row, "surface", "") or "") == "Image"
        }
    normalized: set[int] = set()
    for raw_index in detector_surface_indices:
        try:
            index = int(raw_index)
        except Exception:
            continue
        if 0 <= index < len(rows):
            normalized.add(index)
    return normalized


def _strip_nonterminal_image_hits(
    rows: list,
    points_world: np.ndarray,
    hits: list[RayHit3D],
    surface_ids: np.ndarray,
    *,
    detector_surface_indices: set[int],
) -> tuple[np.ndarray, list[RayHit3D], np.ndarray]:
    """Remove intermediate Image-plane hits from display ray paths.

    In non-sequential layouts the final Image row may be either an explicit
    detector or only the sequential prescription sentinel.  Preserve only
    detector Image hits as terminal events.  When a non-detector Image hit is
    terminal, keep its point as continuation geometry but remove the hit event
    so the scene does not report a physical detector that the user did not
    create.
    """
    if not rows or points_world.ndim != 2 or not hits or surface_ids.size == 0:
        return points_world, hits, surface_ids
    final_index = len(rows) - 1
    if final_index < 0 or str(getattr(rows[final_index], "surface", "") or "") != "Image":
        return points_world, hits, surface_ids
    last_image_step = None
    for step, surface_id in enumerate(surface_ids):
        if int(surface_id) == final_index:
            last_image_step = step
    if last_image_step is None:
        return points_world, hits, surface_ids
    final_image_is_detector = int(final_index) in detector_surface_indices
    keep_steps = [
        step
        for step, surface_id in enumerate(surface_ids)
        if int(surface_id) != final_index
        or (final_image_is_detector and int(step) == int(last_image_step))
    ]
    if len(keep_steps) == len(surface_ids):
        return points_world, hits, surface_ids
    point_indices = [0]
    point_indices.extend(step + 1 for step in keep_steps if step + 1 < points_world.shape[0])
    if not final_image_is_detector and int(last_image_step) == int(len(surface_ids) - 1):
        terminal_point_index = int(last_image_step) + 1
        if terminal_point_index < points_world.shape[0] and terminal_point_index not in point_indices:
            point_indices.append(terminal_point_index)
    filtered_points = np.asarray(points_world[point_indices], dtype=float)
    filtered_hits = [hits[step] for step in keep_steps if step < len(hits)]
    for new_step, hit in enumerate(filtered_hits):
        hit.step = int(new_step)
    filtered_surface_ids = np.asarray([int(surface_ids[step]) for step in keep_steps], dtype=int)
    _assign_hit_branch_ids(filtered_hits)
    return filtered_points, filtered_hits, filtered_surface_ids


def _surface_label(rows: list, surface_index: int | None) -> str:
    if surface_index is None:
        return ""
    try:
        index = int(surface_index)
    except Exception:
        return ""
    name = ""
    if 0 <= index < len(rows):
        name = str(getattr(rows[index], "name", "") or "").strip()
    return f"S{index} {name}".strip()


def _ray_path_termination_diagnostic(
    rows: list,
    points_world: np.ndarray,
    surface_ids: np.ndarray,
    termination_reason: str,
    target_surface_index: int | None,
    detector_surface_indices: set[int],
    branch_tree_diagnostic: str = "",
) -> str:
    reason = str(termination_reason or "").strip()
    tree_text = str(branch_tree_diagnostic or "").strip()
    if tree_text:
        return tree_text
    if reason in {"", "image"}:
        return ""
    last_surface = int(surface_ids[-1]) if surface_ids.size else None
    last_label = _surface_label(rows, last_surface) or "the launch point"
    target_label = _surface_label(rows, target_surface_index)
    detector_labels = [
        _surface_label(rows, index)
        for index in sorted(int(value) for value in detector_surface_indices)
    ]
    detector_text = ", ".join(label for label in detector_labels if label)
    point_text = ""
    try:
        point = np.asarray(points_world[-1], dtype=float).reshape(-1)
        if point.size >= 3 and np.isfinite(point[:3]).all():
            point_text = "last point=({:.6g},{:.6g},{:.6g})".format(
                float(point[0]),
                float(point[1]),
                float(point[2]),
            )
    except Exception:
        point_text = ""
    if reason == "missed_image":
        target_text = detector_text or target_label or "configured detector/image target"
        parts = [f"Ray continued after {last_label} and missed {target_text}."]
    elif reason == "no_next_intersection":
        parts = [f"Ray continued after {last_label}; no downstream object or detector intersection was found."]
        if target_label:
            parts.append(f"target={target_label}")
    elif reason == "no_hit":
        parts = ["Ray did not intersect any modeled surface."]
        if target_label:
            parts.append(f"target={target_label}")
    elif reason == f"stopped_at_surface_{last_surface}":
        parts = [f"Ray stopped at {last_label} without a terminal event or continuation segment."]
    else:
        parts = [reason.replace("_", " ")]
        if last_surface is not None:
            parts.append(f"last={last_label}")
    if point_text:
        parts.append(point_text)
    return " ".join(parts)


def _raykeeper_array(rays: Any, seq_name: str, ray_index: int, *, dtype=None) -> np.ndarray:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return np.empty(0, dtype=(dtype or float))
    try:
        return np.asarray(seq[ray_index], dtype=dtype).ravel()
    except Exception:
        try:
            return np.asarray(seq[ray_index]).ravel()
        except Exception:
            return np.empty(0, dtype=(dtype or float))


def _raykeeper_xyz_array(rays: Any, seq_name: str, ray_index: int) -> np.ndarray:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return np.empty((0, 3), dtype=float)
    try:
        arr = np.asarray(seq[ray_index], dtype=float)
    except Exception:
        return np.empty((0, 3), dtype=float)
    if arr.ndim == 1 and arr.size == 3:
        arr = arr.reshape(1, 3)
    if arr.ndim != 2 or arr.shape[1] < 3:
        return np.empty((0, 3), dtype=float)
    return np.asarray(arr[:, :3], dtype=float)


def _raykeeper_complex_xyz_array(rays: Any, seq_name: str, ray_index: int) -> np.ndarray:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return np.empty((0, 3), dtype=np.complex128)
    try:
        arr = np.asarray(seq[ray_index], dtype=np.complex128)
    except Exception:
        return np.empty((0, 3), dtype=np.complex128)
    if arr.ndim == 1 and arr.size == 3:
        arr = arr.reshape(1, 3)
    if arr.ndim != 2 or arr.shape[1] < 3:
        return np.empty((0, 3), dtype=np.complex128)
    real_finite = np.isfinite(arr[:, :3].real)
    imag_finite = np.isfinite(arr[:, :3].imag)
    if not np.all(real_finite & imag_finite):
        return np.empty((0, 3), dtype=np.complex128)
    return np.asarray(arr[:, :3], dtype=np.complex128)


def _raykeeper_scalar(arr: np.ndarray, index: int) -> float | None:
    if index >= arr.size:
        return None
    try:
        value = float(arr[index])
    except Exception:
        return None
    if not np.isfinite(value):
        return None
    return value


def _raykeeper_vector(arr: np.ndarray, index: int) -> np.ndarray:
    if index >= arr.shape[0]:
        return np.full(3, np.nan, dtype=float)
    value = np.asarray(arr[index], dtype=float).ravel()
    if value.size < 3:
        return np.full(3, np.nan, dtype=float)
    return value[:3]


def _raykeeper_metadata_scalar(rays: Any, seq_name: str, ray_index: int) -> int | float | None:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return None
    try:
        arr = np.asarray(seq[ray_index]).ravel()
    except Exception:
        return None
    if arr.size == 0:
        return None
    try:
        value = float(arr[0])
    except Exception:
        return None
    if not np.isfinite(value):
        return None
    if abs(value - round(value)) < 1e-9:
        return int(round(value))
    return value


def _raykeeper_metadata_complex(rays: Any, seq_name: str, ray_index: int, default: complex) -> complex:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return default
    try:
        arr = np.asarray(seq[ray_index]).ravel()
    except Exception:
        return default
    if arr.size == 0:
        return default
    try:
        value = complex(arr[0])
    except Exception:
        return default
    if not np.isfinite(value.real) or not np.isfinite(value.imag):
        return default
    return value


def _raykeeper_metadata_text(rays: Any, seq_name: str, ray_index: int) -> str:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return ""
    try:
        arr = np.asarray(seq[ray_index], dtype=object).ravel()
    except Exception:
        return ""
    if arr.size == 0:
        return ""
    return str(arr[0])


def _raykeeper_text(arr: np.ndarray, index: int) -> str:
    if index >= arr.size:
        return ""
    try:
        return str(arr[index])
    except Exception:
        return ""


def _classify_ray_interaction(rows: list, surface_id: int | None, n0: float | None, n1: float | None) -> str:
    if surface_id is None or not (0 <= surface_id < len(rows)):
        return "unknown"
    row = rows[surface_id]
    surface_type = str(getattr(row, "surface", "") or "").strip().lower()
    glass = str(getattr(row, "glass", "") or "").strip().upper()
    if surface_type == "diffuse object":
        return "diffuse_scatter"
    if surface_type == "mirror" or glass == "MIRROR":
        return "reflection"
    if surface_type == "beam splitter":
        return "beam_splitter"
    if surface_type == "aperture":
        return "aperture"
    if surface_type == "object":
        return "launch"
    if surface_type == "image":
        return "image"
    if n0 is not None and n1 is not None and abs(float(n0) - float(n1)) > 1e-9:
        return "refraction"
    return "transmission"


def _interaction_event_label(
    rows: list,
    surface_id: int | None,
    interaction_type: str,
    n0: float | None,
    n1: float | None,
) -> str:
    label = str(interaction_type or "").strip().lower()
    if surface_id is not None and 0 <= surface_id < len(rows):
        surface_type = str(getattr(rows[surface_id], "surface", "") or "").strip().lower()
        if surface_type == "object":
            return "launch"
        if surface_type == "image":
            return "image"
        if surface_type == "aperture":
            return "aperture"
    if label in {"reflect_tir", "reflect_mirror"}:
        return label
    if label in {"reflection", "reflect"}:
        return "reflection"
    if label in {"scatter", "diffuse_scatter"}:
        return "scatter"
    if label in {"absorb", "absorption"}:
        return "absorb"
    if label in {"refract", "refraction"}:
        return "refraction"
    if label == "transmit":
        if n0 is not None and n1 is not None and abs(float(n0) - float(n1)) > 1e-9:
            return "refraction"
        return "transmission"
    if label:
        return label
    return _classify_ray_interaction(rows, surface_id, n0, n1)


def _build_ray_hit_records(rows: list, rays: Any, ray_index: int) -> list[RayHit3D]:
    surface_arr = _raykeeper_array(rays, "SURFACE", ray_index, dtype=int)
    name_arr = _raykeeper_array(rays, "NAME", ray_index, dtype=object)
    glass_arr = _raykeeper_array(rays, "GLASS", ray_index, dtype=object)
    xyz_arr = _raykeeper_xyz_array(rays, "XYZ", ray_index)
    lmn_arr = _raykeeper_xyz_array(rays, "LMN", ray_index)
    r_lmn_arr = _raykeeper_xyz_array(rays, "R_LMN", ray_index)
    s_lmn_arr = _raykeeper_xyz_array(rays, "S_LMN", ray_index)
    n0_arr = _raykeeper_array(rays, "N0", ray_index, dtype=float)
    n1_arr = _raykeeper_array(rays, "N1", ray_index, dtype=float)
    dist_arr = _raykeeper_array(rays, "DISTANCE", ray_index, dtype=float)
    op_arr = _raykeeper_array(rays, "OP", ray_index, dtype=float)
    rp_arr = _raykeeper_array(rays, "RP", ray_index, dtype=float)
    rs_arr = _raykeeper_array(rays, "RS", ray_index, dtype=float)
    tp_arr = _raykeeper_array(rays, "TP", ray_index, dtype=float)
    ts_arr = _raykeeper_array(rays, "TS", ray_index, dtype=float)
    ttbe_arr = _raykeeper_array(rays, "TTBE", ray_index, dtype=float)
    interaction_type_arr = _raykeeper_array(rays, "INTERACTION_TYPE", ray_index, dtype=object)
    interaction_model_arr = _raykeeper_array(rays, "INTERACTION_MODEL", ray_index, dtype=object)
    interaction_target_arr = _raykeeper_array(rays, "INTERACTION_TARGET_SURFACE", ray_index, dtype=float)
    interaction_in_power_arr = _raykeeper_array(rays, "INTERACTION_IN_POWER", ray_index, dtype=float)
    interaction_coeff_arr = _raykeeper_array(rays, "INTERACTION_COEFF", ray_index, dtype=float)
    interaction_out_power_arr = _raykeeper_array(rays, "INTERACTION_OUT_POWER", ray_index, dtype=float)
    interaction_loss_power_arr = _raykeeper_array(rays, "INTERACTION_LOSS_POWER", ray_index, dtype=float)
    interaction_bulk_arr = _raykeeper_array(rays, "INTERACTION_BULK", ray_index, dtype=float)
    volume_id_arr = _raykeeper_array(rays, "VOLUME_ID", ray_index, dtype=object)
    media_in_arr = _raykeeper_array(rays, "MEDIA_IN", ray_index, dtype=object)
    media_out_arr = _raykeeper_array(rays, "MEDIA_OUT", ray_index, dtype=object)
    media_transition_arr = _raykeeper_array(rays, "MEDIA_TRANSITION", ray_index, dtype=object)
    media_state_method_arr = _raykeeper_array(rays, "MEDIA_STATE_METHOD", ray_index, dtype=object)
    media_state_diagnostic_arr = _raykeeper_array(rays, "MEDIA_STATE_DIAGNOSTIC", ray_index, dtype=object)
    inside_volumes_before_arr = _raykeeper_array(rays, "INSIDE_VOLUMES_BEFORE", ray_index, dtype=object)
    inside_volumes_after_arr = _raykeeper_array(rays, "INSIDE_VOLUMES_AFTER", ray_index, dtype=object)
    mesh_cell_id_arr = _raykeeper_array(rays, "MESH_CELL_ID", ray_index, dtype=float)
    mesh_original_cell_id_arr = _raykeeper_array(rays, "MESH_ORIGINAL_CELL_ID", ray_index, dtype=float)
    mesh_face_id_arr = _raykeeper_array(rays, "MESH_FACE_ID", ray_index, dtype=object)
    mesh_face_match_method_arr = _raykeeper_array(rays, "MESH_FACE_MATCH_METHOD", ray_index, dtype=object)
    mesh_face_match_score_arr = _raykeeper_array(rays, "MESH_FACE_MATCH_SCORE", ray_index, dtype=float)
    mesh_face_match_warning_arr = _raykeeper_array(rays, "MESH_FACE_MATCH_WARNING", ray_index, dtype=object)

    core_count = int(max(
        name_arr.size,
        glass_arr.size,
        xyz_arr.shape[0],
        lmn_arr.shape[0],
        r_lmn_arr.shape[0],
        s_lmn_arr.shape[0],
        n0_arr.size,
        n1_arr.size,
        dist_arr.size,
        op_arr.size,
    ))
    hit_count = int(surface_arr.size) if surface_arr.size else core_count
    hits: list[RayHit3D] = []
    for step in range(hit_count):
        surface_id = int(surface_arr[step]) if step < surface_arr.size else None
        n0 = _raykeeper_scalar(n0_arr, step)
        n1 = _raykeeper_scalar(n1_arr, step)
        point_step = step + 1 if surface_arr.size and xyz_arr.shape[0] == surface_arr.size + 1 else step
        interaction_type = _raykeeper_text(interaction_type_arr, step)
        hits.append(RayHit3D(
            step=step,
            surface_id=surface_id,
            name=str(name_arr[step]) if step < name_arr.size else "",
            material=str(glass_arr[step]) if step < glass_arr.size else "",
            point_world=_raykeeper_vector(xyz_arr, point_step),
            incoming_direction=_raykeeper_vector(lmn_arr, step),
            outgoing_direction=_raykeeper_vector(r_lmn_arr, step),
            surface_normal=_raykeeper_vector(s_lmn_arr, step),
            n0=n0,
            n1=n1,
            distance=_raykeeper_scalar(dist_arr, step),
            optical_path=_raykeeper_scalar(op_arr, step),
            rp=_raykeeper_scalar(rp_arr, step),
            rs=_raykeeper_scalar(rs_arr, step),
            tp=_raykeeper_scalar(tp_arr, step),
            ts=_raykeeper_scalar(ts_arr, step),
            ttbe=_raykeeper_scalar(ttbe_arr, step),
            interaction=_interaction_event_label(rows, surface_id, interaction_type, n0, n1),
            interaction_model=_raykeeper_text(interaction_model_arr, step),
            interaction_target_surface=_raykeeper_scalar(interaction_target_arr, step),
            interaction_in_power=_raykeeper_scalar(interaction_in_power_arr, step),
            interaction_coeff=_raykeeper_scalar(interaction_coeff_arr, step),
            interaction_out_power=_raykeeper_scalar(interaction_out_power_arr, step),
            interaction_loss_power=_raykeeper_scalar(interaction_loss_power_arr, step),
            interaction_bulk=_raykeeper_scalar(interaction_bulk_arr, step),
            volume_id=_raykeeper_text(volume_id_arr, step),
            media_in=_raykeeper_text(media_in_arr, step),
            media_out=_raykeeper_text(media_out_arr, step),
            media_transition=_raykeeper_text(media_transition_arr, step),
            media_state_method=_raykeeper_text(media_state_method_arr, step),
            media_state_diagnostic=_raykeeper_text(media_state_diagnostic_arr, step),
            inside_volumes_before=_raykeeper_text(inside_volumes_before_arr, step),
            inside_volumes_after=_raykeeper_text(inside_volumes_after_arr, step),
            mesh_cell_id=_raykeeper_scalar(mesh_cell_id_arr, step),
            mesh_original_cell_id=_raykeeper_scalar(mesh_original_cell_id_arr, step),
            mesh_face_id=_raykeeper_text(mesh_face_id_arr, step),
            mesh_face_match_method=_raykeeper_text(mesh_face_match_method_arr, step),
            mesh_face_match_score=_raykeeper_scalar(mesh_face_match_score_arr, step),
            mesh_face_match_warning=_raykeeper_text(mesh_face_match_warning_arr, step),
        ))
    _assign_hit_branch_ids(hits)
    return hits


def _interaction_is_reflective(value: object) -> bool:
    text = str(value or "").strip().lower()
    return text in {"reflection", "reflect", "reflect_tir", "reflect_mirror"} or text.startswith("split_reflect")


def _assign_hit_branch_ids(hits: list[RayHit3D]) -> None:
    branch_id = 0
    previous_surface: int | None = None
    for index, hit in enumerate(hits):
        if previous_surface is not None and hit.surface_id is not None and hit.surface_id <= previous_surface:
            branch_id += 1
        hit.branch_id = branch_id
        previous_surface = hit.surface_id
        if _interaction_is_reflective(hit.interaction) and index < len(hits) - 1:
            branch_id += 1
            previous_surface = None


def _build_ray_branches(
    hits: list[RayHit3D],
    termination_reason: str,
    termination_diagnostic: str = "",
) -> list[RayBranch3D]:
    if not hits:
        return []
    grouped: list[tuple[int, list[RayHit3D]]] = []
    for hit in hits:
        if not grouped or grouped[-1][0] != hit.branch_id:
            grouped.append((hit.branch_id, []))
        grouped[-1][1].append(hit)
    branches: list[RayBranch3D] = []
    parent: int | None = None
    for index, (branch_id, branch_hits) in enumerate(grouped):
        end_step = int(branch_hits[-1].step)
        if index < len(grouped) - 1:
            reason = (
                "reflection"
                if _interaction_is_reflective(branch_hits[-1].interaction)
                else "nonsequential_transition"
            )
        else:
            reason = termination_reason
        surface_ids = np.asarray(
            [hit.surface_id for hit in branch_hits if hit.surface_id is not None],
            dtype=int,
        )
        branches.append(RayBranch3D(
            branch_id=int(branch_id),
            parent_branch_id=parent,
            start_step=int(branch_hits[0].step),
            end_step=end_step,
            surface_ids=surface_ids,
            termination_reason=reason,
            termination_diagnostic=termination_diagnostic if index == len(grouped) - 1 else "",
        ))
        parent = int(branch_id)
    return branches


def _normalize_folded_terminal_policy(value: object) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "": FOLDED_TERMINAL_POLICY_TRACE_EVENTS,
        "trace": FOLDED_TERMINAL_POLICY_TRACE_EVENTS,
        "trace_event": FOLDED_TERMINAL_POLICY_TRACE_EVENTS,
        "trace_events": FOLDED_TERMINAL_POLICY_TRACE_EVENTS,
        "physical": FOLDED_TERMINAL_POLICY_TRACE_EVENTS,
        "physics": FOLDED_TERMINAL_POLICY_TRACE_EVENTS,
        "diagnostic": FOLDED_TERMINAL_POLICY_TRACE_EVENTS,
        "display": FOLDED_TERMINAL_POLICY_DISPLAY_COMPATIBILITY,
        "display_path": FOLDED_TERMINAL_POLICY_DISPLAY_COMPATIBILITY,
        "display_compatibility": FOLDED_TERMINAL_POLICY_DISPLAY_COMPATIBILITY,
        "compatibility": FOLDED_TERMINAL_POLICY_DISPLAY_COMPATIBILITY,
        "legacy": FOLDED_TERMINAL_POLICY_DISPLAY_COMPATIBILITY,
        "authoritative": FOLDED_TERMINAL_POLICY_DISPLAY_COMPATIBILITY,
    }
    return aliases.get(text, FOLDED_TERMINAL_POLICY_TRACE_EVENTS)


def _sync_folded_terminal_events(
    ray_paths: list[RayPath3D],
    folded_ray_display_paths: list[np.ndarray],
    elements: list,
    detector_surface_indices: set[int],
    *,
    folded_terminal_policy: str = FOLDED_TERMINAL_POLICY_TRACE_EVENTS,
) -> None:
    policy = _normalize_folded_terminal_policy(folded_terminal_policy)
    image_element = None
    image_surface_index: int | None = None
    for element_index, element in reversed(list(enumerate(elements, start=1))):
        if element and element[0] == "Image" and int(element_index) in detector_surface_indices:
            image_element = element
            image_surface_index = int(element_index)
            break
    if image_element is None or image_surface_index is None:
        return
    _surface_type, center, row, branch_dir, *_rest = image_element
    center = np.asarray(center, dtype=float)
    branch_dir = np.asarray(branch_dir, dtype=float)
    branch_dir /= max(np.linalg.norm(branch_dir), 1e-12)
    tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
    half = max(float(getattr(row, "diameter", 1.0)) / 2.0, 0.5)
    for path in ray_paths:
        folded_update = _folded_terminal_update(
            path,
            folded_ray_display_paths,
            image_surface_index=image_surface_index,
            center=center,
            branch_dir=branch_dir,
            tangent=tangent,
            half=half,
        )
        if folded_update is None:
            continue
        path.events = _replace_folded_terminal_event(
            path,
            list(getattr(path, "events", []) or []),
            folded_update,
            folded_terminal_policy=policy,
        )
        _sync_path_terminal_state_from_events(path)
        _sync_path_display_geometry_from_events(path)


def _folded_terminal_update(
    path: RayPath3D,
    folded_ray_display_paths: list[np.ndarray],
    *,
    image_surface_index: int,
    center: np.ndarray,
    branch_dir: np.ndarray,
    tangent: np.ndarray,
    half: float,
) -> dict[str, object] | None:
    if path.ray_index >= len(folded_ray_display_paths):
        return None
    pts = np.asarray(folded_ray_display_paths[path.ray_index], dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 2:
        return {
            "termination_reason": "no_folded_display_path",
            "reaches_image": False,
            "surface_id": _last_surface_id(path),
            "diagnostic": "Folded display path was unavailable for detector reach evaluation.",
            "folded_detector_surface": image_surface_index,
            "folded_display_status": "missing_path",
        }
    delta = pts[-1] - center
    normal_error = abs(float(np.dot(delta, branch_dir)))
    along = abs(float(np.dot(delta, tangent)))
    reaches_image = normal_error <= 1e-5 and along <= half + 1e-6
    if reaches_image:
        reason = "image"
        surface_id = image_surface_index
        diagnostic = ""
        status = "hit_detector"
    elif path.termination_reason in {"missed_image", "no_next_intersection"}:
        reason = str(path.termination_reason or "missed_folded_image")
        surface_id = _last_surface_id(path)
        diagnostic = str(path.termination_diagnostic or "")
        status = "missed_detector"
    elif path.surface_ids.size:
        surface_id = int(path.surface_ids[-1])
        reason = f"stopped_at_surface_{surface_id}"
        diagnostic = str(path.termination_diagnostic or "")
        status = "stopped_before_detector"
    else:
        reason = "missed_folded_image"
        surface_id = None
        diagnostic = str(path.termination_diagnostic or "")
        status = "missed_detector"
    return {
        "termination_reason": reason,
        "reaches_image": bool(reaches_image),
        "surface_id": surface_id,
        "diagnostic": diagnostic,
        "folded_detector_surface": image_surface_index,
        "folded_display_status": status,
        "folded_display_normal_error": normal_error,
        "folded_display_along": along,
        "folded_display_half": half,
    }


def _replace_folded_terminal_event(
    path: RayPath3D,
    events: list[RayEvent3D],
    folded_update: dict[str, object],
    *,
    folded_terminal_policy: str = FOLDED_TERMINAL_POLICY_TRACE_EVENTS,
) -> list[RayEvent3D]:
    surface_events = [
        event
        for event in events
        if str(getattr(event, "event_kind", "") or "") != "terminal"
    ]
    terminal_events = [
        event
        for event in events
        if str(getattr(event, "event_kind", "") or "") == "terminal"
    ]
    terminal = terminal_events[-1] if terminal_events else None
    if terminal is None:
        terminal = _ray_path_terminal_event(
            path,
            step=len(surface_events),
            event_source="scene_folded_terminal",
            event_id=f"ray:{int(path.ray_index)}:terminal",
        )
    if terminal is None:
        return surface_events
    policy = _normalize_folded_terminal_policy(folded_terminal_policy)
    authoritative = policy == FOLDED_TERMINAL_POLICY_DISPLAY_COMPATIBILITY
    reaches_image = bool(folded_update.get("reaches_image", False))
    metadata = dict(getattr(terminal, "metadata", {}) or {})
    metadata.update({
        "folded_detector_policy": policy,
        "folded_display_authoritative": bool(authoritative),
        "folded_display_reaches_detector": reaches_image,
        "folded_terminal_source": "folded_display_path",
        "folded_display_status": str(folded_update.get("folded_display_status", "") or ""),
        "folded_detector_surface": folded_update.get("folded_detector_surface"),
        "folded_display_normal_error": folded_update.get("folded_display_normal_error"),
        "folded_display_along": folded_update.get("folded_display_along"),
        "folded_display_half": folded_update.get("folded_display_half"),
    })
    if not authoritative:
        return surface_events + [replace(terminal, metadata=metadata)]
    metadata["reaches_image"] = reaches_image
    metadata["reaches_detector"] = reaches_image
    if reaches_image:
        metadata["terminal_surface_source"] = "folded_display"
        metadata["terminal_trace_surface"] = folded_update.get("surface_id")
    diagnostic = _join_diagnostics(
        getattr(terminal, "diagnostic", ""),
        str(folded_update.get("diagnostic", "") or ""),
    )
    surface_id = _optional_int(folded_update.get("surface_id"))
    return surface_events + [
        replace(
            terminal,
            event_type=str(folded_update.get("termination_reason", "") or terminal.event_type or "terminal"),
            surface_id=surface_id,
            termination_reason=str(folded_update.get("termination_reason", "") or terminal.termination_reason or ""),
            diagnostic=diagnostic,
            metadata=metadata,
        )
    ]


def _sync_path_terminal_state_from_events(path: RayPath3D) -> None:
    terminal_events = [
        event
        for event in list(getattr(path, "events", []) or [])
        if str(getattr(event, "event_kind", "") or "") == "terminal"
    ]
    if not terminal_events:
        return
    terminal = terminal_events[-1]
    metadata = dict(getattr(terminal, "metadata", {}) or {})
    reason = str(getattr(terminal, "termination_reason", "") or getattr(terminal, "event_type", "") or "")
    path.termination_reason = reason
    path.termination_diagnostic = str(getattr(terminal, "diagnostic", "") or "")
    path.reaches_image = bool(
        metadata.get("reaches_image", False)
        or metadata.get("reaches_detector", False)
        or reason == "image"
    )
    if path.branches:
        path.branches[-1].termination_reason = reason
        path.branches[-1].termination_diagnostic = path.termination_diagnostic


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

def _build_reference_plane_labels(
    rows: list,
    *,
    project_fn: Callable | None,
    overrides: dict,
    detector_surface_indices: set[int],
) -> list[LabelSpec]:
    labels: list[LabelSpec] = []
    z_pos = 0.0
    for row_index, row in enumerate(rows):
        display_settings = _row_display_settings(row)
        if display_settings.get("show_reference_label") is False:
            z_pos += row.thickness
            continue
        if row.surface == "Image" and int(row_index) not in detector_surface_indices:
            z_pos += row.thickness
            continue
        if row.surface in {"Object", "Image", "Aperture"}:
            label_text = row.name or row.surface
            points = _reference_plane_display_points(row_index, row, z_pos, overrides, project_fn)
            if points is None or points.shape[0] < 2:
                z_pos += row.thickness
                continue
            world_points = _reference_plane_world_points(row_index, row, z_pos, overrides)
            coordinate_space = _reference_plane_coordinate_space(row_index, row, overrides)
            x_vals = points[:, 0].astype(float)
            y_vals = points[:, 1].astype(float)
            center_x = float(np.mean(x_vals))
            center_y = float(np.mean(y_vals))
            line_vec = np.array([float(x_vals[-1] - x_vals[0]), float(y_vals[-1] - y_vals[0])], dtype=float)
            norm = np.linalg.norm(line_vec)
            if norm <= 1e-12:
                normal = np.array([0.0, 1.0], dtype=float)
            else:
                tangent = line_vec / norm
                normal = np.array([-tangent[1], tangent[0]], dtype=float)
            offset = max(float(row.diameter) * 0.08, 1.2)
            text_x = center_x + normal[0] * offset
            text_y = center_y + normal[1] * offset
            text_ha = "center"
            if row.surface == "Object":
                text_x = center_x + offset
                text_y = float(np.max(y_vals)) + offset
                text_ha = "left"
            elif row.surface == "Image":
                text_x = center_x - offset
                text_y = float(np.max(y_vals)) + offset
                text_ha = "right"
            label_kwargs: dict[str, object] = {}
            if coordinate_space == "world" and world_points is not None and world_points.shape[0] >= 2:
                anchor_world = np.mean(np.asarray(world_points[:, :3], dtype=float), axis=0)
                anchor_display = _curve_points_yz_display(world_points)
                if anchor_display.shape[0] >= 2 and np.all(np.isfinite(anchor_world[:3])):
                    anchor_2d = np.mean(anchor_display, axis=0)
                    label_kwargs = {
                        "point_world": np.asarray(anchor_world[:3], dtype=float),
                        "offset_2d": np.asarray((text_x - float(anchor_2d[0]), text_y - float(anchor_2d[1])), dtype=float),
                        "coordinate_space": "world",
                    }
            labels.append(LabelSpec(
                text=label_text,
                x=text_x,
                y=text_y,
                row_index=row_index,
                fontsize=9.0,
                color="#202020",
                ha=text_ha,
                va="bottom",
                **label_kwargs,
            ))
        z_pos += row.thickness
    return labels


def _row_display_settings(row: Any) -> dict:
    advanced = getattr(row, "advanced", {}) or {}
    if not isinstance(advanced, dict):
        return {}
    settings = advanced.get("Display2D", {})
    if isinstance(settings, dict):
        return settings
    return {}


def _compact_key_optic_label_text(row_index: int, row: Any, curve_kind: str, label_text: str, display_settings: dict) -> str:
    label = " ".join(str(label_text or "").split()).strip()
    if not label:
        return str(getattr(row, "surface", "") or "Surface")
    if any(str(key) in display_settings for key in ("label", "label_text")):
        return label
    advanced = getattr(row, "advanced", {}) or {}
    is_optical_solid = isinstance(advanced, dict) and advanced.get("Solid_3d_stl") not in (None, "", "None")
    if str(curve_kind or "") == "stl_solid" or is_optical_solid:
        if isinstance(advanced, dict) and isinstance(advanced.get("StepOverlayPromotion"), dict):
            step_label = str(advanced.get("StepOverlayPromotion", {}).get("step_label", "") or "").strip()
            step_names = {"optical": "Optical", "lens": "Lens", "camera": "Camera", "led": "LED"}
            source_name = step_names.get(step_label.lower(), step_label.title()) if step_label else "Optical"
            source = f"{source_name} STEP"
            return f"S{int(row_index)} {source}"
        if len(label) > 28:
            return f"S{int(row_index)} CAD/STL solid"
    return label


def _build_key_optic_labels(rows: list, surface_curves: list[SurfaceCurve3D]) -> list[LabelSpec]:
    labels: list[LabelSpec] = []
    label_surfaces = {"Mirror", "Object Target", "Diffuse Object", "Beam Splitter"}
    labeled_rows: set[int] = set()
    all_points = [
        _curve_points_yz_display(curve.points_world)
        for curve in surface_curves
        if _curve_points_yz_display(curve.points_world).shape[0] >= 2
    ]
    scene_span = 1.0
    if all_points:
        finite_points = np.vstack(all_points)
        finite = np.isfinite(finite_points[:, 0]) & np.isfinite(finite_points[:, 1])
        if np.any(finite):
            finite_points = finite_points[finite]
            span_x = float(np.max(finite_points[:, 0]) - np.min(finite_points[:, 0]))
            span_y = float(np.max(finite_points[:, 1]) - np.min(finite_points[:, 1]))
            scene_span = max(span_x, span_y, 1.0)

    for curve in surface_curves:
        row_index = int(curve.row_index)
        if row_index in labeled_rows or row_index < 0 or row_index >= len(rows):
            continue
        row = rows[row_index]
        if row.surface not in label_surfaces and curve.kind != "stl_solid":
            continue
        pts = _curve_points_yz_display(curve.points_world)
        if pts.shape[0] < 2:
            continue
        finite = np.isfinite(pts[:, 0]) & np.isfinite(pts[:, 1])
        if not np.any(finite):
            continue
        pts = pts[finite]
        center = np.mean(pts, axis=0)
        tangent = np.asarray(pts[-1] - pts[0], dtype=float)
        tangent_norm = float(np.linalg.norm(tangent))
        if tangent_norm <= 1e-12:
            normal = np.array([0.0, 1.0], dtype=float)
        else:
            tangent /= tangent_norm
            normal = np.array([-tangent[1], tangent[0]], dtype=float)
        if normal[1] < 0.0:
            normal *= -1.0
        offset = max(0.045 * scene_span, 1.4, 0.10 * max(float(row.diameter), 1.0))
        if curve.kind == "stl_solid":
            color = "#0369a1"
        else:
            color = "#0e7490" if row.surface == "Beam Splitter" else "#202020"
        display_settings = _row_display_settings(row)
        label_text = str(
            display_settings.get("label", display_settings.get("label_text", row.name or row.surface))
            or row.surface
        ).strip()
        label_text = _compact_key_optic_label_text(row_index, row, curve.kind, label_text, display_settings)
        label_x = float(center[0] + normal[0] * offset)
        label_y = float(center[1] + normal[1] * offset)
        label_kwargs: dict[str, object] = {}
        coordinate_space = str(getattr(curve, "coordinate_space", "world") or "world")
        if coordinate_space == "world":
            try:
                world_points = np.asarray(curve.points_world, dtype=float)
            except Exception:
                world_points = np.empty((0, 3), dtype=float)
            if world_points.ndim == 2 and world_points.shape[0] >= 2 and world_points.shape[1] >= 3:
                world_finite = np.all(np.isfinite(world_points[:, :3]), axis=1)
                if np.any(world_finite):
                    anchor_world = np.mean(world_points[world_finite, :3], axis=0)
                    if np.all(np.isfinite(anchor_world)):
                        label_kwargs = {
                            "point_world": np.asarray(anchor_world[:3], dtype=float),
                            "offset_2d": np.asarray((label_x - float(center[0]), label_y - float(center[1])), dtype=float),
                            "coordinate_space": "world",
                        }
        labels.append(
            LabelSpec(
                text=label_text,
                x=label_x,
                y=label_y,
                row_index=row_index,
                fontsize=8.0,
                color=color,
                ha="center",
                va="bottom",
                **label_kwargs,
            )
        )
        labeled_rows.add(row_index)
    return labels


def _build_source_markers(
    sources: list[SceneSource3D],
    *,
    display_orientation: str,
    project_fn: Callable | None,
) -> tuple[list[SurfaceCurve3D], list[LabelSpec]]:
    curves: list[SurfaceCurve3D] = []
    labels: list[LabelSpec] = []
    for source in sources:
        if not bool(getattr(source, "enabled", True)) or not bool(getattr(source, "physical", False)):
            continue
        settings = getattr(source, "settings", {}) or {}
        if not isinstance(settings, dict):
            settings = {}
        origin = np.asarray(getattr(source, "origin", (0.0, 0.0, 0.0)), dtype=float).reshape(-1)
        direction = np.asarray(getattr(source, "direction", (0.0, 0.0, 1.0)), dtype=float).reshape(-1)
        if origin.size < 3 or direction.size < 3:
            continue
        origin = origin[:3]
        direction = direction[:3]
        if not np.all(np.isfinite(origin)) or not np.all(np.isfinite(direction)):
            continue
        direction_norm = float(np.linalg.norm(direction))
        if direction_norm <= 1e-12:
            continue
        direction = direction / direction_norm
        radius = _source_marker_radius(source)
        center_world = origin
        tip_world = origin + direction * max(2.0 * radius, 6.0)
        tangent_world = _source_marker_world_tangent(direction)
        half = max(radius, 1.5)
        aperture = np.vstack((center_world - tangent_world * half, center_world + tangent_world * half))
        axis_line = np.vstack((center_world, tip_world))
        curves.append(SurfaceCurve3D(
            row_index=-1,
            kind="source",
            points_world=aperture,
            style=StyleHint(color="#f97316", linewidth=2.3, alpha=0.95),
        ))
        if _source_marker_setting_bool(settings, ("show_source_axis", "show_axis", "show_launch_axis"), True):
            curves.append(SurfaceCurve3D(
                row_index=-1,
                kind="source_axis",
                points_world=axis_line,
                style=StyleHint(color="#f97316", linewidth=1.2, alpha=0.75),
            ))
        center = _project_3d_yz_point(origin, display_orientation=display_orientation, project_fn=project_fn)
        tip = _project_3d_yz_point(
            tip_world,
            display_orientation=display_orientation,
            project_fn=project_fn,
        )
        if center is None or tip is None:
            continue
        axis = np.asarray(tip - center, dtype=float)
        axis_norm = float(np.linalg.norm(axis))
        if axis_norm <= 1e-12:
            tangent = np.asarray((0.0, 1.0), dtype=float)
        else:
            axis = axis / axis_norm
            tangent = np.asarray((-axis[1], axis[0]), dtype=float)
        text_offset = max(radius * 0.35, 1.4)
        label_x = float(center[0] + tangent[0] * (half + text_offset))
        label_y = float(center[1] + tangent[1] * (half + text_offset))
        labels.append(LabelSpec(
            text=str(getattr(source, "name", "") or getattr(source, "source_id", "") or "Source"),
            x=label_x,
            y=label_y,
            row_index=-1,
            fontsize=8.5,
            color="#c2410c",
            ha="center",
            va="bottom",
            point_world=np.asarray(center_world, dtype=float),
            offset_2d=np.asarray((label_x - float(center[0]), label_y - float(center[1])), dtype=float),
            coordinate_space="world",
            source_id=str(getattr(source, "source_id", "") or ""),
        ))
    return curves, labels


def _source_marker_world_tangent(direction: np.ndarray) -> np.ndarray:
    direction = np.asarray(direction, dtype=float).reshape(-1)[:3]
    if direction.size < 3:
        return np.asarray((0.0, 1.0, 0.0), dtype=float)
    yz_tangent = np.asarray((0.0, direction[2], -direction[1]), dtype=float)
    yz_norm = float(np.linalg.norm(yz_tangent))
    if yz_norm > 1e-12:
        return yz_tangent / yz_norm
    for fallback_axis in (
        np.asarray((0.0, 0.0, 1.0), dtype=float),
        np.asarray((0.0, 1.0, 0.0), dtype=float),
    ):
        tangent = np.cross(direction, fallback_axis)
        norm = float(np.linalg.norm(tangent))
        if norm > 1e-12:
            return tangent / norm
    return np.asarray((0.0, 1.0, 0.0), dtype=float)


def _source_marker_setting_bool(settings: dict[str, object], keys: tuple[str, ...], default: bool) -> bool:
    for key in keys:
        if key not in settings:
            continue
        value = settings.get(key)
        if isinstance(value, str):
            return value.strip().lower() not in {"0", "false", "no", "off", "hide", ""}
        return bool(value)
    return bool(default)


def _source_marker_radius(source: SceneSource3D) -> float:
    settings = getattr(source, "settings", {}) or {}
    for key in ("launch_radius", "radius", "waist_radius"):
        try:
            value = float(settings.get(key))
        except Exception:
            continue
        if np.isfinite(value) and value > 0.0:
            return max(value, 1.5)
    try:
        length = float(settings.get("length"))
    except Exception:
        length = 0.0
    if np.isfinite(length) and length > 0.0:
        return max(0.5 * length, 1.5)
    return 2.0


def _project_3d_yz_point(
    point: np.ndarray,
    *,
    display_orientation: str,
    project_fn: Callable | None,
) -> np.ndarray | None:
    try:
        p = np.asarray(point, dtype=float).reshape(-1)
    except Exception:
        return None
    if p.size < 3 or not np.all(np.isfinite(p[:3])):
        return None
    if project_fn is not None:
        try:
            x_vals, y_vals = project_fn([float(p[2])], [float(p[1])])
            return np.asarray((float(np.asarray(x_vals, dtype=float).ravel()[0]), float(np.asarray(y_vals, dtype=float).ravel()[0])), dtype=float)
        except Exception:
            return None
    if display_orientation == "Horizontal":
        return np.asarray((-float(p[1]), -float(p[2])), dtype=float)
    return np.asarray((float(p[2]), float(p[1])), dtype=float)


# ---------------------------------------------------------------------------
# Pick regions
# ---------------------------------------------------------------------------

def _build_pick_regions(rows: list, surface_curves: list[SurfaceCurve3D]) -> list[PickRegion]:
    region_map: dict[int, list[np.ndarray]] = {}
    for curve in surface_curves:
        if curve.kind == "lens_edge" or int(curve.row_index) < 0:
            continue
        pts = _curve_points_yz_display(curve.points_world)
        if pts.shape[0] < 2:
            continue
        region_map.setdefault(curve.row_index, []).append(pts)
    return [PickRegion(row_index=ri, polylines=polys) for ri, polys in region_map.items()]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def surface_style_for_row(row: Any) -> tuple[str, float, float]:
    surface = getattr(row, "surface", "Standard")
    advanced = getattr(row, "advanced", {}) or {}
    if isinstance(advanced, dict) and advanced.get("Solid_3d_stl") not in (None, "", "None"):
        return "#64748b", 1.45, 0.72
    if surface == "Diffuse Object":
        return "#16a34a", 2.2, 0.95
    if surface in {"Mirror", "Object Target"}:
        return "#202020", 2.2, 0.95
    if surface == "Beam Splitter":
        return "#0891b2", 2.0, 0.92
    if surface == "Aperture":
        return "#b45309", 1.6, 0.95
    if surface == "Thin Lens":
        return "#7c3aed", 1.5, 0.9
    if surface == "Grating":
        return "#0f766e", 1.5, 0.9
    return "#2563eb", 1.4, 0.85


def _has_off_axis_geometry(rows: list) -> bool:
    for row in rows:
        if row.surface in {"Mirror", "Object Target", "Diffuse Object"}:
            return True
        if any(
            abs(value) > 1e-9
            for value in (row.tilt_x, row.tilt_y, row.tilt_z, row.desp_x, row.desp_y, row.desp_z, row.axis_move)
        ):
            return True
    return False


def _default_field_colors(count: int) -> list[str]:
    if count <= 1:
        return ["#39FF14"]
    cmap = [
        "#39FF14", "#00E5FF", "#FF9F1C", "#FF4D6D",
        "#9B5DE5", "#FFD166", "#2EC4B6", "#E71D36",
    ]
    return [cmap[i % len(cmap)] for i in range(count)]


def _reference_plane_coordinate_space(row_index: int, row: Any, overrides: dict) -> str:
    display_settings = _row_display_settings(row)
    center_value = display_settings.get("plane_center")
    tangent_value = display_settings.get("plane_tangent")
    if center_value is not None and tangent_value is not None:
        try:
            center = np.asarray(center_value, dtype=float).ravel()
            tangent = np.asarray(tangent_value, dtype=float).ravel()
            return "world" if center.size >= 3 and tangent.size >= 3 else "yz_display"
        except Exception:
            return "yz_display"
    override = overrides.get(row_index)
    if override is not None:
        try:
            center, along = override
            center = np.asarray(center, dtype=float).ravel()
            along = np.asarray(along, dtype=float).ravel()
            return "world" if center.size >= 3 and along.size >= 3 else "yz_display"
        except Exception:
            return "yz_display"
    return "world"


def _reference_plane_world_points(
    row_index: int,
    row: Any,
    z_pos: float,
    overrides: dict,
) -> np.ndarray | None:
    if row.surface not in {"Object", "Image", "Aperture"}:
        return None
    display_settings = _row_display_settings(row)
    half_height = max(float(row.diameter) / 2.0, 0.5)
    center_value = display_settings.get("plane_center")
    tangent_value = display_settings.get("plane_tangent")
    if center_value is not None and tangent_value is not None:
        try:
            center = np.asarray(center_value, dtype=float).ravel()
            tangent = np.asarray(tangent_value, dtype=float).ravel()
            if center.size >= 3 and tangent.size >= 3:
                center_world = center[:3]
                tangent_world = tangent[:3]
            elif center.size >= 2 and tangent.size >= 2:
                center_world = np.asarray((0.0, center[1], center[0]), dtype=float)
                tangent_world = np.asarray((0.0, tangent[1], tangent[0]), dtype=float)
            else:
                center_world = np.empty(0, dtype=float)
                tangent_world = np.empty(0, dtype=float)
            tangent_norm = float(np.linalg.norm(tangent_world))
            if center_world.size >= 3 and tangent_norm > 1e-12:
                tangent_world = tangent_world / tangent_norm
                return np.vstack((center_world - tangent_world * half_height, center_world + tangent_world * half_height))
        except Exception:
            pass
    override = overrides.get(row_index)
    if override is not None:
        try:
            center, along = override
            center = np.asarray(center, dtype=float).ravel()
            along = np.asarray(along, dtype=float).ravel()
            if center.size >= 3 and along.size >= 3:
                center_world = center[:3]
                tangent_world = np.cross(np.asarray((1.0, 0.0, 0.0), dtype=float), along[:3])
            elif center.size >= 2 and along.size >= 2:
                tangent_display = np.asarray((-along[1], along[0]), dtype=float)
                center_world = np.asarray((0.0, center[1], center[0]), dtype=float)
                tangent_world = np.asarray((0.0, tangent_display[1], tangent_display[0]), dtype=float)
            else:
                return None
            tangent_norm = float(np.linalg.norm(tangent_world))
            if tangent_norm <= 1e-12:
                return None
            tangent_world = tangent_world / tangent_norm
            return np.vstack((center_world - tangent_world * half_height, center_world + tangent_world * half_height))
        except Exception:
            pass
    center_z = z_pos + float(row.desp_z)
    if row.surface == "Image" and abs(float(row.thickness)) > 1e-12:
        center_z += float(row.thickness)
    center_world = np.asarray((float(row.desp_x), float(row.desp_y), center_z), dtype=float)
    tangent_world = np.asarray((0.0, 1.0, 0.0), dtype=float)
    return np.vstack((center_world - tangent_world * half_height, center_world + tangent_world * half_height))


def _reference_plane_display_points(
    row_index: int,
    row: Any,
    z_pos: float,
    overrides: dict,
    project_fn: Callable | None,
) -> np.ndarray | None:
    if row.surface not in {"Object", "Image", "Aperture"}:
        return None
    display_settings = _row_display_settings(row)
    center_value = display_settings.get("plane_center")
    tangent_value = display_settings.get("plane_tangent")
    if center_value is not None and tangent_value is not None:
        try:
            center = np.asarray(center_value, dtype=float).ravel()
            tangent = np.asarray(tangent_value, dtype=float).ravel()
            if center.size >= 3 and tangent.size >= 3:
                center_world = np.asarray(center[:3], dtype=float)
                tangent_world = np.asarray(tangent[:3], dtype=float)
                tangent_norm = float(np.linalg.norm(tangent_world))
                if tangent_norm > 1e-12:
                    tangent_world = tangent_world / tangent_norm
                    half_height = max(row.diameter / 2.0, 0.5)
                    world_points = np.vstack((center_world - tangent_world * half_height, center_world + tangent_world * half_height))
                    if project_fn is not None:
                        x_vals, y_vals = project_fn(world_points[:, 2], world_points[:, 1])
                        return np.column_stack((np.asarray(x_vals, dtype=float), np.asarray(y_vals, dtype=float)))
                    return _curve_points_yz_display(world_points)
            if center.size >= 2 and tangent.size >= 2:
                center = center[:2]
                tangent = tangent[:2]
                tangent_norm = float(np.linalg.norm(tangent))
                if tangent_norm > 1e-12:
                    tangent = tangent / tangent_norm
                    half_height = max(row.diameter / 2.0, 0.5)
                    p0 = center - tangent * half_height
                    p1 = center + tangent * half_height
                    return np.vstack((p0, p1))
        except Exception:
            pass
    override = overrides.get(row_index)
    if override is not None:
        center, along = override
        tangent = np.array([-along[1], along[0]], dtype=float)
        tangent /= max(np.linalg.norm(tangent), 1e-12)
        half_height = max(row.diameter / 2.0, 0.5)
        p0 = center - tangent * half_height
        p1 = center + tangent * half_height
        return np.vstack((p0, p1))
    half_height = max(row.diameter / 2.0, 0.5)
    center_z = z_pos + float(row.desp_z)
    if row.surface == "Image" and abs(float(row.thickness)) > 1e-12:
        center_z += float(row.thickness)
    center_y = float(row.desp_y)
    if project_fn is not None:
        x_vals, y_vals = project_fn(
            [center_z, center_z],
            [center_y - half_height, center_y + half_height],
        )
        return np.column_stack((np.asarray(x_vals, dtype=float), np.asarray(y_vals, dtype=float)))
    return np.array([[center_z, center_y - half_height], [center_z, center_y + half_height]], dtype=float)


def _build_row_surface_groups(rows: list, curve_map: dict[int, np.ndarray]) -> list[list[int]]:
    groups: list[list[int]] = []
    group: list[int] = []
    refractive_surface_types = {"Standard", "Thin Lens", "Grating", "Beam Splitter"}
    for row_index, row in enumerate(rows):
        advanced = getattr(row, "advanced", {}) or {}
        is_optical_solid = isinstance(advanced, dict) and advanced.get("Solid_3d_stl") not in (None, "", "None")
        if row_index in curve_map and row.surface in refractive_surface_types and not is_optical_solid:
            group.append(row_index)
            if str(row.glass).strip().upper() == "AIR":
                if len(group) >= 2:
                    groups.append(group[:])
                group = []
        else:
            if len(group) >= 2:
                groups.append(group[:])
            group = []
    if len(group) >= 2:
        groups.append(group[:])
    return groups


def _polyline_endpoints(polyline: np.ndarray) -> tuple[np.ndarray | None, np.ndarray | None]:
    pts = np.asarray(polyline, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 2:
        return None, None
    return pts[0].copy(), pts[-1].copy()


def _curve_group_aperture_axis(curve_a: np.ndarray, curve_b: np.ndarray) -> np.ndarray:
    axes: list[np.ndarray] = []
    for curve in (curve_a, curve_b):
        p0, p1 = _polyline_endpoints(curve)
        if p0 is None or p1 is None:
            continue
        axis = np.asarray(p1 - p0, dtype=float)
        norm = np.linalg.norm(axis)
        if norm <= 1e-12:
            continue
        axis /= norm
        if axes and float(np.dot(axis, axes[0])) < 0.0:
            axis *= -1.0
        axes.append(axis)
    if not axes:
        return np.array([0.0, 1.0], dtype=float)
    combined = np.sum(np.asarray(axes, dtype=float), axis=0)
    norm = np.linalg.norm(combined)
    if norm <= 1e-12:
        return axes[0]
    return combined / norm


def _curve_edge_points(curve: np.ndarray, aperture_axis: np.ndarray) -> tuple[np.ndarray | None, np.ndarray | None]:
    pts = np.asarray(curve, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 2:
        return None, None
    axis = np.asarray(aperture_axis, dtype=float)
    norm = np.linalg.norm(axis)
    if norm <= 1e-12:
        return _polyline_endpoints(pts)
    axis /= norm
    coord = pts @ axis
    low_idx = int(np.argmin(coord))
    high_idx = int(np.argmax(coord))
    return pts[low_idx].copy(), pts[high_idx].copy()
