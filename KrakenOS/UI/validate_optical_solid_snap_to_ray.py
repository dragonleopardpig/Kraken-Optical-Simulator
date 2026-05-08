from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    KrakenLayoutEditor,
    SurfaceRow,
    auto_assign_optical_solid_face_roles,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_record_from_candidate,
)


@dataclass
class OpticalSolidSnapCheck:
    check: str
    ok: bool
    detail: str


def validate_optical_solid_snap_to_ray() -> list[OpticalSolidSnapCheck]:
    prism_path = Path(__file__).resolve().parents[1] / "Examples" / "prism.stl"
    candidates = cluster_optical_solid_planar_faces(prism_path)
    records = [optical_solid_face_record_from_candidate(candidate) for candidate in candidates]
    auto_records = auto_assign_optical_solid_face_roles(records)
    left_face = next(
        (record for record in auto_records if str(record.get("side_2d", "")) == "Left"),
        min(auto_records, key=lambda item: float(item.get("centroid", [0.0, 0.0, 0.0])[2])) if auto_records else None,
    )
    if left_face is not None:
        left_face["function"] = OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT
        left_face["role"] = "Output"
    metadata = normalize_optical_solid_face_metadata(
        {"source_stl": str(prism_path), "faces": auto_records},
        candidates,
        source_stl=str(prism_path),
    )
    row = SurfaceRow(
        surface="Solid 3D STL",
        name="Snap prism",
        advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata},
        tilt_x=0.0,
        tilt_y=0.0,
        tilt_z=0.0,
        desp_x=0.0,
        desp_y=0.0,
        desp_z=0.0,
    )
    ray_points = np.asarray(
        [
            (0.0, 0.0, -40.0),
            (0.0, 0.0, 60.0),
        ],
        dtype=float,
    )
    anchor = KrakenLayoutEditor._optical_solid_face_snap_anchor(row, 0.0, ray_points)
    left_face_id = str(left_face.get("face_id", "") or "") if left_face is not None else ""
    target = np.asarray(anchor.get("target_world", (np.nan, np.nan, np.nan)), dtype=float) if anchor else np.full(3, np.nan, dtype=float)
    checks = [
        OpticalSolidSnapCheck(
            "prism STL exposes planar face candidates for snap-to-ray",
            len(candidates) >= 4,
            f"candidates={len(candidates)}",
        ),
        OpticalSolidSnapCheck(
            "snap helper chooses an optical-face anchor",
            anchor is not None,
            (
                f"anchor={anchor.get('face_id')} label={anchor.get('label')}"
                if anchor is not None
                else "anchor=None"
            ),
        ),
        OpticalSolidSnapCheck(
            "snap helper prefers the explicitly transmitted left face",
            anchor is not None and str(anchor.get("face_id", "") or "") == left_face_id,
            f"expected={left_face_id or '-'}, got={anchor.get('face_id') if anchor is not None else '-'}",
        ),
        OpticalSolidSnapCheck(
            "snap target lands on the picked axial ray",
            anchor is not None and np.all(np.isfinite(target[:3])) and abs(float(target[0])) < 1e-6 and abs(float(target[1])) < 1e-6,
            f"target=({target[0]:.6g}, {target[1]:.6g}, {target[2]:.6g})",
        ),
        OpticalSolidSnapCheck(
            "snap anchor reports a forward-facing intersection score",
            anchor is not None and float(anchor.get("facing_score", -1.0)) > 0.0,
            f"facing={float(anchor.get('facing_score', float('nan'))) if anchor is not None else float('nan'):.6g}",
        ),
    ]
    return checks


def _print_table(checks: list[OpticalSolidSnapCheck]) -> None:
    print("KrakenOS optical-solid snap-to-ray validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CAD/STL face-anchor snap-to-ray helpers.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_optical_solid_snap_to_ray()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
