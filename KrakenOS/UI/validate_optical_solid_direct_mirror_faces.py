"""Validate direct face-function mirror hits stay inside closed optical solids."""

from __future__ import annotations

import inspect
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import KrakenOS.KrakenSys as KrakenSys

from KrakenOS.UI import layout_editor as le
from KrakenOS.UI.layout_editor import cluster_optical_solid_planar_faces, solve_optical_solid_left_input_pose
from KrakenOS.UI.optical_solid_metadata import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
    OPTICAL_SOLID_FACE_PORT_INTERACTION,
    normalize_optical_solid_face_metadata,
)
from KrakenOS.UI.nonseq_output_ports import attach_scene_boundary_face_index, attach_scene_optical_volume_index
from KrakenOS.UI.validate_vendor_prism_42779 import (
    PRISM_42779_STEP,
    _build_vendor_prism_trace_system,
    _metadata_for_candidates,
)


@dataclass
class DirectMirrorFaceCheck:
    check: str
    ok: bool
    detail: str


def _direct_context_metadata(metadata: dict[str, object], candidates: list[object], mesh_path: Path) -> dict[str, object]:
    faces: list[dict[str, object]] = []
    for face in list(metadata.get("faces", []) or []):
        if not isinstance(face, dict):
            continue
        record = dict(face)
        if str(record.get("function", "") or "").strip() != OPTICAL_SOLID_FACE_FUNCTION_DEFAULT:
            record["port_role"] = OPTICAL_SOLID_FACE_PORT_INTERACTION
        faces.append(record)
    return normalize_optical_solid_face_metadata(
        {"source_stl": str(mesh_path), "faces": faces},
        candidates,
        source_stl=str(mesh_path),
    )


def validate_optical_solid_direct_mirror_faces() -> list[DirectMirrorFaceCheck]:
    checks: list[DirectMirrorFaceCheck] = []
    if not PRISM_42779_STEP.exists():
        return [DirectMirrorFaceCheck("Edmund 42779 STEP asset exists", False, str(PRISM_42779_STEP))]

    original_cache = le.CAD_CACHE_DIR
    with tempfile.TemporaryDirectory(prefix="kraken-direct-mirror-face-") as tmp_dir:
        le.CAD_CACHE_DIR = Path(tmp_dir)
        try:
            mesh_path, _source_path, _source_format = le._optical_solid_mesh_path_from_source(PRISM_42779_STEP)
            candidates = cluster_optical_solid_planar_faces(mesh_path)
            port_metadata = _metadata_for_candidates(candidates, mesh_path)
            solution = solve_optical_solid_left_input_pose(port_metadata)
            if solution is None:
                return [DirectMirrorFaceCheck("direct mirror fixture pose solves", False, "solution=None")]
            direct_metadata = _direct_context_metadata(port_metadata, candidates, mesh_path)
            system = _build_vendor_prism_trace_system(mesh_path, port_metadata, solution)
            system.SDT[1].OpticalSolidFaces = direct_metadata
            rows = [dict(row) for row in list(getattr(system, "_optical_solid_output_port_rows", []) or [])]
            if len(rows) >= 2:
                row = dict(rows[1])
                advanced = dict(row.get("advanced", {}) or {})
                advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = direct_metadata
                advanced["Solid_3d_stl"] = str(mesh_path)
                row["advanced"] = advanced
                rows[1] = row
                setattr(system, "_optical_solid_output_port_rows", rows)
                attach_scene_boundary_face_index(system, rows)
                attach_scene_optical_volume_index(system, rows)
            system.energy_probability = 0
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
    solid_interactions = [
        str(interactions[index] or "")
        for index in solid_steps
        if index < interactions.size
    ]
    solid_transitions = [
        str(transitions[index] or "")
        for index in solid_steps
        if index < transitions.size
    ]
    solid_inside_before = [
        str(inside_before[index] or "")
        for index in solid_steps
        if index < inside_before.size
    ]
    solid_inside_after = [
        str(inside_after[index] or "")
        for index in solid_steps
        if index < inside_after.size
    ]
    detail = (
        f"steps={solid_steps.tolist()}, faces={solid_faces}, interactions={solid_interactions}, "
        f"transitions={solid_transitions}, inside_before={solid_inside_before}, inside_after={solid_inside_after}"
    )
    checks.append(
        DirectMirrorFaceCheck(
            "direct Interaction Surface mirror faces do not skip the closed solid",
            solid_faces[:4] == ["F005", "F003", "F004", "F006"],
            detail,
        )
    )
    checks.append(
        DirectMirrorFaceCheck(
            "direct mirror hits stay in the optical volume until the exit face",
            solid_transitions[:4] == ["entry", "reflection", "reflection", "exit"]
            and solid_inside_after[:4] == ["volume:1", "volume:1", "volume:1", ""],
            detail,
        )
    )
    checks.append(
        DirectMirrorFaceCheck(
            "direct mirror hits are recorded as reflection events",
            len(solid_interactions) >= 4
            and solid_interactions[1:3] == ["reflect", "reflect"],
            detail,
        )
    )
    system_source = inspect.getsource(KrakenSys.system)
    checks.append(
        DirectMirrorFaceCheck(
            "external mirror reflection keeps same-solid faces eligible",
            system_source.count('bool(face_override.get("external_reflection"))') >= 2
            and system_source.count("skip_surface_once = None") >= 2,
            "external reflection nudges the origin but no longer skips the whole optical-solid row",
        )
    )
    return checks


def main() -> int:
    checks = validate_optical_solid_direct_mirror_faces()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} - {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
