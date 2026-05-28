"""Capture and validate imported lens STEP face selection and axis snap.

This drives the real Tk/VTK Open 3D inspector.  It is intentionally screenshot
backed because the imported-lens face picker can pass metadata-only tests while
still failing through the VTK actor/cell path used by the UI.

Run under an X display, for example:

    env DISPLAY=:99 python -m KrakenOS.UI.capture_open3d_lens_face_selection_snap
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
    PROJECT_ROOT,
    _configure_base_editor,
    _open_3d_inspector,
    _refresh,
    _save_vtk_snapshot,
    _set_optical_step_overlay,
)
from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor, _short_error_message


LENS_STEP = PROJECT_ROOT / "attachment" / "Lens" / "Aspherized_Achromatic_Lenses" / "step_49665.step"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "attachment" / "open3d_lens_face_selection_snap"


def _settle(widget, delay_s: float = 0.25) -> None:
    widget.update_idletasks()
    widget.update()
    time.sleep(delay_s)
    widget.update_idletasks()
    widget.update()


def _world_to_display(inspector: Kraken3DInspector, point: object) -> tuple[int, int]:
    if inspector._renderer is None:
        raise RuntimeError("Open 3D renderer is unavailable.")
    vector = np.asarray(point, dtype=float).reshape(-1)[:3]
    if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
        raise RuntimeError(f"Cannot project non-finite point: {point!r}")
    inspector._renderer.SetWorldPoint(float(vector[0]), float(vector[1]), float(vector[2]), 1.0)
    inspector._renderer.WorldToDisplay()
    display = np.asarray(inspector._renderer.GetDisplayPoint(), dtype=float).reshape(3)
    if not np.all(np.isfinite(display[:2])):
        raise RuntimeError(f"Cannot project world point to display: {point!r}")
    return int(round(float(display[0]))), int(round(float(display[1])))


def _front_lens_face(app: KrakenLayoutEditor) -> dict[str, object]:
    metadata = app._step_overlay_face_metadata("optical")
    candidates = [face for face in list(metadata.get("faces", []) or []) if isinstance(face, dict)]
    if not candidates:
        raise RuntimeError("Imported optical STEP metadata did not expose any selectable faces.")
    optical_faces = [
        face
        for face in candidates
        if str(face.get("assignment_source", "") or "").startswith("step_analytic_axisymmetric_group")
    ]
    pool = optical_faces or candidates
    for face in pool:
        try:
            normal = np.asarray(face.get("normal", ()), dtype=float).reshape(-1)[:3]
        except Exception:
            continue
        if normal.size >= 3 and np.all(np.isfinite(normal[:3])) and float(normal[2]) < -0.75:
            return face
    return pool[0]


def _pick_lens_face(inspector: Kraken3DInspector, face: dict[str, object]) -> dict[str, object]:
    if inspector._picker is None or inspector._renderer is None:
        raise RuntimeError("Open 3D picker is unavailable.")
    x, y = _world_to_display(inspector, face.get("centroid", ()))
    inspector._picker.Pick(int(x), int(y), 0.0, inspector._renderer)
    actor = inspector._picker.GetActor()
    actor_key = inspector._actor_key(actor)
    try:
        cell_id = int(inspector._picker.GetCellId())
    except Exception:
        cell_id = -1
    feature_pick = inspector._step_feature_pick_for_display_xy(
        "optical",
        (x, y),
        actor=actor,
        actor_key=actor_key,
        cell_id=cell_id,
    )
    if feature_pick is None:
        raise RuntimeError(f"VTK cell pick did not resolve a lens face at display ({x}, {y}); cell={cell_id}.")
    feature = feature_pick.get("feature")
    if feature is None:
        raise RuntimeError(f"Lens feature pick did not return hover geometry at display ({x}, {y}); cell={cell_id}.")
    face_id = str(feature_pick.get("face_id", "") or "").strip()
    if not face_id:
        raise RuntimeError(f"Lens feature pick resolved only a generic cell, not a grouped face; cell={cell_id}.")
    outline = inspector._hover_overlay_for_feature(feature[0], feature[1])
    inspector._set_step_hover_outline(outline, ("capture", "optical", face_id))
    return {
        "display_xy": [int(x), int(y)],
        "cell_id": int(cell_id),
        "face_id": face_id,
        "surface_center": [float(value) for value in np.asarray(feature_pick.get("surface_center"), dtype=float).reshape(-1)[:3]],
    }


def _global_axis_record(inspector: Kraken3DInspector) -> dict[str, object]:
    for record in inspector._optical_axis_records_for_3d(inspector._current_scene_bundle):
        if str(record.get("axis_id", "") or "") == "axis:global":
            return record
    raise RuntimeError("Global optical-axis guide is not available in Open 3D.")


def _axis_record_count(inspector: Kraken3DInspector) -> int:
    return len(inspector._optical_axis_records_for_3d(inspector._current_scene_bundle))


def capture(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"lens_step": str(LENS_STEP), "snapshots": []}
    outputs: list[Path] = []
    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry("1800x1040+20+20")
        _configure_base_editor(app)
        inspector = _open_3d_inspector(app)
        inspector.set_camera_preset("bottom")

        _set_optical_step_overlay(app, LENS_STEP, offset_xyz=(8.0, -6.0, 35.0))
        _refresh(inspector, reset_camera=True)
        inspector.set_camera_preset("bottom")
        outputs.append(_save_vtk_snapshot(inspector, output_dir / "01_imported_lens.png"))
        report["snapshots"].append(str(outputs[-1]))

        face = _front_lens_face(app)
        report["target_face"] = {
            "face_id": str(face.get("face_id", "") or ""),
            "normal": [float(value) for value in np.asarray(face.get("normal", ()), dtype=float).reshape(-1)[:3]],
            "centroid": [float(value) for value in np.asarray(face.get("centroid", ()), dtype=float).reshape(-1)[:3]],
            "assignment_source": str(face.get("assignment_source", "") or ""),
        }
        pick = _pick_lens_face(inspector, face)
        report["pick"] = pick
        _settle(inspector, 0.2)
        outputs.append(_save_vtk_snapshot(inspector, output_dir / "02_grouped_face_hover.png"))
        report["snapshots"].append(str(outputs[-1]))

        snap = app.snap_step_overlay_face_to_optical_axis(
            "optical",
            _global_axis_record(inspector),
            face_id=str(pick["face_id"]),
        )
        if snap is None:
            raise RuntimeError(f"Lens face snap failed: {app.status_var.get()}")
        report["snap"] = {
            "face_id": str(snap.get("face_id", "") or ""),
            "axis_id": str(snap.get("axis_id", "") or ""),
            "angle_error_deg": float(snap.get("angle_error_deg", float("nan"))),
            "rotation_deg": [float(value) for value in snap.get("rotation_deg", ())],
            "placement_offset_xyz": [float(value) for value in snap.get("placement_offset_xyz", ())],
        }
        _refresh(inspector)
        inspector.set_camera_preset("zy")
        axis_count = _axis_record_count(inspector)
        report["axis_count_after_snap"] = axis_count
        if axis_count != 1:
            raise RuntimeError(f"Expected one optical-axis guide after axial lens snap, got {axis_count}.")
        outputs.append(_save_vtk_snapshot(inspector, output_dir / "03_after_axis_snap.png"))
        report["snapshots"].append(str(outputs[-1]))
    except Exception as exc:
        report["error"] = _short_error_message(exc)
        raise
    finally:
        (output_dir / "lens_face_selection_snap_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
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
    for path in capture(args.output_dir):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
