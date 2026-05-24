"""Generate and validate a five-penta-prism 3D cascade.

This guard exists because a penta prism is not fully placed by aligning only
the entrance face normal. The roll around the incoming beam axis determines
which way the prism turns the beam. Each stage therefore uses two physical
constraints:

1. vendor face F005 is the entrance face and its outward normal points upstream;
2. vendor face F006 is the exit face and its outward normal is the requested
   downstream optical axis.

The mirror faces are the vendor coated faces F004 and F003. The validator fails
if any ray reaches a different face sequence, so it cannot hide a bad roll by
assigning whichever faces the wrong ray happened to hit.

Run:

    python -m KrakenOS.UI.validate_five_penta_prism_cascade
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI import optical_solid_metadata
from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
    PROJECT_ROOT,
    _configure_base_editor,
    _open_3d_inspector,
    _refresh,
    _save_vtk_snapshot,
)
from KrakenOS.UI.capture_vendor_prism_case_study_screenshots import (
    PRISM_42779_STEP,
    _mesh_vendor_prism,
    _metadata_for_mesh,
)
from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    KrakenLayoutEditor,
    SurfaceRow,
    _dotted_axis_records_from_ray_path,
    _short_error_message,
)
from KrakenOS.UI.scene_geometry import ray_path_terminal_status_from_events
from KrakenOS.UI.validate_penta_mirror_3d_cascade import (
    PENTA_ENTRANCE_FACE,
    PENTA_MIRROR_FACES,
    _central_path,
    _configure_collimated_bundle,
    _event_action,
    _event_face_id,
    _surface_events,
    _surface_sequence,
    _terminal_direction,
)


PENTA_COUNT = 5
PENTA_EXIT_FACE = "F006"
PENTA_FACE_SEQUENCE = (PENTA_ENTRANCE_FACE, "F003", "F004", PENTA_EXIT_FACE)
PENTA_ACTION_SEQUENCE = ("refraction", "reflection", "reflection", "refraction")
PENTA_PATH_DIRECTIONS = (
    (0.0, 0.0, 1.0),   # input beam
    (0.0, -1.0, 0.0),  # prism 1 output
    (1.0, 0.0, 0.0),   # prism 2 output
    (0.0, 0.0, 1.0),   # prism 3 output
    (0.0, 1.0, 0.0),   # prism 4 output
    (-1.0, 0.0, 0.0),  # prism 5 output
)
FIRST_ENTRANCE_POINT_MM = np.asarray((0.0, 0.0, 45.0), dtype=float)
NEXT_PRISM_SPACING_MM = 115.0
DEFAULT_LAYOUT_PATH = PROJECT_ROOT / "attachment" / "five_penta_prism_cascade.py"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "attachment" / "five_penta_prism_cascade"
DEFAULT_MESH_CACHE_DIR = DEFAULT_OUTPUT_DIR / "meshes"


def _unit(value: object) -> np.ndarray:
    vector = np.asarray(value, dtype=float).reshape(-1)[:3]
    if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
        raise ValueError(f"Expected finite 3-vector, got {value!r}.")
    norm = float(np.linalg.norm(vector[:3]))
    if norm <= 1e-12:
        raise ValueError(f"Expected non-zero 3-vector, got {value!r}.")
    return vector[:3] / norm


def _vector_json(value: object) -> list[float]:
    return [round(float(component), 9) for component in _unit(value)]


def _point_json(value: object) -> list[float]:
    point = np.asarray(value, dtype=float).reshape(-1)[:3]
    if point.size < 3 or not np.all(np.isfinite(point[:3])):
        return []
    return [round(float(component), 9) for component in point[:3]]


def _face_record(metadata: dict[str, object], face_id: str) -> dict[str, object]:
    for face in list(metadata.get("faces", []) or []):
        if isinstance(face, dict) and str(face.get("face_id", "") or "").strip() == face_id:
            return optical_solid_metadata.normalize_optical_solid_face_record(face)
    raise RuntimeError(f"Vendor penta metadata does not contain face {face_id}.")


def _basis_from_pair(primary: np.ndarray, secondary: np.ndarray) -> np.ndarray:
    e1 = _unit(primary)
    projected = np.asarray(secondary, dtype=float).reshape(3) - e1 * float(np.dot(secondary, e1))
    e2 = _unit(projected)
    e3 = _unit(np.cross(e1, e2))
    return np.column_stack((e1, e2, e3))


def _rotation_from_face_pair(
    *,
    local_input_outward: np.ndarray,
    local_output_outward: np.ndarray,
    incoming_direction: np.ndarray,
    outgoing_direction: np.ndarray,
) -> np.ndarray:
    incoming = _unit(incoming_direction)
    outgoing = _unit(outgoing_direction)
    if abs(float(np.dot(incoming, outgoing))) > 1e-8:
        raise ValueError(f"Penta input/output directions must be perpendicular: {incoming} -> {outgoing}.")
    local_basis = _basis_from_pair(_unit(local_input_outward), _unit(local_output_outward))
    target_basis = _basis_from_pair(-incoming, outgoing)
    rotation = target_basis @ local_basis.T
    if float(np.linalg.det(rotation)) < 0.0:
        raise RuntimeError("Solved penta rotation is left-handed.")
    return rotation


def _prepare_penta_asset() -> tuple[Path, dict[str, object]]:
    if not PRISM_42779_STEP.exists():
        raise RuntimeError(f"Expected STEP fixture: {PRISM_42779_STEP}")
    DEFAULT_MESH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    mesh_path, _source_path, _source_format, _diagnostics = _mesh_vendor_prism(DEFAULT_MESH_CACHE_DIR)
    metadata = _metadata_for_mesh(mesh_path)
    for face in list(metadata.get("faces", []) or []):
        if not isinstance(face, dict):
            continue
        if str(face.get("face_id", "") or "").strip() in set(PENTA_FACE_SEQUENCE):
            # This diagnostic places every prism explicitly. Do not let the
            # legacy output-port follower override the solved row poses.
            face["port_role"] = optical_solid_metadata.OPTICAL_SOLID_FACE_PORT_INTERACTION
    return mesh_path, metadata


def _z_station_for_insert(rows: list[SurfaceRow], insert_at: int) -> float:
    return float(sum(float(getattr(row, "thickness", 0.0) or 0.0) for row in rows[:insert_at]))


def _solve_penta_row_pose(
    metadata: dict[str, object],
    *,
    incoming_direction: np.ndarray,
    outgoing_direction: np.ndarray,
    entrance_point_world: np.ndarray,
    z_station: float,
) -> dict[str, object]:
    input_face = _face_record(metadata, PENTA_ENTRANCE_FACE)
    output_face = _face_record(metadata, PENTA_EXIT_FACE)
    rotation = _rotation_from_face_pair(
        local_input_outward=optical_solid_metadata.optical_solid_face_local_normal(input_face),
        local_output_outward=optical_solid_metadata.optical_solid_face_local_normal(output_face),
        incoming_direction=incoming_direction,
        outgoing_direction=outgoing_direction,
    )
    anchor_local = optical_solid_metadata.optical_solid_face_local_anchor_point(input_face)
    center_world = np.asarray(entrance_point_world, dtype=float).reshape(3) - (rotation @ anchor_local)
    tilts = optical_solid_metadata.kraken_tilts_from_rotation_matrix(rotation)
    desp = (float(center_world[0]), float(center_world[1]), float(center_world[2] - float(z_station)))
    return {
        "rotation": rotation,
        "tilts": tuple(float(value) for value in tilts),
        "desp": desp,
        "center_world": center_world,
        "entrance_point_world": np.asarray(entrance_point_world, dtype=float).reshape(3),
    }


def _make_penta_row(
    *,
    prism_number: int,
    mesh_path: Path,
    metadata: dict[str, object],
    pose: dict[str, object],
) -> SurfaceRow:
    tilt_x, tilt_y, tilt_z = (float(value) for value in pose["tilts"])
    desp_x, desp_y, desp_z = (float(value) for value in pose["desp"])
    return SurfaceRow(
        surface="Solid 3D STL",
        element=f"Penta {prism_number}",
        name=f"Penta prism {prism_number}",
        thickness=0.0,
        diameter=45.0,
        drawing=1.0,
        glass="BK7",
        axis_move=0.0,
        tilt_x=tilt_x,
        tilt_y=tilt_y,
        tilt_z=tilt_z,
        desp_x=desp_x,
        desp_y=desp_y,
        desp_z=desp_z,
        advanced={
            "Solid_3d_stl": str(mesh_path),
            "OpticalSolidSourcePath": str(PRISM_42779_STEP),
            "OpticalSolidSourceFormat": "STEP",
            OPTICAL_SOLID_FACES_ADVANCED_ATTR: copy.deepcopy(metadata),
            "Note": (
                "Five-penta cascade diagnostic row. F005 is constrained as the entrance face, "
                "F006 as the intended exit axis, and vendor coated faces F004/F003 are Full Reflecting."
            ),
        },
    )


def _trace_scene(app: KrakenLayoutEditor):
    return app._build_preview_system_rays_bundle(sampling_mode="world_envelope", update_state=False)


def _axis_from_central_exit(scene_bundle: object, expected_direction: np.ndarray, prism_number: int) -> tuple[np.ndarray, np.ndarray]:
    ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
    central = _central_path(ray_paths)
    points = np.asarray(getattr(central, "points_world", ()), dtype=float)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
        raise RuntimeError(f"Prism {prism_number} central path has no usable exit segment.")
    actual_direction = _terminal_direction(central)
    expected = _unit(expected_direction)
    if float(np.dot(actual_direction, expected)) < 0.999:
        raise RuntimeError(
            f"Prism {prism_number} output direction does not match the requested penta roll: "
            f"actual={actual_direction}, expected={expected}."
        )
    exit_point = points[-2, :3]
    return exit_point + expected * float(NEXT_PRISM_SPACING_MM), actual_direction


def _validate_collimated_launch(scene_bundle: object) -> dict[str, object]:
    ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
    directions: list[np.ndarray] = []
    origins: list[np.ndarray] = []
    for path in ray_paths:
        points = np.asarray(getattr(path, "points_world", ()), dtype=float)
        if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
            continue
        segment = points[1, :3] - points[0, :3]
        norm = float(np.linalg.norm(segment))
        if norm <= 1e-12:
            continue
        directions.append(segment / norm)
        origins.append(points[0, :3])
    if not directions:
        raise RuntimeError("No usable launch segments were available for collimation validation.")
    reference = _unit(np.mean(np.asarray(directions, dtype=float), axis=0))
    max_angle_error = max(
        float(np.rad2deg(np.arccos(np.clip(float(np.dot(direction, reference)), -1.0, 1.0))))
        for direction in directions
    )
    if max_angle_error > 1e-5:
        raise RuntimeError(f"Launch bundle is not collimated; max angular spread is {max_angle_error:.6g} deg.")
    origin_radius = 0.0
    if origins:
        origin_points = np.asarray(origins, dtype=float)
        center = np.mean(origin_points[:, :3], axis=0)
        origin_radius = float(np.max(np.linalg.norm(origin_points[:, :3] - center[:3], axis=1)))
    return {
        "ray_count": len(directions),
        "mean_direction": _vector_json(reference),
        "max_angle_error_deg": round(float(max_angle_error), 12),
        "origin_radius_mm": round(float(origin_radius), 9),
    }


def _snapshot(
    app: KrakenLayoutEditor,
    inspector,
    stage_snapshot_dir: Path | None,
    filename: str,
) -> str | None:
    if inspector is None or stage_snapshot_dir is None:
        return None
    _refresh(inspector, reset_camera=True)
    inspector.set_camera_preset("iso")
    return str(_save_vtk_snapshot(inspector, stage_snapshot_dir / filename))


def _mesh_triangles(mesh: object) -> np.ndarray:
    try:
        surface = mesh.extract_surface(algorithm="dataset_surface")
    except Exception:
        surface = mesh
    try:
        points = np.asarray(surface.points, dtype=float)
        faces = np.asarray(surface.faces, dtype=np.int64).ravel()
    except Exception:
        return np.empty((0, 3, 3), dtype=float)
    if points.ndim != 2 or points.shape[0] < 3 or points.shape[1] < 3 or faces.size < 4:
        return np.empty((0, 3, 3), dtype=float)
    triangles: list[np.ndarray] = []
    cursor = 0
    while cursor < faces.size:
        count = int(faces[cursor])
        cursor += 1
        if count < 3 or cursor + count > faces.size:
            break
        indices = faces[cursor : cursor + count]
        cursor += count
        if np.any(indices < 0) or np.any(indices >= points.shape[0]):
            continue
        for offset in range(1, count - 1):
            triangles.append(points[[indices[0], indices[offset], indices[offset + 1]], :3])
    if not triangles:
        return np.empty((0, 3, 3), dtype=float)
    return np.asarray(triangles, dtype=float)


def _point_triangle_distance_sq(point: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    # Real-Time Collision Detection, Christer Ericson, closest point on triangle.
    ab = b - a
    ac = c - a
    ap = point - a
    d1 = float(np.dot(ab, ap))
    d2 = float(np.dot(ac, ap))
    if d1 <= 0.0 and d2 <= 0.0:
        return float(np.dot(ap, ap))

    bp = point - b
    d3 = float(np.dot(ab, bp))
    d4 = float(np.dot(ac, bp))
    if d3 >= 0.0 and d4 <= d3:
        return float(np.dot(bp, bp))

    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        closest = a + v * ab
        delta = point - closest
        return float(np.dot(delta, delta))

    cp = point - c
    d5 = float(np.dot(ab, cp))
    d6 = float(np.dot(ac, cp))
    if d6 >= 0.0 and d5 <= d6:
        return float(np.dot(cp, cp))

    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        closest = a + w * ac
        delta = point - closest
        return float(np.dot(delta, delta))

    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        closest = b + w * (c - b)
        delta = point - closest
        return float(np.dot(delta, delta))

    denom = va + vb + vc
    if abs(denom) <= 1.0e-18:
        return min(float(np.dot(ap, ap)), float(np.dot(bp, bp)), float(np.dot(cp, cp)))
    v = vb / denom
    w = vc / denom
    closest = a + ab * v + ac * w
    delta = point - closest
    return float(np.dot(delta, delta))


def _point_to_mesh_distance(point: np.ndarray, triangles: np.ndarray) -> float:
    if triangles.ndim != 3 or triangles.shape[0] < 1:
        return float("inf")
    p = np.asarray(point, dtype=float).reshape(-1)[:3]
    if p.size < 3 or not np.all(np.isfinite(p[:3])):
        return float("inf")
    best_sq = float("inf")
    for triangle in triangles:
        if not np.all(np.isfinite(triangle)):
            continue
        distance_sq = _point_triangle_distance_sq(p[:3], triangle[0], triangle[1], triangle[2])
        if distance_sq < best_sq:
            best_sq = distance_sq
    return math.sqrt(best_sq) if np.isfinite(best_sq) else float("inf")


def _validate_event_mesh_congruence(
    app: KrakenLayoutEditor,
    system: object,
    scene_bundle: object,
    row_indices: list[int],
    *,
    max_allowed_distance_mm: float = 0.15,
) -> dict[str, object]:
    row_set = {int(index) for index in row_indices}
    mesh_by_row: dict[int, np.ndarray] = {}
    for mesh_item in app._scene_surface_meshes(system, scene_bundle, include_reference_surfaces=False):
        try:
            row_index = int(getattr(mesh_item, "row_index"))
        except Exception:
            continue
        if row_index not in row_set:
            continue
        triangles = _mesh_triangles(getattr(mesh_item, "mesh", None))
        if triangles.shape[0] > 0:
            mesh_by_row[row_index] = triangles

    missing = sorted(row_set.difference(mesh_by_row))
    if missing:
        raise RuntimeError(f"Open 3D display mesh missing for traced penta rows: {missing}.")

    checked = 0
    worst: dict[str, object] = {"distance_mm": 0.0}
    for path in list(getattr(scene_bundle, "ray_paths", []) or []):
        for event in _surface_events(path):
            try:
                row_index = int(getattr(event, "surface_id", -1))
            except Exception:
                continue
            if row_index not in row_set:
                continue
            point = np.asarray(getattr(event, "point_world", ()), dtype=float).reshape(-1)[:3]
            if point.size < 3 or not np.all(np.isfinite(point[:3])):
                raise RuntimeError(f"Ray event has no finite point for row {row_index}.")
            distance = _point_to_mesh_distance(point[:3], mesh_by_row[row_index])
            checked += 1
            if distance > float(worst.get("distance_mm", 0.0) or 0.0):
                worst = {
                    "distance_mm": round(float(distance), 9),
                    "row_index": row_index,
                    "ray_index": int(getattr(path, "ray_index", -1) or -1),
                    "step": int(getattr(event, "step", -1) or -1),
                    "face_id": _event_face_id(event),
                    "action": _event_action(event),
                    "point_world": _point_json(point[:3]),
                }
    if checked <= 0:
        raise RuntimeError("No penta ray/surface events were available for display-mesh congruence validation.")
    if float(worst.get("distance_mm", 0.0) or 0.0) > max_allowed_distance_mm:
        raise RuntimeError(
            "Open 3D rendered mesh is not congruent with traced ray events; "
            f"worst={worst}, allowed={max_allowed_distance_mm} mm."
        )
    return {
        "checked_events": checked,
        "max_allowed_distance_mm": float(max_allowed_distance_mm),
        "max_event_to_display_mesh_distance_mm": worst["distance_mm"],
        "worst_event": worst,
    }


def _bounds_for_ray_path(path: object) -> np.ndarray:
    points = np.asarray(getattr(path, "points_world", ()), dtype=float)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
        return np.asarray((-10.0, 10.0, -10.0, 10.0, 0.0, 100.0), dtype=float)
    finite = np.all(np.isfinite(points[:, :3]), axis=1)
    if not np.any(finite):
        return np.asarray((-10.0, 10.0, -10.0, 10.0, 0.0, 100.0), dtype=float)
    pts = points[finite, :3]
    mins = np.min(pts, axis=0)
    maxs = np.max(pts, axis=0)
    pad = max(float(np.max(maxs - mins)) * 0.05, 5.0)
    return np.asarray(
        (
            float(mins[0] - pad),
            float(maxs[0] + pad),
            float(mins[1] - pad),
            float(maxs[1] + pad),
            float(mins[2] - pad),
            float(maxs[2] + pad),
        ),
        dtype=float,
    )


def _validate_exit_axis_records(scene_bundle: object, *, expected_exit_axes: int) -> dict[str, object]:
    ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
    central = _central_path(ray_paths)
    records = _dotted_axis_records_from_ray_path(
        central,
        _bounds_for_ray_path(central),
        max_segments=max(int(expected_exit_axes) + 2, 8),
    )
    exit_records = [
        record
        for record in records
        if str(record.get("axis_role", "") or "") in {"between_surfaces", "post_surface"}
    ]
    internal_records = [
        record
        for record in records
        if str(record.get("axis_role", "") or "") == "between_surfaces"
        and record.get("from_surface_id") == record.get("to_surface_id")
    ]
    if internal_records:
        raise RuntimeError(f"Optical-axis records include internal same-row segments: {internal_records!r}.")
    if len(exit_records) != int(expected_exit_axes):
        raise RuntimeError(
            f"Expected {expected_exit_axes} external penta exit-axis records, got {len(exit_records)}: "
            f"{[(record.get('axis_role'), record.get('from_surface_id'), record.get('to_surface_id'), record.get('from_mesh_face_id'), record.get('to_mesh_face_id')) for record in exit_records]}"
        )
    return {
        "expected_exit_axes": int(expected_exit_axes),
        "exit_axis_count": len(exit_records),
        "axis_roles": [str(record.get("axis_role", "") or "") for record in exit_records],
        "axis_segments": [
            {
                "axis_label": str(record.get("axis_label", "") or ""),
                "axis_role": str(record.get("axis_role", "") or ""),
                "from_surface_id": record.get("from_surface_id"),
                "to_surface_id": record.get("to_surface_id"),
                "from_mesh_face_id": str(record.get("from_mesh_face_id", "") or ""),
                "to_mesh_face_id": str(record.get("to_mesh_face_id", "") or ""),
                "segment_direction": _vector_json(record.get("segment_direction", ())),
            }
            for record in exit_records
        ],
    }


def _validate_trace(scene_bundle: object, row_indices: list[int], *, final_expected_direction: np.ndarray) -> dict[str, object]:
    ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
    if not ray_paths:
        raise RuntimeError("Cascade trace produced no ray paths.")
    expected_faces = tuple(PENTA_FACE_SEQUENCE) * len(row_indices)
    expected_actions = tuple(PENTA_ACTION_SEQUENCE) * len(row_indices)
    expected_surfaces: list[int] = []
    for row_index in row_indices:
        expected_surfaces.extend([int(row_index)] * len(PENTA_FACE_SEQUENCE))

    sequences = Counter(_surface_sequence(path) for path in ray_paths)
    event_counts = Counter(
        (_event_face_id(event), _event_action(event))
        for path in ray_paths
        for event in _surface_events(path)
    )
    terminal_counts = Counter(
        str(ray_path_terminal_status_from_events(path) or "unknown").strip() or "unknown"
        for path in ray_paths
    )

    for path in ray_paths:
        events = _surface_events(path)
        faces = tuple(_event_face_id(event) for event in events)
        actions = tuple(_event_action(event) for event in events)
        surfaces = tuple(int(getattr(event, "surface_id", -1)) for event in events)
        if faces != expected_faces or actions != expected_actions or surfaces != tuple(expected_surfaces):
            raise RuntimeError(
                "Expected every ray to follow the same five-penta vendor path; "
                f"faces={faces}, actions={actions}, surfaces={surfaces}, "
                f"sequence={' -> '.join(_surface_sequence(path))}."
            )

    central = _central_path(ray_paths)
    final_direction = _terminal_direction(central)
    if float(np.dot(final_direction, _unit(final_expected_direction))) < 0.999:
        raise RuntimeError(f"Final beam direction mismatch: actual={final_direction}, expected={final_expected_direction}.")

    return {
        "ray_paths": len(ray_paths),
        "central_terminal_direction": _vector_json(final_direction),
        "row_indices": [int(index) for index in row_indices],
        "terminal_counts": dict(sorted(terminal_counts.items())),
        "surface_sequence_counts": {" -> ".join(sequence): count for sequence, count in sorted(sequences.items())},
        "surface_event_counts": {f"{face}:{action}": count for (face, action), count in sorted(event_counts.items())},
    }


def build_case_editor(stage_snapshot_dir: Path | None = None) -> tuple[KrakenLayoutEditor, dict[str, Any]]:
    source_mesh_path, source_metadata = _prepare_penta_asset()
    app = KrakenLayoutEditor(headless=True)
    if stage_snapshot_dir is not None:
        stage_snapshot_dir = stage_snapshot_dir.resolve()
        stage_snapshot_dir.mkdir(parents=True, exist_ok=True)
    _configure_base_editor(app)
    _configure_collimated_bundle(app)
    app.source_radius_var.set("4.0")
    app.ray_count_var.set("13")
    app.source_cone_angle_var.set("0.0")
    app._invalidate_preview_scene_trace()

    stages: list[dict[str, object]] = []
    row_indices: list[int] = []
    entrance_point = FIRST_ENTRANCE_POINT_MM.copy()
    scene_bundle = None
    directions = [_unit(direction) for direction in PENTA_PATH_DIRECTIONS]
    inspector = _open_3d_inspector(app) if stage_snapshot_dir is not None else None
    for index in range(PENTA_COUNT):
        prism_number = index + 1
        insert_at = max(1, len(app.rows) - 1)
        z_station = _z_station_for_insert(app.rows, insert_at)
        incoming = directions[index]
        outgoing = directions[index + 1]
        pose = _solve_penta_row_pose(
            source_metadata,
            incoming_direction=incoming,
            outgoing_direction=outgoing,
            entrance_point_world=entrance_point,
            z_station=z_station,
        )
        row = _make_penta_row(prism_number=prism_number, mesh_path=source_mesh_path, metadata=source_metadata, pose=pose)
        app.rows.insert(insert_at, row)
        app._normalize_special_rows()
        app._sync_table()
        app._select_table_row(insert_at)
        app._invalidate_preview_scene_trace()

        _system, _rays, scene_bundle = _trace_scene(app)
        ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
        if not ray_paths:
            raise RuntimeError(f"Trace after prism {prism_number} produced no ray paths.")
        central = _central_path(ray_paths)
        prefix_validation = _validate_trace(scene_bundle, row_indices + [insert_at], final_expected_direction=outgoing)
        mesh_congruence = _validate_event_mesh_congruence(app, _system, scene_bundle, row_indices + [insert_at])
        exit_axis_validation = _validate_exit_axis_records(scene_bundle, expected_exit_axes=prism_number)
        stage: dict[str, object] = {
            "prism": prism_number,
            "row_index": insert_at,
            "z_station": round(float(z_station), 9),
            "incoming_direction": _vector_json(incoming),
            "requested_outgoing_direction": _vector_json(outgoing),
            "entrance_point_world": _point_json(entrance_point),
            "center_world": _point_json(pose["center_world"]),
            "tilts_deg": [round(float(value), 9) for value in pose["tilts"]],
            "desp": [round(float(value), 9) for value in pose["desp"]],
            "actions": [
                {
                    "action": "place_optical_step_reference",
                    "constraints": {
                        "entrance_face": PENTA_ENTRANCE_FACE,
                        "exit_face": PENTA_EXIT_FACE,
                        "mirror_faces": list(PENTA_MIRROR_FACES),
                    },
                },
                {"action": "trace_after_placement", "row_index": insert_at},
            ],
            "launch_validation": _validate_collimated_launch(scene_bundle),
            "ray_paths_after_trace": len(ray_paths),
            "central_terminal_direction": _vector_json(_terminal_direction(central)),
            "central_sequence": " -> ".join(_surface_sequence(central)),
            "prefix_validation": prefix_validation,
            "display_mesh_congruence": mesh_congruence,
            "exit_axis_validation": exit_axis_validation,
            "snapshots": {},
        }
        snapshot_path = _snapshot(
            app,
            inspector,
            stage_snapshot_dir,
            f"five_penta_stage_{prism_number:02d}_after_trace.png",
        )
        if snapshot_path:
            stage["snapshots"]["trace"] = snapshot_path
        stages.append(stage)
        row_indices.append(insert_at)
        if index < PENTA_COUNT - 1:
            entrance_point, _actual = _axis_from_central_exit(scene_bundle, outgoing, prism_number)

    final = _validate_trace(scene_bundle, row_indices, final_expected_direction=directions[-1])
    final["display_mesh_congruence"] = _validate_event_mesh_congruence(app, _system, scene_bundle, row_indices)
    final["exit_axis_validation"] = _validate_exit_axis_records(scene_bundle, expected_exit_axes=len(row_indices))
    report = {
        "ok": True,
        "penta_count": PENTA_COUNT,
        "source_step": str(PRISM_42779_STEP),
        "source_mesh": str(source_mesh_path),
        "entrance_face": PENTA_ENTRANCE_FACE,
        "exit_face": PENTA_EXIT_FACE,
        "mirror_faces": list(PENTA_MIRROR_FACES),
        "placement_mode": "deterministic two-face reference placement: F005 upstream, F006 requested output-axis roll",
        "source_validation": {
            "source_model": str(app.source_model_var.get()),
            "source_radius": str(app.source_radius_var.get()),
            "source_cone_angle": str(app.source_cone_angle_var.get()),
            "ray_count": str(app.ray_count_var.get()),
        },
        "path_directions": [_vector_json(direction) for direction in directions],
        "stage_count": len(stages),
        "stages": stages,
        "final": final,
    }
    return app, report


def run_case() -> dict[str, Any]:
    app, report = build_case_editor()
    try:
        return report
    finally:
        app.destroy()


def save_case_layout(path: Path = DEFAULT_LAYOUT_PATH) -> tuple[Path, dict[str, Any]]:
    app, report = build_case_editor()
    try:
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        app.current_layout_file = path
        app._write_layout_file(path)
        report["layout_path"] = str(path)
        return path, report
    finally:
        app.destroy()


def capture_case(output_dir: Path = DEFAULT_OUTPUT_DIR, *, layout_path: Path | None = DEFAULT_LAYOUT_PATH) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    app, report = build_case_editor(stage_snapshot_dir=output_dir)
    try:
        if layout_path is not None:
            layout_path = layout_path.resolve()
            layout_path.parent.mkdir(parents=True, exist_ok=True)
            app.current_layout_file = layout_path
            app._write_layout_file(layout_path)
            report["layout_path"] = str(layout_path)
        inspector = _open_3d_inspector(app)
        _refresh(inspector, reset_camera=True)
        snapshots: dict[str, str] = {}
        for preset, filename in (
            ("iso", "five_penta_final_iso.png"),
            ("zy", "five_penta_final_yz.png"),
            ("xy", "five_penta_final_xy.png"),
            ("xz", "five_penta_final_xz.png"),
        ):
            inspector.set_camera_preset(preset)
            snapshot_path = _save_vtk_snapshot(inspector, output_dir / filename)
            snapshots[preset] = str(snapshot_path)
        report["snapshots"] = snapshots
        report_path = output_dir / "five_penta_prism_cascade_report.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report["report_path"] = str(report_path)
        return report
    finally:
        try:
            if app._three_d_inspector is not None:
                app._three_d_inspector._on_close()
        except Exception:
            pass
        app.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=None, help="Optional JSON report path.")
    parser.add_argument("--layout", type=Path, default=None, help="Optional normal KrakenOS .py layout output path.")
    parser.add_argument("--capture-dir", type=Path, default=None, help="Optional Open 3D snapshot/report output directory.")
    args = parser.parse_args()
    try:
        if args.capture_dir is not None:
            report = capture_case(args.capture_dir, layout_path=args.layout or DEFAULT_LAYOUT_PATH)
        elif args.layout is not None:
            _layout_path, report = save_case_layout(args.layout)
        else:
            report = run_case()
    except Exception as exc:
        report = {"ok": False, "error": _short_error_message(exc)}
        if args.report is not None:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
