from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FIT_ROLL_NONE,
    SurfaceRow,
    normalize_optical_solid_face_metadata,
    optical_solid_face_world_records,
    solve_optical_solid_face_fit,
)


@dataclass
class InputOffsetCheck:
    check: str
    ok: bool
    detail: str


def validate_optical_solid_input_offset() -> list[InputOffsetCheck]:
    metadata = normalize_optical_solid_face_metadata(
        {
            "faces": [
                {
                    "face_id": "F001",
                    "function": "Transmit/Port",
                    "side_2d": "Down",
                    "port_role": "Input Port",
                    "normal": [0.0, -1.0, 0.0],
                    "centroid": [0.0, 0.0, 0.0],
                    "area_mm2": 100.0,
                    "triangle_count": 2,
                    "plane_offset_mm": 0.0,
                    "input_offset_u_mm": 7.5,
                    "input_offset_v_mm": 0.0,
                }
            ]
        }
    )
    solution = solve_optical_solid_face_fit(
        metadata,
        face_id="F001",
        target_normal=(0.0, -1.0, 0.0),
        target_point=(0.0, 0.0, 0.0),
        roll_mode=OPTICAL_SOLID_FACE_FIT_ROLL_NONE,
    )
    checks: list[InputOffsetCheck] = []
    if solution is None:
        return [InputOffsetCheck("offset input face fit produced a solution", False, "solve_optical_solid_face_fit returned None")]

    row = SurfaceRow(
        surface="Solid 3D STL",
        name="Offset input snap test",
        advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata},
        tilt_x=float(solution["tilts"][0]),
        tilt_y=float(solution["tilts"][1]),
        tilt_z=float(solution["tilts"][2]),
        desp_x=float(solution["desp"][0]),
        desp_y=float(solution["desp"][1]),
        desp_z=float(solution["desp"][2]),
    )
    faces = optical_solid_face_world_records(row, 0.0, assigned_only=False)
    face = next((item for item in faces if str(item.get("face_id", "") or "").strip() == "F001"), None)
    anchor_world = np.asarray(face.get("anchor_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(3) if isinstance(face, dict) else np.full(3, np.nan)
    centroid_world = np.asarray(face.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(3) if isinstance(face, dict) else np.full(3, np.nan)
    checks.append(
        InputOffsetCheck(
            "offset input face fit produced a solution",
            True,
            f"desp={solution['desp']}, tilts={solution['tilts']}",
        )
    )
    checks.append(
        InputOffsetCheck(
            "input offset anchor lands on the requested target point",
            bool(np.all(np.isfinite(anchor_world)) and np.linalg.norm(anchor_world) < 1e-6),
            f"anchor_world={tuple(np.round(anchor_world, 6).tolist())}",
        )
    )
    checks.append(
        InputOffsetCheck(
            "face centroid remains offset when anchor uses nonzero snap U/V",
            bool(np.all(np.isfinite(centroid_world)) and abs(float(centroid_world[2]) + 7.5) < 1e-6),
            f"centroid_world={tuple(np.round(centroid_world, 6).tolist())}",
        )
    )
    checks.append(
        InputOffsetCheck(
            "solution reports saved input snap offsets",
            abs(float(solution.get("input_offset_u_mm", np.nan)) - 7.5) < 1e-9
            and abs(float(solution.get("input_offset_v_mm", np.nan))) < 1e-9,
            f"reported_offsets=({solution.get('input_offset_u_mm')}, {solution.get('input_offset_v_mm')})",
        )
    )
    return checks


def main() -> int:
    checks = validate_optical_solid_input_offset()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} | {check.detail}")
    if failed:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
