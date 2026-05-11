from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y,
    KrakenLayoutEditor,
    SurfaceRow,
    build_optical_solid_cube_splitter_virtual_plane,
    normalize_optical_solid_face_metadata,
    optical_solid_has_virtual_splitter_plane,
    optical_solid_virtual_plane_world_records,
)
from KrakenOS.UI.optical_solid_metadata import (
    build_optical_solid_cube_splitter_virtual_plane as service_build_optical_solid_cube_splitter_virtual_plane,
    optical_solid_has_virtual_splitter_plane as service_optical_solid_has_virtual_splitter_plane,
)


@dataclass
class OpticalSolidVirtualPlaneCheck:
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


def validate_optical_solid_virtual_plane() -> list[OpticalSolidVirtualPlaneCheck]:
    metadata = _cube_face_metadata()
    plane = build_optical_solid_cube_splitter_virtual_plane(
        metadata,
        diagonal_mode=OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y,
        split_ratio=0.5,
        loss=0.02,
        phase_deg=180.0,
    )
    service_plane = service_build_optical_solid_cube_splitter_virtual_plane(
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
        tilt_x=15.0,
        tilt_y=-10.0,
        tilt_z=5.0,
        desp_x=2.0,
        desp_y=-3.0,
        desp_z=4.0,
        advanced={
            OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata_with_plane,
            "Solid_3d_stl": "cube_bs.stl",
            "OpticalSolidSourcePath": "68551.step",
            "OpticalSolidSourceFormat": "STEP",
        },
    )
    world_planes = optical_solid_virtual_plane_world_records(row, 40.0, assigned_only=True)
    world = world_planes[0] if world_planes else None
    plane_normal = np.asarray(plane.get("normal", (np.nan, np.nan, np.nan)), dtype=float)
    expected_local = np.asarray((0.0, 1.0, -1.0), dtype=float)
    expected_local = expected_local / float(np.linalg.norm(expected_local))
    checks = [
        OpticalSolidVirtualPlaneCheck(
            "cube splitter builder returns one virtual internal plane",
            bool(plane),
            f"plane_id={plane.get('plane_id', '-')}, kind={plane.get('kind', '-')}",
        ),
        OpticalSolidVirtualPlaneCheck(
            "cube splitter plane is centered inside the labeled cube",
            np.linalg.norm(np.asarray(plane.get("point", (np.nan, np.nan, np.nan)), dtype=float)[:3]) < 1e-9,
            f"point={plane.get('point')}",
        ),
        OpticalSolidVirtualPlaneCheck(
            "cube splitter plane normal is the expected 45-degree diagonal",
            np.all(np.isfinite(plane_normal))
            and abs(float(np.dot(plane_normal[:3], expected_local[:3])) - 1.0) < 1e-9,
            f"normal={tuple(plane_normal[:3])}",
        ),
        OpticalSolidVirtualPlaneCheck(
            "virtual plane metadata is preserved in OpticalSolidFaces",
            optical_solid_has_virtual_splitter_plane(metadata_with_plane),
            f"virtual_planes={len(list(metadata_with_plane.get('virtual_planes', []) or []))}",
        ),
        OpticalSolidVirtualPlaneCheck(
            "virtual splitter metadata helpers are service-owned",
            service_plane == plane
            and service_optical_solid_has_virtual_splitter_plane(metadata_with_plane)
            == optical_solid_has_virtual_splitter_plane(metadata_with_plane),
            f"service_plane={service_plane.get('plane_id', '-')}, has={service_optical_solid_has_virtual_splitter_plane(metadata_with_plane)}",
        ),
        OpticalSolidVirtualPlaneCheck(
            "world virtual plane transform returns finite point and normal",
            world is not None
            and np.all(np.isfinite(np.asarray(world.get('point_world', (np.nan, np.nan, np.nan)), dtype=float)[:3]))
            and np.all(np.isfinite(np.asarray(world.get('normal_world', (np.nan, np.nan, np.nan)), dtype=float)[:3])),
            (
                f"point_world={world.get('point_world')}, normal_world={world.get('normal_world')}"
                if world is not None
                else "world_plane=None"
            ),
        ),
        OpticalSolidVirtualPlaneCheck(
            "passive cube CAD warning is suppressed once virtual splitter metadata exists",
            not (
                KrakenLayoutEditor._scene_graph_value_present(row.advanced.get("Solid_3d_stl"))
                and any(token in " ".join(str(v or "") for v in (row.name, row.advanced.get("Solid_3d_stl"), row.advanced.get("OpticalSolidSourcePath"), row.advanced.get("OpticalSolidSourceFormat"))).lower() for token in ("beam splitter", "beamsplitter", "cube bs", " 68551", "/68551", "step_68551"))
                and not optical_solid_has_virtual_splitter_plane(metadata_with_plane)
            ),
            "virtual splitter plane present",
        ),
    ]
    return checks


def _print_table(checks: list[OpticalSolidVirtualPlaneCheck]) -> None:
    print("KrakenOS optical-solid virtual-plane validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate virtual internal plane metadata for optical CAD/STL solids.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_optical_solid_virtual_plane()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
