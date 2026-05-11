from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from KrakenOS.UI import cad_import_service
import KrakenOS.UI.layout_editor as le


@dataclass
class OpticalCadSolidImportCheck:
    check: str
    ok: bool
    detail: str


def validate_optical_cad_solid_import() -> list[OpticalCadSolidImportCheck]:
    checks: list[OpticalCadSolidImportCheck] = []
    prism_path = Path(__file__).resolve().parents[1] / "Examples" / "prism.stl"
    solid_indices = (1, 3)
    layout_cache_path = le._cached_cad_mesh_path(prism_path)
    service_cache_path = cad_import_service.cached_cad_mesh_path(prism_path, le.CAD_CACHE_DIR)
    layout_outer_path = le._cached_outer_cad_mesh_path(prism_path, solid_indices)
    service_outer_path = cad_import_service.cached_outer_cad_mesh_path(prism_path, solid_indices, le.CAD_CACHE_DIR)
    layout_ref_path = le._cached_cad_reference_path(prism_path, solid_indices)
    service_ref_path = cad_import_service.cached_cad_reference_path(prism_path, solid_indices, le.CAD_CACHE_DIR)
    layout_section_path = le._cached_cad_section_path(prism_path, solid_indices)
    service_section_path = cad_import_service.cached_cad_section_path(prism_path, solid_indices, le.CAD_CACHE_DIR)
    layout_mesh_tuple = le._optical_solid_mesh_path_from_source(prism_path)
    service_mesh_tuple = cad_import_service.optical_solid_mesh_path_from_source(
        prism_path,
        cache_dir=le.CAD_CACHE_DIR,
        stl_suffixes=le.OPTICAL_SOLID_STL_SUFFIXES,
        cad_suffixes=le.OPTICAL_SOLID_CAD_SUFFIXES,
    )
    checks.append(
        OpticalCadSolidImportCheck(
            "CAD cache path helpers are service-owned",
            layout_cache_path == service_cache_path
            and layout_outer_path == service_outer_path
            and layout_ref_path == service_ref_path
            and layout_section_path == service_section_path,
            f"mesh={service_cache_path.name}, outer={service_outer_path.name}",
        )
    )
    checks.append(
        OpticalCadSolidImportCheck(
            "optical solid source-to-mesh resolver is service-owned for STL",
            layout_mesh_tuple == service_mesh_tuple and layout_mesh_tuple[2] == "STL",
            f"mesh={service_mesh_tuple[0].name}, source={service_mesh_tuple[1]}, format={service_mesh_tuple[2]}",
        )
    )
    source_path = le.PROJECT_ROOT / "attachment" / "68551" / "step_68551.step"
    if not source_path.exists():
        checks.append(
            OpticalCadSolidImportCheck(
                "Edmund 68551 sample",
                True,
                f"SKIP: local vendor STEP not found at {source_path}",
            )
        )
        return checks

    original_cache = le.CAD_CACHE_DIR
    with tempfile.TemporaryDirectory(prefix="kraken-cad-solid-") as tmp_dir:
        le.CAD_CACHE_DIR = Path(tmp_dir)
        try:
            mesh_path, cad_source_path, source_format = le._optical_solid_mesh_path_from_source(source_path)
            report = le.inspect_stl_mesh(mesh_path)
        finally:
            le.CAD_CACHE_DIR = original_cache

    checks.append(
        OpticalCadSolidImportCheck(
            "source recognized as CAD",
            cad_source_path == source_path and source_format == "STEP",
            f"source={cad_source_path}, format={source_format}",
        )
    )
    checks.append(
        OpticalCadSolidImportCheck(
            "cached STL mesh generated",
            mesh_path.suffix.lower() == ".stl" and mesh_path.name.startswith("step_68551"),
            str(mesh_path),
        )
    )
    checks.append(
        OpticalCadSolidImportCheck(
            "mesh has closed boundary",
            report.triangle_count > 0 and report.boundary_edge_count == 0 and not report.errors,
            le.short_stl_mesh_diagnostics(report),
        )
    )
    checks.append(
        OpticalCadSolidImportCheck(
            "cube scale preserved",
            20.0 <= max(report.extents) <= 30.0,
            f"extents={report.extents}",
        )
    )
    return checks


def _print_table(checks: list[OpticalCadSolidImportCheck]) -> None:
    print("KrakenOS optical CAD solid import validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate STEP/IGES-to-cached-STL optical solid import with the optional Edmund 68551 sample."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_optical_cad_solid_import()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
