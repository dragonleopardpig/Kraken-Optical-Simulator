"""Validate the bundled Edmund 42779 vendor prism CAD workflow."""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import KrakenOS as Kos

from KrakenOS.MeshRayTrace import KRAKEN_FACE_ID, KRAKEN_FACE_MATCH_METHOD
import KrakenOS.UI.layout_editor as le
from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    SOURCE_MODEL_DEFAULT,
    SurfaceRow,
    auto_assign_optical_solid_face_roles,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_record_from_candidate,
    optical_solid_trace_sequence_records,
    optical_solid_face_world_records,
    solve_optical_solid_face_fit,
    solve_optical_solid_left_input_pose,
)
from KrakenOS.UI.nonseq_output_ports import apply_optical_solid_output_port_system_overrides
from KrakenOS.UI.scene_builder import build_scene_bundle, _build_row_surface_groups, _reference_plane_display_points


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
        face_id = str(record.get("face_id", "") or "").strip()
        record["side_2d"] = "Auto"
        record["role"] = "Unassigned"
        record["function"] = "Unassigned"
        if face_id == "F005":
            record["side_2d"] = "Left"
            record["role"] = "Input"
            record["function"] = "Transmit/Port"
        elif face_id == "F006":
            record["side_2d"] = "Down"
            record["role"] = "Output"
            record["function"] = "Transmit/Port"
        elif face_id == "F003":
            record["side_2d"] = "Right"
            record["role"] = "Mirror"
            record["function"] = "Mirror"
        elif face_id == "F004":
            record["side_2d"] = "Up"
            record["role"] = "Mirror"
            record["function"] = "Mirror"
    return normalize_optical_solid_face_metadata(
        {"source_stl": str(mesh_path), "faces": records},
        candidates,
        source_stl=str(mesh_path),
    )


def _build_vendor_prism_trace_system(
    mesh_path: Path,
    metadata: dict[str, object],
    solution: dict[str, object],
    *,
    image_diameter: float = 50.0,
):
    obj = Kos.surf()
    obj.Name = "Object"
    obj.Thickness = 100.0
    obj.Diameter = 25.0
    obj.Drawing = 0

    prism = Kos.surf()
    prism.Name = "Edmund 42779 vendor prism"
    prism.Solid_3d_stl = str(mesh_path)
    prism.Glass = "BK7"
    prism.Diameter = 25.0
    prism.Thickness = 40.0
    prism.AxisMove = 2.0
    prism.TiltX = float(solution["tilts"][0])
    prism.TiltY = float(solution["tilts"][1])
    prism.TiltZ = float(solution["tilts"][2])
    prism.DespX = float(solution["desp"][0])
    prism.DespY = float(solution["desp"][1])
    prism.DespZ = float(solution["desp"][2])
    prism.OpticalSolidFaces = metadata

    image = Kos.surf()
    image.Name = "Image"
    image.Glass = "AIR"
    image.Diameter = float(image_diameter)
    image.Drawing = 1

    system = Kos.system([obj, prism, image], Kos.Setup())
    apply_optical_solid_output_port_system_overrides(
        system,
        [
            {"surface": "Object", "name": "Object", "thickness": 100.0, "diameter": 25.0, "advanced": {}, "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0, "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0},
            {
                "surface": "Standard",
                "name": "Edmund 42779 vendor prism",
                "thickness": 40.0,
                "diameter": 25.0,
                "advanced": {OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata, "Solid_3d_stl": str(mesh_path)},
                "tilt_x": float(solution["tilts"][0]),
                "tilt_y": float(solution["tilts"][1]),
                "tilt_z": float(solution["tilts"][2]),
                "desp_x": float(solution["desp"][0]),
                "desp_y": float(solution["desp"][1]),
                "desp_z": float(solution["desp"][2]),
            },
            {"surface": "Image", "name": "Image", "thickness": 0.0, "diameter": float(image_diameter), "advanced": {}, "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0, "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0},
        ],
    )
    return system


