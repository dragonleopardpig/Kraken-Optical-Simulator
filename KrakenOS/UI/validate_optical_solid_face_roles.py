from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from KrakenOS.KrakenSys import system as KrakenSystem
from KrakenOS.UI import stl_geometry
from KrakenOS.UI import layout_editor as layout_editor_module
from KrakenOS.UI.panels import main_optical_solid_face_roles_dialog
from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    SurfaceRow,
    apply_optical_solid_face_suggestions,
    auto_assign_optical_solid_face_roles,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_candidate_triangles,
    optical_solid_face_world_markers,
    optical_solid_face_record_from_candidate,
    suggest_optical_solid_face_roles,
    _advanced_surface_attrs_from_spec,
)
from KrakenOS.UI.optical_solid_metadata import (
    OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    OPTICAL_SOLID_FACE_PORT_INPUT,
    OPTICAL_SOLID_FACE_PORT_INTERACTION,
    OPTICAL_SOLID_FACE_PORT_OUTPUT,
    OPTICAL_SOLID_FACE_ROLE_DEFAULT,
    OPTICAL_SOLID_FACE_SIDE_DEFAULT,
    apply_optical_solid_face_suggestions as service_apply_optical_solid_face_suggestions,
    auto_assign_optical_solid_face_roles as service_auto_assign_optical_solid_face_roles,
    normalize_optical_solid_face_metadata as service_normalize_optical_solid_face_metadata,
    optical_solid_face_port_role,
    optical_solid_face_record_from_candidate as service_optical_solid_face_record_from_candidate,
    optical_solid_input_anchor_face,
    optical_solid_faces_summary_text,
    suggest_optical_solid_face_roles as service_suggest_optical_solid_face_roles,
)
from KrakenOS.UI.nonseq_output_ports import (
    build_optical_solid_output_port_pose_overrides,
    select_optical_solid_interaction_face,
    select_optical_solid_output_face,
)
from KrakenOS.UI import nonseq_output_ports as nonseq_output_ports_module


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
    service_suggested_records = service_suggest_optical_solid_face_roles(records)
    suggested_records = suggest_optical_solid_face_roles(records)
    suggested_ports = [str(record.get("suggested_port_role", "")) for record in suggested_records]
    suggested_functions = [str(record.get("suggested_function", "")) for record in suggested_records]
    authored_before_suggestion = [
        (
            str(record.get("side_2d", "")),
            str(record.get("function", "")),
            str(record.get("port_role", "")),
        )
        for record in suggested_records
    ]
    explicit_suggestion_records = [dict(record) for record in suggested_records]
    if explicit_suggestion_records:
        explicit_suggestion_records[0]["side_2d"] = "Up"
        explicit_suggestion_records[0]["function"] = "Mirror"
        explicit_suggestion_records[0]["role"] = "Mirror"
        explicit_suggestion_records[0]["port_role"] = OPTICAL_SOLID_FACE_PORT_INTERACTION
    applied_suggested_records = apply_optical_solid_face_suggestions(explicit_suggestion_records)
    service_applied_suggested_records = service_apply_optical_solid_face_suggestions(explicit_suggestion_records)
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
                        },
                        {
                            "face_id": "O001",
                            "function": "Transmit/Port",
                            "role": "Output",
                            "port_role": OPTICAL_SOLID_FACE_PORT_OUTPUT,
                            "side_2d": "Down",
                            "normal": [0.0, -1.0, 0.0],
                            "centroid": [0.0, -10.0, 0.0],
                            "area_mm2": 75.0,
                        },
                    ]
                },
                "Solid_3d_stl": str(prism_path),
            },
        ),
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=10.0, glass="AIR"),
    ]
    mirror_overrides = build_optical_solid_output_port_pose_overrides(mirror_rows)
    inferred_input_rows = [
        SurfaceRow(surface="Object", name="Object", thickness=25.0, diameter=10.0, glass="AIR"),
        SurfaceRow(
            surface="Solid 3D STL",
            name="Inferred prism-through mirror",
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
                            "normal": [0.0, -1.0, 0.0],
                            "centroid": [0.0, 0.0, 12.5],
                            "area_mm2": 100.0,
                        },
                        {
                            "face_id": "O001",
                            "function": "Transmit/Port",
                            "role": "Output",
                            "port_role": OPTICAL_SOLID_FACE_PORT_OUTPUT,
                            "side_2d": "Right",
                            "normal": [-0.7071067811865476, 0.7071067811865476, 0.0],
                            "centroid": [-8.838834764831844, 8.838834764831846, 12.5],
                            "area_mm2": 75.0,
                        },
                        {
                            "face_id": "O002",
                            "function": "Transmit/Port",
                            "role": "Output",
                            "port_role": OPTICAL_SOLID_FACE_PORT_OUTPUT,
                            "side_2d": "Down",
                            "normal": [0.7071067811865477, 0.7071067811865474, 0.0],
                            "centroid": [8.838834764831839, 8.838834764831853, 12.5],
                            "area_mm2": 75.0,
                        },
                        {
                            "face_id": "U001",
                            "function": "Unassigned",
                            "role": "Unassigned",
                            "port_role": "Auto",
                            "side_2d": "Auto",
                            "normal": [0.0, 0.0, -1.0],
                            "centroid": [0.0, 5.8925565098879025, 0.0],
                            "area_mm2": 37.5,
                        },
                        {
                            "face_id": "U002",
                            "function": "Unassigned",
                            "role": "Unassigned",
                            "port_role": "Auto",
                            "side_2d": "Auto",
                            "normal": [0.0, 0.0, 1.0],
                            "centroid": [0.0, 5.892556509887903, 25.0],
                            "area_mm2": 37.5,
                        },
                    ]
                },
                "Solid_3d_stl": str(prism_path),
            },
        ),
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=10.0, glass="AIR"),
    ]
    inferred_input_pose = nonseq_output_ports_module._downstream_pose_from_frame(
        inferred_input_rows[1],
        np.asarray((0.0, 0.0, 25.0), dtype=float),
        np.eye(3, dtype=float),
    )
    inferred_reflected_direction = np.full(3, np.nan, dtype=float)
    if inferred_input_pose is not None:
        inferred_center, inferred_rotation = inferred_input_pose
        inferred_rotation = np.asarray(inferred_rotation, dtype=float).reshape(3, 3)
        interaction_record = next(
            (
                face
                for face in list(inferred_input_rows[1].advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR].get("faces", []) or [])
                if str(face.get("face_id", "")) == "M001"
            ),
            None,
        )
        if interaction_record is not None:
            interaction_normal = np.asarray(interaction_record.get("normal", (0.0, 0.0, 1.0)), dtype=float).reshape(3)
            if bool(interaction_record.get("flip_normal", False)):
                interaction_normal = -interaction_normal
            interaction_world_normal = inferred_rotation @ interaction_normal
            interaction_world_normal /= max(float(np.linalg.norm(interaction_world_normal)), 1e-12)
            incoming = np.asarray((0.0, 0.0, 1.0), dtype=float)
            inferred_reflected_direction = incoming - 2.0 * float(np.dot(incoming, interaction_world_normal)) * interaction_world_normal
            inferred_reflected_direction /= max(float(np.linalg.norm(inferred_reflected_direction)), 1e-12)
    explicit_external_rows = [
        SurfaceRow(surface="Object", name="Object", thickness=25.0, diameter=10.0, glass="AIR"),
        SurfaceRow(
            surface="Solid 3D STL",
            name="Explicit external mirror",
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
                            "normal": [0.0, -1.0, 0.0],
                            "centroid": [0.0, 0.0, 12.5],
                            "area_mm2": 100.0,
                        },
                        {
                            "face_id": "O001",
                            "function": "Transmit/Port",
                            "role": "Output",
                            "port_role": OPTICAL_SOLID_FACE_PORT_OUTPUT,
                            "side_2d": "Right",
                            "fit_reference": "+Z normal",
                            "normal": [-0.7071067811865476, 0.7071067811865476, 0.0],
                            "centroid": [-8.838834764831844, 8.838834764831846, 12.5],
                            "area_mm2": 75.0,
                        },
                        {
                            "face_id": "O002",
                            "function": "Transmit/Port",
                            "role": "Output",
                            "port_role": OPTICAL_SOLID_FACE_PORT_OUTPUT,
                            "side_2d": "Down",
                            "fit_reference": "-Y normal",
                            "normal": [0.7071067811865477, 0.7071067811865474, 0.0],
                            "centroid": [8.838834764831839, 8.838834764831853, 12.5],
                            "area_mm2": 75.0,
                        },
                        {
                            "face_id": "U001",
                            "function": "Unassigned",
                            "role": "Unassigned",
                            "port_role": "Auto",
                            "side_2d": "Auto",
                            "normal": [0.0, 0.0, -1.0],
                            "centroid": [0.0, 5.8925565098879025, 0.0],
                            "area_mm2": 37.5,
                        },
                        {
                            "face_id": "U002",
                            "function": "Unassigned",
                            "role": "Unassigned",
                            "port_role": "Auto",
                            "side_2d": "Auto",
                            "normal": [0.0, 0.0, 1.0],
                            "centroid": [0.0, 5.892556509887903, 25.0],
                            "area_mm2": 37.5,
                        },
                    ]
                },
                "Solid_3d_stl": str(prism_path),
            },
        ),
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=10.0, glass="AIR"),
    ]
    explicit_external_pose = nonseq_output_ports_module._downstream_pose_from_frame(
        explicit_external_rows[1],
        np.asarray((0.0, 0.0, 25.0), dtype=float),
        np.eye(3, dtype=float),
    )
    explicit_external_faces: dict[str, dict[str, object]] = {}
    if explicit_external_pose is not None:
        explicit_external_faces = {
            str(face.get("face_id", "") or "").strip(): face
            for face in nonseq_output_ports_module._optical_solid_faces_at_pose(
                explicit_external_rows[1],
                np.asarray(explicit_external_pose[0], dtype=float).reshape(3),
                np.asarray(explicit_external_pose[1], dtype=float).reshape(3, 3),
                assigned_only=False,
            )
            if isinstance(face, dict)
        }
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
    layout_editor_source += "\n" + Path(main_optical_solid_face_roles_dialog.__file__).read_text(encoding="utf-8")
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
    signed_terminal_system = KrakenSystem.__new__(KrakenSystem)
    signed_terminal_system.RAY = [np.asarray((0.0, 0.0, 0.0), dtype=float)]
    signed_terminal_system.SDT = [type("Surf", (), {"Diameter": 10.0})()]
    signed_terminal_system._system__AppendNsTerminalSegment((0.0, 0.0, 0.0), (0.0, 0.0, -1.0), -1.0)
    signed_terminal_endpoint = np.asarray(signed_terminal_system.RAY[-1], dtype=float)
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
            "geometry assistant suggests uncoated optical intent without authoring it",
            bool(suggested_records)
            and service_suggested_records == suggested_records
            and OPTICAL_SOLID_FACE_PORT_INPUT in suggested_ports
            and OPTICAL_SOLID_FACE_PORT_OUTPUT in suggested_ports
            and all(function == OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT for function in suggested_functions)
            and all(side == OPTICAL_SOLID_FACE_SIDE_DEFAULT for side, _function, _port in authored_before_suggestion)
            and all(function == OPTICAL_SOLID_FACE_FUNCTION_DEFAULT for _side, function, _port in authored_before_suggestion)
            and all(port == "Auto" for _side, _function, port in authored_before_suggestion),
            {
                "suggested_ports": suggested_ports[:6],
                "suggested_functions": suggested_functions[:6],
                "authored_before": authored_before_suggestion[:3],
            },
        ),
        OpticalSolidFaceRoleCheck(
            "applying geometry suggestions preserves explicit face overrides",
            bool(applied_suggested_records)
            and service_applied_suggested_records == applied_suggested_records
            and str(applied_suggested_records[0].get("function")) == "Mirror"
            and str(applied_suggested_records[0].get("role")) == "Mirror"
            and str(applied_suggested_records[0].get("side_2d")) == "Up"
            and str(applied_suggested_records[0].get("port_role")) == OPTICAL_SOLID_FACE_PORT_INTERACTION
            and any(
                str(record.get("function")) == OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT
                and str(record.get("role")) != OPTICAL_SOLID_FACE_ROLE_DEFAULT
                for record in applied_suggested_records[1:]
            ),
            {
                "first": applied_suggested_records[0] if applied_suggested_records else {},
                "applied_functions": [record.get("function") for record in applied_suggested_records[:6]],
            },
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
            and float(np.linalg.norm(np.asarray(mirror_overrides[2]["normal"], dtype=float).reshape(3))) > 0.999
            and float(np.dot(np.asarray(mirror_overrides[2]["normal"], dtype=float).reshape(3), np.asarray((0.0, -1.0, 0.0), dtype=float))) > 0.999,
            (
                f"override_keys={sorted(int(key) for key in mirror_overrides)}, "
                f"normal={tuple(float(value) for value in np.asarray(mirror_overrides.get(2, {}).get('normal', (0.0, 0.0, 0.0)), dtype=float).reshape(3))}"
            ),
        ),
        OpticalSolidFaceRoleCheck(
            "mirror-coated prism can infer an entrance face from output references",
            inferred_input_pose is not None
            and float(np.dot(inferred_reflected_direction, np.asarray((0.0, -1.0, 0.0), dtype=float))) > 0.99,
            (
                f"center={None if inferred_input_pose is None else tuple(float(value) for value in np.asarray(inferred_center, dtype=float).reshape(3))}, "
                f"reflected={tuple(float(value) for value in inferred_reflected_direction)}"
            ),
        ),
        OpticalSolidFaceRoleCheck(
            "explicit fit references prefer external mirror fold pose over prism-through inference",
            explicit_external_pose is not None
            and explicit_external_faces.get("O001") is not None
            and explicit_external_faces.get("O002") is not None
            and float(
                np.dot(
                    np.asarray(explicit_external_faces["O001"].get("normal_world", (0.0, 0.0, 0.0)), dtype=float).reshape(3),
                    np.asarray((0.0, 0.0, 1.0), dtype=float),
                )
            ) > 0.99
            and float(
                np.dot(
                    np.asarray(explicit_external_faces["O002"].get("normal_world", (0.0, 0.0, 0.0)), dtype=float).reshape(3),
                    np.asarray((0.0, -1.0, 0.0), dtype=float),
                )
            ) > 0.99,
            (
                f"pose={None if explicit_external_pose is None else tuple(float(value) for value in np.asarray(explicit_external_pose[0], dtype=float).reshape(3))}, "
                f"O001={None if explicit_external_faces.get('O001') is None else tuple(float(value) for value in np.asarray(explicit_external_faces['O001'].get('normal_world', (0.0, 0.0, 0.0)), dtype=float).reshape(3))}, "
                f"O002={None if explicit_external_faces.get('O002') is None else tuple(float(value) for value in np.asarray(explicit_external_faces['O002'].get('normal_world', (0.0, 0.0, 0.0)), dtype=float).reshape(3))}"
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
            and (
                "click selects, left-drag rotates" in layout_editor_source
                or "click selects; left-drag rotates" in layout_editor_source
            )
            and "rotate_preview_camera_fixed_drag" in layout_editor_source
            and (
                'preview_widget.bind("<B1-Motion>", left_motion)' in layout_editor_source
                or "preview_widget.bind('<B1-Motion>', left_motion)" in layout_editor_source
            )
            and (
                'preview_widget.bind("<ButtonRelease-1>", left_release)' in layout_editor_source
                or "preview_widget.bind('<ButtonRelease-1>', left_release)" in layout_editor_source
            ),
            "VTK face preview uses click-on-release selection plus fixed-speed left-drag rotation.",
        ),
        OpticalSolidFaceRoleCheck(
            "non-sequential terminal escape segment uses signed ray direction",
            signed_terminal_endpoint[2] > 0.0,
            f"endpoint={tuple(float(value) for value in signed_terminal_endpoint)}",
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
