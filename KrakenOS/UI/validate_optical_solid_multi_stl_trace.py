"""Validate chained tracing through multiple file-backed optical STL solids."""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.TraceEvents import trace_event_to_record
from KrakenOS.UI.layout_editor import SurfaceRow, _build_system_from_specs
from KrakenOS.UI.optical_solid_metadata import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    normalize_optical_solid_face_metadata,
)
from KrakenOS.UI.scene_builder import build_scene_boundary_face_index, build_scene_bundle


@dataclass
class OpticalSolidMultiStlTraceCheck:
    check: str
    ok: bool
    detail: str


def _box_face_specs(half_x: float, half_y: float, half_z: float) -> list[dict[str, object]]:
    return [
        {
            "face_id": "IN",
            "side_2d": "Left",
            "normal": (0.0, 0.0, -1.0),
            "centroid": (0.0, 0.0, -half_z),
            "u": (0.0, half_y, 0.0),
            "v": (half_x, 0.0, 0.0),
            "area_mm2": 4.0 * half_x * half_y,
            "function": OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
            "role": "Input",
            "port_role": "Input Port",
        },
        {
            "face_id": "OUT",
            "side_2d": "Right",
            "normal": (0.0, 0.0, 1.0),
            "centroid": (0.0, 0.0, half_z),
            "u": (half_x, 0.0, 0.0),
            "v": (0.0, half_y, 0.0),
            "area_mm2": 4.0 * half_x * half_y,
            "function": OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
            "role": "Output",
            "port_role": "Output Port",
        },
        {
            "face_id": "UP",
            "side_2d": "Up",
            "normal": (0.0, 1.0, 0.0),
            "centroid": (0.0, half_y, 0.0),
            "u": (0.0, 0.0, half_z),
            "v": (half_x, 0.0, 0.0),
            "area_mm2": 4.0 * half_x * half_z,
            "function": "Absorber/Mechanical",
            "role": "Absorber/Mechanical",
            "port_role": "Interaction Surface",
        },
        {
            "face_id": "DOWN",
            "side_2d": "Down",
            "normal": (0.0, -1.0, 0.0),
            "centroid": (0.0, -half_y, 0.0),
            "u": (half_x, 0.0, 0.0),
            "v": (0.0, 0.0, half_z),
            "area_mm2": 4.0 * half_x * half_z,
            "function": "Absorber/Mechanical",
            "role": "Absorber/Mechanical",
            "port_role": "Interaction Surface",
        },
        {
            "face_id": "FRONT",
            "side_2d": "Front",
            "normal": (-1.0, 0.0, 0.0),
            "centroid": (-half_x, 0.0, 0.0),
            "u": (0.0, 0.0, half_z),
            "v": (0.0, half_y, 0.0),
            "area_mm2": 4.0 * half_y * half_z,
            "function": "Absorber/Mechanical",
            "role": "Absorber/Mechanical",
            "port_role": "Interaction Surface",
        },
        {
            "face_id": "BACK",
            "side_2d": "Back",
            "normal": (1.0, 0.0, 0.0),
            "centroid": (half_x, 0.0, 0.0),
            "u": (0.0, half_y, 0.0),
            "v": (0.0, 0.0, half_z),
            "area_mm2": 4.0 * half_y * half_z,
            "function": "Absorber/Mechanical",
            "role": "Absorber/Mechanical",
            "port_role": "Interaction Surface",
        },
    ]


def _write_box_stl(path: Path, *, half_x: float = 3.0, half_y: float = 3.0, half_z: float = 2.0) -> list[dict[str, object]]:
    faces = _box_face_specs(half_x, half_y, half_z)
    triangles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
    for face in faces:
        center = np.asarray(face["centroid"], dtype=float)
        u_axis = np.asarray(face["u"], dtype=float)
        v_axis = np.asarray(face["v"], dtype=float)
        normal = np.asarray(face["normal"], dtype=float)
        p00 = center - u_axis - v_axis
        p10 = center + u_axis - v_axis
        p11 = center + u_axis + v_axis
        p01 = center - u_axis + v_axis
        face["triangle_start"] = len(triangles)
        triangles.extend(((normal, p00, p10, p11), (normal, p00, p11, p01)))

    lines = [f"solid {path.stem}"]
    for normal, p0, p1, p2 in triangles:
        lines.append("  facet normal {:.9g} {:.9g} {:.9g}".format(*normal))
        lines.append("    outer loop")
        for point in (p0, p1, p2):
            lines.append("      vertex {:.9g} {:.9g} {:.9g}".format(*point))
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {path.stem}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return faces