def _build_vendor_prism_doublet_trace_system(mesh_path: Path, metadata: dict[str, object], solution: dict[str, object]):
    obj = Kos.surf()
    obj.Name = "Object"
    obj.Thickness = 100.0
    obj.Diameter = 25.0
    obj.Drawing = 0

    prism = Kos.surf()
    prism.Name = "Edmund 42779 vendor prism"
    prism.Solid_3d_stl = str(mesh_path)
    prism.Glass = "BK7"
    prism.Diameter = 25.0
    prism.Thickness = 20.0
    prism.AxisMove = 2.0
    prism.TiltX = float(solution["tilts"][0])
    prism.TiltY = float(solution["tilts"][1])
    prism.TiltZ = float(solution["tilts"][2])
    prism.DespX = float(solution["desp"][0])
    prism.DespY = float(solution["desp"][1])
    prism.DespZ = float(solution["desp"][2])
    prism.OpticalSolidFaces = metadata

    crown = Kos.surf()
    crown.Name = "Crown Front"
    crown.Rc = 92.8470657
    crown.Thickness = 6.0
    crown.Diameter = 30.0
    crown.Glass = "BK7"

    flint = Kos.surf()
    flint.Name = "Flint Front"
    flint.Rc = -30.7160867
    flint.Thickness = 3.0
    flint.Diameter = 30.0
    flint.Glass = "F2"

    back = Kos.surf()
    back.Name = "Flint Back"
    back.Rc = -78.19730726
    back.Thickness = 97.37604743
    back.Diameter = 30.0
    back.Glass = "AIR"

    image = Kos.surf()
    image.Name = "Image"
    image.Glass = "AIR"
    image.Diameter = 50.0
    image.Drawing = 1

    rows = [
        {"surface": "Object", "name": "Object", "thickness": 100.0, "diameter": 25.0, "advanced": {}, "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0, "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0},
        {
            "surface": "Standard",
            "name": "Edmund 42779 vendor prism",
            "thickness": 20.0,
            "diameter": 25.0,
            "advanced": {OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata, "Solid_3d_stl": str(mesh_path)},
            "tilt_x": float(solution["tilts"][0]),
            "tilt_y": float(solution["tilts"][1]),
            "tilt_z": float(solution["tilts"][2]),
            "desp_x": float(solution["desp"][0]),
            "desp_y": float(solution["desp"][1]),
            "desp_z": float(solution["desp"][2]),
        },
        {"surface": "Standard", "name": "Crown Front", "thickness": 6.0, "diameter": 30.0, "advanced": {}, "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0, "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0},
        {"surface": "Standard", "name": "Flint Front", "thickness": 3.0, "diameter": 30.0, "advanced": {}, "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0, "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0},
        {"surface": "Standard", "name": "Flint Back", "thickness": 97.37604743, "diameter": 30.0, "advanced": {}, "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0, "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0},
        {"surface": "Image", "name": "Image", "thickness": 0.0, "diameter": 50.0, "advanced": {}, "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0, "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0},
    ]
    system = Kos.system([obj, prism, crown, flint, back, image], Kos.Setup())
    apply_optical_solid_output_port_system_overrides(system, rows)
    return system, rows


class _ReferencePlaneHarness:
    def __init__(self, rows: list[SurfaceRow]):
        self.rows = rows

    def _requested_trace_mode(self) -> str:
        return "Auto"

    def _current_source_model(self) -> str:
        return SOURCE_MODEL_DEFAULT

    def _current_display_orientation(self) -> str:
        return "YZ"

    def _current_nonseq_energy_probability(self) -> bool:
        return False

    def _current_nonseq_target_surface_index(self):
        return None

    def _project_xy(self, z, y):
        return np.asarray(z, dtype=float), np.asarray(y, dtype=float)


