"""Validate physics-derived exit placement for chained CAD/STL solids."""

from __future__ import annotations

import copy
import importlib.util
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import KrakenOS as Kos

from KrakenOS.UI import layout_editor as layout_editor_module
from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.nonseq_output_ports import (
    build_optical_solid_output_port_pose_overrides,
    row_z_positions,
)
from KrakenOS.UI.optical_solid_metadata import OPTICAL_SOLID_FACES_ADVANCED_ATTR, normalize_optical_solid_face_metadata
from KrakenOS.UI.saved_layout_plot import _rows_from_surface_specs, _snapshot_editor
from KrakenOS.UI.scene_projector import SceneProjector2D


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


def _runtime_3d_bounds_match(system, module, row_indices: list[int]) -> tuple[bool, str]:
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


def _trace_and_project_scene(system, row_specs: list[dict[str, object]], settings: dict[str, object], *, sampling_mode: str):
    rows = _rows_from_surface_specs(row_specs)
    editor = _snapshot_editor(rows, settings)
    rays = Kos.raykeeper(system)
    max_radius = max((max(float(row.diameter) / 2.0, 0.5) for row in rows), default=1.0)
    editor._trace_preview_rays(
        system,
        rays,
        editor._current_wavelength(),
        max_radius,
        allow_full_pupil=False,
        sampling_mode=sampling_mode,
    )
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    projected = SceneProjector2D(editor._current_display_orientation()).project_bundle(bundle)
    return editor, rays, bundle, projected


def _unique_endpoint_count(projected) -> int:
    endpoints: set[tuple[float, float]] = set()
    for ray in getattr(projected, "rays", []) or []:
        points = np.asarray(ray.points_2d, dtype=float)
        if points.ndim != 2 or points.shape[0] < 1:
            continue
        point = points[-1]
        if np.all(np.isfinite(point[:2])):
            endpoints.add((round(float(point[0]), 3), round(float(point[1]), 3)))
    return len(endpoints)


def _scene_trace_consistency_checks(system, row_specs: list[dict[str, object]], settings: dict[str, object]) -> list[PhysicsExitPoseCheck]:
    checks: list[PhysicsExitPoseCheck] = []
    expected_count = max(1, int(round(float(settings.get("ray_count", 1)))))
    final_surface = max(0, len(row_specs) - 1)
    try:
        _editor, _rays, bundle, projected = _trace_and_project_scene(
            system,
            row_specs,
            settings,
            sampling_mode="display_slice",
        )
        ray_count = len(getattr(bundle, "ray_paths", []) or [])
        projected_count = len(getattr(projected, "rays", []) or [])
        ray_paths = list(getattr(bundle, "ray_paths", []) or [])
        reached_count = sum(1 for ray in ray_paths if bool(ray.reaches_image))
        endpoint_count = _unique_endpoint_count(projected)
        checks.append(
            PhysicsExitPoseCheck(
                "Dove 2D projected scene preserves the full through-going ray fan",
                bool(
                    ray_count >= expected_count
                    and projected_count == ray_count
                    and reached_count == ray_count
                    and endpoint_count >= max(3, min(expected_count, 8))
                ),
                (
                    f"rays={ray_count}, projected={projected_count}, reached_image={reached_count}, "
                    f"unique_detector_endpoints={endpoint_count}, final_surface=S{final_surface}"
                ),
            )
        )
        exits_last_solid = 0
        last_solid_hits = 0
        example_sequence: list[int] = []
        for ray in ray_paths:
            surface_ids = np.asarray(getattr(ray, "surface_ids", []), dtype=int).ravel()
            if surface_ids.size:
                example_sequence = [int(value) for value in surface_ids.tolist()]
            if surface_ids.size >= 2 and int(surface_ids[-2]) == final_surface - 1 and int(surface_ids[-1]) == final_surface:
                exits_last_solid += 1
            last_solid_hits += int(np.count_nonzero(surface_ids == final_surface - 1))
        checks.append(
            PhysicsExitPoseCheck(
                "Dove rays exit the final optical solid before reaching Image",
                bool(ray_count > 0 and exits_last_solid == ray_count and last_solid_hits >= 4 * ray_count),
                (
                    f"rays={ray_count}, exited_S{final_surface - 1}_then_S{final_surface}={exits_last_solid}, "
                    f"S{final_surface - 1}_hits={last_solid_hits}, example_sequence={example_sequence}"
                ),
            )
        )
    except Exception as exc:
        checks.append(
            PhysicsExitPoseCheck(
                "Dove 2D projected scene preserves the full through-going ray fan",
                False,
                f"trace/project failed: {exc}",
            )
        )
        checks.append(
            PhysicsExitPoseCheck(
                "Dove rays exit the final optical solid before reaching Image",
                False,
                f"trace/project failed: {exc}",
            )
        )
    try:
        _editor, _rays, bundle, _projected = _trace_and_project_scene(
            system,
            row_specs,
            settings,
            sampling_mode="world_envelope",
        )
        ray_paths = list(getattr(bundle, "ray_paths", []) or [])
        ray_count = len(ray_paths)
        reached_count = sum(1 for ray in ray_paths if bool(ray.reaches_image))
        last_points = []
        for ray in ray_paths:
            points = np.asarray(ray.points_world, dtype=float)
            if points.ndim == 2 and points.shape[0] >= 1 and points.shape[1] >= 3:
                point = points[-1, :3]
                if np.all(np.isfinite(point)):
                    last_points.append(tuple(round(float(value), 3) for value in point))
        unique_last_points = len(set(last_points))
        checks.append(
            PhysicsExitPoseCheck(
                "Dove Open 3D scene carries all through-going image-plane rays",
                bool(
                    ray_count >= expected_count
                    and reached_count == ray_count
                    and unique_last_points >= max(3, min(expected_count, 8))
                ),
                (
                    f"scene_rays={ray_count}, reached_image={reached_count}, "
                    f"unique_3d_endpoints={unique_last_points}, final_surface=S{final_surface}"
                ),
            )
        )
    except Exception as exc:
        checks.append(
            PhysicsExitPoseCheck(
                "Dove Open 3D scene carries all through-going image-plane rays",
                False,
                f"trace/project failed: {exc}",
            )
        )
    return checks


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
    posed_3d_bounds_ok, posed_3d_bounds_detail = _runtime_3d_bounds_match(system, module, [2, 3, 4, 5, 6, 7])
    checks = [
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
            "3D posed follower meshes use the same runtime trace meshes as non-sequential ray tracing",
            posed_3d_bounds_ok,
            posed_3d_bounds_detail,
        ),
    ]
    checks.extend(_scene_trace_consistency_checks(system, rows, module.SETTINGS))
    return checks


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
