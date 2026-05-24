"""Validate a 3D penta-prism workflow with two reflecting faces.

This is a future-development guard for the Open 3D authoring path. It mimics
the important user actions without depending on screen coordinates:

1. import the Edmund 42779 STEP as an optical element;
2. select the entrance face and snap its normal to the optical axis;
3. promote the STEP overlay to an optical solid row;
4. assign the two coated fold faces as Full Reflecting;
5. trace a finite collimated bundle and verify that the beam is steered by the
   prism physics in a true 3D direction, not only in the YZ display plane.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.capture_open3d_step_workflow_screenshots import PRISM_42779_STEP, _configure_base_editor, _set_optical_step_overlay
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _short_error_message
from KrakenOS.UI.scene_geometry import ray_path_terminal_status_from_events


PENTA_IMPORT_OFFSET = (18.0, -22.0, 38.0)
PENTA_INITIAL_ROLL_DEG = 34.0
PENTA_ENTRANCE_FACE = "F005"
PENTA_EXIT_FACE = "F006"
PENTA_MIRROR_FACES = ("F004", "F003")
PENTA_REQUESTED_EXIT_DIRECTION = np.asarray((1.0, 0.0, 0.0), dtype=float)


def _global_plus_z_axis() -> dict[str, object]:
    return {
        "axis_id": "diagnostic:global-plus-z",
        "axis_label": "diagnostic global +Z optical axis",
        "axis_kind": "prescription_axis",
        "axis_role": "input_axis",
        "points": [(0.0, 0.0, -80.0), (0.0, 0.0, 180.0)],
        "direction": (0.0, 0.0, 1.0),
        "segment_index": 0,
    }


def _event_face_id(event: object) -> str:
    metadata = getattr(event, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return str(
        getattr(event, "mesh_face_id", "")
        or getattr(event, "face_id", "")
        or metadata.get("mesh_face_id", "")
        or metadata.get("face_id", "")
        or ""
    ).strip()


def _event_action(event: object) -> str:
    return str(getattr(event, "event_type", "") or getattr(event, "interaction", "") or "").strip().lower()


def _surface_events(path: object) -> list[object]:
    return [event for event in list(getattr(path, "events", []) or []) if str(getattr(event, "event_kind", "") or "") == "surface"]


def _surface_sequence(path: object) -> tuple[str, ...]:
    sequence: list[str] = []
    for event in _surface_events(path):
        face_id = _event_face_id(event) or "surface"
        action = _event_action(event)
        sequence.append(f"{face_id}:{action}" if action else face_id)
    return tuple(sequence)


def _central_path(ray_paths: list[object]) -> object:
    if not ray_paths:
        raise RuntimeError("No ray paths were traced.")

    def _score(path: object) -> tuple[float, int]:
        try:
            points = np.asarray(getattr(path, "points_world", ()), dtype=float)
            radius = float(np.linalg.norm(points[0, :2])) if points.ndim == 2 and points.shape[0] else float("inf")
        except Exception:
            radius = float("inf")
        try:
            ray_index = int(getattr(path, "ray_index", 0) or 0)
        except Exception:
            ray_index = 0
        return radius, ray_index

    return min(ray_paths, key=_score)


def _terminal_direction(path: object) -> np.ndarray:
    points = np.asarray(getattr(path, "points_world", ()), dtype=float)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
        raise RuntimeError("Ray path has no usable terminal segment.")
    direction = points[-1, :3] - points[-2, :3]
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-12:
        raise RuntimeError("Ray path terminal segment has zero length.")
    return direction / norm


def _configure_collimated_bundle(app: KrakenLayoutEditor) -> None:
    app.source_model_var.set("Collimated disk source")
    app.source_radius_var.set("4.0")
    app.source_cone_angle_var.set("0.0")
    app.ray_count_var.set("13")
    app.field_count_var.set("1")
    app.field_value_var.set("0.0")
    app.wavelength_var.set("0.55")
    try:
        app._sync_object_controls()
        app._sync_left_mode_controls()
    except Exception:
        pass
    app._invalidate_preview_scene_trace()


def _promote_optical_step(app: KrakenLayoutEditor) -> int:
    promoted = app.promote_imported_step_to_optical_solid_row(
        "optical",
        insert_at=1,
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


def _assign_reflecting_face(app: KrakenLayoutEditor, row_index: int, face_id: str) -> dict[str, object]:
    assigned = app.assign_optical_solid_face_function(
        row_index,
        face_id,
        "Full Reflecting",
        direct_context=True,
    )
    if str(assigned.get("function", "") or "") != "Mirror":
        raise RuntimeError(f"{face_id} was not assigned as Full Reflecting: {assigned!r}")
    return dict(assigned)


def _trace_scene(app: KrakenLayoutEditor):
    return app._build_preview_system_rays_bundle(sampling_mode="world_envelope", update_state=False)


def run_case() -> dict[str, Any]:
    if not PRISM_42779_STEP.exists():
        raise RuntimeError(f"Expected STEP fixture: {PRISM_42779_STEP}")
    app = KrakenLayoutEditor(headless=True)
    actions: list[dict[str, object]] = []
    try:
        _configure_base_editor(app)
        _configure_collimated_bundle(app)
        _set_optical_step_overlay(
            app,
            PRISM_42779_STEP,
            offset_xyz=PENTA_IMPORT_OFFSET,
            rotation_xyz=(0.0, 90.0, 180.0 + PENTA_INITIAL_ROLL_DEG),
        )
        actions.append({"action": "import_optical_step", "path": str(PRISM_42779_STEP), "roll_deg": PENTA_INITIAL_ROLL_DEG})

        app.select_step_component("optical")
        snap = app.snap_step_overlay_face_to_optical_axis(
            "optical",
            _global_plus_z_axis(),
            face_id=PENTA_ENTRANCE_FACE,
            guide_face_id=PENTA_EXIT_FACE,
            guide_direction=PENTA_REQUESTED_EXIT_DIRECTION,
        )
        if snap is None:
            raise RuntimeError(f"Entrance-face snap failed: {app.status_var.get()}")
        actions.append(
            {
                "action": "snap_face_normal_to_optical_axis",
                "face_id": PENTA_ENTRANCE_FACE,
                "guide_face_id": str(snap.get("guide_face_id", "")),
                "guide_direction": [round(float(value), 6) for value in snap.get("guide_direction", ())],
                "axis_id": str(snap.get("axis_id", "")),
                "rotation_deg": [round(float(value), 6) for value in snap.get("rotation_deg", ())],
                "placement_offset_xyz": [round(float(value), 6) for value in snap.get("placement_offset_xyz", ())],
            }
        )

        row_index = _promote_optical_step(app)
        actions.append({"action": "promote_step_to_optical_solid_row", "row_index": row_index})

        assigned_faces = []
        for face_id in PENTA_MIRROR_FACES:
            assigned = _assign_reflecting_face(app, row_index, face_id)
            assigned_faces.append(assigned)
            actions.append({"action": "assign_face_function", "row_index": row_index, "face_id": face_id, "function": "Full Reflecting"})

        _system, _rays, scene_bundle = _trace_scene(app)
        ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
        if not ray_paths:
            raise RuntimeError("Trace produced no ray paths.")
        central = _central_path(ray_paths)
        direction = _terminal_direction(central)
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

        expected_reflect_count = len(ray_paths)
        for face_id in PENTA_MIRROR_FACES:
            count = int(event_counts.get((face_id, "reflection"), 0) or 0)
            if count != expected_reflect_count:
                raise RuntimeError(
                    f"Expected every ray to reflect at {face_id}; rays={expected_reflect_count}, reflections={count}, "
                    f"events={dict(event_counts)!r}."
                )
        if float(np.dot(direction, PENTA_REQUESTED_EXIT_DIRECTION)) < 0.999:
            raise RuntimeError(
                "Terminal beam did not follow the requested deterministic penta exit direction: "
                f"actual={direction}, expected={PENTA_REQUESTED_EXIT_DIRECTION}."
            )

        return {
            "ok": True,
            "actions": actions,
            "row_index": row_index,
            "assigned_faces": [
                {"face_id": str(face.get("face_id", "")), "function": str(face.get("function", ""))}
                for face in assigned_faces
            ],
            "ray_paths": len(ray_paths),
            "terminal_direction": [round(float(value), 9) for value in direction[:3]],
            "terminal_counts": dict(sorted(terminal_counts.items())),
            "surface_sequence_counts": {" -> ".join(sequence): count for sequence, count in sorted(sequences.items())},
            "surface_event_counts": {f"{face}:{action}": count for (face, action), count in sorted(event_counts.items())},
        }
    finally:
        app.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=None, help="Optional JSON report path.")
    args = parser.parse_args()
    try:
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
