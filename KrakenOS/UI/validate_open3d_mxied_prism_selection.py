"""Validate imported penta-prism face picking from the saved mxied layout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _save_vtk_snapshot, _settle
from KrakenOS.UI.capture_vendor_prism_case_study_screenshots import PROJECT_ROOT
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data, _short_error_message


DEFAULT_LAYOUT_PATH = PROJECT_ROOT / "attachment" / "mxied.py"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "attachment" / "open3d_mxied_prism_selection"


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


def _safe_unit(values) -> np.ndarray | None:
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


def _view_up_for_normal(normal: np.ndarray) -> tuple[float, float, float]:
    candidate = np.asarray((0.0, 1.0, 0.0), dtype=float)
    if abs(float(np.dot(candidate, normal))) > 0.88:
        candidate = np.asarray((1.0, 0.0, 0.0), dtype=float)
    up = candidate - normal * float(np.dot(candidate, normal))
    norm = float(np.linalg.norm(up))
    if not np.isfinite(norm) or norm <= 1.0e-12:
        return (0.0, 1.0, 0.0)
    return tuple(float(value) for value in up / norm)


def _face_center(face: dict[str, object]) -> np.ndarray | None:
    for key in ("centroid_world", "centroid"):
        try:
            center = np.asarray(face.get(key), dtype=float).reshape(-1)[:3]
        except Exception:
            center = np.asarray([], dtype=float)
        if center.size >= 3 and np.all(np.isfinite(center[:3])):
            return center[:3]
    return None


def _promoted_prism_face_source(app: KrakenLayoutEditor, inspector) -> tuple[str, int | None, list[dict[str, object]]]:
    """Return the saved-layout prism faces to validate.

    `mxied.py` can contain both a live imported STEP overlay and already
    promoted optical-solid rows. Prefer the live overlay when it is prism-like;
    otherwise validate the promoted penta/right-angle prism row that is actually
    visible in the saved 3D scene.
    """
    try:
        metadata = app._step_overlay_face_metadata("optical")
        faces = [face for face in list(metadata.get("faces", []) or []) if isinstance(face, dict)]
    except Exception:
        faces = []
    if len(faces) >= 5:
        return "step", None, faces

    candidates: list[tuple[int, int, int, list[dict[str, object]]]] = []
    for row_index in range(len(app.rows)):
        try:
            row, path, metadata = app._optical_solid_face_metadata_for_row(int(row_index))
        except Exception:
            continue
        advanced = dict(getattr(row, "advanced", {}) or {})
        promotion = dict(advanced.get("StepOverlayPromotion", {}) or {})
        placement = dict(advanced.get("ScenePlacement", {}) or {})
        source_text = " ".join(
            (
                str(path or ""),
                str(getattr(row, "OpticalSolidSourcePath", "") or ""),
                str(advanced.get("OpticalSolidSourcePath", "") or ""),
                str(promotion.get("source_step_path", "") or ""),
                str(placement.get("promotion_source_step_path", "") or ""),
            )
        ).lower()
        if "prism" not in source_text and "42779" not in source_text and "45595" not in source_text:
            continue
        try:
            transform = inspector._runtime_transform_for_row(inspector.__dict__.get("_current_system"), int(row_index))
            if transform is not None:
                faces = inspector._runtime_world_face_records_for_pick(row, metadata, transform)
            else:
                faces = app._optical_solid_face_records_for_temp_row(row, int(row_index), metadata)
        except Exception:
            faces = []
        faces = [face for face in list(faces or []) if isinstance(face, dict)]
        if len(faces) < 5:
            continue
        penta_rank = 0 if "42779" in source_text else 1
        candidates.append((penta_rank, -len(faces), int(row_index), faces))
    if not candidates:
        return "step", None, []
    _rank, _face_sort, row_index, faces = min(candidates, key=lambda item: item[:3])
    return "row", int(row_index), faces


def validate_case(layout_path: Path = DEFAULT_LAYOUT_PATH, output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    if not layout_path.exists():
        raise RuntimeError(f"Missing layout: {layout_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry("1800x1040+20+20")
        _load_saved_layout(app, layout_path)
        inspector = _open_3d_inspector(app)
        _settle(inspector, 0.35)
        inspector.set_camera_preset("iso")
        initial_image = _save_vtk_snapshot(inspector, output_dir / "initial_mxied.png")

        source_kind, source_row_index, faces = _promoted_prism_face_source(app, inspector)
        if len(faces) < 5:
            raise RuntimeError(f"Expected penta/right-angle prism faces, got {len(faces)}")
        try:
            _scene_center, scene_radius = inspector._scene_bounds()
        except Exception:
            scene_radius = 80.0
        scene_radius = max(float(scene_radius), 20.0)
        camera = inspector._renderer.GetActiveCamera() if inspector._renderer is not None else None
        if camera is None:
            raise RuntimeError("Open 3D renderer has no active camera")

        picked: list[dict[str, object]] = []
        failures: list[str] = []
        for face in faces:
            face_id = str(face.get("face_id", "") or "").strip()
            center = _face_center(face)
            normal = _safe_unit(face.get("normal_world", face.get("normal")))
            if center is None or normal is None:
                failures.append(f"{face_id or 'face'} has no finite center/normal")
                continue
            camera.SetFocalPoint(*tuple(float(value) for value in center[:3]))
            camera.SetPosition(*tuple(float(value) for value in center[:3] + normal[:3] * scene_radius * 2.8))
            camera.SetViewUp(*_view_up_for_normal(normal))
            camera.ParallelProjectionOn()
            camera.SetParallelScale(max(scene_radius * 0.35, 18.0))
            inspector._reset_camera_clipping_range_for_scene()
            inspector.render()
            _settle(inspector, 0.03)
            display = inspector._world_to_display_2d(center)
            if display is None:
                failures.append(f"{face_id} center did not project to screen")
                continue
            picked_face = ""
            if source_kind == "row" and source_row_index is not None:
                row_pick = inspector._row_face_ray_pick_for_display_xy(int(source_row_index), display[:2])
                if row_pick is not None:
                    picked_face = str(row_pick.face.get("face_id", "") or "").strip()
            else:
                feature_pick = inspector._step_feature_pick_any_for_display_xy(display[:2], labels=("optical",))
                if isinstance(feature_pick, dict):
                    payload = feature_pick.get("feature_pick")
                    if isinstance(payload, dict):
                        picked_face = str(payload.get("face_id", "") or "").strip()
            picked.append({"face_id": face_id, "picked_face_id": picked_face})
            if picked_face != face_id:
                failures.append(f"{face_id} projected pick returned {picked_face or 'none'}")

        inspector.show_rotation_handles_var.set(True)
        if source_kind == "row" and source_row_index is not None:
            inspector._placement_handle_selected_row_index = int(source_row_index)
            inspector._set_row_highlight(int(source_row_index))
            app._select_table_row(int(source_row_index))
            inspector.refresh_from_editor()
            _settle(inspector, 0.1)
            if not getattr(inspector, "_actor_placement_rotate_map", {}):
                failures.append("Selected promoted prism did not show placement rotation handles before clear")
            if not inspector._clear_open3d_selection(render=False):
                failures.append("Open 3D clear did not report a selected promoted prism row")
            if getattr(inspector, "_actor_placement_rotate_map", {}):
                failures.append("Blank-clear path left promoted prism placement handles visible")
            inspector._placement_handle_selected_row_index = int(source_row_index)
            inspector._set_row_highlight(int(source_row_index))
            app._select_table_row(int(source_row_index))
            inspector.refresh_from_editor()
            _settle(inspector, 0.1)
            if not getattr(inspector, "_actor_placement_rotate_map", {}):
                failures.append("Could not arm promoted prism handles before Center Row mode")
        else:
            app.select_step_component("optical")
            inspector.refresh_from_editor()
            inspector.show_step_rotation_handler("optical")
            _settle(inspector, 0.1)
            if not getattr(inspector, "_actor_step_rotate_map", {}):
                failures.append("Selected imported prism did not show rotation handles before clear")
            if not inspector._clear_open3d_selection(render=False):
                failures.append("Open 3D clear did not report a selected imported STEP")
            if getattr(app, "_selected_step_label", None) is not None:
                failures.append("Blank-clear path left imported STEP selected")
            if getattr(inspector, "_actor_step_rotate_map", {}):
                failures.append("Blank-clear path left imported STEP rotation handles visible")
            app.select_step_component("optical")
            inspector.refresh_from_editor()
            inspector.show_step_rotation_handler("optical")
            _settle(inspector, 0.1)
            if not getattr(inspector, "_actor_step_rotate_map", {}):
                failures.append("Could not arm imported STEP handles before Center Row mode")
        inspector.start_center_row_to_ray()
        _settle(inspector, 0.1)
        if getattr(app, "_selected_step_label", None) is not None:
            failures.append("Center Row mode did not clear the selected imported STEP")
        if getattr(inspector, "_actor_step_rotate_map", {}):
            failures.append("Center Row mode left STEP rotation handles visible")
        if getattr(inspector, "_actor_placement_rotate_map", {}):
            failures.append("Center Row mode left promoted-row placement handles visible")
        center_mode_pick_failures: list[str] = []
        for face in faces:
            face_id = str(face.get("face_id", "") or "").strip()
            center = _face_center(face)
            normal = _safe_unit(face.get("normal_world", face.get("normal")))
            if center is None or normal is None:
                continue
            camera.SetFocalPoint(*tuple(float(value) for value in center[:3]))
            camera.SetPosition(*tuple(float(value) for value in center[:3] + normal[:3] * scene_radius * 2.8))
            camera.SetViewUp(*_view_up_for_normal(normal))
            camera.ParallelProjectionOn()
            camera.SetParallelScale(max(scene_radius * 0.35, 18.0))
            inspector._reset_camera_clipping_range_for_scene()
            inspector.render()
            _settle(inspector, 0.02)
            display = inspector._world_to_display_2d(center)
            if display is None:
                continue
            source_pick = inspector._center_axis_source_pick_ignoring_axis_overlays(float(display[0]), float(display[1]))
            picked_step = str(source_pick.get("step_label", "") if isinstance(source_pick, dict) else "")
            feature_pick = source_pick.get("feature_pick") if isinstance(source_pick, dict) else None
            payload_face = str(feature_pick.get("face_id", "") if isinstance(feature_pick, dict) else "").strip()
            row_face_pick = source_pick.get("row_face_pick") if isinstance(source_pick, dict) else None
            row_face_id = ""
            if row_face_pick is not None:
                row_face_id = str(row_face_pick.face.get("face_id", "") or "").strip()
            if source_kind == "row" and row_face_id != face_id:
                center_mode_pick_failures.append(f"{face_id}->row/{row_face_id or 'none'}")
            elif source_kind != "row" and (picked_step != "optical" or payload_face != face_id) and not row_face_id:
                center_mode_pick_failures.append(f"{face_id}->{picked_step}/{payload_face or 'none'}")
        if center_mode_pick_failures:
            failures.append("Center Row mode could not pick imported penta faces: " + ", ".join(center_mode_pick_failures))

        final_image = _save_vtk_snapshot(inspector, output_dir / "after_clear_selection.png")
        report = {
            "ok": not failures,
            "layout_path": str(layout_path.resolve()),
            "source_kind": source_kind,
            "source_row_index": source_row_index,
            "initial_image": str(initial_image),
            "final_image": str(final_image),
            "face_count": len(faces),
            "picked": picked,
            "failures": failures,
        }
        report_path = output_dir / "mxied_prism_selection_report.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report["report_path"] = str(report_path)
        if failures:
            raise RuntimeError("; ".join(failures))
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
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    try:
        report = validate_case(args.layout, args.output_dir)
    except Exception as exc:
        print(f"Open 3D mxied prism selection validation failed: {_short_error_message(exc)}")
        return 1
    print(
        "Open 3D mxied prism selection validation passed: "
        f"faces={report['face_count']} report={report['report_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
