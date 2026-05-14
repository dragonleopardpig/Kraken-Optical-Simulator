"""Validate physics-derived exit placement for chained CAD/STL solids."""

from __future__ import annotations

import copy
import importlib.util
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI import layout_editor as layout_editor_module
from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.nonseq_output_ports import (
    build_optical_solid_output_port_pose_overrides,
    row_z_positions,
)
from KrakenOS.UI.optical_solid_metadata import OPTICAL_SOLID_FACES_ADVANCED_ATTR, normalize_optical_solid_face_metadata
from KrakenOS.UI.saved_layout_plot import _rows_from_surface_specs, _snapshot_editor


@dataclass
class PhysicsExitPoseCheck:
    check: str
    ok: bool
    detail: str


def _load_dove_module():
    repo_root = Path(__file__).resolve().parents[2]
    layout_path = repo_root / "attachment" / "dove.py"
    spec = importlib.util.spec_from_file_location("kraken_ui_dove_layout", layout_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {layout_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows_without_explicit_output(module) -> list[dict[str, object]]:
    rows = copy.deepcopy(module.SURFACES)
    target = rows[7]
    advanced = dict(target.get("advanced", {}) or {})
    metadata = normalize_optical_solid_face_metadata(advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
    updated_faces: list[dict[str, object]] = []
    for face in list(metadata.get("faces", []) or []):
        record = dict(face)
        if str(record.get("port_role", "") or "").strip() == "Output Port":
            record["port_role"] = "Auto"
        updated_faces.append(record)
    metadata["faces"] = updated_faces
    advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
    target["advanced"] = advanced
    return rows


def _runtime_spec(row: dict[str, object]) -> dict[str, object]:
    spec = dict(row)
    spec.setdefault("rc", 0.0)
    spec.setdefault("k", 0.0)
    spec.setdefault("axicon", 0.0)
    spec.setdefault("diff_ord", 0.0)
    spec.setdefault("grating_d", 0.0)
    spec.setdefault("grating_angle", 0.0)
    spec.setdefault("in_diameter", 0.0)
    spec.setdefault("drawing", 1.0)
    spec.setdefault("extra_data", 0.0)
    spec.setdefault("uda", "None")
    spec.setdefault("tilt_x", 0.0)
    spec.setdefault("tilt_y", 0.0)
    spec.setdefault("tilt_z", 0.0)
    spec.setdefault("desp_x", 0.0)
    spec.setdefault("desp_y", 0.0)
    spec.setdefault("desp_z", 0.0)
    spec.setdefault("axis_move", 0.0)
    spec.setdefault("glass", "AIR")
    return spec


def _distance(a, b) -> float:
    return float(np.linalg.norm(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)))


def _finite_vector(values) -> bool:
    try:
        vector = np.asarray(values, dtype=float).reshape(3)
    except Exception:
        return False
    return bool(np.all(np.isfinite(vector)))


def _bounds_2d(points: np.ndarray) -> np.ndarray | None:
    array = np.asarray(points, dtype=float)
    if array.ndim != 2 or array.shape[1] < 2:
        return None
    finite = np.all(np.isfinite(array[:, :2]), axis=1)
    if not np.any(finite):
        return None
    xy = array[finite, :2]
    return np.asarray((np.min(xy[:, 0]), np.max(xy[:, 0]), np.min(xy[:, 1]), np.max(xy[:, 1])), dtype=float)


def _bounds_3d(points: np.ndarray) -> np.ndarray | None:
    array = np.asarray(points, dtype=float)
    if array.ndim != 2 or array.shape[1] < 3:
        return None
    finite = np.all(np.isfinite(array[:, :3]), axis=1)
    if not np.any(finite):
        return None
    xyz = array[finite, :3]
    return np.asarray(
        (
            np.min(xyz[:, 0]),
            np.max(xyz[:, 0]),
            np.min(xyz[:, 1]),
            np.max(xyz[:, 1]),
            np.min(xyz[:, 2]),
            np.max(xyz[:, 2]),
        ),
        dtype=float,
    )


def _runtime_stl_2d_bounds_match(system, module, row_indices: list[int]) -> tuple[bool, str]:
    rows = _rows_from_surface_specs(module.SURFACES)
    editor = _snapshot_editor(rows, module.SETTINGS)
    z_positions = row_z_positions(rows)
    details: list[str] = []
    for row_index in row_indices:
        polylines = editor._stl_mesh_layout_polylines(system, row_index, z_positions[row_index])
        if not polylines:
            return False, f"S{row_index}: no 2D STL polylines"
        layout_bounds = _bounds_2d(np.vstack([np.asarray(poly, dtype=float) for poly in polylines if len(poly) >= 2]))
        try:
            mesh_points = np.asarray(system.EEE[row_index].points, dtype=float)
        except Exception:
            mesh_points = np.empty((0, 3), dtype=float)
        if mesh_points.ndim != 2 or mesh_points.shape[1] < 3 or mesh_points.shape[0] < 2:
            return False, f"S{row_index}: no runtime trace mesh points"
        runtime_projected = np.column_stack((mesh_points[:, 2], mesh_points[:, 1]))
        runtime_bounds = _bounds_2d(runtime_projected)
        if layout_bounds is None or runtime_bounds is None:
            return False, f"S{row_index}: unavailable bounds"
        delta = float(np.max(np.abs(layout_bounds - runtime_bounds)))
        details.append(f"S{row_index}:delta={delta:.6g}")
        if delta > 0.5:
            return False, f"S{row_index}: layout_bounds={layout_bounds.tolist()}, runtime_bounds={runtime_bounds.tolist()}, delta={delta:.6g}"
    return True, ", ".join(details)


def _runtime_stl_3d_bounds_match(system, module, row_indices: list[int]) -> tuple[bool, str]:
    layout_editor_module._load_3d_backends()
    if layout_editor_module.pv is None:
        return False, "PyVista is unavailable"
    rows = _rows_from_surface_specs(module.SURFACES)
    editor = _snapshot_editor(rows, module.SETTINGS)
    mesh_items = editor._iter_3d_surface_meshes(system, include_reference_surfaces=True)
    display_mesh_by_row = {
        int(item.row_index): item.mesh
        for item in mesh_items
        if not bool(getattr(item, "is_body", False)) and int(getattr(item, "row_index", -1)) in row_indices
    }
    details: list[str] = []
    for row_index in row_indices:
        mesh = display_mesh_by_row.get(int(row_index))
        if mesh is None:
            return False, f"S{row_index}: no 3D display mesh"
        try:
            display_bounds = _bounds_3d(np.asarray(mesh.points, dtype=float))
            runtime_bounds = _bounds_3d(np.asarray(system.EEE[row_index].points, dtype=float))
        except Exception as exc:
            return False, f"S{row_index}: unavailable bounds: {exc}"
        if display_bounds is None or runtime_bounds is None:
            return False, f"S{row_index}: unavailable bounds"
        delta = float(np.max(np.abs(display_bounds - runtime_bounds)))
        details.append(f"S{row_index}:delta={delta:.6g}")
        if delta > 0.5:
            return False, f"S{row_index}: display_bounds={display_bounds.tolist()}, runtime_bounds={runtime_bounds.tolist()}, delta={delta:.6g}"
    return True, ", ".join(details)


def validate_optical_solid_physics_exit_pose() -> list[PhysicsExitPoseCheck]:
    module = _load_dove_module()
    rows = _rows_without_explicit_output(module)
    static_overrides = build_optical_solid_output_port_pose_overrides(rows)
    system = _build_system_from_specs([_runtime_spec(row) for row in rows])
    runtime_overrides = getattr(system, "_optical_solid_output_port_pose_overrides", {}) or {}
    fresh_overrides = build_optical_solid_output_port_pose_overrides(rows, system=system)
    image_pose = dict(runtime_overrides.get(8, {}) or {})
    fresh_image_pose = dict(fresh_overrides.get(8, {}) or {})
    static_image_pose = dict(static_overrides.get(8, {}) or {})
    runtime_center = np.asarray(image_pose.get("center", (np.nan, np.nan, np.nan)), dtype=float)
    runtime_normal = np.asarray(image_pose.get("normal", (np.nan, np.nan, np.nan)), dtype=float)
    fresh_center = np.asarray(fresh_image_pose.get("center", (np.nan, np.nan, np.nan)), dtype=float)
    fresh_normal = np.asarray(fresh_image_pose.get("normal", (np.nan, np.nan, np.nan)), dtype=float)
    static_center = np.asarray(static_image_pose.get("center", (np.nan, np.nan, np.nan)), dtype=float)
    stl_bounds_ok, stl_bounds_detail = _runtime_stl_2d_bounds_match(system, module, [5, 6, 7])
    stl_3d_bounds_ok, stl_3d_bounds_detail = _runtime_stl_3d_bounds_match(system, module, [5, 6, 7])
    return [
        PhysicsExitPoseCheck(
            "dove image follower uses traced exit when no explicit output port is authored",
            str(image_pose.get("frame_source", "") or "").strip() == "physics_exit_trace",
            f"frame_source={image_pose.get('frame_source')!r}",
        ),
        PhysicsExitPoseCheck(
            "stored runtime image pose matches a fresh settled recomputation",
            bool(
                np.allclose(runtime_center, fresh_center, atol=1e-6)
                and np.allclose(runtime_normal, fresh_normal, atol=1e-6)
            ),
            (
                f"runtime_center={runtime_center.tolist()}, fresh_center={fresh_center.tolist()}, "
                f"runtime_normal={runtime_normal.tolist()}, fresh_normal={fresh_normal.tolist()}"
            ),
        ),
        PhysicsExitPoseCheck(
            "runtime image pose replaces unavailable or stale static inferred-output fallback",
            bool(
                _finite_vector(runtime_center)
                and (
                    not _finite_vector(static_center)
                    or _distance(runtime_center, static_center) > 1.0
                )
            ),
            (
                f"runtime_center={runtime_center.tolist()}, static_center={static_center.tolist()}, "
                f"distance_mm={_distance(runtime_center, static_center) if _finite_vector(static_center) else 'unavailable'}"
            ),
        ),
        PhysicsExitPoseCheck(
            "2D STL silhouettes use the same runtime trace meshes as non-sequential ray tracing",
            stl_bounds_ok,
            stl_bounds_detail,
        ),
        PhysicsExitPoseCheck(
            "3D STL meshes use the same runtime trace meshes as non-sequential ray tracing",
            stl_3d_bounds_ok,
            stl_3d_bounds_detail,
        ),
    ]


def _print_table(checks: list[PhysicsExitPoseCheck]) -> None:
    print("KrakenOS optical-solid physics-exit placement validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    checks = validate_optical_solid_physics_exit_pose()
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
