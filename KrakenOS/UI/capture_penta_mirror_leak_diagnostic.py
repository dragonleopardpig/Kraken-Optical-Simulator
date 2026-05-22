"""Headless Open 3D diagnostic for the 42779 penta-prism mirror faces.

The diagnostic reproduces the Open 3D import/promote/assign workflow and saves
VTK snapshots plus a JSON report. It checks the important physics contract:
F004 must reflect when assigned Full Reflecting. If only F004 is assigned, rays
may still leave through F003 because F003 remains default Uncoated.

Run under an X display, for example:

    env DISPLAY=:99 python -m KrakenOS.UI.capture_penta_mirror_leak_diagnostic
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
    PRISM_42779_STEP,
    _configure_base_editor,
    _open_3d_inspector,
    _refresh,
    _save_vtk_snapshot,
    _set_optical_step_overlay,
)
from KrakenOS.UI.capture_vendor_prism_case_study_screenshots import PROJECT_ROOT
from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor, _short_error_message
from KrakenOS.UI.scene_geometry import ray_path_terminal_status_from_events


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "attachment" / "open3d_penta_mirror_diagnostic"
PENTA_OFFSET = (0.0, 5.338434219360337, 35.338052809592156)
PENTA_ROTATION = (0.0, 90.0, 180.0)


def _event_face_id(event: object) -> str:
    metadata = getattr(event, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return str(
        getattr(event, "mesh_face_id", "")
        or metadata.get("mesh_face_id", "")
        or metadata.get("face_id", "")
        or ""
    ).strip()


def _event_action(event: object) -> str:
    return str(getattr(event, "event_type", "") or "").strip().lower()


def _surface_sequence(path: object) -> tuple[str, ...]:
    sequence: list[str] = []
    for event in list(getattr(path, "events", []) or []):
        if str(getattr(event, "event_kind", "") or "") != "surface":
            continue
        face_id = _event_face_id(event) or "surface"
        action = _event_action(event)
        sequence.append(f"{face_id}:{action}" if action else face_id)
    return tuple(sequence)


def _last_surface_summary(path: object) -> str:
    sequence = _surface_sequence(path)
    if not sequence:
        return ""
    face_action = sequence[-1].split(":", 1)
    if len(face_action) == 2 and face_action[1]:
        return f"{face_action[0]} {face_action[1]}"
    return face_action[0]


def _all_surface_events(ray_paths: list[object]) -> list[tuple[str, str]]:
    events: list[tuple[str, str]] = []
    for path in ray_paths:
        for event in list(getattr(path, "events", []) or []):
            if str(getattr(event, "event_kind", "") or "") != "surface":
                continue
            events.append((_event_face_id(event), _event_action(event)))
    return events


def _trace_summary_text(inspector: Kraken3DInspector) -> str:
    actor = getattr(inspector, "_trace_summary_actor", None)
    if actor is None:
        return ""
    try:
        return str(actor.GetInput() or "")
    except Exception:
        return ""


def _state_report(app: KrakenLayoutEditor, inspector: Kraken3DInspector, label: str) -> dict[str, Any]:
    scene_bundle = getattr(inspector, "_current_scene_bundle", None)
    ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
    sequences = Counter(_surface_sequence(path) for path in ray_paths)
    terminal_counts = Counter(
        str(ray_path_terminal_status_from_events(path) or "unknown").strip() or "unknown"
        for path in ray_paths
    )
    terminal_faces = Counter(_last_surface_summary(path) for path in ray_paths if _last_surface_summary(path))
    events = Counter(_all_surface_events(ray_paths))
    return {
        "label": label,
        "ray_paths": len(ray_paths),
        "terminal_counts": dict(sorted(terminal_counts.items())),
        "terminal_last_faces": dict(sorted(terminal_faces.items())),
        "surface_sequence_counts": {" -> ".join(sequence): count for sequence, count in sorted(sequences.items())},
        "surface_event_counts": {f"{face}:{action}": count for (face, action), count in sorted(events.items())},
        "trace_summary_text": _trace_summary_text(inspector),
        "status": str(app.status_var.get()),
    }


def _promote_current_optical_step_with_default_faces(app: KrakenLayoutEditor) -> int:
    result = app.promote_imported_step_to_optical_solid_row(
        "optical",
        insert_at=1,
        open_face_editor=False,
        clear_overlay=True,
        refresh_open_3d=False,
    )
    if result is None:
        raise RuntimeError(f"STEP promotion failed: {app.status_var.get()}")
    row_index = int(result["row_index"])
    row = app.rows[row_index]
    row.glass = "BK7"
    row.axis_move = 0.0
    app._sync_table()
    app._select_table_row(row_index)
    app._invalidate_preview_scene_trace()
    return row_index


def _assign_mirror(app: KrakenLayoutEditor, row_index: int, face_id: str) -> None:
    assigned = app.assign_optical_solid_face_function(
        row_index,
        face_id,
        "Full Reflecting",
        direct_context=True,
    )
    if str(assigned.get("function", "") or "") != "Mirror":
        raise RuntimeError(f"{face_id} was not assigned as Mirror: {assigned!r}")


def _assert_f004_reflects(report: dict[str, Any], *, expected_terminal: str | None = None) -> None:
    ray_paths = int(report.get("ray_paths", 0) or 0)
    if ray_paths <= 0:
        raise RuntimeError(f"{report.get('label')} produced no ray paths.")
    events = dict(report.get("surface_event_counts", {}) or {})
    f004_reflections = int(events.get("F004:reflection", 0) or 0)
    if f004_reflections != ray_paths:
        raise RuntimeError(
            f"Expected every ray to reflect at F004; rays={ray_paths}, "
            f"F004 reflections={f004_reflections}, events={events!r}."
        )
    leaking = {
        key: count
        for key, count in events.items()
        if key.startswith("F004:") and key != "F004:reflection" and int(count) > 0
    }
    if leaking:
        raise RuntimeError(f"F004 had non-reflection events: {leaking!r}.")
    if expected_terminal is not None:
        terminal_faces = dict(report.get("terminal_last_faces", {}) or {})
        if int(terminal_faces.get(expected_terminal, 0) or 0) != ray_paths:
            raise RuntimeError(
                f"Expected terminal last face {expected_terminal!r} for all rays; "
                f"rays={ray_paths}, terminal_faces={terminal_faces!r}."
            )


def capture(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    reports: list[dict[str, Any]] = []
    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry("1800x1040+20+20")
        _configure_base_editor(app)
        inspector = _open_3d_inspector(app)

        _set_optical_step_overlay(
            app,
            PRISM_42779_STEP,
            offset_xyz=PENTA_OFFSET,
            rotation_xyz=PENTA_ROTATION,
        )
        row_index = _promote_current_optical_step_with_default_faces(app)

        _assign_mirror(app, row_index, "F004")
        _refresh(inspector, reset_camera=True)
        path = _save_vtk_snapshot(inspector, output_dir / "f004_only_mirror.png")
        report = _state_report(app, inspector, "F004 mirror only; F003 still default Uncoated")
        report["image"] = str(path.relative_to(PROJECT_ROOT))
        reports.append(report)
        outputs.append(path)
        _assert_f004_reflects(report, expected_terminal="F003 refraction")

        _assign_mirror(app, row_index, "F003")
        _refresh(inspector, reset_camera=True)
        path = _save_vtk_snapshot(inspector, output_dir / "f003_f004_mirrors.png")
        report = _state_report(app, inspector, "F003 and F004 mirrors")
        report["image"] = str(path.relative_to(PROJECT_ROOT))
        reports.append(report)
        outputs.append(path)
        _assert_f004_reflects(report)
        terminal_faces = dict(report.get("terminal_last_faces", {}) or {})
        if int(terminal_faces.get("F006 refraction", 0) or 0) != int(report.get("ray_paths", 0) or 0):
            raise RuntimeError(f"Expected all rays to exit at F006 after both mirror faces; got {terminal_faces!r}.")
    except Exception as exc:
        reports.append({"label": "error", "error": _short_error_message(exc)})
        raise
    finally:
        (output_dir / "penta_mirror_diagnostic_report.json").write_text(
            json.dumps(reports, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            if app._three_d_inspector is not None:
                app._three_d_inspector._on_close()
        except Exception:
            pass
        app.destroy()
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    paths = capture(args.output_dir)
    for path in paths:
        print(path)
    print(args.output_dir / "penta_mirror_diagnostic_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
