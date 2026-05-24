"""Validate five cascaded 42779 penta prisms in a true 3D path.

The diagnostic mimics the Open 3D authoring workflow without depending on
screen coordinates:

1. import a penta STEP overlay;
2. snap face F005 to the current optical axis;
3. promote the overlay to a row-backed optical solid;
4. trace the central ray and assign the next two actual hit faces as Full
   Reflecting, because arbitrary 3D rolls can change promoted-row face labels;
5. trace and use the central ray's exit segment as the next optical axis.

The final assertion starts with a central collimated beam ray and requires it
to pass through five complete row-local penta-prism action groups:

    refraction -> reflection -> reflection -> refraction

The face ids can differ after arbitrary 3D roll and promotion, so the guard
validates the physics action sequence per promoted prism row rather than
assuming the vendor drawing's F003/F004 labels survive every orientation.

Run:

    python -m KrakenOS.UI.validate_five_penta_prism_cascade
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
    PRISM_42779_STEP,
    PROJECT_ROOT,
    _configure_base_editor,
    _open_3d_inspector,
    _refresh,
    _save_vtk_snapshot,
    _set_optical_step_overlay,
)
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _short_error_message
from KrakenOS.UI.scene_geometry import ray_path_terminal_status_from_events
from KrakenOS.UI.validate_penta_mirror_3d_cascade import (
    PENTA_ENTRANCE_FACE,
    PENTA_MIRROR_FACES,
    _assign_reflecting_face,
    _central_path,
    _configure_collimated_bundle,
    _event_action,
    _event_face_id,
    _global_plus_z_axis,
    _surface_events,
    _surface_sequence,
    _terminal_direction,
    _trace_scene,
)


PENTA_COUNT = 5
PENTA_ROLLS_DEG = (34.0, 34.0, 34.0, 34.0, 34.0)
PENTA_INTERACTION_GROUP = (
    "refraction",
    "reflection",
    "reflection",
    "refraction",
)
NEXT_PRISM_SPACING_MM = 180.0
DEFAULT_LAYOUT_PATH = PROJECT_ROOT / "attachment" / "five_penta_prism_cascade.py"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "attachment" / "five_penta_prism_cascade"


def _initial_axis() -> dict[str, object]:
    axis = _global_plus_z_axis()
    axis["target_point"] = (0.0, 0.0, 38.0)
    axis["segment_midpoint"] = (0.0, 0.0, 38.0)
    return axis


def _vector_json(value: object) -> list[float]:
    try:
        vector = np.asarray(value, dtype=float).reshape(-1)[:3]
    except Exception:
        return []
    if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
        return []
    return [round(float(component), 9) for component in vector[:3]]


def _promote_optical_step(app: KrakenLayoutEditor) -> int:
    promoted = app.promote_imported_step_to_optical_solid_row(
        "optical",
        insert_at=max(1, len(app.rows) - 1),
        open_face_editor=False,
        clear_overlay=True,
        refresh_open_3d=False,
    )
    if promoted is None:
        raise RuntimeError(f"STEP promotion failed: {app.status_var.get()}")
    row_index = int(promoted["row_index"])
    row = app.rows[row_index]
    row.glass = "BK7"
    row.axis_move = 0.0
    app._sync_table()
    app._select_table_row(row_index)
    app._invalidate_preview_scene_trace()
    return row_index


def _axis_from_central_exit(scene_bundle: object, prism_number: int) -> dict[str, object]:
    ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
    central = _central_path(ray_paths)
    points = np.asarray(getattr(central, "points_world", ()), dtype=float)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
        raise RuntimeError(f"Prism {prism_number} central path has no usable exit segment.")
    start = points[-2, :3]
    direction = _terminal_direction(central)
    target = start + direction * float(NEXT_PRISM_SPACING_MM)
    end = start + direction * float(NEXT_PRISM_SPACING_MM + 160.0)
    return {
        "axis_id": f"diagnostic:penta-{prism_number}-exit",
        "axis_label": f"diagnostic penta {prism_number} exit axis",
        "axis_kind": "traced_chief_ray_segment",
        "axis_role": "post_surface",
        "points": [tuple(float(value) for value in start), tuple(float(value) for value in end)],
        "target_point": tuple(float(value) for value in target),
        "segment_midpoint": tuple(float(value) for value in target),
        "direction": tuple(float(value) for value in direction),
        "segment_direction": tuple(float(value) for value in direction),
        "segment_index": int(points.shape[0] - 2),
        "ray_index": int(getattr(central, "ray_index", -1) or -1),
        "source_id": str(getattr(central, "source_id", "") or ""),
        "branch_path": str(getattr(central, "branch_path", "") or ""),
    }


def _event_surface_id(event: object) -> int | None:
    try:
        return int(getattr(event, "surface_id", None))
    except Exception:
        return None


def _central_row_events(scene_bundle: object, row_index: int) -> list[object]:
    ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
    central = _central_path(ray_paths)
    return [event for event in _surface_events(central) if _event_surface_id(event) == int(row_index)]


def _assign_penta_mirrors_from_trace(
    app: KrakenLayoutEditor,
    row_index: int,
    prism_number: int,
) -> list[dict[str, object]]:
    assigned: list[dict[str, object]] = []
    for mirror_number, event_index in enumerate((1, 2), start=1):
        _system, _rays, scene_bundle = _trace_scene(app)
        row_events = _central_row_events(scene_bundle, row_index)
        if len(row_events) <= event_index:
            sequence = " -> ".join(_surface_sequence(_central_path(list(getattr(scene_bundle, "ray_paths", []) or []))))
            raise RuntimeError(
                f"Prism {prism_number} mirror {mirror_number}: central ray did not reach event index {event_index}; "
                f"row_events={len(row_events)}, sequence={sequence}."
            )
        event = row_events[event_index]
        face_id = _event_face_id(event)
        if not face_id:
            raise RuntimeError(f"Prism {prism_number} mirror {mirror_number}: traced event has no CAD face id.")
        assigned_face = _assign_reflecting_face(app, row_index, face_id)
        assigned.append(
            {
                "mirror_number": mirror_number,
                "traced_event_index": event_index,
                "traced_face_id": face_id,
                "traced_action_before_assignment": _event_action(event),
                "assigned_face_id": str(assigned_face.get("face_id", "")),
                "function": str(assigned_face.get("function", "")),
            }
        )
    return assigned


def _import_and_place_penta(
    app: KrakenLayoutEditor,
    *,
    prism_number: int,
    axis_info: dict[str, object],
    roll_deg: float,
) -> dict[str, object]:
    target = np.asarray(axis_info.get("target_point", (0.0, 0.0, 38.0)), dtype=float).reshape(-1)[:3]
    if target.size < 3 or not np.all(np.isfinite(target[:3])):
        target = np.asarray((0.0, 0.0, 38.0), dtype=float)
    staging_offset = target + np.asarray((20.0, -24.0, 12.0), dtype=float)
    _set_optical_step_overlay(
        app,
        PRISM_42779_STEP,
        offset_xyz=tuple(float(value) for value in staging_offset[:3]),
        rotation_xyz=(0.0, 90.0, 180.0 + float(roll_deg)),
    )
    app.select_step_component("optical")
    snap = app.snap_step_overlay_face_to_optical_axis(
        "optical",
        axis_info,
        face_id=PENTA_ENTRANCE_FACE,
    )
    if snap is None:
        raise RuntimeError(f"Prism {prism_number} entrance snap failed: {app.status_var.get()}")
    row_index = _promote_optical_step(app)
    assigned = _assign_penta_mirrors_from_trace(app, row_index, prism_number)
    return {
        "prism": prism_number,
        "row_index": row_index,
        "roll_deg": float(roll_deg),
        "axis_id": str(axis_info.get("axis_id", "")),
        "axis_label": str(axis_info.get("axis_label", "")),
        "snap": {
            "face_id": str(snap.get("face_id", "")),
            "rotation_deg": [round(float(value), 6) for value in snap.get("rotation_deg", ())],
            "placement_offset_xyz": _vector_json(snap.get("placement_offset_xyz", ())),
            "target_point": _vector_json(snap.get("target_point", ())),
            "target_direction": _vector_json(snap.get("target_direction", ())),
            "angle_error_deg": round(float(snap.get("angle_error_deg", 0.0) or 0.0), 9),
        },
        "assigned_faces": assigned,
    }


def _validate_final_trace(scene_bundle: object, row_indices: list[int]) -> dict[str, object]:
    ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
    if not ray_paths:
        raise RuntimeError("Final cascade trace produced no ray paths.")
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
    expected_actions = tuple(PENTA_INTERACTION_GROUP) * len(row_indices)
    for path in ray_paths:
        events = _surface_events(path)
        actions = tuple(_event_action(event) for event in events)
        surfaces = tuple(_event_surface_id(event) for event in events)
        if actions != expected_actions:
            raise RuntimeError(
                "Expected every ray to traverse five penta groups with "
                f"refract/reflect/reflect/refract actions; got actions={actions}, "
                f"surfaces={surfaces}, sequence={' -> '.join(_surface_sequence(path))}."
            )
        expected_surfaces: list[int] = []
        for row_index in row_indices:
            expected_surfaces.extend([int(row_index)] * len(PENTA_INTERACTION_GROUP))
        if surfaces != tuple(expected_surfaces):
            raise RuntimeError(
                f"Expected row sequence {tuple(expected_surfaces)}; got surfaces={surfaces}, "
                f"sequence={' -> '.join(_surface_sequence(path))}."
            )

    central = _central_path(ray_paths)
    direction = _terminal_direction(central)
    if abs(float(direction[0])) < 0.05 or abs(float(direction[1])) < 0.05:
        raise RuntimeError(f"Final beam did not remain a true 3D direction; direction={direction}.")
    if float(np.dot(direction, np.asarray((0.0, 0.0, 1.0), dtype=float))) > 0.95:
        raise RuntimeError(f"Final beam was not steered away from the input optical axis; direction={direction}.")

    return {
        "ray_paths": len(ray_paths),
        "central_terminal_direction": _vector_json(direction),
        "row_indices": [int(index) for index in row_indices],
        "terminal_counts": dict(sorted(terminal_counts.items())),
        "surface_sequence_counts": {" -> ".join(sequence): count for sequence, count in sorted(sequences.items())},
        "surface_event_counts": {f"{face}:{action}": count for (face, action), count in sorted(event_counts.items())},
    }


def build_case_editor(stage_snapshot_dir: Path | None = None) -> tuple[KrakenLayoutEditor, dict[str, Any]]:
    if not PRISM_42779_STEP.exists():
        raise RuntimeError(f"Expected STEP fixture: {PRISM_42779_STEP}")
    app = KrakenLayoutEditor(headless=True)
    stages: list[dict[str, object]] = []
    row_indices: list[int] = []
    if stage_snapshot_dir is not None:
        stage_snapshot_dir = stage_snapshot_dir.resolve()
        stage_snapshot_dir.mkdir(parents=True, exist_ok=True)
    _configure_base_editor(app)
    _configure_collimated_bundle(app)
    app.source_radius_var.set("0.0")
    app.ray_count_var.set("1")
    app._invalidate_preview_scene_trace()

    axis_info = _initial_axis()
    scene_bundle = None
    for index, roll_deg in enumerate(PENTA_ROLLS_DEG, start=1):
        stage = _import_and_place_penta(
            app,
            prism_number=index,
            axis_info=axis_info,
            roll_deg=roll_deg,
        )
        row_indices.append(int(stage["row_index"]))
        _system, _rays, scene_bundle = _trace_scene(app)
        ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
        if not ray_paths:
            raise RuntimeError(f"Trace after prism {index} produced no ray paths.")
        central = _central_path(ray_paths)
        stage["ray_paths_after_trace"] = len(ray_paths)
        stage["central_terminal_direction"] = _vector_json(_terminal_direction(central))
        stage["central_sequence"] = " -> ".join(_surface_sequence(central))
        if stage_snapshot_dir is not None:
            inspector = _open_3d_inspector(app)
            _refresh(inspector, reset_camera=True)
            inspector.set_camera_preset("iso")
            snapshot_path = _save_vtk_snapshot(
                inspector,
                stage_snapshot_dir / f"five_penta_stage_{index:02d}_after_trace.png",
            )
            stage["snapshot"] = str(snapshot_path)
        stages.append(stage)
        if index < PENTA_COUNT:
            axis_info = _axis_from_central_exit(scene_bundle, index)

    final = _validate_final_trace(scene_bundle, row_indices)
    report = {
        "ok": True,
        "penta_count": PENTA_COUNT,
        "entrance_face": PENTA_ENTRANCE_FACE,
        "nominal_vendor_mirror_faces": list(PENTA_MIRROR_FACES),
        "mirror_assignment_mode": "trace actual central-ray leak faces after promotion",
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
