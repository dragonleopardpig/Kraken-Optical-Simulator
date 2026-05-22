"""Capture the Open 3D STEP authoring workflow as STEP1.png through STEP8.png.

The script drives the real Tk/VTK inspector under an X display. In CI or a
headless shell, run it through Xvfb:

    env DISPLAY=:99 python -m KrakenOS.UI.capture_open3d_step_workflow_screenshots
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.capture_vendor_prism_case_study_screenshots import (
    PRISM_42779_STEP,
    PROJECT_ROOT,
    _metadata_for_mesh,
)
from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    Kraken3DInspector,
    KrakenLayoutEditor,
    SurfaceRow,
    _short_error_message,
)
from KrakenOS.UI.scene_geometry import ray_path_terminal_status_from_events


PRISM_32336_STEP = PROJECT_ROOT / "attachment" / "prisms" / "32336" / "step_32336.step"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "attachment" / "open3d_step_workflow_headless"


def _save_vtk_snapshot(inspector: Kraken3DInspector, path: Path) -> Path:
    from vtkmodules.vtkIOImage import vtkPNGWriter  # type: ignore
    from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter  # type: ignore

    path.parent.mkdir(parents=True, exist_ok=True)
    render_window = inspector._vtk_widget.GetRenderWindow()
    render_window.SetSize(1600, 900)
    render_window.Render()
    capture = vtkWindowToImageFilter()
    capture.SetInput(render_window)
    try:
        capture.SetInputBufferTypeToRGBA()
    except Exception:
        pass
    try:
        capture.ReadFrontBufferOff()
    except Exception:
        pass
    capture.Update()
    writer = vtkPNGWriter()
    writer.SetFileName(str(path))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()
    if not path.exists() or path.stat().st_size <= 2048:
        raise RuntimeError(f"VTK snapshot was not written: {path}")
    return path


def _settle(widget, delay_s: float = 0.25) -> None:
    widget.update_idletasks()
    widget.update()
    time.sleep(delay_s)
    widget.update_idletasks()
    widget.update()


def _configure_base_editor(app: KrakenLayoutEditor) -> None:
    app._reset_complete_layout_runtime_state(close_viewers=True)
    app.rows = [
        SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=80.0, glass="AIR"),
    ]
    app.current_layout_file = None
    app._normalize_special_rows()
    app._sync_table()
    app._select_table_row(0)
    app.display_orientation_var.set("Vertical")
    app.trace_mode_var.set("Non-Sequential Preview")
    app.image_diameter_mode_var.set("Manual")
    app.source_model_var.set("Random point cone")
    app.pupil_pattern_var.set("Random disk")
    app.source_cone_angle_var.set("2.0")
    app.source_radius_var.set("0.0")
    app.field_count_var.set("1")
    app.field_value_var.set("0.0")
    app.ray_count_var.set("12")
    app.wavelength_var.set("0.55")
    app.auto_save_plot_var.set(False)
    try:
        app._sync_object_controls()
        app._sync_left_mode_controls()
    except Exception:
        pass
    if app.rows and app.rows[-1].surface == "Image":
        app.rows[-1].diameter = 80.0
    app._invalidate_preview_scene_trace()
    app.update_idletasks()
    app.update()


def _open_3d_inspector(app: KrakenLayoutEditor) -> Kraken3DInspector:
    app.open_3d_view()
    _settle(app, 0.4)
    inspector = app._three_d_inspector
    if inspector is None or not inspector.available:
        reason = getattr(inspector, "unavailable_reason", "") if inspector is not None else "3D inspector did not open"
        raise RuntimeError(f"Embedded 3D inspector unavailable: {reason}")
    inspector.geometry("1760x980+40+40")
    inspector.show_rotation_handles_var.set(False)
    inspector.show_placement_handles_var.set(False)
    inspector.deiconify()
    inspector.lift()
    _settle(inspector, 0.5)
    inspector.set_camera_preset("zy")
    return inspector


def _refresh(inspector: Kraken3DInspector, *, live: bool = False, reset_camera: bool = False) -> None:
    if live:
        inspector._refresh_live_preview_scene("headless trace ray")
    else:
        inspector.refresh_from_editor(
            sampling_mode=inspector.editor._preview_3d_sampling_mode(),
            force_retrace=True,
        )
    if reset_camera:
        try:
            inspector._renderer.ResetCamera()
        except Exception:
            pass
    inspector.set_camera_preset("zy")
    _settle(inspector, 0.35)


def _set_optical_step_overlay(
    app: KrakenLayoutEditor,
    path: Path,
    *,
    offset_xyz: tuple[float, float, float],
    rotation_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    app.imported_optical_step_path = path.resolve()
    app.optical_step_rotation_x_deg = float(rotation_xyz[0])
    app.optical_step_rotation_y_deg = float(rotation_xyz[1])
    app.optical_step_rotation_z_deg = float(rotation_xyz[2])
    app.optical_step_axis_offset_xy = (0.0, 0.0)
    app.optical_step_placement_offset_xyz = tuple(float(value) for value in offset_xyz)
    app._selected_step_label = "optical"
    app._live_step_overlay_trace_plan_cache = {}
    app._invalidate_preview_scene_trace()
    app.select_step_component("optical")


def _set_ray_count(app: KrakenLayoutEditor, ray_count: int, cone_deg: float) -> None:
    app.ray_count_var.set(str(int(ray_count)))
    app.source_cone_angle_var.set(f"{float(cone_deg):g}")
    try:
        app._sync_object_controls()
        app._sync_left_mode_controls()
    except Exception:
        pass
    app._invalidate_preview_scene_trace()


def _promote_current_optical_step(app: KrakenLayoutEditor) -> int:
    result = app.promote_imported_step_to_optical_solid_row(
        "optical",
        open_face_editor=False,
        clear_overlay=True,
        refresh_open_3d=False,
    )
    if result is None:
        raise RuntimeError(f"STEP promotion failed: {app.status_var.get()}")
    row_index = int(result["row_index"])
    mesh_path = Path(str(result["mesh_path"])).resolve()
    metadata = _metadata_for_mesh(mesh_path)
    row = app.rows[row_index]
    row.glass = "BK7"
    row.axis_move = 0.0
    row.advanced = dict(row.advanced or {})
    row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
    app._sync_table()
    app._select_table_row(row_index)
    app._invalidate_preview_scene_trace()
    return row_index


def _json_vector(value: object) -> list[float]:
    try:
        vector = np.asarray(value, dtype=float).reshape(-1)[:3]
    except Exception:
        return []
    if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
        return []
    return [round(float(component), 6) for component in vector[:3]]


def _surface_event_record(event: object) -> dict[str, object]:
    metadata = getattr(event, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "step": int(getattr(event, "step", 0) or 0),
        "surface_id": getattr(event, "surface_id", None),
        "face_id": str(
            getattr(event, "mesh_face_id", "")
            or metadata.get("mesh_face_id", "")
            or metadata.get("face_id", "")
            or ""
        ),
        "event_type": str(getattr(event, "event_type", "") or ""),
        "interaction_model": str(getattr(event, "interaction_model", "") or ""),
        "media_transition": str(getattr(event, "media_transition", "") or ""),
        "inside_before": str(getattr(event, "inside_volumes_before", "") or ""),
        "inside_after": str(getattr(event, "inside_volumes_after", "") or ""),
        "point_world": _json_vector(getattr(event, "point_world", ())),
        "incoming_direction": _json_vector(getattr(event, "incoming_direction", ())),
        "outgoing_direction": _json_vector(getattr(event, "outgoing_direction", ())),
        "surface_normal": _json_vector(getattr(event, "surface_normal", ())),
    }


def _dominant_path_records(ray_paths: list[object], *, limit: int = 3) -> list[dict[str, object]]:
    def _score(path: object) -> tuple[float, float, float]:
        try:
            source_ray = float(getattr(path, "source_ray_index", getattr(path, "ray_index", 0)) or 0)
        except Exception:
            source_ray = 0.0
        try:
            power = float(getattr(path, "branch_power", 1.0) or 0.0)
        except Exception:
            power = 0.0
        try:
            ray_index = float(getattr(path, "ray_index", 0) or 0)
        except Exception:
            ray_index = 0.0
        target = max((len(ray_paths) - 1) / 2.0, 0.0)
        return (abs(source_ray - target), -power, abs(ray_index - target))

    records: list[dict[str, object]] = []
    for path in sorted(ray_paths, key=_score)[: max(1, int(limit))]:
        events = [
            _surface_event_record(event)
            for event in list(getattr(path, "events", []) or [])
            if str(getattr(event, "event_kind", "") or "") == "surface"
        ]
        records.append(
            {
                "ray_index": int(getattr(path, "ray_index", 0) or 0),
                "source_ray_index": getattr(path, "source_ray_index", None),
                "branch_path": str(getattr(path, "branch_path", "") or ""),
                "branch_power": getattr(path, "branch_power", None),
                "terminal_status": ray_path_terminal_status_from_events(path),
                "surface_sequence": Kraken3DInspector._ray_path_surface_sequence_summary(path),
                "events": events,
            }
        )
    return records


def _optical_axis_report(inspector: Kraken3DInspector) -> list[dict[str, object]]:
    records = []
    for record in list(getattr(inspector, "_optical_axis_pick_records", []) or []):
        points = np.asarray(record.get("points", ()), dtype=float)
        records.append(
            {
                "axis_id": str(record.get("axis_id", "") or ""),
                "axis_label": str(record.get("axis_label", "") or ""),
                "axis_kind": str(record.get("axis_kind", "") or ""),
                "points": [_json_vector(point) for point in points[:2]] if points.ndim == 2 and points.shape[0] >= 2 else [],
            }
        )
    return records


def _scene_report(app: KrakenLayoutEditor, inspector: Kraken3DInspector, label: str) -> dict[str, Any]:
    scene_bundle = getattr(inspector, "_current_scene_bundle", None)
    ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
    file_backed_rows = [
        index
        for index in range(len(app.rows))
        if app._file_backed_stl_row_at(index) is not None
    ]
    render_rows = list(app._preview_render_rows(scene_bundle))
    render_file_backed_rows = []
    for index, row in enumerate(render_rows):
        try:
            path = app._stl_path_from_row(row)
        except Exception:
            path = None
        if path is not None and Path(path).exists():
            render_file_backed_rows.append(index)
    terminal_counts: dict[str, int] = {}
    sequence_counts: dict[str, int] = {}
    for path in ray_paths:
        status = str(ray_path_terminal_status_from_events(path) or "unknown").strip() or "unknown"
        terminal_counts[status or "unknown"] = int(terminal_counts.get(status or "unknown", 0)) + 1
        sequence = Kraken3DInspector._ray_path_surface_sequence_summary(path)
        if sequence:
            sequence_counts[sequence] = int(sequence_counts.get(sequence, 0)) + 1
    return {
        "label": label,
        "rows": len(app.rows),
        "file_backed_rows": file_backed_rows,
        "render_file_backed_rows": render_file_backed_rows,
        "has_optical_overlay": app.imported_optical_step_path is not None,
        "ray_paths": len(ray_paths),
        "terminal_counts": terminal_counts,
        "sequence_counts": sequence_counts,
        "dominant_paths": _dominant_path_records(ray_paths),
        "optical_axis_records": _optical_axis_report(inspector),
        "actor_counts": inspector._debug_actor_counts(),
        "status": str(inspector.status_var.get()),
    }


def _save_step(
    output_dir: Path,
    inspector: Kraken3DInspector,
    reports: list[dict[str, Any]],
    app: KrakenLayoutEditor,
    number: int,
    label: str,
) -> Path:
    path = _save_vtk_snapshot(inspector, output_dir / f"STEP{int(number)}.png")
    report = _scene_report(app, inspector, label)
    report["image"] = str(path.relative_to(PROJECT_ROOT))
    reports.append(report)
    return path


def _assert_final_state(reports: list[dict[str, Any]]) -> None:
    final = reports[-1]
    if int(final.get("ray_paths", 0)) <= 0:
        raise RuntimeError("Final STEP workflow trace produced no ray paths.")
    if not final.get("has_optical_overlay"):
        raise RuntimeError("Final workflow should include the transient second STEP overlay before Trace Ray.")
    file_backed_rows = list(final.get("file_backed_rows", []) or [])
    if file_backed_rows != [1]:
        raise RuntimeError(f"Expected exactly one promoted physics STEP row before the live overlay; got {file_backed_rows}.")
    actor_counts = dict(final.get("actor_counts", {}) or {})
    step_actor_labels = dict(actor_counts.get("step_actor_labels", {}) or {})
    if step_actor_labels:
        raise RuntimeError(
            "Final live trace still rendered a display-only STEP overlay in addition to the traced transient row; "
            f"counts={actor_counts}."
        )
    row_actor_rows = sorted(int(value) for value in list(actor_counts.get("row_actor_rows", []) or []))
    physical_trace_rows = [value for value in row_actor_rows if value > 0]
    if physical_trace_rows != [1, 2]:
        raise RuntimeError(
            "Final live trace should render the promoted penta row and one transient trace row only; "
            f"row actors={row_actor_rows}, counts={actor_counts}."
        )


def capture(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    reports: list[dict[str, Any]] = []
    outputs: list[Path] = []
    try:
        app.geometry("1800x1040+20+20")
        _configure_base_editor(app)
        inspector = _open_3d_inspector(app)

        _refresh(inspector, reset_camera=True)
        outputs.append(_save_step(output_dir, inspector, reports, app, 1, "base Object/Image trace"))

        _set_optical_step_overlay(
            app,
            PRISM_42779_STEP,
            offset_xyz=(0.0, 48.0, 35.338052809592156),
            rotation_xyz=(0.0, 90.0, 180.0),
        )
        _refresh(inspector)
        outputs.append(_save_step(output_dir, inspector, reports, app, 2, "imported penta STEP above ray"))

        app._set_step_placement_offset_xyz("optical", (0.0, 5.338434219360337, 35.338052809592156))
        app._invalidate_preview_scene_trace()
        _refresh(inspector)
        outputs.append(_save_step(output_dir, inspector, reports, app, 3, "penta STEP carried onto ray"))

        _refresh(inspector, live=True)
        outputs.append(_save_step(output_dir, inspector, reports, app, 4, "Trace Ray with transient penta STEP"))

        penta_row = _promote_current_optical_step(app)
        _refresh(inspector)
        outputs.append(_save_step(output_dir, inspector, reports, app, 5, f"promoted penta STEP row S{penta_row}"))

        _set_ray_count(app, 31, 5.0)
        _refresh(inspector)
        outputs.append(_save_step(output_dir, inspector, reports, app, 6, "promoted penta with 31-ray cone"))

        _set_optical_step_overlay(
            app,
            PRISM_32336_STEP,
            offset_xyz=(0.0, -58.0, 48.0),
            rotation_xyz=(0.0, 0.0, 0.0),
        )
        _refresh(inspector)
        outputs.append(_save_step(output_dir, inspector, reports, app, 7, "second right-angle STEP staged"))

        _refresh(inspector, live=True)
        outputs.append(_save_step(output_dir, inspector, reports, app, 8, "Trace Ray with promoted penta plus transient right-angle STEP"))

        _assert_final_state(reports)
    except Exception as exc:
        reports.append({"label": "error", "error": _short_error_message(exc)})
        raise
    finally:
        report_path = output_dir / "step_workflow_report.json"
        report_path.write_text(json.dumps(reports, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    print(args.output_dir / "step_workflow_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
