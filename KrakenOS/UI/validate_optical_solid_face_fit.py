from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    SurfaceRow,
    auto_assign_optical_solid_face_roles,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_record_from_candidate,
    optical_solid_face_world_records,
    solve_optical_solid_face_fit,
)


@dataclass
class OpticalSolidFaceFitCheck:
    check: str
    ok: bool
    detail: str


def validate_optical_solid_face_fit() -> list[OpticalSolidFaceFitCheck]:
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
    left_face_id = str(left_face.get("face_id", "") or "") if left_face is not None else ""
    solution = solve_optical_solid_face_fit(
        metadata,
        face_id=left_face_id,
        target_normal=(0.0, 0.0, 1.0),
    )
    row = None
    faces = []
    if solution is not None:
        row = SurfaceRow(
            surface="Solid 3D STL",
            name="Fitted prism",
            advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata},
            tilt_x=float(solution["tilts"][0]),
            tilt_y=float(solution["tilts"][1]),
            tilt_z=float(solution["tilts"][2]),
            desp_x=float(solution["desp"][0]),
            desp_y=float(solution["desp"][1]),
            desp_z=float(solution["desp"][2]),
        )
        faces = optical_solid_face_world_records(row, 0.0, assigned_only=False)
    anchor = next((face for face in faces if str(face.get("face_id", "") or "") == left_face_id), None)
    guide_side = str(solution.get("roll_side", "") or "") if solution is not None else ""
    guide = next((face for face in faces if str(face.get("side_2d", "") or "") == guide_side), None) if guide_side else None
    desired_axes = {
        "Up": np.asarray((0.0, 1.0, 0.0), dtype=float),
        "Down": np.asarray((0.0, -1.0, 0.0), dtype=float),
        "Front": np.asarray((-1.0, 0.0, 0.0), dtype=float),
        "Back": np.asarray((1.0, 0.0, 0.0), dtype=float),
    }
    roll_alignment = float("nan")
    if guide is not None and guide_side in desired_axes:
        normal = np.asarray(guide.get("normal_world", (0.0, 0.0, 0.0)), dtype=float)
        proj = normal - np.asarray((0.0, 0.0, 1.0), dtype=float) * float(np.dot(normal, np.asarray((0.0, 0.0, 1.0), dtype=float)))
        norm = float(np.linalg.norm(proj))
        if norm > 1e-12:
            proj = proj / norm
            roll_alignment = float(np.dot(proj, desired_axes[guide_side]))
    checks = [
        OpticalSolidFaceFitCheck(
            "face-fit solver returns a placement solution",
            solution is not None,
            (
                f"face={solution.get('face_id')} roll={solution.get('roll_side')} tilts={solution.get('tilts')}"
                if solution is not None
                else "solution=None"
            ),
        ),
        OpticalSolidFaceFitCheck(
            "selected anchor face ends on the row origin plane",
            anchor is not None
            and np.all(np.isfinite(np.asarray(anchor.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float)[:3]))
            and np.linalg.norm(np.asarray(anchor.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float)[:3]) < 1e-6,
            (
                f"anchor_centroid={anchor.get('centroid_world')}"
                if anchor is not None
                else "anchor=None"
            ),
        ),
        OpticalSolidFaceFitCheck(
            "selected anchor face normal aligns to +Z",
            anchor is not None
            and abs(float(np.dot(np.asarray(anchor.get("normal_world", (0.0, 0.0, 0.0)), dtype=float), np.asarray((0.0, 0.0, 1.0), dtype=float))) - 1.0) < 1e-6,
            (
                f"anchor_normal={anchor.get('normal_world')}"
                if anchor is not None
                else "anchor=None"
            ),
        ),
        OpticalSolidFaceFitCheck(
            "auto roll chooses a labeled side face when available",
            solution is not None and bool(guide_side),
            f"roll_side={guide_side or '-'}",
        ),
        OpticalSolidFaceFitCheck(
            "roll guide projects onto the expected layout direction",
            bool(guide_side) and np.isfinite(roll_alignment) and roll_alignment > 0.9,
            f"roll_side={guide_side or '-'}, alignment={roll_alignment:.6g}",
        ),
    ]
    return checks


def _print_table(checks: list[OpticalSolidFaceFitCheck]) -> None:
    print("KrakenOS optical-solid face-fit validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CAD/STL face-anchor fit and roll helpers.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_optical_solid_face_fit()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
