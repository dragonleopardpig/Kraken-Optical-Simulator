"""Validate the bundled Edmund 42779 vendor prism CAD workflow."""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

import KrakenOS.UI.layout_editor as le
from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    SurfaceRow,
    auto_assign_optical_solid_face_roles,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_record_from_candidate,
    optical_solid_face_world_records,
    solve_optical_solid_face_fit,
)


PRISM_42779_STEP = le.PROJECT_ROOT / "attachment" / "prisms" / "42779" / "step_42779.step"


@dataclass
class VendorPrism42779Check:
    check: str
    ok: bool
    detail: str


def _metadata_for_candidates(candidates: list[object], mesh_path: Path) -> dict[str, object]:
    records = auto_assign_optical_solid_face_roles(
        [optical_solid_face_record_from_candidate(candidate) for candidate in candidates]
    )
    for record in records:
        side = str(record.get("side_2d", "") or "")
        if side == "Left":
            record["role"] = "Input"
            record["function"] = "Transmit/Port"
        elif side == "Right":
            record["role"] = "Output"
            record["function"] = "Transmit/Port"
        elif side == "Down":
            record["role"] = "TIR"
            record["function"] = "TIR"
        elif side in {"Front", "Back"}:
            record["role"] = "Absorber/Mechanical"
            record["function"] = "Absorber/Mechanical"
    return normalize_optical_solid_face_metadata(
        {"source_stl": str(mesh_path), "faces": records},
        candidates,
        source_stl=str(mesh_path),
    )


def validate_vendor_prism_42779() -> list[VendorPrism42779Check]:
    checks: list[VendorPrism42779Check] = []
    if not PRISM_42779_STEP.exists():
        return [
            VendorPrism42779Check(
                "Edmund 42779 STEP asset exists",
                False,
                str(PRISM_42779_STEP),
            )
        ]

    original_cache = le.CAD_CACHE_DIR
    with tempfile.TemporaryDirectory(prefix="kraken-prism42779-") as tmp_dir:
        le.CAD_CACHE_DIR = Path(tmp_dir)
        try:
            mesh_path, source_path, source_format = le._optical_solid_mesh_path_from_source(PRISM_42779_STEP)
            diagnostics = le.inspect_stl_mesh(mesh_path)
            candidates = cluster_optical_solid_planar_faces(mesh_path)
            metadata = _metadata_for_candidates(candidates, mesh_path)
            faces = list(metadata.get("faces", []) or [])
            anchor = next((face for face in faces if str(face.get("side_2d", "")) == "Left"), None)
            face_id = str(anchor.get("face_id", "") or "") if isinstance(anchor, dict) else ""
            solution = solve_optical_solid_face_fit(metadata, face_id=face_id, target_normal=(0.0, 0.0, 1.0))
            row = None
            anchor_world = None
            if solution is not None:
                row = SurfaceRow(
                    surface="Solid 3D STL",
                    name="Edmund 42779 vendor prism",
                    advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata, "Solid_3d_stl": str(mesh_path)},
                    tilt_x=float(solution["tilts"][0]),
                    tilt_y=float(solution["tilts"][1]),
                    tilt_z=float(solution["tilts"][2]),
                    desp_x=float(solution["desp"][0]),
                    desp_y=float(solution["desp"][1]),
                    desp_z=float(solution["desp"][2]),
                )
                world_faces = optical_solid_face_world_records(row, 0.0, assigned_only=False)
                anchor_world = next((face for face in world_faces if str(face.get("face_id", "")) == face_id), None)
        finally:
            le.CAD_CACHE_DIR = original_cache

    checks.extend(
        [
            VendorPrism42779Check(
                "Edmund 42779 STEP resolves to cached STL",
                source_path == PRISM_42779_STEP and source_format == "STEP" and mesh_path.suffix.lower() == ".stl",
                f"mesh={mesh_path.name}, source={source_path.name}, format={source_format}",
            ),
            VendorPrism42779Check(
                "meshed 42779 prism is trace-ready",
                diagnostics.is_trace_ready and diagnostics.triangle_count > 0,
                le.short_stl_mesh_diagnostics(diagnostics),
            ),
            VendorPrism42779Check(
                "meshed 42779 prism keeps plausible millimeter scale",
                20.0 <= max(diagnostics.extents) <= 60.0 and min(diagnostics.extents) >= 5.0,
                f"extents={diagnostics.extents}",
            ),
            VendorPrism42779Check(
                "meshed 42779 prism clusters into planar optical face candidates",
                len(candidates) >= 5,
                f"faces={len(candidates)}, areas={[round(float(candidate.area_mm2), 3) for candidate in candidates[:8]]}",
            ),
            VendorPrism42779Check(
                "auto side labels include placement anchor faces",
                {"Left", "Right", "Down"}.issubset({str(face.get("side_2d", "")) for face in faces}),
                f"sides={[str(face.get('side_2d', '')) for face in faces]}",
            ),
            VendorPrism42779Check(
                "face-fit solver places selected input face on +Z",
                solution is not None
                and anchor_world is not None
                and abs(
                    float(
                        np.dot(
                            np.asarray(anchor_world.get("normal_world", (0.0, 0.0, 0.0)), dtype=float),
                            np.asarray((0.0, 0.0, 1.0), dtype=float),
                        )
                    )
                    - 1.0
                )
                < 1e-6,
                (
                    f"face={face_id}, tilts={solution.get('tilts') if solution else '-'}, "
                    f"normal={anchor_world.get('normal_world') if anchor_world else '-'}"
                ),
            ),
        ]
    )
    return checks


def _print_table(checks: list[VendorPrism42779Check]) -> None:
    print("KrakenOS vendor prism 42779 validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_vendor_prism_42779()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
