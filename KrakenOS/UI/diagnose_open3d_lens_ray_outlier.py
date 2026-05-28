"""Diagnose large-angle Open 3D exit rays for an imported analytic lens STEP.

Run under an X display, for example:

    env DISPLAY=:99 python -m KrakenOS.UI.diagnose_open3d_lens_ray_outlier
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.capture_open3d_lens_face_selection_snap import (
    LENS_STEP,
    _front_lens_face,
    _global_axis_record,
    _pick_lens_face,
)
from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
    PROJECT_ROOT,
    _configure_base_editor,
    _open_3d_inspector,
    _refresh,
    _save_vtk_snapshot,
    _set_optical_step_overlay,
)
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _short_error_message
from KrakenOS.UI.scene_geometry import ray_path_terminal_status_from_events
from KrakenOS.UI.source_trace_helpers import SOURCE_MODEL_DEFAULT


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "attachment" / "open3d_lens_ray_outlier"


def _unit(value: object) -> list[float]:
    try:
        vector = np.asarray(value, dtype=float).reshape(-1)[:3]
    except Exception:
        return []
    if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
        return []
    norm = float(np.linalg.norm(vector[:3]))
    if not np.isfinite(norm) or norm <= 1.0e-12:
        return []
    return [round(float(component), 9) for component in (vector[:3] / norm)]


def _xyz(value: object) -> list[float]:
    try:
        vector = np.asarray(value, dtype=float).reshape(-1)[:3]
    except Exception:
        return []
    if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
        return []
    return [round(float(component), 6) for component in vector[:3]]


def _ray_exit_record(path: object) -> dict[str, object]:
    try:
        points = np.asarray(getattr(path, "points_world", []), dtype=float)
    except Exception:
        points = np.empty((0, 3), dtype=float)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
        direction = np.asarray((0.0, 0.0, 1.0), dtype=float)
        angle_deg = float("nan")
    else:
        segment = points[-1, :3] - points[-2, :3]
        norm = float(np.linalg.norm(segment))
        direction = segment / norm if norm > 1.0e-12 else np.asarray((0.0, 0.0, 1.0), dtype=float)
        angle_deg = math.degrees(math.atan2(float(np.linalg.norm(direction[:2])), float(direction[2])))
    events = [
        event
        for event in list(getattr(path, "events", []) or [])
        if str(getattr(event, "event_kind", "") or "") == "surface"
    ]
    surface_events: list[dict[str, object]] = []
    for event in events:
        surface_events.append(
            {
                "surface": getattr(event, "surface_id", None),
                "surface_name": str(getattr(event, "surface_name", "") or ""),
                "face_id": str(
                    getattr(event, "mesh_face_id", "")
                    or (getattr(event, "metadata", {}) or {}).get("mesh_face_id", "")
                    or (getattr(event, "metadata", {}) or {}).get("face_id", "")
                    or ""
                ),
                "event_type": str(getattr(event, "event_type", "") or ""),
                "interaction_model": str(getattr(event, "interaction_model", "") or ""),
                "point": _xyz(getattr(event, "point_world", ())),
                "incoming": _unit(getattr(event, "incoming_direction", ())),
                "outgoing": _unit(getattr(event, "outgoing_direction", ())),
                "normal": _unit(getattr(event, "surface_normal", ())),
            }
        )
    return {
        "ray_index": int(getattr(path, "ray_index", -1) or -1),
        "source_ray_index": getattr(path, "source_ray_index", None),
        "terminal_status": ray_path_terminal_status_from_events(path),
        "exit_angle_deg": round(float(angle_deg), 6) if np.isfinite(angle_deg) else None,
        "exit_direction": _unit(direction),
        "point_count": int(points.shape[0]) if points.ndim == 2 else 0,
        "start": _xyz(points[0, :3]) if points.ndim == 2 and points.shape[0] else [],
        "end": _xyz(points[-1, :3]) if points.ndim == 2 and points.shape[0] else [],
        "surface_count": len(surface_events),
        "surfaces": surface_events,
    }


def _configure_parallel_infinity_source(app: KrakenLayoutEditor, *, ray_count: int) -> None:
    app.object_mode_var.set("Infinity")
    app.source_model_var.set(SOURCE_MODEL_DEFAULT)
    app.pupil_pattern_var.set("Meridional fan")
    app.source_cone_angle_var.set("0.0")
    app.source_radius_var.set("0.0")
    app.field_type_var.set(app._field_type_display_label("Angle"))
    app.field_value_var.set("0.0")
    app.field_count_var.set("1")
    app.ray_count_var.set(str(int(ray_count)))
    app.emit_full_ray_var.set(False)
    app.show_clipped_rays_var.set(True)
    try:
        app._sync_object_controls()
        app._sync_left_mode_controls()
    except Exception:
        pass
    app._invalidate_preview_scene_trace()


def diagnose(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    ray_count: int = 41,
    max_exit_angle_deg: float = 5.0,
) -> dict[str, object]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "lens_step": str(LENS_STEP),
        "ray_count_setting": int(ray_count),
        "snapshots": [],
    }
    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry("1800x1040+20+20")
        _configure_base_editor(app)
        _configure_parallel_infinity_source(app, ray_count=ray_count)
        inspector = _open_3d_inspector(app)
        inspector.set_camera_preset("zy")
        _set_optical_step_overlay(app, LENS_STEP, offset_xyz=(8.0, -6.0, 35.0))
        _refresh(inspector, reset_camera=True)

        face = _front_lens_face(app)
        pick = _pick_lens_face(inspector, face)
        snap = app.snap_step_overlay_face_to_optical_axis(
            "optical",
            _global_axis_record(inspector),
            face_id=str(pick["face_id"]),
        )
        if snap is None:
            raise RuntimeError(f"Lens face snap failed: {app.status_var.get()}")
        app._open3d_trace_refresh_service().mark_step_overlay_physics_preview_ready("optical")
        report["snap"] = {
            "face_id": str(snap.get("face_id", "") or ""),
            "axis_id": str(snap.get("axis_id", "") or ""),
            "angle_error_deg": float(snap.get("angle_error_deg", float("nan"))),
            "placement_offset_xyz": [float(value) for value in snap.get("placement_offset_xyz", ())],
        }

        inspector.show_rays_var.set(True)
        inspector.show_terminal_diagnostics_var.set(False)
        _refresh(inspector)
        snapshot = _save_vtk_snapshot(inspector, output_dir / "01_show_rays.png")
        report["snapshots"].append(str(snapshot))
        scene_bundle = inspector._current_scene_bundle
        paths = list(getattr(scene_bundle, "ray_paths", []) or [])
        ray_records = [_ray_exit_record(path) for path in paths]
        ray_records.sort(
            key=lambda row: float(row.get("exit_angle_deg") if row.get("exit_angle_deg") is not None else -1.0),
            reverse=True,
        )
        live_records = list(getattr(app, "_last_live_step_overlay_trace_records", []) or [])
        trace_backends = sorted(
            {
                str(record.get("trace_backend", "") or "stl_mesh")
                for record in live_records
                if isinstance(record, dict)
            }
        )
        status_counts: dict[str, int] = {}
        for row in ray_records:
            status = str(row.get("terminal_status", "") or "unknown")
            status_counts[status] = int(status_counts.get(status, 0)) + 1
        report.update(
            {
                "path_count": len(paths),
                "rendered_ray_count": len(app._iter_3d_scene_ray_records(inspector._current_rays, scene_bundle)),
                "trace_backends": trace_backends,
                "terminal_status_counts": status_counts,
                "largest_exit_angles": ray_records[:8],
            }
        )
        max_angle = float(ray_records[0].get("exit_angle_deg") or 0.0) if ray_records else 0.0
        report["max_exit_angle_deg"] = round(max_angle, 6)
        report["max_exit_angle_limit_deg"] = float(max_exit_angle_deg)
        if "native_analytic_rows" not in trace_backends:
            raise RuntimeError(f"Expected analytic native live trace backend, got {trace_backends or ['stl_mesh']}.")
        if max_angle > float(max_exit_angle_deg):
            raise RuntimeError(
                f"Imported analytic lens produced a large outlier exit angle: {max_angle:.6g} deg "
                f"> {float(max_exit_angle_deg):.6g} deg."
            )
    except Exception as exc:
        report["error"] = _short_error_message(exc)
        raise
    finally:
        (output_dir / "lens_ray_outlier_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            if app._three_d_inspector is not None:
                app._three_d_inspector._on_close()
        except Exception:
            pass
        app.destroy()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ray-count", type=int, default=41)
    parser.add_argument("--max-exit-angle-deg", type=float, default=5.0)
    args = parser.parse_args(argv)
    report = diagnose(
        args.output_dir,
        ray_count=max(1, int(args.ray_count)),
        max_exit_angle_deg=float(args.max_exit_angle_deg),
    )
    print(
        "PASS: imported lens ray outlier diagnostic "
        f"backend={','.join(report.get('trace_backends', [])) or 'unknown'} "
        f"max_exit_angle={float(report.get('max_exit_angle_deg', 0.0)):.6g} deg "
        f"paths={int(report.get('path_count', 0) or 0)} "
        f"report={Path(args.output_dir).resolve() / 'lens_ray_outlier_report.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
