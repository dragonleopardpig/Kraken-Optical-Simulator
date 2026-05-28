"""Validate Center Row -> Optical Axis face-pick visuals.

This drives the real Tk/VTK Open 3D inspector and writes screenshots for the
specific failure class where Center Row mode could leave STEP rotation handles
visible, or round lens-like STEP bodies could hover-highlight the whole body
instead of a front, rear, or side face.

Run under an X display, for example:

    env DISPLAY=:99 python -m KrakenOS.UI.validate_open3d_center_row_face_visual
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from KrakenOS.UI.capture_open3d_lens_face_selection_snap import LENS_STEP
from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
    PROJECT_ROOT,
    _configure_base_editor,
    _open_3d_inspector,
    _refresh,
    _save_vtk_snapshot,
    _set_optical_step_overlay,
)
from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor, _load_python_data, _short_error_message


MXIED_LAYOUT = PROJECT_ROOT / "attachment" / "mxied.py"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "attachment" / "open3d_center_row_face_visual"


def _settle(widget, delay_s: float = 0.2) -> None:
    widget.update_idletasks()
    widget.update()
    time.sleep(delay_s)
    widget.update_idletasks()
    widget.update()


def _load_saved_layout(app: KrakenLayoutEditor, path: Path) -> None:
    info = _load_python_data(path)
    app._reset_complete_layout_runtime_state(close_viewers=True)
    app.current_layout_file = path.resolve()
    app.rows = app._normalized_rows_copy([app._row_from_layout_item(item) for item in info["surfaces"]])
    app._auto_assign_missing_elements(app.rows)
    app._apply_layout_settings(info.get("settings", {}))
    app._normalize_special_rows()
    app._sync_table()
    app._select_table_row(0)
    app._invalidate_preview_scene_trace()
    app.auto_save_plot_var.set(False)
    app.update_idletasks()
    app.update()


def _safe_unit(values: object) -> np.ndarray | None:
    try:
        vector = np.asarray(values, dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
        return None
    norm = float(np.linalg.norm(vector[:3]))
    if not np.isfinite(norm) or norm <= 1.0e-12:
        return None
    return vector[:3] / norm


def _face_center(face: dict[str, object]) -> np.ndarray | None:
    for key in ("centroid_world", "centroid"):
        try:
            center = np.asarray(face.get(key), dtype=float).reshape(-1)[:3]
        except Exception:
            center = np.asarray([], dtype=float)
        if center.size >= 3 and np.all(np.isfinite(center[:3])):
            return center[:3]
    return None


def _face_normal(face: dict[str, object]) -> np.ndarray | None:
    for key in ("normal_world", "normal"):
        normal = _safe_unit(face.get(key))
        if normal is not None:
            return normal
    return None


def _view_up_for_normal(normal: np.ndarray) -> tuple[float, float, float]:
    candidate = np.asarray((0.0, 1.0, 0.0), dtype=float)
    if abs(float(np.dot(candidate, normal))) > 0.88:
        candidate = np.asarray((1.0, 0.0, 0.0), dtype=float)
    up = candidate - normal * float(np.dot(candidate, normal))
    norm = float(np.linalg.norm(up))
    if not np.isfinite(norm) or norm <= 1.0e-12:
        return (0.0, 1.0, 0.0)
    return tuple(float(value) for value in up / norm)


def _scene_radius(inspector: Kraken3DInspector) -> float:
    try:
        _center, radius = inspector._scene_bounds()
    except Exception:
        radius = 80.0
    return max(float(radius), 20.0)


def _point_to_display(inspector: Kraken3DInspector, point: np.ndarray) -> tuple[float, float] | None:
    display = inspector._world_to_display_2d(point)
    if display is None:
        return None
    try:
        vector = np.asarray(display, dtype=float).reshape(-1)[:2]
    except Exception:
        return None
    if vector.size < 2 or not np.all(np.isfinite(vector[:2])):
        return None
    return float(vector[0]), float(vector[1])


def _aim_camera_at_face(inspector: Kraken3DInspector, face: dict[str, object], *, scale: float = 0.45) -> tuple[float, float]:
    center = _face_center(face)
    normal = _face_normal(face)
    if center is None or normal is None:
        raise RuntimeError(f"Face has no finite center/normal: {face.get('face_id', '<unknown>')}")
    if inspector._renderer is None:
        raise RuntimeError("Open 3D renderer is unavailable.")
    radius = _scene_radius(inspector)
    camera = inspector._renderer.GetActiveCamera()
    if camera is None:
        raise RuntimeError("Open 3D renderer has no active camera.")
    camera.SetFocalPoint(*tuple(float(value) for value in center[:3]))
    camera.SetPosition(*tuple(float(value) for value in center[:3] + normal[:3] * radius * 2.8))
    camera.SetViewUp(*_view_up_for_normal(normal))
    camera.ParallelProjectionOn()
    camera.SetParallelScale(max(radius * float(scale), 12.0))
    inspector._reset_camera_clipping_range_for_scene()
    inspector.render()
    _settle(inspector, 0.05)
    display = _point_to_display(inspector, center)
    if display is None:
        raise RuntimeError(f"Face center did not project to display: {face.get('face_id', '<unknown>')}")
    return display


def _hover_actor_stats(inspector: Kraken3DInspector) -> dict[str, object]:
    actor = getattr(inspector, "_hover_step_outline_actor", None)
    if actor is None:
        return {"present": False, "n_points": 0, "n_polys": 0, "n_cells": 0, "bounds": []}
    try:
        data = actor.GetMapper().GetInput()
    except Exception:
        data = None
    if data is None:
        return {"present": False, "n_points": 0, "n_polys": 0, "n_cells": 0, "bounds": []}
    try:
        bounds = [float(value) for value in data.GetBounds()]
    except Exception:
        bounds = []
    try:
        n_polys = int(data.GetNumberOfPolys())
    except Exception:
        n_polys = 0
    try:
        n_cells = int(data.GetNumberOfCells())
    except Exception:
        n_cells = 0
    return {
        "present": True,
        "n_points": int(data.GetNumberOfPoints()),
        "n_polys": int(n_polys),
        "n_cells": int(n_cells),
        "bounds": bounds,
    }


def _body_cell_count(app: KrakenLayoutEditor, label: str) -> int:
    try:
        mesh = app._transformed_imported_step_mesh_for_label(label)
    except Exception:
        return 0
    try:
        return int(getattr(mesh, "n_cells", 0))
    except Exception:
        return 0


def _set_step_feature_hover(
    inspector: Kraken3DInspector,
    feature_pick: dict[str, object],
    hover_key: tuple[object, ...],
) -> dict[str, object]:
    feature = feature_pick.get("feature")
    if not isinstance(feature, tuple) or len(feature) < 2:
        raise RuntimeError("Feature pick did not return hover geometry.")
    outline = inspector._hover_overlay_for_feature(feature[0], feature[1])
    inspector._set_step_hover_outline(outline, hover_key)
    inspector.render()
    _settle(inspector, 0.05)
    return _hover_actor_stats(inspector)


def _set_row_feature_hover(
    inspector: Kraken3DInspector,
    row_index: int,
    row_face_pick: object,
    hover_key: tuple[object, ...],
) -> dict[str, object]:
    face = getattr(row_face_pick, "face", None)
    outline = inspector._hover_overlay_for_row_face(int(row_index), face)
    inspector._set_step_hover_outline(outline, hover_key)
    inspector.render()
    _settle(inspector, 0.05)
    return _hover_actor_stats(inspector)


def _lens_face_targets(app: KrakenLayoutEditor) -> dict[str, dict[str, object]]:
    metadata = app._step_overlay_face_metadata("optical")
    faces = [face for face in list(metadata.get("faces", []) or []) if isinstance(face, dict)]
    if not faces:
        raise RuntimeError("Imported lens STEP metadata exposes no faces.")
    caps = [
        face
        for face in faces
        if str(face.get("assignment_source", "") or "").startswith("step_analytic_axisymmetric_group")
    ]
    sides = [
        face
        for face in faces
        if str(face.get("surface_type", "") or "").strip().lower() == "cylinder"
    ]
    if len(caps) < 2 or not sides:
        raise RuntimeError(f"Expected lens front/rear/side records; got caps={len(caps)}, sides={len(sides)}.")

    def normal_z(face: dict[str, object]) -> float:
        normal = _face_normal(face)
        return float(normal[2]) if normal is not None else 0.0

    def normal_y(face: dict[str, object]) -> float:
        normal = _face_normal(face)
        return float(normal[1]) if normal is not None else 0.0

    return {
        "front": min(caps, key=normal_z),
        "rear": max(caps, key=normal_z),
        "side": max(sides, key=lambda face: abs(normal_y(face))),
    }


def _close_open3d(app: KrakenLayoutEditor) -> None:
    try:
        if app._three_d_inspector is not None:
            app._three_d_inspector._on_close()
    except Exception:
        pass


def _validate_lens_center_row(app: KrakenLayoutEditor, output_dir: Path) -> dict[str, object]:
    report: dict[str, object] = {"lens_step": str(LENS_STEP), "snapshots": []}
    failures: list[str] = []
    try:
        _configure_base_editor(app)
        inspector = _open_3d_inspector(app)
        inspector.show_rays_var.set(False)
        inspector.show_rotation_handles_var.set(True)
        _set_optical_step_overlay(app, LENS_STEP, offset_xyz=(8.0, -6.0, 35.0))
        _refresh(inspector, reset_camera=True)
        inspector.set_camera_preset("bottom")
        inspector.show_step_rotation_handler("optical")
        _settle(inspector, 0.1)
        before_handles = int(len(getattr(inspector, "_actor_step_rotate_map", {}) or {}))
        report["handles_before_center_row"] = before_handles
        report["snapshots"].append(str(_save_vtk_snapshot(inspector, output_dir / "01_lens_before_center_row.png")))
        if before_handles <= 0:
            failures.append("Lens STEP handles were not visible before Center Row setup.")

        inspector.start_center_row_to_ray()
        _settle(inspector, 0.1)
        handles_after = int(len(getattr(inspector, "_actor_step_rotate_map", {}) or {}))
        report["handles_after_center_row"] = handles_after
        if getattr(app, "_selected_step_label", None) is not None:
            failures.append("Center Row left the imported lens selected.")
        if handles_after:
            failures.append("Center Row left lens rotation handles visible.")

        body_cells = _body_cell_count(app, "optical")
        report["body_cells"] = int(body_cells)
        face_reports: dict[str, object] = {}
        for name, face in _lens_face_targets(app).items():
            display_xy = _aim_camera_at_face(inspector, face, scale=0.28)
            source_pick = inspector._center_axis_source_pick_ignoring_axis_overlays(*display_xy)
            feature_pick = source_pick.get("feature_pick") if isinstance(source_pick, dict) else None
            if not isinstance(feature_pick, dict):
                failures.append(f"Lens {name} face did not produce an imported STEP feature pick.")
                continue
            picked_face_id = str(feature_pick.get("face_id", "") or "").strip()
            target_face_id = str(face.get("face_id", "") or "").strip()
            hover_stats = _set_step_feature_hover(inspector, feature_pick, ("lens", name, picked_face_id))
            snapshot = _save_vtk_snapshot(inspector, output_dir / f"02_lens_{name}_face_hover.png")
            report["snapshots"].append(str(snapshot))
            n_polys = int(hover_stats.get("n_polys", 0) or 0)
            if picked_face_id != target_face_id:
                failures.append(f"Lens {name} pick returned {picked_face_id or 'none'}, expected {target_face_id}.")
            if n_polys <= 0:
                failures.append(f"Lens {name} hover did not contain selected face polygons.")
            if body_cells > 0 and n_polys >= int(0.85 * body_cells):
                failures.append(f"Lens {name} hover appears to cover the whole body ({n_polys}/{body_cells} polys).")
            face_reports[name] = {
                "target_face_id": target_face_id,
                "picked_face_id": picked_face_id,
                "display_xy": [float(display_xy[0]), float(display_xy[1])],
                "hover": hover_stats,
                "snapshot": str(snapshot),
            }
        picked_ids = [
            str(record.get("picked_face_id", "") or "")
            for record in face_reports.values()
            if isinstance(record, dict)
        ]
        if len(set(picked_ids)) < 3:
            failures.append(f"Lens Center Row picks did not separate front/rear/side faces: {picked_ids}.")
        report["faces"] = face_reports
    finally:
        _close_open3d(app)
    report["failures"] = failures
    report["ok"] = not failures
    return report


def _validate_prism_center_row(app: KrakenLayoutEditor, output_dir: Path) -> dict[str, object]:
    report: dict[str, object] = {"layout": str(MXIED_LAYOUT), "snapshots": []}
    failures: list[str] = []
    try:
        _load_saved_layout(app, MXIED_LAYOUT)
        inspector = _open_3d_inspector(app)
        inspector.show_rays_var.set(False)
        inspector.show_rotation_handles_var.set(True)
        inspector.refresh_from_editor(force_retrace=True)
        inspector.set_camera_preset("iso")
        app.select_step_component("optical")
        inspector.show_step_rotation_handler("optical")
        _settle(inspector, 0.1)
        before_handles = int(len(getattr(inspector, "_actor_step_rotate_map", {}) or {}))
        report["handles_before_center_row"] = before_handles
        report["snapshots"].append(str(_save_vtk_snapshot(inspector, output_dir / "03_prism_before_center_row.png")))
        if before_handles <= 0:
            failures.append("Prism STEP handles were not visible before Center Row setup.")

        inspector.start_center_row_to_ray()
        _settle(inspector, 0.1)
        handles_after = int(len(getattr(inspector, "_actor_step_rotate_map", {}) or {}))
        report["handles_after_center_row"] = handles_after
        report["snapshots"].append(str(_save_vtk_snapshot(inspector, output_dir / "04_prism_center_row_no_handles.png")))
        if getattr(app, "_selected_step_label", None) is not None:
            failures.append("Center Row left the imported prism selected.")
        if handles_after:
            failures.append("Center Row left prism rotation handles visible.")

        metadata = app._step_overlay_face_metadata("optical")
        faces = [face for face in list(metadata.get("faces", []) or []) if isinstance(face, dict)]
        selected_face_report = None
        for face in faces:
            target_face_id = str(face.get("face_id", "") or "").strip()
            try:
                display_xy = _aim_camera_at_face(inspector, face, scale=0.45)
            except Exception:
                continue
            source_pick = inspector._center_axis_source_pick_ignoring_axis_overlays(*display_xy)
            if not isinstance(source_pick, dict):
                continue
            feature_pick = source_pick.get("feature_pick")
            if isinstance(feature_pick, dict):
                picked_face_id = str(feature_pick.get("face_id", "") or "").strip()
                hover_stats = _set_step_feature_hover(inspector, feature_pick, ("prism-step", picked_face_id))
                selected_face_report = {
                    "source": "imported-step",
                    "target_face_id": target_face_id,
                    "picked_face_id": picked_face_id,
                    "hover": hover_stats,
                }
                break
            row_face_pick = source_pick.get("row_face_pick")
            if row_face_pick is not None and source_pick.get("row_index") is not None:
                row_index = int(source_pick.get("row_index"))
                picked_face_id = str(row_face_pick.face.get("face_id", "") or "").strip()
                hover_stats = _set_row_feature_hover(inspector, row_index, row_face_pick, ("prism-row", row_index, picked_face_id))
                selected_face_report = {
                    "source": "row-backed-solid",
                    "row_index": int(row_index),
                    "target_face_id": target_face_id,
                    "picked_face_id": picked_face_id,
                    "hover": hover_stats,
                }
                break
        if selected_face_report is None:
            failures.append("Center Row could not hover-pick any prism face after clearing handles.")
        else:
            n_points = int(dict(selected_face_report.get("hover", {})).get("n_points", 0) or 0)
            if n_points <= 0:
                failures.append("Prism Center Row hover produced no visible face outline.")
            report["face_pick"] = selected_face_report
            report["snapshots"].append(str(_save_vtk_snapshot(inspector, output_dir / "05_prism_face_hover.png")))
    finally:
        _close_open3d(app)
    report["failures"] = failures
    report["ok"] = not failures
    return report


def validate(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry("1800x1040+20+20")
        report = {
            "output_dir": str(output_dir),
            "lens": _validate_lens_center_row(app, output_dir),
            "prism": _validate_prism_center_row(app, output_dir),
        }
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    failures: list[str] = []
    for section in ("lens", "prism"):
        section_report = report.get(section)
        if isinstance(section_report, dict):
            failures.extend(f"{section}: {failure}" for failure in list(section_report.get("failures", []) or []))
    report["failures"] = failures
    report["ok"] = not failures
    report_path = output_dir / "center_row_face_visual_report.json"
    report["report"] = str(report_path)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failures:
        raise RuntimeError("; ".join(failures))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    try:
        report = validate(args.output_dir)
    except Exception as exc:
        print(f"Open 3D Center Row face visual validation failed: {_short_error_message(exc)}")
        return 1
    print(
        "Open 3D Center Row face visual validation passed: "
        f"report={report['report']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
