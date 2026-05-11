from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from KrakenOS.UI import layout_editor as layout_editor_module
from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    SurfaceRow,
    auto_assign_optical_solid_face_roles,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_candidate_triangles,
    optical_solid_face_world_markers,
    optical_solid_face_record_from_candidate,
    _advanced_surface_attrs_from_spec,
)
from KrakenOS.UI.optical_solid_metadata import (
    auto_assign_optical_solid_face_roles as service_auto_assign_optical_solid_face_roles,
    normalize_optical_solid_face_metadata as service_normalize_optical_solid_face_metadata,
    optical_solid_face_record_from_candidate as service_optical_solid_face_record_from_candidate,
    optical_solid_faces_summary_text,
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
    service_records = [service_optical_solid_face_record_from_candidate(candidate) for candidate in candidates]
    service_auto_records = service_auto_assign_optical_solid_face_roles(records)
    auto_records = auto_assign_optical_solid_face_roles(records)
    sides = [str(record.get("side_2d", "")) for record in auto_records]
    if auto_records:
        auto_records[0]["function"] = "Beam Splitter"
        auto_records[0]["role"] = "Beam Splitter"
        auto_records[0]["side_2d"] = "Left"
        auto_records[0]["split_ratio"] = 0.37
    metadata = normalize_optical_solid_face_metadata(
        {"source_stl": str(prism_path), "faces": auto_records},
        candidates,
        source_stl=str(prism_path),
    )
    service_metadata = service_normalize_optical_solid_face_metadata(
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
    marker_row = SurfaceRow(
        surface="Standard",
        name="Validated STL prism",
        advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata},
        tilt_x=12.0,
        tilt_y=-7.0,
        tilt_z=25.0,
        desp_x=1.5,
        desp_y=-2.0,
        desp_z=0.75,
    )
    world_markers = optical_solid_face_world_markers(marker_row, 42.0, assigned_only=True)
    layout_summary = layout_editor_module.KrakenLayoutEditor._optical_solid_faces_summary(3, marker_row)
    service_summary = optical_solid_faces_summary_text(3, marker_row.name, marker_row.surface, metadata)
    marker_norms = [
        sum(float(component) ** 2 for component in marker.normal) ** 0.5
        for marker in world_markers
    ]
    layout_editor_module._load_3d_backends()
    vtk_tk_loaded = layout_editor_module.vtkTkRenderWindowInteractor is not None
    vtk_tk_reason = getattr(layout_editor_module, "_VTK_TK_UNAVAILABLE_REASON", "")
    try:
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: F401
        from matplotlib.figure import Figure  # noqa: F401

        matplotlib_picker_loaded = True
    except Exception as exc:
        matplotlib_picker_loaded = False
        vtk_tk_reason = f"{vtk_tk_reason}; Matplotlib/Tk unavailable: {exc}".strip("; ")
    checks = [
        OpticalSolidFaceRoleCheck(
            "prism STL clusters into selectable planar face candidates",
            len(candidates) >= 4,
            f"faces={len(candidates)}, areas={[round(candidate.area_mm2, 6) for candidate in candidates[:6]]}",
        ),
        OpticalSolidFaceRoleCheck(
            "face candidates expose clickable triangle meshes for 3D picking",
            bool(candidates)
            and all(optical_solid_face_candidate_triangles(prism_path, candidate).shape[0] > 0 for candidate in candidates[: min(5, len(candidates))]),
            f"triangles={[int(optical_solid_face_candidate_triangles(prism_path, candidate).shape[0]) for candidate in candidates[: min(5, len(candidates))]]}",
        ),
        OpticalSolidFaceRoleCheck(
            "auto assignment creates 2D side labels",
            "Left" in sides and "Right" in sides,
            f"sides={sides[:6]}",
        ),
        OpticalSolidFaceRoleCheck(
            "metadata preserves candidate count",
            len(preserved_faces) == len(candidates),
            f"metadata_faces={len(preserved_faces)}, candidates={len(candidates)}",
        ),
        OpticalSolidFaceRoleCheck(
            "beam-splitter face role stores split ratio",
            bool(preserved_faces)
            and str(preserved_faces[0].get("function")) == "Beam Splitter"
            and str(preserved_faces[0].get("role")) == "Beam Splitter"
            and str(preserved_faces[0].get("side_2d")) == "Left"
            and abs(float(preserved_faces[0].get("split_ratio", 0.0)) - 0.37) < 1e-9,
            (
                "side={side}, function={function}, role={role}, split={split}".format(
                    side=preserved_faces[0].get("side_2d") if preserved_faces else "-",
                    function=preserved_faces[0].get("function") if preserved_faces else "-",
                    role=preserved_faces[0].get("role") if preserved_faces else "-",
                    split=preserved_faces[0].get("split_ratio") if preserved_faces else "-",
                )
            ),
        ),
        OpticalSolidFaceRoleCheck(
            "advanced attribute parser preserves OpticalSolidFaces",
            OPTICAL_SOLID_FACES_ADVANCED_ATTR in parsed_attrs and len(parsed_faces) == len(candidates),
            f"parsed_keys={sorted(parsed_attrs)}, parsed_faces={len(parsed_faces)}",
        ),
        OpticalSolidFaceRoleCheck(
            "assigned face roles transform into finite 3D viewer markers",
            bool(world_markers)
            and all(abs(norm - 1.0) < 1e-9 for norm in marker_norms)
            and all(all(abs(float(value)) < 1e6 for value in marker.centroid) for marker in world_markers),
            f"markers={len(world_markers)}, norms={[round(norm, 9) for norm in marker_norms[:6]]}",
        ),
        OpticalSolidFaceRoleCheck(
            "optical-solid metadata helpers are service-owned",
            service_records == records
            and service_auto_records == auto_assign_optical_solid_face_roles(records)
            and service_metadata == metadata
            and service_summary == layout_summary
            and "Assigned optical faces:" in service_summary,
            {
                "records": len(service_records),
                "auto_sides": [record.get("side_2d") for record in service_auto_records[:6]],
                "metadata_faces": len(list(service_metadata.get("faces", []) or [])),
                "summary": service_summary.splitlines()[:3],
            },
        ),
        OpticalSolidFaceRoleCheck(
            "CAD/STL face picker has an available visual backend",
            vtk_tk_loaded or matplotlib_picker_loaded,
            (
                f"VTK/Tk={'available' if vtk_tk_loaded else 'unavailable'}, "
                f"Matplotlib/Tk={'available' if matplotlib_picker_loaded else 'unavailable'}, "
                f"reason={vtk_tk_reason or '-'}"
            ),
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