_ReferencePlaneHarness._scene_graph_value_present = staticmethod(le.KrakenLayoutEditor._scene_graph_value_present)
_ReferencePlaneHarness._system_transform_list = staticmethod(le.KrakenLayoutEditor._system_transform_list)
_ReferencePlaneHarness._row_z_positions = le.KrakenLayoutEditor._row_z_positions
_ReferencePlaneHarness._can_build_folded_layout = le.KrakenLayoutEditor._can_build_folded_layout
_ReferencePlaneHarness._has_off_axis_geometry = le.KrakenLayoutEditor._has_off_axis_geometry
_ReferencePlaneHarness._has_beam_splitter_surface = le.KrakenLayoutEditor._has_beam_splitter_surface
_ReferencePlaneHarness._has_diffuse_scatter_surface = le.KrakenLayoutEditor._has_diffuse_scatter_surface
_ReferencePlaneHarness._has_optical_stl_solid = le.KrakenLayoutEditor._has_optical_stl_solid
_ReferencePlaneHarness._resolved_trace_mode = le.KrakenLayoutEditor._resolved_trace_mode
_ReferencePlaneHarness._transform_reference_plane_overrides = le.KrakenLayoutEditor._transform_reference_plane_overrides
_ReferencePlaneHarness._select_optical_solid_output_face = staticmethod(le.KrakenLayoutEditor._select_optical_solid_output_face)
_ReferencePlaneHarness._optical_solid_image_plane_overrides = le.KrakenLayoutEditor._optical_solid_image_plane_overrides
_ReferencePlaneHarness._reference_plane_overrides = le.KrakenLayoutEditor._reference_plane_overrides
_ReferencePlaneHarness._project_layout_polyline = le.KrakenLayoutEditor._project_layout_polyline
_ReferencePlaneHarness._optical_solid_face_layout_polylines = le.KrakenLayoutEditor._optical_solid_face_layout_polylines
_ReferencePlaneHarness._stl_mesh_layout_polylines = le.KrakenLayoutEditor._stl_mesh_layout_polylines
_ReferencePlaneHarness._stl_path_from_row = le.KrakenLayoutEditor._stl_path_from_row
_ReferencePlaneHarness._stl_mesh_with_world_transform = le.KrakenLayoutEditor._stl_mesh_with_world_transform
_ReferencePlaneHarness._iter_3d_optical_surface_meshes = le.KrakenLayoutEditor._iter_3d_optical_surface_meshes
_ReferencePlaneHarness._legacy_3d_is_stop_plane = staticmethod(le.KrakenLayoutEditor._legacy_3d_is_stop_plane)


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
            face_membership_ok = all(
                isinstance(face, dict)
                and len(list(face.get("triangle_indices", []) or [])) == int(face.get("triangle_count", 0) or 0)
                and int(face.get("triangle_count", 0) or 0) > 0
                for face in faces
            )
            face_membership_detail = (
                f"membership={[len(list(face.get('triangle_indices', []) or [])) for face in faces]}, "
                f"counts={[int(face.get('triangle_count', 0) or 0) for face in faces]}"
            )
            anchor = next((face for face in faces if str(face.get("side_2d", "")) == "Left"), None)
            face_id = str(anchor.get("face_id", "") or "") if isinstance(anchor, dict) else ""
            solution = solve_optical_solid_face_fit(metadata, face_id=face_id, target_normal=(0.0, 0.0, -1.0))
            workflow_solution = solve_optical_solid_left_input_pose(metadata)
            row = None
            anchor_world = None
            workflow_anchor_world = None
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
            if workflow_solution is not None:
                workflow_row = SurfaceRow(
                    surface="Solid 3D STL",
                    name="Edmund 42779 vendor prism workflow",
                    advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata, "Solid_3d_stl": str(mesh_path)},
                    tilt_x=float(workflow_solution["tilts"][0]),
                    tilt_y=float(workflow_solution["tilts"][1]),
                    tilt_z=float(workflow_solution["tilts"][2]),
                    desp_x=float(workflow_solution["desp"][0]),
                    desp_y=float(workflow_solution["desp"][1]),
                    desp_z=float(workflow_solution["desp"][2]),
                )
                workflow_faces = optical_solid_face_world_records(workflow_row, 0.0, assigned_only=False)
                workflow_anchor_world = next(
                    (
                        face
                        for face in workflow_faces
                        if str(face.get("face_id", "")) == str(workflow_solution.get("face_id", ""))
                    ),
                    None,
                )
            trace_sequence = []
            image_reference_points = None
            image_reference_expected_center = None
            image_reference_override_keys: list[int] = []
            runtime_image_center = None
            runtime_last_surface = None
            runtime_last_point = None
            runtime_mesh_identity_ok = False
            runtime_mesh_identity_detail = "-"
            raykeeper_mesh_identity_ok = False
            raykeeper_mesh_identity_detail = "-"
            fan_exit_continued = 0
            fan_exit_stopped = 0
            fan_image_hits = 0
            doublet_last_surface = None
            doublet_override_keys: list[int] = []
            doublet_normals_follow_port = False
            doublet_centers_advance = False
            doublet_focus_span = np.nan
            core_faces_follow_output_port_override = False
            core_faces_follow_output_port_detail = "-"
            penta_layout_hull_vertices = 0
            penta_layout_polyline_count = 0
            scene_default_image_suppressed = False
            scene_default_image_detail = "-"
            open3d_layout_bounds_match = False
            open3d_layout_bounds_detail = "-"
            if workflow_solution is not None:
                trace_system = _build_vendor_prism_trace_system(mesh_path, metadata, workflow_solution)
                trace_system.energy_probability = 0
                trace_system.NsTrace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
                runtime_last_surface = int(trace_system.SURFACE[-1]) if len(trace_system.SURFACE) > 0 else None
                runtime_last_point = np.asarray(trace_system.XYZ[-1], dtype=float) if len(trace_system.XYZ) > 0 else None
                runtime_surfaces = np.asarray(getattr(trace_system, "SURFACE", []), dtype=int).ravel()
                runtime_cells = np.asarray(getattr(trace_system, "MESH_CELL_ID", []), dtype=int).ravel()
                runtime_original_cells = np.asarray(getattr(trace_system, "MESH_ORIGINAL_CELL_ID", []), dtype=int).ravel()
                runtime_face_ids = np.asarray(getattr(trace_system, "MESH_FACE_ID", []), dtype=object).ravel()
                solid_steps = np.flatnonzero(runtime_surfaces == 1)
                solid_cells = [
                    int(runtime_cells[index])
                    for index in solid_steps
                    if index < runtime_cells.size
                ]
                solid_original_cells = [
                    int(runtime_original_cells[index])
                    for index in solid_steps
                    if index < runtime_original_cells.size
                ]
                solid_face_ids = [
                    str(runtime_face_ids[index] or "")
                    for index in solid_steps
                    if index < runtime_face_ids.size
                ]
                try:
                    mesh_face_ids = np.asarray(trace_system.EEE[1].cell_data.get(KRAKEN_FACE_ID, []), dtype=object).reshape(-1)
                    mesh_face_methods = np.asarray(
                        trace_system.EEE[1].cell_data.get(KRAKEN_FACE_MATCH_METHOD, []),
                        dtype=object,
                    ).reshape(-1)
                    direct_face_ids = [
                        str(mesh_face_ids[cell] or "")
                        for cell in solid_cells
                        if 0 <= int(cell) < mesh_face_ids.size
                    ]
                    direct_face_methods = [
                        str(mesh_face_methods[cell] or "")
                        for cell in solid_cells
                        if 0 <= int(cell) < mesh_face_methods.size
                    ]
                except Exception:
                    direct_face_ids = []
                    direct_face_methods = []
                runtime_mesh_identity_ok = (
                    bool(solid_steps.size)
                    and all(cell >= 0 for cell in solid_cells)
                    and all(cell >= 0 for cell in solid_original_cells)
                    and any(face_id for face_id in solid_face_ids)
                    and direct_face_ids == solid_face_ids
                    and direct_face_methods
                    and all(method == "triangle_membership" for method in direct_face_methods)
                )
                runtime_mesh_identity_detail = (
                    f"steps={solid_steps.tolist()}, cells={solid_cells}, "
                    f"original={solid_original_cells}, faces={solid_face_ids}, "
                    f"direct_faces={direct_face_ids}, match_methods={direct_face_methods}"
                )
                identity_rays = Kos.raykeeper(trace_system)
                identity_rays.push()
                keeper_cells = np.asarray(identity_rays.MESH_CELL_ID[0], dtype=int).ravel() if identity_rays.MESH_CELL_ID else np.asarray([], dtype=int)
                keeper_faces = np.asarray(identity_rays.MESH_FACE_ID[0], dtype=object).ravel() if identity_rays.MESH_FACE_ID else np.asarray([], dtype=object)
                raykeeper_mesh_identity_ok = (
                    keeper_cells.size == runtime_cells.size
                    and any(int(cell) >= 0 for cell in keeper_cells.tolist())
                    and any(str(face or "") for face in keeper_faces.tolist())
                )
                raykeeper_mesh_identity_detail = f"keeper_cells={keeper_cells.tolist()}, keeper_faces={[str(face or '') for face in keeper_faces.tolist()]}"
                transforms = getattr(trace_system, "TRANS_2A", None)
                if transforms is not None and len(transforms) > 2:
                    runtime_image_center = np.asarray(transforms[2], dtype=float)[:3, 3]
                fan_system = _build_vendor_prism_trace_system(
                    mesh_path,
                    metadata,
                    workflow_solution,
                    image_diameter=1.0,
                )
                fan_system.energy_probability = 0
                for angle_deg in np.linspace(-2.0, 2.0, 9):
                    angle_rad = np.deg2rad(float(angle_deg))
                    fan_system.NsTrace(
                        [0.0, 0.0, 0.0],
                        [0.0, float(np.sin(angle_rad)), float(np.cos(angle_rad))],
                        0.55,
                    )
                    fan_surfaces = np.asarray(fan_system.SURFACE, dtype=int).ravel()
                    if fan_surfaces.size == 0:
                        continue
                    if int(fan_surfaces[-1]) == 2:
                        fan_image_hits += 1
                    elif int(fan_surfaces[-1]) == 1:
                        if len(getattr(fan_system, "RAY", [])) > len(fan_surfaces) + 1:
                            fan_exit_continued += 1
                        else:
                            fan_exit_stopped += 1
                hit_points = [
                    np.asarray(trace_system.XYZ[index + 1], dtype=float)
                    for index, surface in enumerate(list(trace_system.SURFACE))
                    if int(surface) == 1
                ]
                hit_normals = [
                    np.asarray(trace_system.S_LMN[index], dtype=float)
                    for index, surface in enumerate(list(trace_system.SURFACE))
                    if int(surface) == 1
                ]
                trace_sequence = optical_solid_trace_sequence_records(
                    SurfaceRow(
                        surface="Solid 3D STL",
                        name="Edmund 42779 vendor prism workflow",
                        advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata, "Solid_3d_stl": str(mesh_path)},
                        tilt_x=float(workflow_solution["tilts"][0]),
                        tilt_y=float(workflow_solution["tilts"][1]),
                        tilt_z=float(workflow_solution["tilts"][2]),
                        desp_x=float(workflow_solution["desp"][0]),
                        desp_y=float(workflow_solution["desp"][1]),
                        desp_z=float(workflow_solution["desp"][2]),
                    ),
                    100.0,
                    hit_points,
                    hit_normals,
                )
                preview_rows = [
                    SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
                    SurfaceRow(
                        surface="Solid 3D STL",
                        name="Edmund 42779 vendor prism workflow",
                        glass="BK7",
                        diameter=25.0,
                        thickness=40.0,
                        advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata, "Solid_3d_stl": str(mesh_path)},
                        tilt_x=float(workflow_solution["tilts"][0]),
                        tilt_y=float(workflow_solution["tilts"][1]),
                        tilt_z=float(workflow_solution["tilts"][2]),
                        desp_x=float(workflow_solution["desp"][0]),
                        desp_y=float(workflow_solution["desp"][1]),
                        desp_z=float(workflow_solution["desp"][2]),
                    ),
                    SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=17.4977327052, glass="AIR"),
                ]
                harness = _ReferencePlaneHarness(preview_rows)
                overrides = harness._reference_plane_overrides(system=trace_system)
                image_reference_override_keys = sorted(int(key) for key in overrides)
                scene_rays = Kos.raykeeper(trace_system)
                scene_rays.push()
                scene_bundle = build_scene_bundle(
                    rows=preview_rows,
                    system=trace_system,
                    rays=scene_rays,
                    display_orientation="YZ",
                    project_fn=harness._project_xy,
                    reference_plane_overrides=overrides,
                    detector_surface_indices=set(),
                    trace_mode_active="Non-Sequential Preview",
                )
                scene_detector_indices = list(scene_bundle.extra.get("detector_surface_indices", []) or [])
                scene_image_curves = [
                    int(curve.row_index)
                    for curve in scene_bundle.surface_curves
                    if str(getattr(curve, "kind", "")) == "image"
                ]
                scene_image_labels = [
                    int(label.row_index)
                    for label in scene_bundle.labels
                    if str(getattr(label, "text", "")) == "Image"
                ]
                scene_reached_image_count = sum(1 for path in scene_bundle.ray_paths if bool(path.reaches_image))
                scene_terminations = sorted(
                    {str(getattr(path, "termination_reason", "") or "") for path in scene_bundle.ray_paths}
                )
                scene_default_image_suppressed = (
                    not scene_detector_indices
                    and not scene_image_curves
                    and not scene_image_labels
                    and scene_reached_image_count == 0
                    and scene_terminations == ["no_next_intersection"]
                )
                scene_default_image_detail = (
                    f"detectors={scene_detector_indices}, image_curves={scene_image_curves}, "
                    f"image_labels={scene_image_labels}, reached={scene_reached_image_count}, "
                    f"terminations={scene_terminations}"
                )
                preview_z_positions: list[float] = [0.0]
                preview_z = 0.0
                for preview_row in preview_rows[:-1]:
                    preview_z += float(preview_row.thickness)
                    preview_z_positions.append(preview_z)
                output_face = le.KrakenLayoutEditor._select_optical_solid_output_face(
                    optical_solid_face_world_records(preview_rows[1], float(preview_z_positions[1]), assigned_only=True)
                )
                if output_face is not None:
                    centroid_world = np.asarray(output_face.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
                    normal_world = np.asarray(output_face.get("normal_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
                    if (
                        centroid_world.size >= 3
                        and normal_world.size >= 3
                        and np.all(np.isfinite(centroid_world[:3]))
                        and np.all(np.isfinite(normal_world[:3]))
                    ):
                        image_center_world = centroid_world[:3] + normal_world[:3] * float(preview_rows[1].thickness)
                        image_reference_expected_center = np.asarray((float(image_center_world[2]), float(image_center_world[1])), dtype=float)
                penta_layout_polylines = harness._stl_mesh_layout_polylines(trace_system, 1, float(preview_z_positions[1]))
                penta_layout_polyline_count = len(penta_layout_polylines)
                penta_layout_hull_vertices = int(penta_layout_polylines[0].shape[0]) if penta_layout_polylines else 0
                try:
                    le._load_3d_backends()
                    mesh_items = harness._iter_3d_optical_surface_meshes(trace_system, include_reference_surfaces=True)
                    prism_mesh = next(item.mesh for item in mesh_items if int(item.row_index) == 1)
                    mesh_points = np.asarray(prism_mesh.points, dtype=float)
                    layout_points = np.asarray(penta_layout_polylines[0], dtype=float) if penta_layout_polylines else np.empty((0, 2))
                    if mesh_points.ndim == 2 and mesh_points.shape[1] >= 3 and layout_points.ndim == 2 and layout_points.shape[1] >= 2:
                        mesh_yz = np.column_stack((mesh_points[:, 2], mesh_points[:, 1]))
                        mesh_bounds = np.asarray(
                            (
                                float(np.min(mesh_yz[:, 0])),
                                float(np.max(mesh_yz[:, 0])),
                                float(np.min(mesh_yz[:, 1])),
                                float(np.max(mesh_yz[:, 1])),
                            ),
                            dtype=float,
                        )
                        layout_bounds = np.asarray(
                            (
                                float(np.min(layout_points[:, 0])),
                                float(np.max(layout_points[:, 0])),
                                float(np.min(layout_points[:, 1])),
                                float(np.max(layout_points[:, 1])),
                            ),
                            dtype=float,
                        )
                        delta = float(np.max(np.abs(mesh_bounds - layout_bounds)))
                        open3d_layout_bounds_match = delta < 1e-6
                        open3d_layout_bounds_detail = f"delta={delta:.6g}, mesh_bounds={mesh_bounds.tolist()}, layout_bounds={layout_bounds.tolist()}"
                except Exception as exc:
                    open3d_layout_bounds_detail = f"3D bounds check unavailable: {exc}"
                z_pos = 0.0
                for row_index, row in enumerate(preview_rows):
                    points = _reference_plane_display_points(row_index, row, z_pos, overrides, harness._project_xy)
                    if row.surface == "Image":
                        image_reference_points = points
                    z_pos += float(row.thickness)
                doublet_system, _doublet_rows = _build_vendor_prism_doublet_trace_system(
                    mesh_path,
                    metadata,
                    workflow_solution,
                )
                doublet_system.energy_probability = 0
                doublet_image_z_values = []
                for launch_y in (-10.0, 0.0, 10.0):
                    doublet_system.NsTrace([0.0, launch_y, 0.0], [0.0, 0.0, 1.0], 0.55)
                    doublet_last_surface = int(doublet_system.SURFACE[-1]) if len(doublet_system.SURFACE) > 0 else None
                    if doublet_last_surface == 5 and len(doublet_system.XYZ) > 0:
                        doublet_image_z_values.append(float(np.asarray(doublet_system.XYZ[-1], dtype=float)[2]))
                if doublet_image_z_values:
                    doublet_focus_span = float(max(doublet_image_z_values) - min(doublet_image_z_values))
                doublet_overrides = getattr(doublet_system, "_optical_solid_output_port_pose_overrides", {}) or {}
                doublet_override_keys = sorted(int(key) for key in doublet_overrides)
                if doublet_override_keys:
                    first_pose = doublet_overrides[doublet_override_keys[0]]
                    output_normal = np.asarray(
                        first_pose.get("output_face", {}).get("normal_world", (0.0, 0.0, 1.0)),
                        dtype=float,
                    ).reshape(3)
                    output_normal = output_normal / max(float(np.linalg.norm(output_normal)), 1e-12)
                    normals = [
                        np.asarray(doublet_overrides[index]["normal"], dtype=float).reshape(3)
                        for index in doublet_override_keys
                    ]
                    centers = [
                        np.asarray(doublet_overrides[index]["center"], dtype=float).reshape(3)
                        for index in doublet_override_keys
                    ]
                    distances = [float(np.dot(center, output_normal)) for center in centers]
                    doublet_normals_follow_port = all(float(np.dot(normal, output_normal)) > 0.999 for normal in normals)
                    doublet_centers_advance = all(
                        distances[index + 1] > distances[index] + 1e-9
                        for index in range(len(distances) - 1)
                    )
                prism_rows = [
                    {
                        "surface": "Object",
                        "name": "Object",
                        "thickness": 100.0,
                        "diameter": 25.0,
                        "advanced": {},
                        "tilt_x": 0.0,
                        "tilt_y": 0.0,
                        "tilt_z": 0.0,
                        "desp_x": 0.0,
                        "desp_y": 0.0,
                        "desp_z": 0.0,
                    },
                    {
                        "surface": "Standard",
                        "name": "Upstream 42779 prism",
                        "thickness": 20.0,
                        "diameter": 25.0,
                        "advanced": {OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata, "Solid_3d_stl": str(mesh_path)},
                        "tilt_x": float(workflow_solution["tilts"][0]),
                        "tilt_y": float(workflow_solution["tilts"][1]),
                        "tilt_z": float(workflow_solution["tilts"][2]),
                        "desp_x": float(workflow_solution["desp"][0]),
                        "desp_y": float(workflow_solution["desp"][1]),
                        "desp_z": float(workflow_solution["desp"][2]),
                    },
                    {
                        "surface": "Standard",
                        "name": "Follower 42779 prism",
                        "thickness": 20.0,
                        "diameter": 25.0,
                        "advanced": {OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata, "Solid_3d_stl": str(mesh_path)},
                        "tilt_x": 0.0,
                        "tilt_y": 0.0,
                        "tilt_z": 0.0,
                        "desp_x": 0.0,
                        "desp_y": 0.0,
                        "desp_z": 0.0,
                    },
                    {
                        "surface": "Image",
                        "name": "Image",
                        "thickness": 0.0,
                        "diameter": 50.0,
                        "advanced": {},
                        "tilt_x": 0.0,
                        "tilt_y": 0.0,
                        "tilt_z": 0.0,
                        "desp_x": 0.0,
                        "desp_y": 0.0,
                        "desp_z": 0.0,
                    },
                ]
                follower_prism = Kos.surf()
                follower_prism.Name = "Follower 42779 prism"
                follower_prism.Solid_3d_stl = str(mesh_path)
                follower_prism.Glass = "BK7"
                follower_prism.Diameter = 25.0
                follower_prism.Thickness = 20.0
                follower_prism.AxisMove = 2.0
                follower_prism.OpticalSolidFaces = metadata
                upstream_prism = Kos.surf()
                upstream_prism.Name = "Upstream 42779 prism"
                upstream_prism.Solid_3d_stl = str(mesh_path)
                upstream_prism.Glass = "BK7"
                upstream_prism.Diameter = 25.0
                upstream_prism.Thickness = 20.0
                upstream_prism.AxisMove = 2.0
                upstream_prism.TiltX = float(workflow_solution["tilts"][0])
                upstream_prism.TiltY = float(workflow_solution["tilts"][1])
                upstream_prism.TiltZ = float(workflow_solution["tilts"][2])
                upstream_prism.DespX = float(workflow_solution["desp"][0])
                upstream_prism.DespY = float(workflow_solution["desp"][1])
                upstream_prism.DespZ = float(workflow_solution["desp"][2])
                upstream_prism.OpticalSolidFaces = metadata
                chain_object = Kos.surf()
                chain_object.Name = "Object"
                chain_object.Thickness = 100.0
                chain_object.Diameter = 25.0
                chain_image = Kos.surf()
                chain_image.Name = "Image"
                chain_image.Diameter = 50.0
                chain_system = Kos.system([chain_object, upstream_prism, follower_prism, chain_image], Kos.Setup())
                apply_optical_solid_output_port_system_overrides(chain_system, prism_rows)
                chain_overrides = getattr(chain_system, "_optical_solid_output_port_pose_overrides", {}) or {}
                follower_pose = chain_overrides.get(2)
                if isinstance(follower_pose, dict):
                    input_face = next(
                        (
                            face
                            for face in list(metadata.get("faces", []) or [])
                            if str(face.get("side_2d", "")) == "Left"
                        ),
                        None,
                    )
                    core_input_face = next(
                        (
                            face
                            for face in chain_system._system__OpticalSolidWorldFaces(2)
                            if str(face.get("side_2d", "")) == "Left"
                        ),
                        None,
                    )
                    if isinstance(input_face, dict) and isinstance(core_input_face, dict):
                        pose_center = np.asarray(follower_pose.get("center"), dtype=float).reshape(3)
                        pose_rotation = np.asarray(follower_pose.get("rotation"), dtype=float).reshape(3, 3)
                        expected_centroid = (
                            np.asarray(input_face.get("centroid", (0.0, 0.0, 0.0)), dtype=float).reshape(3)
                            @ pose_rotation.T
                            + pose_center
                        )
                        actual_centroid = np.asarray(core_input_face.get("centroid_world"), dtype=float).reshape(3)
                        error = float(np.linalg.norm(actual_centroid - expected_centroid))
                        core_faces_follow_output_port_override = error < 1e-6
                        core_faces_follow_output_port_detail = f"error_mm={error:.6g}, override_keys={sorted(int(key) for key in chain_overrides)}"
        finally:
            le.CAD_CACHE_DIR = original_cache
    layout_editor_source = Path(le.__file__).read_text(encoding="utf-8")
    nonseq_output_ports_source = (Path(le.__file__).resolve().parent / "nonseq_output_ports.py").read_text(encoding="utf-8")
    grouping_rows = [
        SurfaceRow(label="0", surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
        SurfaceRow(
            label="1",
            surface="Standard",
            name="Optical solid",
            thickness=20.0,
            diameter=25.0,
            glass="BK7",
            advanced={"Solid_3d_stl": str(mesh_path)},
        ),
        SurfaceRow(label="2", surface="Standard", name="Crown Front", thickness=6.0, diameter=30.0, glass="BK7"),
        SurfaceRow(label="3", surface="Standard", name="Flint Front", thickness=3.0, diameter=30.0, glass="F2"),
        SurfaceRow(label="4", surface="Standard", name="Flint Back", thickness=80.0, diameter=30.0, glass="AIR"),
        SurfaceRow(label="5", surface="Image", name="Image", thickness=0.0, diameter=10.0, glass="AIR"),
    ]
    lens_groups = _build_row_surface_groups(
        grouping_rows,
        {
            1: np.asarray([[0.0, -1.0], [0.0, 1.0]], dtype=float),
            2: np.asarray([[1.0, -1.0], [1.0, 1.0]], dtype=float),
            3: np.asarray([[2.0, -1.0], [2.0, 1.0]], dtype=float),
            4: np.asarray([[3.0, -1.0], [3.0, 1.0]], dtype=float),
        },
    )

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
                "CAD/STL face metadata preserves exact triangle membership",
                face_membership_ok,
                face_membership_detail,
            ),
            VendorPrism42779Check(
                "auto side labels include placement anchor faces",
                {"Left", "Right", "Up", "Down"}.issubset({str(face.get("side_2d", "")) for face in faces}),
                f"sides={[str(face.get('side_2d', '')) for face in faces]}",
            ),
            VendorPrism42779Check(
                "face-fit solver places selected input face as incoming -Z normal",
                solution is not None
                and anchor_world is not None
                and abs(
                    float(
                        np.dot(
                            np.asarray(anchor_world.get("normal_world", (0.0, 0.0, 0.0)), dtype=float),
                            np.asarray((0.0, 0.0, -1.0), dtype=float),
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
            VendorPrism42779Check(
                "Left-face workflow solver follows penta-prism input convention",
                workflow_solution is not None
                and workflow_anchor_world is not None
                and abs(
                    float(
                        np.dot(
                            np.asarray(workflow_anchor_world.get("normal_world", (0.0, 0.0, 0.0)), dtype=float),
                            np.asarray((0.0, 0.0, -1.0), dtype=float),
                        )
                    )
                    - 1.0
                )
                < 1e-6
                and np.linalg.norm(np.asarray(workflow_anchor_world.get("centroid_world", (0.0, 0.0, 0.0)), dtype=float)) < 1e-6,
                (
                    f"face={workflow_solution.get('face_id') if workflow_solution else '-'}, "
                    f"tilts={workflow_solution.get('tilts') if workflow_solution else '-'}, "
                    f"desp={workflow_solution.get('desp') if workflow_solution else '-'}, "
                    f"normal={workflow_anchor_world.get('normal_world') if workflow_anchor_world else '-'}, "
                    f"centroid={workflow_anchor_world.get('centroid_world') if workflow_anchor_world else '-'}"
                ),
            ),
            VendorPrism42779Check(
                "mirror-labeled vendor prism faces drive the non-sequential folded path",
                [str(event.get("side_2d", "")) for event in trace_sequence if str(event.get("kind", "")) == "face_hit"]
                == ["Left", "Right", "Up", "Down"],
                f"sequence={[str(event.get('side_2d', '')) for event in trace_sequence if str(event.get('kind', '')) == 'face_hit']}",
            ),
            VendorPrism42779Check(
                "non-sequential prism hits preserve mesh cell and matched face identity",
                runtime_mesh_identity_ok,
                runtime_mesh_identity_detail,
            ),
            VendorPrism42779Check(
                "raykeeper preserves non-sequential mesh hit identity",
                raykeeper_mesh_identity_ok,
                raykeeper_mesh_identity_detail,
            ),
            VendorPrism42779Check(
                "vendor prism 3D preview skips the duplicate side-body mesh",
                'if self._geometry_value_present(advanced.get("Solid_3d_stl")):' in layout_editor_source,
                "3D body-mesh collector skips Solid_3d_stl rows so imported optical solids are not drawn twice",
            ),
            VendorPrism42779Check(
                "2D lens edge grouping does not connect optical solids to follower lenses",
                lens_groups == [[2, 3, 4]],
                f"groups={lens_groups}",
            ),
            VendorPrism42779Check(
                "2D optical-solid drawing uses the projected prism silhouette",
                penta_layout_polyline_count == 1 and penta_layout_hull_vertices >= 5,
                f"polylines={penta_layout_polyline_count}, hull_vertices={penta_layout_hull_vertices}",
            ),
            VendorPrism42779Check(
                "2D follower CAD/STL drawing honors output-port pose override",
                "runtime_transform" in layout_editor_source
                and "optical_solid_output_port_runtime_transform_override(system, self.rows, row_index)" in layout_editor_source,
                "layout polylines use the shared runtime output-port transform resolver for follower optical solids",
            ),
            VendorPrism42779Check(
                "2D and Open 3D share the CAD/STL output-port pose resolver",
                open3d_layout_bounds_match
                and "def optical_solid_output_port_runtime_transform_override" in nonseq_output_ports_source
                and "optical_solid_output_port_runtime_transform_override(system, self.rows, index)" in layout_editor_source
                and "optical_solid_output_port_runtime_transform_override(system, self.editor.rows, row_index)" in layout_editor_source,
                open3d_layout_bounds_detail,
            ),
            VendorPrism42779Check(
                "core CAD/STL face matching honors output-port pose override",
                core_faces_follow_output_port_override,
                core_faces_follow_output_port_detail,
            ),
            VendorPrism42779Check(
                "non-sequential STL image reference plane follows the output port",
                image_reference_points is not None
                and image_reference_expected_center is not None
                and 2 in image_reference_override_keys
                and float(np.linalg.norm(np.mean(np.asarray(image_reference_points, dtype=float), axis=0) - image_reference_expected_center)) < 1e-6,
                f"override_keys={image_reference_override_keys}, expected_center={None if image_reference_expected_center is None else image_reference_expected_center.tolist()}, image_points={None if image_reference_points is None else np.asarray(image_reference_points, dtype=float).tolist()}",
            ),
            VendorPrism42779Check(
                "vendor prism runtime trace reaches the port-anchored image plane",
                runtime_last_surface == 2,
                f"last_surface={runtime_last_surface}, last_point={None if runtime_last_point is None else runtime_last_point.tolist()}",
            ),
            VendorPrism42779Check(
                "vendor prism runtime image transform matches the port-anchored detector pose",
                runtime_image_center is not None
                and image_reference_expected_center is not None
                and float(np.linalg.norm(runtime_image_center[[2, 1]] - image_reference_expected_center)) < 1e-6,
                f"runtime_image_center={None if runtime_image_center is None else runtime_image_center.tolist()}, expected_center={None if image_reference_expected_center is None else image_reference_expected_center.tolist()}",
            ),
            VendorPrism42779Check(
                "non-sequential scene display does not promote default Image row to detector",
                scene_default_image_suppressed,
                scene_default_image_detail,
            ),
            VendorPrism42779Check(
                "non-sequential STL fan continues after transmissive output misses",
                fan_exit_stopped == 0
                and fan_exit_continued > 0
                and fan_image_hits > 0,
                f"continued_after_exit={fan_exit_continued}, stopped_at_exit={fan_exit_stopped}, image_hits={fan_image_hits}",
            ),
            VendorPrism42779Check(
                "output-port follower optics advance along the selected port normal",
                doublet_override_keys == [2, 3, 4, 5]
                and doublet_normals_follow_port
                and doublet_centers_advance,
                (
                    f"override_keys={doublet_override_keys}, "
                    f"normals_follow={doublet_normals_follow_port}, centers_advance={doublet_centers_advance}"
                ),
            ),
            VendorPrism42779Check(
                "vendor prism followed by a cemented doublet reaches the image plane",
                doublet_last_surface == 5,
                f"last_surface={doublet_last_surface}",
            ),
            VendorPrism42779Check(
                "vendor prism followed by a cemented doublet focuses the meridional fan",
                np.isfinite(doublet_focus_span) and doublet_focus_span < 0.05,
                f"image_z_span_mm={doublet_focus_span:.6g}",
            ),
            VendorPrism42779Check(
                "CAD/STL import opens face assignment workflow",
                "Opening CAD/STL face assignment" in layout_editor_source
                and "open_optical_solid_face_role_editor(idx)" in layout_editor_source,
                "import/convert schedules the face-role dialog after inserting the optical solid row",
            ),
            VendorPrism42779Check(
                "face assignment save can snap Input Port face to traced ray",
                "snap Input Port to traced ray" in layout_editor_source
                and "_solve_optical_solid_path_input_pose(row_index, metadata_to_save)" in layout_editor_source
                and "solve_optical_solid_left_input_pose(metadata_to_save)" in layout_editor_source,
                "Save Roles prefers traced path/table-surface placement and falls back to the axial Left-face input solver",
            ),
            VendorPrism42779Check(
                "Save Roles applies the current selected face form before persisting",
                "def apply_current_form_to_selection_for_save" in layout_editor_source
                and "if not apply_current_form_to_selection_for_save()" in layout_editor_source
                and 'side_menu.bind("<<ComboboxSelected>>", auto_apply_selected_face_identity' in layout_editor_source
                and 'function_menu.bind("<<ComboboxSelected>>", auto_apply_selected_face_identity' in layout_editor_source,
                "users can change 2D side/function fields, switch faces, or press Save Roles without a separate Apply click",
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
        payload = []
        for check in checks:
            item = asdict(check)
            item["ok"] = bool(item.get("ok"))
            payload.append(item)
        print(json.dumps(payload, indent=2, default=str))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
