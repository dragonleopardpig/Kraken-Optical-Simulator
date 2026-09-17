"""Validate an imported right-angle STEP prism produces physical TIR."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import KrakenOS as Kos

from KrakenOS.UI import layout_editor as le
from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_record_from_candidate,
    solve_optical_solid_left_input_pose,
)
from KrakenOS.UI.nonseq_output_ports import apply_optical_solid_output_port_system_overrides
from KrakenOS.UI.optical_solid_metadata import (
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    OPTICAL_SOLID_FACE_PORT_INPUT,
    OPTICAL_SOLID_FACE_PORT_INTERACTION,
    OPTICAL_SOLID_FACE_PORT_OUTPUT,
)
from KrakenOS.UI.services.prism_fixtures import PRISM_32336_STEP


RIGHT_ANGLE_PRISM_STEP = PRISM_32336_STEP


@dataclass
class RightAnglePrismTirCheck:
    check: str
    ok: bool
    detail: str


def _candidate_normal(candidate: object) -> np.ndarray:
    normal = np.asarray(getattr(candidate, "normal", (np.nan, np.nan, np.nan)), dtype=float)
    norm = float(np.linalg.norm(normal))
    if not np.isfinite(norm) or norm <= 0.0:
        return np.asarray((np.nan, np.nan, np.nan), dtype=float)
    return normal / norm


def _candidate_area(candidate: object) -> float:
    try:
        return float(getattr(candidate, "area_mm2", np.nan))
    except Exception:
        return float("nan")


def _right_angle_metadata(candidates: list[object], mesh_path: Path) -> dict[str, object]:
    records = [optical_solid_face_record_from_candidate(candidate) for candidate in candidates]
    if len(records) < 5:
        raise ValueError(f"expected at least five planar faces, got {len(records)}")

    by_id = {str(record.get("face_id", "") or ""): record for record in records}
    candidate_by_id = {
        str(getattr(candidate, "face_id", "") or ""): candidate
        for candidate in candidates
    }
    finite_area_records = [
        record
        for record in records
        if np.isfinite(_candidate_area(candidate_by_id.get(str(record.get("face_id", "") or ""))))
    ]
    hypotenuse = max(
        finite_area_records,
        key=lambda record: _candidate_area(candidate_by_id[str(record.get("face_id", "") or "")]),
    )
    hypotenuse_id = str(hypotenuse.get("face_id", "") or "")
    side_faces = []
    for record in records:
        face_id = str(record.get("face_id", "") or "")
        if face_id == hypotenuse_id:
            continue
        candidate = candidate_by_id.get(face_id)
        if candidate is None:
            continue
        normal = _candidate_normal(candidate)
        if abs(float(normal[2])) < 0.5:
            side_faces.append(record)
    if len(side_faces) < 2:
        raise ValueError("could not find the two optical leg faces of the prism")
    side_faces.sort(key=lambda record: str(record.get("face_id", "") or ""))
    input_id = str(side_faces[0].get("face_id", "") or "")
    output_id = str(side_faces[1].get("face_id", "") or "")

    for record in records:
        face_id = str(record.get("face_id", "") or "")
        record["function"] = OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT
        record["role"] = "Unassigned"
        record["side_2d"] = "Auto"
        record["port_role"] = OPTICAL_SOLID_FACE_PORT_INTERACTION
        if face_id == input_id:
            record["role"] = "Input"
            record["side_2d"] = "Left"
            record["port_role"] = OPTICAL_SOLID_FACE_PORT_INPUT
        elif face_id == output_id:
            record["role"] = "Output"
            record["side_2d"] = "Right"
            record["port_role"] = OPTICAL_SOLID_FACE_PORT_OUTPUT
    metadata = normalize_optical_solid_face_metadata(
        {"source_stl": str(mesh_path), "faces": records},
        candidates,
        source_stl=str(mesh_path),
    )
    metadata["validator_face_ids"] = {
        "input": input_id,
        "hypotenuse": hypotenuse_id,
        "output": output_id,
    }
    return metadata


def _build_trace_system(mesh_path: Path, metadata: dict[str, object], solution: dict[str, object]):
    obj = Kos.surf()
    obj.Name = "Point source reference"
    obj.Thickness = 80.0
    obj.Diameter = 20.0
    obj.Drawing = 0

    prism = Kos.surf()
    prism.Name = "Imported right-angle prism"
    prism.Solid_3d_stl = str(mesh_path)
    prism.Glass = "BK7"
    prism.Diameter = 35.0
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
    image.Name = "Reference image"
    image.Glass = "AIR"
    image.Diameter = 80.0
    image.Drawing = 1

    rows = [
        {
            "surface": "Object",
            "name": obj.Name,
            "thickness": obj.Thickness,
            "diameter": obj.Diameter,
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
            "name": prism.Name,
            "thickness": prism.Thickness,
            "diameter": prism.Diameter,
            "advanced": {
                OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata,
                "Solid_3d_stl": str(mesh_path),
            },
            "tilt_x": prism.TiltX,
            "tilt_y": prism.TiltY,
            "tilt_z": prism.TiltZ,
            "desp_x": prism.DespX,
            "desp_y": prism.DespY,
            "desp_z": prism.DespZ,
        },
        {
            "surface": "Image",
            "name": image.Name,
            "thickness": 0.0,
            "diameter": image.Diameter,
            "advanced": {},
            "tilt_x": 0.0,
            "tilt_y": 0.0,
            "tilt_z": 0.0,
            "desp_x": 0.0,
            "desp_y": 0.0,
            "desp_z": 0.0,
        },
    ]
    system = Kos.system([obj, prism, image], Kos.Setup())
    apply_optical_solid_output_port_system_overrides(system, rows)
    system.energy_probability = 0
    return system


def validate_right_angle_prism_tir() -> list[RightAnglePrismTirCheck]:
    checks: list[RightAnglePrismTirCheck] = []
    if not RIGHT_ANGLE_PRISM_STEP.exists():
        return [
            RightAnglePrismTirCheck(
                "right-angle STEP fixture exists",
                False,
                str(RIGHT_ANGLE_PRISM_STEP),
            )
        ]

    original_cache = le.CAD_CACHE_DIR
    with tempfile.TemporaryDirectory(prefix="kraken-right-angle-tir-") as tmp_dir:
        le.CAD_CACHE_DIR = Path(tmp_dir)
        try:
            mesh_path, _source_path, _source_format = le._optical_solid_mesh_path_from_source(RIGHT_ANGLE_PRISM_STEP)
            candidates = cluster_optical_solid_planar_faces(mesh_path)
            metadata = _right_angle_metadata(candidates, mesh_path)
            solution = solve_optical_solid_left_input_pose(metadata)
            if solution is None:
                return [RightAnglePrismTirCheck("right-angle input pose solves", False, "solution=None")]
            system = _build_trace_system(mesh_path, metadata, solution)
            system.NsTrace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
        finally:
            le.CAD_CACHE_DIR = original_cache

    surfaces = np.asarray(getattr(system, "SURFACE", []), dtype=int).ravel()
    face_ids = np.asarray(getattr(system, "MESH_FACE_ID", []), dtype=object).ravel()
    interactions = np.asarray(getattr(system, "INTERACTION_TYPE", []), dtype=object).ravel()
    transitions = np.asarray(getattr(system, "MEDIA_TRANSITION", []), dtype=object).ravel()
    inside_before = np.asarray(getattr(system, "INSIDE_VOLUMES_BEFORE", []), dtype=object).ravel()
    inside_after = np.asarray(getattr(system, "INSIDE_VOLUMES_AFTER", []), dtype=object).ravel()
    solid_steps = np.flatnonzero(surfaces == 1)
    solid_faces = [str(face_ids[index] or "") for index in solid_steps if index < face_ids.size]
    solid_interactions = [str(interactions[index] or "") for index in solid_steps if index < interactions.size]
    solid_transitions = [str(transitions[index] or "") for index in solid_steps if index < transitions.size]
    solid_inside_before = [str(inside_before[index] or "") for index in solid_steps if index < inside_before.size]
    solid_inside_after = [str(inside_after[index] or "") for index in solid_steps if index < inside_after.size]
    ids = dict(metadata.get("validator_face_ids", {}) or {})
    expected_faces = [ids.get("input", ""), ids.get("hypotenuse", ""), ids.get("output", "")]
    detail = (
        f"faces={solid_faces}, interactions={solid_interactions}, transitions={solid_transitions}, "
        f"inside_before={solid_inside_before}, inside_after={solid_inside_after}, ids={ids}"
    )
    checks.append(
        RightAnglePrismTirCheck(
            "uncoated right-angle prism central ray enters, TIRs on hypotenuse, and exits",
            solid_faces[:3] == expected_faces
            and solid_interactions[:3] == ["refract", "reflect_tir", "refract"],
            detail,
        )
    )
    checks.append(
        RightAnglePrismTirCheck(
            "TIR is derived from uncoated BK7-air physics, not a forced mirror role",
            solid_transitions[:3] == ["entry", "reflection", "exit"]
            and solid_inside_before[:3] == ["", "volume:1", "volume:1"]
            and solid_inside_after[:3] == ["volume:1", "volume:1", ""],
            detail,
        )
    )
    return checks


def main() -> int:
    checks = validate_right_angle_prism_tir()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} - {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
