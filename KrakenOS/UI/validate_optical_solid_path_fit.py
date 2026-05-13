from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    ARM_VIEW_DEFAULT,
    SurfaceRow,
    auto_assign_optical_solid_face_roles,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_record_from_candidate,
    optical_solid_face_world_records,
    solve_optical_solid_face_fit,
)
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor


@dataclass
class OpticalSolidPathFitCheck:
    check: str
    ok: bool
    detail: str


def _prism_face_metadata() -> tuple[dict[str, object], str]:
    prism_path = Path(__file__).resolve().parents[1] / "Examples" / "prism.stl"
    candidates = cluster_optical_solid_planar_faces(prism_path)
    records = [optical_solid_face_record_from_candidate(candidate) for candidate in candidates]
    auto_records = auto_assign_optical_solid_face_roles(records)
    left_face = next((record for record in auto_records if str(record.get("side_2d", "")) == "Left"), None)
    if left_face is not None:
        left_face["function"] = OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT
        left_face["role"] = "Output"
    metadata = normalize_optical_solid_face_metadata(
        {"source_stl": str(prism_path), "faces": auto_records},
        candidates,
        source_stl=str(prism_path),
    )
    return metadata, str(left_face.get("face_id", "") or "") if left_face is not None else ""


def _fitted_anchor(
    metadata: dict[str, object],
    face_id: str,
    *,
    target_point,
    target_normal,
    z_station: float = 0.0,
) -> dict[str, object] | None:
    target_world = np.asarray(target_point, dtype=float).reshape(3)
    target_local = (float(target_world[0]), float(target_world[1]), float(target_world[2]) - float(z_station))
    solution = solve_optical_solid_face_fit(
        metadata,
        face_id=face_id,
        target_point=target_local,
        target_normal=tuple(float(value) for value in np.asarray(target_normal, dtype=float).reshape(3)),
    )
    if solution is None:
        return None
    row = SurfaceRow(
        surface="Solid 3D STL",
        name="Path-fitted prism",
        advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata},
        tilt_x=float(solution["tilts"][0]),
        tilt_y=float(solution["tilts"][1]),
        tilt_z=float(solution["tilts"][2]),
        desp_x=float(solution["desp"][0]),
        desp_y=float(solution["desp"][1]),
        desp_z=float(solution["desp"][2]),
    )
    faces = optical_solid_face_world_records(row, float(z_station), assigned_only=False)
    for face in faces:
        if str(face.get("face_id", "") or "").strip() == face_id:
            return face
    return None


