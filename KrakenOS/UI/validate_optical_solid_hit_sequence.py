from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from KrakenOS.Examples.Examp_Phase6_Optical_STL_Prism import (
    PRISM_STL,
    Prism_Solid,
    build_system,
    trace_collimated_grid,
)
from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y,
    SurfaceRow,
    auto_assign_optical_solid_face_roles,
    build_optical_solid_cube_splitter_virtual_plane,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_record_from_candidate,
    optical_solid_trace_sequence_records,
)
from KrakenOS.UI.optical_solid_metadata import (
    optical_solid_trace_sequence_records as service_optical_solid_trace_sequence_records,
)
from KrakenOS.UI.scene_builder import _build_ray_hit_records


@dataclass
class OpticalSolidHitSequenceCheck:
    check: str
    ok: bool
    detail: str


def _cube_face_metadata() -> dict[str, object]:
    faces = [
        {"face_id": "F001", "side_2d": "Left", "function": "Transmit/Port", "normal": [0.0, 0.0, -1.0], "centroid": [0.0, 0.0, -5.0], "area_mm2": 100.0},
        {"face_id": "F002", "side_2d": "Right", "function": "Transmit/Port", "normal": [0.0, 0.0, 1.0], "centroid": [0.0, 0.0, 5.0], "area_mm2": 100.0},
        {"face_id": "F003", "side_2d": "Up", "function": "Transmit/Port", "normal": [0.0, 1.0, 0.0], "centroid": [0.0, 5.0, 0.0], "area_mm2": 100.0},
        {"face_id": "F004", "side_2d": "Down", "function": "Transmit/Port", "normal": [0.0, -1.0, 0.0], "centroid": [0.0, -5.0, 0.0], "area_mm2": 100.0},
        {"face_id": "F005", "side_2d": "Front", "function": "Absorber/Mechanical", "normal": [-1.0, 0.0, 0.0], "centroid": [-5.0, 0.0, 0.0], "area_mm2": 100.0},
        {"face_id": "F006", "side_2d": "Back", "function": "Absorber/Mechanical", "normal": [1.0, 0.0, 0.0], "centroid": [5.0, 0.0, 0.0], "area_mm2": 100.0},
    ]
    return normalize_optical_solid_face_metadata({"faces": faces, "source_stl": "cube_bs.stl"}, source_stl="cube_bs.stl")


def _prism_row_with_face_metadata() -> SurfaceRow:
    candidates = cluster_optical_solid_planar_faces(PRISM_STL)
    records = [optical_solid_face_record_from_candidate(candidate) for candidate in candidates]
    metadata = normalize_optical_solid_face_metadata(
        {"source_stl": str(PRISM_STL), "faces": auto_assign_optical_solid_face_roles(records)},
        candidates,
        source_stl=str(PRISM_STL),
    )
    return SurfaceRow(
        surface="Solid 3D STL",
        name=Prism_Solid.Name,
        glass=Prism_Solid.Glass,
        diameter=Prism_Solid.Diameter,
        thickness=Prism_Solid.Thickness,
        desp_y=Prism_Solid.DespY,
        axis_move=Prism_Solid.AxisMove,
        advanced={
            OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata,
            "Solid_3d_stl": str(PRISM_STL),
        },
    )


def _validate_real_prism_sequence() -> list[OpticalSolidHitSequenceCheck]:
    row = _prism_row_with_face_metadata()
    system = build_system()
    rays = trace_collimated_grid(system, grid_count=1, radius_mm=0.0, wavelength_um=0.55)
    prism_hits = [hit for hit in _build_ray_hit_records(system.SDT, rays, 0) if hit.surface_id == 1]
    sequence = optical_solid_trace_sequence_records(
        row,
        30.0,
        [hit.point_world for hit in prism_hits],
        [hit.surface_normal for hit in prism_hits],
    )
    service_sequence = service_optical_solid_trace_sequence_records(
        row,
        30.0,
        [hit.point_world for hit in prism_hits],
        [hit.surface_normal for hit in prism_hits],
    )
    face_hits = [event for event in sequence if str(event.get("kind")) == "face_hit"]
    sides = [str(event.get("side_2d", "")) for event in face_hits]
    alignments = [float(event.get("normal_alignment", np.nan)) for event in face_hits]
    plane_distances = [float(event.get("plane_distance_mm", np.nan)) for event in face_hits]
    return [
        OpticalSolidHitSequenceCheck(
            "real prism hit-sequence classifier preserves hit count",
            len(face_hits) == len(prism_hits) and len(face_hits) == 4,
            f"sequence_hits={len(face_hits)}, traced_hits={len(prism_hits)}",
        ),
        OpticalSolidHitSequenceCheck(
            "real prism chief ray maps to Left -> Right -> Down -> Left faces",
            sides == ["Left", "Right", "Down", "Left"],
            f"sides={sides}",
        ),
        OpticalSolidHitSequenceCheck(
            "real prism hit classification keeps finite face alignment and plane distance",
            bool(face_hits)
            and all(np.isfinite(alignments))
            and all(np.isfinite(plane_distances))
            and min(alignments) > 0.99
            and max(plane_distances) < 1e-3,
            (
                f"alignments={[round(value, 6) for value in alignments]}, "
                f"plane_mm={[round(value, 9) for value in plane_distances]}"
            ),
        ),
        OpticalSolidHitSequenceCheck(
            "real prism sequence does not insert virtual-plane events when none are defined",
            all(str(event.get("kind")) != "virtual_plane" for event in sequence),
            f"kinds={[str(event.get('kind')) for event in sequence]}",
        ),
        OpticalSolidHitSequenceCheck(
            "real prism hit-sequence classifier is service-owned",
            service_sequence == sequence,
            f"service_events={len(service_sequence)}, ui_events={len(sequence)}",
        ),
    ]