def _box_metadata(path: Path) -> dict[str, object]:
    faces = _write_box_stl(path)
    records: list[dict[str, object]] = []
    for face in faces:
        start = int(face["triangle_start"])
        records.append(
            {
                "face_id": str(face["face_id"]),
                "role": str(face["role"]),
                "function": str(face["function"]),
                "side_2d": str(face["side_2d"]),
                "port_role": str(face["port_role"]),
                "normal": [float(value) for value in face["normal"]],
                "centroid": [float(value) for value in face["centroid"]],
                "area_mm2": float(face["area_mm2"]),
                "triangle_count": 2,
                "triangle_indices": [start, start + 1],
                "plane_offset_mm": 0.0,
                "flip_normal": False,
                "material": "",
                "coating": "",
                "split_ratio": 0.5,
                "loss": 0.0,
                "phase_deg": 0.0,
            }
        )
    return normalize_optical_solid_face_metadata(
        {"source_stl": str(path), "faces": records},
        source_stl=str(path),
    )


def _multi_stl_rows() -> list[SurfaceRow]:
    temp_dir = Path(tempfile.gettempdir())
    first_stl = temp_dir / "kraken_multi_stl_trace_first.stl"
    second_stl = temp_dir / "kraken_multi_stl_trace_second.stl"
    first_metadata = _box_metadata(first_stl)
    second_metadata = _box_metadata(second_stl)
    return [
        SurfaceRow(surface="Object", name="Source reference", thickness=20.0, diameter=12.0, drawing=0.0),
        SurfaceRow(
            surface="Solid 3D STL",
            name="First file-backed STL solid",
            thickness=20.0,
            diameter=12.0,
            glass="BK7",
            axis_move=2.0,
            advanced={
                "Solid_3d_stl": str(first_stl),
                OPTICAL_SOLID_FACES_ADVANCED_ATTR: first_metadata,
            },
        ),
        SurfaceRow(
            surface="Solid 3D STL",
            name="Second file-backed STL solid",
            thickness=20.0,
            diameter=12.0,
            glass="F2",
            axis_move=2.0,
            advanced={
                "Solid_3d_stl": str(second_stl),
                OPTICAL_SOLID_FACES_ADVANCED_ATTR: second_metadata,
            },
        ),
        SurfaceRow(surface="Image", name="Detector plane", thickness=0.0, diameter=20.0, glass="AIR", drawing=1.0),
    ]


def _trace_fixture(rows: list[SurfaceRow]):
    system = _build_system_from_specs([asdict(row) for row in rows])
    rays = Kos.raykeeper(system)
    system.energy_probability = 0
    launch_points = (
        (0.0, 0.0, 0.0),
        (-0.45, 0.25, 0.0),
        (0.50, -0.30, 0.0),
    )
    for point in launch_points:
        system.NsTrace([float(point[0]), float(point[1]), float(point[2])], [0.0, 0.0, 1.0], 0.55)
        rays.push()
    return system, rays


def _ray_event_records(rays) -> list[list[dict[str, object]]]:
    event_sets = list(getattr(rays, "TRACE_EVENTS", []) or [])
    return [[trace_event_to_record(event) for event in event_set] for event_set in event_sets]


def _surface_sequence(records: list[dict[str, object]]) -> list[int]:
    sequence: list[int] = []
    for record in records:
        if str(record.get("event_kind", "") or "") != "surface":
            continue
        try:
            sequence.append(int(record.get("surface_id")))
        except Exception:
            continue
    return sequence


def _records_for_surface(records: list[dict[str, object]], surface_id: int) -> list[dict[str, object]]:
    return [
        record
        for record in records
        if str(record.get("event_kind", "") or "") == "surface"
        and int(record.get("surface_id", -1)) == int(surface_id)
    ]


