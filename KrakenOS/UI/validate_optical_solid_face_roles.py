from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI import stl_geometry
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
    OPTICAL_SOLID_FACE_PORT_INPUT,
    OPTICAL_SOLID_FACE_PORT_INTERACTION,
    OPTICAL_SOLID_FACE_PORT_OUTPUT,
    auto_assign_optical_solid_face_roles as service_auto_assign_optical_solid_face_roles,
    normalize_optical_solid_face_metadata as service_normalize_optical_solid_face_metadata,
    optical_solid_face_port_role,
    optical_solid_face_record_from_candidate as service_optical_solid_face_record_from_candidate,
    optical_solid_input_anchor_face,
    optical_solid_faces_summary_text,
)
from KrakenOS.UI.nonseq_output_ports import (
    build_optical_solid_output_port_pose_overrides,
    select_optical_solid_interaction_face,
    select_optical_solid_output_face,
)


@dataclass
class OpticalSolidFaceRoleCheck:
    check: str
    ok: bool
    detail: str


def validate_optical_solid_face_roles() -> list[OpticalSolidFaceRoleCheck]:
    prism_path = Path(__file__).resolve().parents[1] / "Examples" / "prism.stl"
    layout_stl_format, layout_triangles = layout_editor_module._read_stl_triangle_vertices(prism_path)
    service_stl_format, service_triangles = stl_geometry.read_stl_triangle_vertices(prism_path)
    layout_diagnostics = layout_editor_module.inspect_stl_mesh(prism_path)
    service_diagnostics = stl_geometry.inspect_stl_mesh(prism_path)
    transform_tilts = (12.0, -7.0, 25.0)
    transform_desp = (1.5, -2.0, 0.75)
    transform_z = 42.0
    layout_rotated_bounds = layout_editor_module.rotated_stl_bounds(prism_path, transform_tilts)
    service_rotated_bounds = stl_geometry.rotated_stl_bounds(prism_path, transform_tilts)
    layout_transformed_points = layout_editor_module.transformed_stl_points(
        prism_path,
        transform_tilts,
        transform_desp,
        transform_z,
    )
    service_transformed_points = stl_geometry.transformed_stl_points(
        prism_path,
        transform_tilts,
        transform_desp,
        transform_z,
    )
    layout_transformed_bounds = layout_editor_module.transformed_stl_bounds(
        prism_path,
        transform_tilts,
        transform_desp,
        transform_z,
    )
    service_transformed_bounds = stl_geometry.transformed_stl_bounds(
        prism_path,
        transform_tilts,
        transform_desp,
        transform_z,
    )
    hull_fixture = np.asarray(
        [
            (0.0, 0.0),
            (1.0, 0.0),
            (1.0, 1.0),
            (0.0, 1.0),
            (0.5, 0.5),
            (np.nan, 0.0),
        ],
        dtype=float,
    )
    layout_hull = layout_editor_module.convex_hull_2d(hull_fixture)
    service_hull = stl_geometry.convex_hull_2d(hull_fixture)
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
        auto_records[0]["port_role"] = OPTICAL_SOLID_FACE_PORT_INTERACTION
    if len(auto_records) > 1:
        auto_records[1]["function"] = "Transmit/Port"
        auto_records[1]["role"] = "Output"
        auto_records[1]["side_2d"] = "Right"
        auto_records[1]["port_role"] = OPTICAL_SOLID_FACE_PORT_OUTPUT
    if len(auto_records) > 2:
        auto_records[2]["function"] = "Transmit/Port"
        auto_records[2]["role"] = "Input"
        auto_records[2]["side_2d"] = "Left"
        auto_records[2]["port_role"] = OPTICAL_SOLID_FACE_PORT_INPUT
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
    input_anchor = optical_solid_input_anchor_face(metadata)
    selected_output = select_optical_solid_output_face(preserved_faces)
    selected_interaction = select_optical_solid_interaction_face(preserved_faces)
    legacy_transmit_metadata = normalize_optical_solid_face_metadata(
        {
            "faces": [
                {
                    "face_id": "LegacyLeft",
                    "role": "Output",
                    "function": "Transmit/Port",
                    "side_2d": "Left",
                    "normal": [0.0, 0.0, -1.0],
                    "centroid": [0.0, 0.0, 0.0],
                    "area_mm2": 50.0,
                },
                {
                    "face_id": "LegacyDown",
                    "role": "Output",
                    "function": "Transmit/Port",
                    "side_2d": "Down",
                    "normal": [0.0, -1.0, 0.0],
                    "centroid": [0.0, -10.0, 0.0],
                    "area_mm2": 50.0,
                },
            ]
        }
    )
    legacy_left_face = optical_solid_input_anchor_face(legacy_transmit_metadata)
    legacy_output_face = select_optical_solid_output_face(list(legacy_transmit_metadata.get("faces", []) or []))
    mirror_rows = [
        SurfaceRow(surface="Object", name="Object", thickness=25.0, diameter=10.0, glass="AIR"),
        SurfaceRow(
            surface="Solid 3D STL",
            name="Port semantics mirror",
            thickness=30.0,
            diameter=10.0,
            advanced={
                OPTICAL_SOLID_FACES_ADVANCED_ATTR: {
                    "faces": [
                        {
                            "face_id": "M001",
                            "function": "Mirror",
                            "role": "Mirror",
                            "port_role": OPTICAL_SOLID_FACE_PORT_INTERACTION,
                            "side_2d": "Left",
                            "normal": [0.0, 1.0, -1.0],
                            "centroid": [0.0, 0.0, 0.0],
                            "area_mm2": 100.0,
                        }
                    ]
                },
                "Solid_3d_stl": str(prism_path),
            },
        ),
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=10.0, glass="AIR"),
    ]
    mirror_overrides = build_optical_solid_output_port_pose_overrides(mirror_rows)
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
    layout_editor_source = Path(layout_editor_module.__file__).read_text(encoding="utf-8")
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
            and str(preserved_faces[0].get("port_role")) == OPTICAL_SOLID_FACE_PORT_INTERACTION
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
            "face port semantics separate input, output, and interaction faces",
            input_anchor is not None
            and selected_output is not None
            and selected_interaction is not None
            and optical_solid_face_port_role(input_anchor) == OPTICAL_SOLID_FACE_PORT_INPUT
            and optical_solid_face_port_role(selected_output) == OPTICAL_SOLID_FACE_PORT_OUTPUT
            and optical_solid_face_port_role(selected_interaction) == OPTICAL_SOLID_FACE_PORT_INTERACTION,
            (
                f"input={None if input_anchor is None else input_anchor.get('face_id')}, "
                f"output={None if selected_output is None else selected_output.get('face_id')}, "
                f"interaction={None if selected_interaction is None else selected_interaction.get('face_id')}"
            ),
        ),
        OpticalSolidFaceRoleCheck(
            "legacy transmit-role metadata keeps Left as input and non-left as output",
            legacy_left_face is not None
            and legacy_output_face is not None
            and str(legacy_left_face.get("face_id")) == "LegacyLeft"
            and str(legacy_output_face.get("face_id")) == "LegacyDown"
            and optical_solid_face_port_role(legacy_left_face) == OPTICAL_SOLID_FACE_PORT_INPUT
            and optical_solid_face_port_role(legacy_output_face) == OPTICAL_SOLID_FACE_PORT_OUTPUT,
            (
                f"input={None if legacy_left_face is None else legacy_left_face.get('face_id')}, "
                f"output={None if legacy_output_face is None else legacy_output_face.get('face_id')}"
            ),
        ),
        OpticalSolidFaceRoleCheck(
            "mirror interaction face can propagate the downstream pose frame",
            2 in mirror_overrides
            and float(np.linalg.norm(np.asarray(mirror_overrides[2]["normal"], dtype=float).reshape(3))) > 0.999,
            f"override_keys={sorted(int(key) for key in mirror_overrides)}",
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
            "STL geometry read and diagnostic helpers are service-owned",
            layout_stl_format == service_stl_format
            and np.allclose(layout_triangles, service_triangles)
            and asdict(layout_diagnostics) == asdict(service_diagnostics)
            and layout_editor_module.format_stl_mesh_diagnostics(layout_diagnostics)
            == stl_geometry.format_stl_mesh_diagnostics(service_diagnostics)
            and layout_editor_module.short_stl_mesh_diagnostics(layout_diagnostics)
            == stl_geometry.short_stl_mesh_diagnostics(service_diagnostics),
            (
                f"format={service_stl_format}, triangles={int(service_triangles.shape[0])}, "
                f"winding={service_diagnostics.winding}"
            ),
        ),
        OpticalSolidFaceRoleCheck(
            "STL bounds transform and hull helpers are service-owned",
            all(np.allclose(left, right) for left, right in zip(layout_rotated_bounds, service_rotated_bounds))
            and np.allclose(layout_transformed_points, service_transformed_points)
            and all(np.allclose(left, right) for left, right in zip(layout_transformed_bounds, service_transformed_bounds))
            and np.allclose(layout_hull, service_hull),
            (
                f"points={service_transformed_points.shape[0]}, "
                f"bounds_center={tuple(float(value) for value in service_transformed_bounds[2])}, "
                f"hull={service_hull.shape[0]}"
            ),
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
        OpticalSolidFaceRoleCheck(
            "CAD/STL face picker matches Open 3D click-drag behavior",
            "def install_vtk_face_preview_mouse_bindings" in layout_editor_source
            and "click selects, left-drag rotates" in layout_editor_source
            and "rotate_preview_camera_fixed_drag" in layout_editor_source
            and 'preview_widget.bind("<B1-Motion>", left_motion)' in layout_editor_source
            and 'preview_widget.bind("<ButtonRelease-1>", left_release)' in layout_editor_source,
            "VTK face preview uses click-on-release selection plus fixed-speed left-drag rotation.",
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