def _validate_virtual_plane_sequence() -> list[OpticalSolidHitSequenceCheck]:
    metadata = _cube_face_metadata()
    plane = build_optical_solid_cube_splitter_virtual_plane(
        metadata,
        diagonal_mode=OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y,
        split_ratio=0.5,
        loss=0.02,
        phase_deg=180.0,
    )
    metadata_with_plane = normalize_optical_solid_face_metadata(
        {"faces": metadata.get("faces", []), "virtual_planes": [plane], "source_stl": "cube_bs.stl"},
        source_stl="cube_bs.stl",
    )
    row = SurfaceRow(
        surface="Solid 3D STL",
        name="68551 cube",
        advanced={
            OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata_with_plane,
            "Solid_3d_stl": "cube_bs.stl",
            "OpticalSolidSourcePath": str(Path("attachment") / "68551"),
            "OpticalSolidSourceFormat": "STEP",
        },
    )
    sequence = optical_solid_trace_sequence_records(
        row,
        0.0,
        [(0.0, 0.0, -5.0), (0.0, 0.0, 5.0)],
        [(0.0, 0.0, -1.0), (0.0, 0.0, 1.0)],
    )
    service_sequence = service_optical_solid_trace_sequence_records(
        row,
        0.0,
        [(0.0, 0.0, -5.0), (0.0, 0.0, 5.0)],
        [(0.0, 0.0, -1.0), (0.0, 0.0, 1.0)],
    )
    kinds = [str(event.get("kind", "")) for event in sequence]
    labels = [str(event.get("side_2d", event.get("plane_kind", ""))) for event in sequence]
    plane_events = [event for event in sequence if str(event.get("kind")) == "virtual_plane"]
    crossing_point = np.asarray(
        plane_events[0].get("crossing_point_world", (np.nan, np.nan, np.nan)),
        dtype=float,
    ) if plane_events else np.full(3, np.nan, dtype=float)
    return [
        OpticalSolidHitSequenceCheck(
            "virtual internal plane inserts a sequence event between entry and exit faces",
            kinds == ["face_hit", "virtual_plane", "face_hit"],
            f"kinds={kinds}, labels={labels}",
        ),
        OpticalSolidHitSequenceCheck(
            "virtual internal plane crossing stays centered inside the cube",
            np.all(np.isfinite(crossing_point)) and np.linalg.norm(crossing_point[:3]) < 1e-9,
            f"crossing={tuple(float(value) for value in crossing_point[:3])}",
        ),
        OpticalSolidHitSequenceCheck(
            "virtual internal plane preserves splitter metadata through the sequence record",
            bool(plane_events)
            and str(plane_events[0].get("plane_kind")) == "Beam Splitter"
            and abs(float(plane_events[0].get("split_ratio", 0.0)) - 0.5) < 1e-9
            and abs(float(plane_events[0].get("loss", 0.0)) - 0.02) < 1e-9
            and abs(float(plane_events[0].get("phase_deg", 0.0)) - 180.0) < 1e-9,
            (
                f"kind={plane_events[0].get('plane_kind') if plane_events else '-'}, "
                f"split={plane_events[0].get('split_ratio') if plane_events else '-'}, "
                f"loss={plane_events[0].get('loss') if plane_events else '-'}, "
                f"phase={plane_events[0].get('phase_deg') if plane_events else '-'}"
            ),
        ),
        OpticalSolidHitSequenceCheck(
            "virtual internal plane sequence classifier is service-owned",
            service_sequence == sequence,
            f"service_events={len(service_sequence)}, ui_events={len(sequence)}",
        ),
    ]


def validate_optical_solid_hit_sequence() -> list[OpticalSolidHitSequenceCheck]:
    return [
        *_validate_real_prism_sequence(),
        *_validate_virtual_plane_sequence(),
    ]


def _print_table(checks: list[OpticalSolidHitSequenceCheck]) -> None:
    print("KrakenOS optical-solid hit-sequence validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate traced optical-solid hit sequences against saved face-role metadata.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_optical_solid_hit_sequence()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
