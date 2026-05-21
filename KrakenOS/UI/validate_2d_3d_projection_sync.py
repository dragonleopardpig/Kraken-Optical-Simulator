"""Validate that 2-D views are projections of the Open 3-D display rays."""

from __future__ import annotations

from collections import Counter
import importlib.util
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.saved_layout_plot import _rows_from_surface_specs, _snapshot_editor
from KrakenOS.UI.scene_geometry import ray_path_terminal_status_from_events
from KrakenOS.UI.scene_projector import SceneProjector2D, scene_display_center_radius


def _load_python_module(path: Path):
    spec = importlib.util.spec_from_file_location("_kraken_projection_sync_layout", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _penta_bundle():
    repo_root = Path(__file__).resolve().parents[2]
    layout_path = repo_root / "attachment" / "penta.py"
    module = _load_python_module(layout_path)
    system = module.build_runtime_system()
    rays = module.build_rays(system)
    rows = _rows_from_surface_specs(module.SURFACES)
    editor = _snapshot_editor(rows, module.SETTINGS)
    editor.current_layout_file = layout_path
    editor._normalize_special_rows()
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    try:
        editor._preview_field_ray_count = max(1, int(module.SETTINGS.get("ray_count", len(getattr(rays, "CC", [])))))
    except Exception:
        editor._preview_field_ray_count = max(1, len(getattr(rays, "CC", [])))
    try:
        editor._preview_field_bundle_count = max(1, int(module.SETTINGS.get("field_count", 1)))
    except Exception:
        editor._preview_field_bundle_count = 1
    max_radius = max((max(float(row.diameter) / 2.0, 0.5) for row in rows), default=1.0)
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    editor._last_scene_bundle = bundle
    return editor, rays, bundle


def _surface_face_sequence(path: object) -> tuple[str, ...]:
    faces: list[str] = []
    for event in list(getattr(path, "events", []) or []):
        if str(getattr(event, "event_kind", "") or "") != "surface":
            continue
        face = str(getattr(event, "mesh_face_id", "") or "").strip()
        if face:
            faces.append(face)
    return tuple(faces)


def _validate_projection_sync(editor: KrakenLayoutEditor, rays: object, bundle: object) -> list[str]:
    failures: list[str] = []
    paths_by_index = KrakenLayoutEditor._scene_ray_path_by_index(bundle)
    center, radius = scene_display_center_radius(bundle)
    records = list(editor._iter_3d_scene_ray_records(rays, bundle))
    if len(records) != len(getattr(bundle, "ray_paths", []) or []):
        failures.append(f"3D records={len(records)} bundle paths={len(getattr(bundle, 'ray_paths', []) or [])}")
    for plane in ("YZ", "XZ", "XY"):
        projector = SceneProjector2D(plane)
        projected = projector.project_bundle(bundle)
        projected_by_index = {int(ray.ray_index): ray for ray in projected.rays}
        if len(projected_by_index) != len(records):
            failures.append(f"{plane}: projected rays={len(projected_by_index)} 3D records={len(records)}")
        for ray_index, _color, ray_pts, terminal_status in records:
            ray_index = int(ray_index)
            projected_ray = projected_by_index.get(ray_index)
            if projected_ray is None:
                failures.append(f"{plane}: missing projected ray {ray_index}")
                continue
            path = paths_by_index.get(ray_index)
            terminal_target = KrakenLayoutEditor._missed_detector_target_for_path(bundle, path)
            terminal_direction = KrakenLayoutEditor._terminal_display_direction_for_path(path)
            display_3d, _was_bounded = KrakenLayoutEditor._bounded_3d_ray_points_for_display(
                ray_pts,
                center,
                radius,
                terminal_status=terminal_status,
                terminal_target=terminal_target,
                terminal_direction=terminal_direction,
            )
            projected_from_3d = projector.project_xyz_points(display_3d)
            points_2d = np.asarray(projected_ray.points_2d, dtype=float)
            if points_2d.shape != projected_from_3d.shape:
                failures.append(
                    f"{plane}: ray {ray_index} shape mismatch 2D={points_2d.shape} 3D={projected_from_3d.shape}"
                )
                continue
            if not np.allclose(points_2d, projected_from_3d, rtol=0.0, atol=1.0e-9):
                delta = float(np.nanmax(np.abs(points_2d - projected_from_3d)))
                failures.append(f"{plane}: ray {ray_index} projection delta={delta:.3e}")
    return failures


def _validate_penta_physics(bundle: object) -> list[str]:
    failures: list[str] = []
    paths = list(getattr(bundle, "ray_paths", []) or [])
    if len(paths) != 31:
        failures.append(f"penta ray count={len(paths)}, expected 31")
    sequences = Counter(_surface_face_sequence(path) for path in paths)
    expected_sequence = ("F005", "F003", "F004", "F006")
    if set(sequences) != {expected_sequence}:
        failures.append(f"penta face sequences={dict(sequences)}, expected only {expected_sequence}")
    statuses = Counter(ray_path_terminal_status_from_events(path) for path in paths)
    unexpected_statuses = set(statuses) - {"escaped", "hit_detector"}
    if unexpected_statuses:
        failures.append(f"unexpected penta terminal statuses={dict(statuses)}")
    return failures


def main() -> int:
    editor, rays, bundle = _penta_bundle()
    failures = []
    failures.extend(_validate_projection_sync(editor, rays, bundle))
    failures.extend(_validate_penta_physics(bundle))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("2D/Open 3D projection sync validator passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