def _event_z_values(records: list[dict[str, object]], surface_id: int) -> list[float]:
    values: list[float] = []
    for record in _records_for_surface(records, surface_id):
        try:
            point = np.asarray(record.get("point_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
        except Exception:
            continue
        if point.size >= 3 and np.isfinite(point[2]):
            values.append(float(point[2]))
    return values


def _close(actual: object, expected: object, *, atol: float = 1e-7) -> bool:
    try:
        return bool(np.allclose(np.asarray(actual, dtype=float), np.asarray(expected, dtype=float), atol=atol))
    except Exception:
        return False


def validate_optical_solid_multi_stl_trace() -> list[OpticalSolidMultiStlTraceCheck]:
    rows = _multi_stl_rows()
    system, rays = _trace_fixture(rows)
    event_sets = _ray_event_records(rays)
    sequences = [_surface_sequence(records) for records in event_sets]
    solid_records = [
        [record for record in records if int(record.get("surface_id", -1)) in {1, 2}]
        for records in event_sets
    ]
    first_ray_solid_records = solid_records[0] if solid_records else []
    volume_index = getattr(system, "_scene_optical_volumes_by_surface", {}) or {}
    boundary_index = getattr(system, "_scene_boundary_faces_by_surface", {}) or {}
    rebuilt_boundary_index = build_scene_boundary_face_index(rows, system=system)
    bundle = build_scene_bundle(rows=rows, system=system, rays=rays)
    bundle_volumes = list(getattr(bundle, "extra", {}).get("optical_volume_records", []) or [])
    bundle_boundaries = list(getattr(bundle, "extra", {}).get("boundary_face_records", []) or [])
    overrides = getattr(system, "_optical_solid_output_port_pose_overrides", {}) or {}
    downstream_override = overrides.get(2, {}) if isinstance(overrides, dict) else {}
    row_two_volume = volume_index.get(2, {}) if isinstance(volume_index, dict) else {}
    row_two_centroid = row_two_volume.get("centroid_world", (np.nan, np.nan, np.nan))
    row_two_bounds_min = np.asarray(row_two_volume.get("bounds_min_world", (np.nan, np.nan, np.nan)), dtype=float)
    row_two_bounds_max = np.asarray(row_two_volume.get("bounds_max_world", (np.nan, np.nan, np.nan)), dtype=float)
    first_ray_row_two_z = _event_z_values(event_sets[0], 2) if event_sets else []
    bundle_surface_sequences = [
        [int(value) for value in np.asarray(getattr(path, "surface_ids", ()), dtype=int).reshape(-1)]
        for path in list(getattr(bundle, "ray_paths", []) or [])
    ]
    bundle_path_reaches_image = [bool(getattr(path, "reaches_image", False)) for path in list(getattr(bundle, "ray_paths", []) or [])]
    bundle_event_surface_sequences = [
        [
            int(getattr(event, "surface_id"))
            for event in list(getattr(path, "events", []) or [])
            if str(getattr(event, "event_kind", "") or "") == "surface"
            and getattr(event, "surface_id", None) is not None
        ]
        for path in list(getattr(bundle, "ray_paths", []) or [])
    ]
    boundary_rows = sorted({int(record.get("row_index", -1)) for record in bundle_boundaries})
    volume_rows = sorted({int(record.get("row_index", -1)) for record in bundle_volumes})
    volume_materials = {
        int(record.get("row_index", -1)): str(record.get("material", "") or "")
        for record in bundle_volumes
    }
    volume_ids = {
        int(record.get("row_index", -1)): str(record.get("volume_id", "") or "")
        for record in bundle_volumes
    }
    return [
        OpticalSolidMultiStlTraceCheck(
            "every launch traces through both STL solids and then the Image row",
            sequences == [[1, 1, 2, 2, 3], [1, 1, 2, 2, 3], [1, 1, 2, 2, 3]],
            f"surface_sequences={sequences}",
        ),
        OpticalSolidMultiStlTraceCheck(
            "closed-volume media state resets between file-backed STL solids",
            [
                (
                    str(record.get("surface_id", "")),
                    str(record.get("media_transition", "")),
                    str(record.get("volume_id", "")),
                    str(record.get("inside_volumes_before", "")),
                    str(record.get("inside_volumes_after", "")),
                )
                for record in first_ray_solid_records
            ]
            == [
                ("1", "entry", "volume:1", "", "volume:1"),
                ("1", "exit", "volume:1", "volume:1", ""),
                ("2", "entry", "volume:2", "", "volume:2"),
                ("2", "exit", "volume:2", "volume:2", ""),
            ],
            "solid_media="
            + str(
                [
                    (
                        record.get("surface_id"),
                        record.get("media_transition"),
                        record.get("volume_id"),
                        record.get("inside_volumes_before"),
                        record.get("inside_volumes_after"),
                    )
                    for record in first_ray_solid_records
                ]
            ),
        ),
        OpticalSolidMultiStlTraceCheck(
            "duplicated STL face ids remain row-scoped and triangle-backed",
            [
                (
                    int(record.get("surface_id", -1)),
                    str(record.get("mesh_face_id", "")),
                    str(record.get("mesh_face_match_method", "")),
                    str(record.get("mesh_face_match_warning", "")),
                )
                for record in first_ray_solid_records
            ]
            == [
                (1, "IN", "triangle_membership", ""),
                (1, "OUT", "triangle_membership", ""),
                (2, "IN", "triangle_membership", ""),
                (2, "OUT", "triangle_membership", ""),
            ],
            "mesh_faces="
            + str(
                [
                    (
                        record.get("surface_id"),
                        record.get("mesh_face_id"),
                        record.get("mesh_face_match_method"),
                        record.get("mesh_face_match_warning"),
                    )
                    for record in first_ray_solid_records
                ]
            ),
        ),
        OpticalSolidMultiStlTraceCheck(
            "runtime scene volume bounds follow chained STL output-port placement",
            len(first_ray_row_two_z) == 2
            and np.isfinite(row_two_bounds_min[2])
            and np.isfinite(row_two_bounds_max[2])
            and _close([row_two_bounds_min[2], row_two_bounds_max[2]], [min(first_ray_row_two_z), max(first_ray_row_two_z)])
            and _close(row_two_centroid, downstream_override.get("center", (np.nan, np.nan, np.nan))),
            (
                f"row2_trace_z={first_ray_row_two_z}, row2_bounds_z="
                f"{[float(row_two_bounds_min[2]), float(row_two_bounds_max[2])]}, "
                f"row2_centroid={row_two_centroid}, override_center={downstream_override.get('center')}"
            ),
        ),
        OpticalSolidMultiStlTraceCheck(
            "scene bundle exports separate boundary and volume records for both STL rows",
            boundary_rows == [1, 2]
            and volume_rows == [1, 2]
            and volume_materials == {1: "BK7", 2: "F2"}
            and volume_ids == {1: "volume:1", 2: "volume:2"}
            and len(boundary_index.get(1, [])) == 6
            and len(boundary_index.get(2, [])) == 6
            and rebuilt_boundary_index == boundary_index,
            (
                f"boundary_rows={boundary_rows}, volume_rows={volume_rows}, "
                f"materials={volume_materials}, volume_ids={volume_ids}, "
                f"boundary_counts={{1: {len(boundary_index.get(1, []))}, 2: {len(boundary_index.get(2, []))}}}"
            ),
        ),
        OpticalSolidMultiStlTraceCheck(
            "canonical scene paths keep the same 3D trace and Image reach",
            bundle_surface_sequences == sequences
            and bundle_event_surface_sequences == sequences
            and bundle_path_reaches_image == [True, True, True],
            (
                f"path_sequences={bundle_surface_sequences}, "
                f"event_sequences={bundle_event_surface_sequences}, reaches_image={bundle_path_reaches_image}"
            ),
        ),
    ]


def _print_table(checks: list[OpticalSolidMultiStlTraceCheck]) -> None:
    print("KrakenOS multi-STL optical-solid trace validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate chained tracing through multiple file-backed optical STL solids.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_optical_solid_multi_stl_trace()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
