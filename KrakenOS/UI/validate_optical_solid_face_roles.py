from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    auto_assign_optical_solid_face_roles,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_record_from_candidate,
    _advanced_surface_attrs_from_spec,
)


@dataclass
class OpticalSolidFaceRoleCheck:
    check: str
    ok: bool
    detail: str


def validate_optical_solid_face_roles() -> list[OpticalSolidFaceRoleCheck]:
    prism_path = Path(__file__).resolve().parents[1] / "Examples" / "prism.stl"
    candidates = cluster_optical_solid_planar_faces(prism_path)
    records = [optical_solid_face_record_from_candidate(candidate) for candidate in candidates]
    auto_records = auto_assign_optical_solid_face_roles(records)
    roles = [str(record.get("role", "")) for record in auto_records]
    if auto_records:
        auto_records[0]["role"] = "Beam Splitter"
        auto_records[0]["split_ratio"] = 0.37
    metadata = normalize_optical_solid_face_metadata(
        {"source_stl": str(prism_path), "faces": auto_records},
        candidates,
        source_stl=str(prism_path),
    )
    preserved_faces = list(metadata.get("faces", []) or [])
    parsed_attrs = _advanced_surface_attrs_from_spec(
        {"advanced": {OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata}}
    )
    parsed_metadata = normalize_optical_solid_face_metadata(parsed_attrs.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
    parsed_faces = list(parsed_metadata.get("faces", []) or [])
    checks = [
        OpticalSolidFaceRoleCheck(
            "prism STL clusters into selectable planar face candidates",
            len(candidates) >= 4,
            f"faces={len(candidates)}, areas={[round(candidate.area_mm2, 6) for candidate in candidates[:6]]}",
        ),
        OpticalSolidFaceRoleCheck(
            "auto assignment creates input/output intent",
            "Input" in roles and "Output" in roles,
            f"roles={roles[:6]}",
        ),
        OpticalSolidFaceRoleCheck(
            "metadata preserves candidate count",
            len(preserved_faces) == len(candidates),
            f"metadata_faces={len(preserved_faces)}, candidates={len(candidates)}",
        ),
        OpticalSolidFaceRoleCheck(
            "beam-splitter face role stores split ratio",
            bool(preserved_faces)
            and str(preserved_faces[0].get("role")) == "Beam Splitter"
            and abs(float(preserved_faces[0].get("split_ratio", 0.0)) - 0.37) < 1e-9,
            f"role={preserved_faces[0].get('role') if preserved_faces else '-'}, split={preserved_faces[0].get('split_ratio') if preserved_faces else '-'}",
        ),
        OpticalSolidFaceRoleCheck(
            "advanced attribute parser preserves OpticalSolidFaces",
            OPTICAL_SOLID_FACES_ADVANCED_ATTR in parsed_attrs and len(parsed_faces) == len(candidates),
            f"parsed_keys={sorted(parsed_attrs)}, parsed_faces={len(parsed_faces)}",
        ),
    ]
    return checks


def _print_table(checks: list[OpticalSolidFaceRoleCheck]) -> None:
    print("KrakenOS optical-solid face-role validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CAD/STL optical face-role metadata helpers.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_optical_solid_face_roles()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