def validate_optical_solid_path_fit() -> list[OpticalSolidPathFitCheck]:
    metadata, face_id = _prism_face_metadata()
    editor, _system, _rays, _wavelength = _load_traced_editor("Beam Splitter Two Path Doublets")
    checks: list[OpticalSolidPathFitCheck] = []
    ray_frame: dict[str, object] | None = None
    path_frame: dict[str, object] | None = None
    save_roles_solution: dict[str, object] | None = None
    save_roles_anchor = None
    ray_anchor = None
    path_anchor = None
    try:
        editor.__dict__.setdefault("_ray_inspector_ray_table", None)
        editor.__dict__.setdefault("_three_d_inspector", None)
        editor.__dict__.setdefault("_legacy_3d_plotter", None)
        synthetic_branch_path = "S1:BS1/transmit->S5:TX_DET/transmit"
        synthetic_ray_paths = [
            SimpleNamespace(
                ray_index=101,
                branch_path=synthetic_branch_path,
                source_id="source:test",
                surface_ids=np.asarray([1, 5], dtype=int),
                points_world=np.asarray(
                    [
                        (0.0, 0.0, -40.0),
                        (0.0, 0.0, 0.0),
                        (0.0, 20.0, 75.0),
                    ],
                    dtype=float,
                ),
            ),
            SimpleNamespace(
                ray_index=102,
                branch_path=synthetic_branch_path,
                source_id="source:test",
                surface_ids=np.asarray([1, 5], dtype=int),
                points_world=np.asarray(
                    [
                        (0.0, 0.0, -40.0),
                        (0.0, 0.0, 0.0),
                        (0.0, 18.0, 75.0),
                    ],
                    dtype=float,
                ),
            ),
        ]
        editor._last_scene_bundle = SimpleNamespace(ray_paths=synthetic_ray_paths)
        selected_path = synthetic_ray_paths[0]
        selected_ray_index = int(getattr(selected_path, "ray_index", -1))
        selected_branch_path = str(getattr(selected_path, "branch_path", "") or "").strip()
        editor._legacy_3d_plotter = SimpleNamespace(_kraken_selected_ray=selected_ray_index)
        ray_frame = editor._selected_ray_frame_near_point((0.0, 0.0, 0.0))
        ray_anchor = _fitted_anchor(
            metadata,
            face_id,
            target_point=ray_frame["target_point"],
            target_normal=ray_frame["direction"],
        )

        catalog = [entry for entry in editor._arm_catalog() if str(entry.get("kind", "")).strip() == "path"]
        chosen_label = ""
        if selected_branch_path:
            for entry in catalog:
                if editor._branch_path_for_arm_key(entry.get("key", "")) == selected_branch_path:
                    chosen_label = str(entry.get("label", "") or "")
                    break
        if not chosen_label and catalog:
            chosen_label = str(catalog[0].get("label", "") or "")
        if not chosen_label:
            editor.arm_view_var.set(ARM_VIEW_DEFAULT)
            raise RuntimeError("No traced path view label is available.")
        editor.arm_view_var.set(chosen_label)
        path_frame = editor._current_path_view_frame_near_point((0.0, 0.0, 0.0))
        path_anchor = _fitted_anchor(
            metadata,
            face_id,
            target_point=path_frame["target_point"],
            target_normal=path_frame["direction"],
        )
        row_index = max(1, len(editor.rows) - 1)
        editor.rows.insert(
            row_index,
            SurfaceRow(
                surface="Solid 3D STL",
                name="Save Roles path snap test",
                advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata},
                desp_y=100.0,
            ),
        )
        save_roles_solution = editor._solve_optical_solid_path_input_pose(row_index, metadata)
        if save_roles_solution is not None:
            test_row = SurfaceRow(
                surface="Solid 3D STL",
                name="Save Roles fitted prism",
                advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata},
                tilt_x=float(save_roles_solution["tilts"][0]),
                tilt_y=float(save_roles_solution["tilts"][1]),
                tilt_z=float(save_roles_solution["tilts"][2]),
                desp_x=float(save_roles_solution["desp"][0]),
                desp_y=float(save_roles_solution["desp"][1]),
                desp_z=float(save_roles_solution["desp"][2]),
            )
            z_positions = editor._row_z_positions()
            z_station = float(z_positions[row_index]) if row_index < len(z_positions) else 0.0
            for face in optical_solid_face_world_records(test_row, z_station, assigned_only=False):
                if str(face.get("face_id", "") or "").strip() == face_id:
                    save_roles_anchor = face
                    break
        checks.extend(
            [
                OpticalSolidPathFitCheck(
                    "selected-ray frame is available for CAD face fit",
                    ray_frame is not None,
                    (
                        f"ray={selected_ray_index}, branch={selected_branch_path or 'primary'}"
                        if ray_frame is not None
                        else "ray frame unavailable"
                    ),
                ),
                OpticalSolidPathFitCheck(
                    "selected-ray face fit snaps anchor to the traced 3D point",
                    ray_anchor is not None
                    and np.linalg.norm(
                        np.asarray(ray_anchor.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float)[:3]
                        - np.asarray(ray_frame["target_point"], dtype=float)[:3]
                    )
                    < 1e-6,
                    (
                        f"anchor={tuple(np.asarray(ray_anchor.get('centroid_world', (np.nan, np.nan, np.nan)), dtype=float)[:3])}, "
                        f"target={tuple(np.asarray(ray_frame['target_point'], dtype=float)[:3])}"
                        if ray_anchor is not None and ray_frame is not None
                        else "ray anchor unavailable"
                    ),
                ),
                OpticalSolidPathFitCheck(
                    "selected-ray face fit aligns anchor normal to the local ray direction",
                    ray_anchor is not None
                    and abs(
                        float(
                            np.dot(
                                np.asarray(ray_anchor.get("normal_world", (0.0, 0.0, 0.0)), dtype=float)[:3],
                                np.asarray(ray_frame["direction"], dtype=float)[:3],
                            )
                        )
                        - 1.0
                    )
                    < 1e-6,
                    (
                        f"normal={tuple(np.asarray(ray_anchor.get('normal_world', (np.nan, np.nan, np.nan)), dtype=float)[:3])}, "
                        f"dir={tuple(np.asarray(ray_frame['direction'], dtype=float)[:3])}"
                        if ray_anchor is not None and ray_frame is not None
                        else "ray alignment unavailable"
                    ),
                ),
                OpticalSolidPathFitCheck(
                    "current path-view frame is available for CAD face fit",
                    path_frame is not None and int(path_frame.get("sample_count", 0)) > 0,
                    (
                        f"path={path_frame.get('branch_path', '')}, samples={int(path_frame.get('sample_count', 0))}"
                        if path_frame is not None
                        else "path frame unavailable"
                    ),
                ),
                OpticalSolidPathFitCheck(
                    "path-view face fit snaps anchor to the projected path-frame point",
                    path_anchor is not None
                    and np.linalg.norm(
                        np.asarray(path_anchor.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float)[:3]
                        - np.asarray(path_frame["target_point"], dtype=float)[:3]
                    )
                    < 1e-6,
                    (
                        f"anchor={tuple(np.asarray(path_anchor.get('centroid_world', (np.nan, np.nan, np.nan)), dtype=float)[:3])}, "
                        f"target={tuple(np.asarray(path_frame['target_point'], dtype=float)[:3])}"
                        if path_anchor is not None and path_frame is not None
                        else "path anchor unavailable"
                    ),
                ),
                OpticalSolidPathFitCheck(
                    "path-view face fit aligns anchor normal to the path direction",
                    path_anchor is not None
                    and abs(
                        float(
                            np.dot(
                                np.asarray(path_anchor.get("normal_world", (0.0, 0.0, 0.0)), dtype=float)[:3],
                                np.asarray(path_frame["direction"], dtype=float)[:3],
                            )
                        )
                        - 1.0
                    )
                    < 1e-6,
                    (
                        f"normal={tuple(np.asarray(path_anchor.get('normal_world', (np.nan, np.nan, np.nan)), dtype=float)[:3])}, "
                        f"dir={tuple(np.asarray(path_frame['direction'], dtype=float)[:3])}"
                        if path_anchor is not None and path_frame is not None
                        else "path alignment unavailable"
                    ),
                ),
                OpticalSolidPathFitCheck(
                    "Save Roles path snap uses traced 3D ray before row-plane fallback",
                    save_roles_solution is not None
                    and str(save_roles_solution.get("fit_source", ""))
                    in {"previous table surface", "nearest traced ray", "current Path view"},
                    (
                        f"source={save_roles_solution.get('fit_source')}, target={save_roles_solution.get('target_world_point')}"
                        if save_roles_solution is not None
                        else "path snap solution unavailable"
                    ),
                ),
                OpticalSolidPathFitCheck(
                    "Save Roles path snap stores row-relative decenter for nonzero row station",
                    save_roles_anchor is not None
                    and save_roles_solution is not None
                    and np.linalg.norm(
                        np.asarray(save_roles_anchor.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float)[:3]
                        - np.asarray(save_roles_solution["target_world_point"], dtype=float)[:3]
                    )
                    < 1e-6,
                    (
                        f"anchor={tuple(np.asarray(save_roles_anchor.get('centroid_world', (np.nan, np.nan, np.nan)), dtype=float)[:3])}, "
                        f"target={tuple(np.asarray(save_roles_solution['target_world_point'], dtype=float)[:3])}"
                        if save_roles_anchor is not None and save_roles_solution is not None
                        else "save-role anchor unavailable"
                    ),
                ),
            ]
        )
    finally:
        try:
            editor.destroy()
        except Exception:
            pass
    return checks


def _print_table(checks: list[OpticalSolidPathFitCheck]) -> None:
    print("KrakenOS optical-solid path/ray face-fit validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CAD/STL face fit against selected rays and path-view frames.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_optical_solid_path_fit()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
