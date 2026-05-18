"""Validate output-port placement across chained CAD/STL optical solids."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

from KrakenOS.UI.layout_editor import SurfaceRow, _build_system_from_specs
from KrakenOS.UI.nonseq_output_ports import build_optical_solid_output_port_pose_overrides
from KrakenOS.UI.optical_solid_metadata import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    normalize_optical_solid_face_metadata,
    optical_solid_face_suggestion_label,
    suggest_optical_solid_face_roles,
)
from KrakenOS.UI.scene_builder import build_scene_bundle


@dataclass
class OpticalSolidChainedPortCheck:
    check: str
    ok: bool
    detail: str


def _face(
    face_id: str,
    *,
    side: str,
    function: str,
    normal: tuple[float, float, float],
    centroid: tuple[float, float, float],
    area: float = 100.0,
    triangle_start: int = 0,
) -> dict[str, object]:
    return {
        "face_id": face_id,
        "role": "Output" if function == OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT else "Unassigned",
        "function": function,
        "side_2d": side,
        "normal": list(normal),
        "centroid": list(centroid),
        "area_mm2": float(area),
        "triangle_count": 2,
        "triangle_indices": [int(triangle_start), int(triangle_start) + 1],
        "plane_offset_mm": 0.0,
        "flip_normal": False,
        "material": "",
        "coating": "",
        "split_ratio": 0.5,
        "loss": 0.0,
        "phase_deg": 0.0,
        "clear_aperture_mm": 0.0,
        "notes": "",
    }


def _synthetic_port_metadata(
    *,
    output_side: str,
    output_normal: tuple[float, float, float],
    output_centroid: tuple[float, float, float],
) -> dict[str, object]:
    metadata = normalize_optical_solid_face_metadata(
        {
            "faces": [
                _face(
                    "IN",
                    side="Left",
                    function=OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
                    normal=(0.0, 0.0, -1.0),
                    centroid=(0.0, 0.0, 0.0),
                    triangle_start=0,
                ),
                _face(
                    "OUT",
                    side=output_side,
                    function=OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
                    normal=output_normal,
                    centroid=output_centroid,
                    triangle_start=2,
                ),
                _face(
                    "UP",
                    side="Up",
                    function="Unassigned",
                    normal=(0.0, 1.0, 0.0),
                    centroid=(0.0, 5.0, 0.0),
                    area=10.0,
                    triangle_start=4,
                ),
            ]
        }
    )
    metadata["faces"] = suggest_optical_solid_face_roles(list(metadata.get("faces", []) or []))
    return normalize_optical_solid_face_metadata(metadata)


def _close(actual, expected, *, atol: float = 1e-9) -> bool:
    return bool(np.allclose(np.asarray(actual, dtype=float), np.asarray(expected, dtype=float), atol=atol))


def _runtime_spec(row: dict[str, object]) -> dict[str, object]:
    spec = dict(row)
    spec.setdefault("rc", 0.0)
    spec.setdefault("k", 0.0)
    spec.setdefault("axicon", 0.0)
    spec.setdefault("diff_ord", 0.0)
    spec.setdefault("grating_d", 0.0)
    spec.setdefault("grating_angle", 0.0)
    spec.setdefault("in_diameter", 0.0)
    spec.setdefault("drawing", 1.0)
    spec.setdefault("extra_data", 0.0)
    spec.setdefault("uda", "None")
    spec.setdefault("tilt_x", 0.0)
    spec.setdefault("tilt_y", 0.0)
    spec.setdefault("tilt_z", 0.0)
    spec.setdefault("desp_x", 0.0)
    spec.setdefault("desp_y", 0.0)
    spec.setdefault("desp_z", 0.0)
    spec.setdefault("axis_move", 0.0)
    spec.setdefault("glass", "AIR")
    return spec


def _surface_row_from_spec(row: dict[str, object], label: int) -> SurfaceRow:
    spec = _runtime_spec(row)
    return SurfaceRow(
        label=str(int(label)),
        surface=str(spec.get("surface", "Standard") or "Standard"),
        name=str(spec.get("name", "Surface") or "Surface"),
        rc=float(spec.get("rc", 0.0) or 0.0),
        k=float(spec.get("k", 0.0) or 0.0),
        axicon=float(spec.get("axicon", 0.0) or 0.0),
        diff_ord=float(spec.get("diff_ord", 0.0) or 0.0),
        grating_d=float(spec.get("grating_d", 0.0) or 0.0),
        grating_angle=float(spec.get("grating_angle", 0.0) or 0.0),
        thickness=float(spec.get("thickness", 0.0) or 0.0),
        diameter=float(spec.get("diameter", 25.0) or 25.0),
        in_diameter=float(spec.get("in_diameter", 0.0) or 0.0),
        drawing=float(spec.get("drawing", 1.0) or 1.0),
        extra_data=spec.get("extra_data", 0.0),
        uda=spec.get("uda", "None"),
        advanced=dict(spec.get("advanced", {}) or {}),
        tilt_x=float(spec.get("tilt_x", 0.0) or 0.0),
        tilt_y=float(spec.get("tilt_y", 0.0) or 0.0),
        tilt_z=float(spec.get("tilt_z", 0.0) or 0.0),
        desp_x=float(spec.get("desp_x", 0.0) or 0.0),
        desp_y=float(spec.get("desp_y", 0.0) or 0.0),
        desp_z=float(spec.get("desp_z", 0.0) or 0.0),
        axis_move=float(spec.get("axis_move", 0.0) or 0.0),
        glass=str(spec.get("glass", "AIR") or "AIR"),
    )


def _surface_rows_from_specs(rows: list[dict[str, object]]) -> list[SurfaceRow]:
    return [_surface_row_from_spec(row, index) for index, row in enumerate(rows)]


def validate_optical_solid_chained_ports() -> list[OpticalSolidChainedPortCheck]:
    first_metadata = _synthetic_port_metadata(
        output_side="Down",
        output_normal=(0.0, -1.0, 0.0),
        output_centroid=(0.0, 0.0, 12.0),
    )
    second_metadata = _synthetic_port_metadata(
        output_side="Right",
        output_normal=(1.0, 0.0, 0.0),
        output_centroid=(5.0, 0.0, 5.0),
    )
    rows = [
        {"surface": "Object", "name": "Object", "thickness": 100.0, "diameter": 20.0, "advanced": {}},
        {
            "surface": "Standard",
            "name": "Synthetic fold prism",
            "glass": "BK7",
            "thickness": 20.0,
            "diameter": 20.0,
            "advanced": {OPTICAL_SOLID_FACES_ADVANCED_ATTR: first_metadata, "Solid_3d_stl": "synthetic_first.stl"},
        },
        {"surface": "Standard", "name": "Follower lens", "thickness": 30.0, "diameter": 20.0, "advanced": {}},
        {
            "surface": "Standard",
            "name": "Synthetic chained prism",
            "glass": "F2",
            "thickness": 15.0,
            "diameter": 20.0,
            "advanced": {OPTICAL_SOLID_FACES_ADVANCED_ATTR: second_metadata, "Solid_3d_stl": "synthetic_second.stl"},
        },
        {"surface": "Image", "name": "Image", "thickness": 0.0, "diameter": 20.0, "advanced": {}},
    ]
    overrides = build_optical_solid_output_port_pose_overrides(rows)
    system = _build_system_from_specs([_runtime_spec(row) for row in rows])
    keys = sorted(int(key) for key in overrides)
    follower_pose = overrides.get(2, {})
    chained_pose = overrides.get(3, {})
    image_pose = overrides.get(4, {})
    runtime_boundary_index = getattr(system, "_scene_boundary_faces_by_surface", {}) or {}
    runtime_volume_index = getattr(system, "_scene_optical_volumes_by_surface", {}) or {}
    surface_rows = _surface_rows_from_specs(rows)
    bundle = build_scene_bundle(rows=surface_rows, system=system, rays=None)
    boundary_records = list(getattr(bundle, "extra", {}).get("boundary_face_records", []) or [])
    volume_records = list(getattr(bundle, "extra", {}).get("optical_volume_records", []) or [])
    boundary_rows = sorted({int(record.get("row_index", -1)) for record in boundary_records})
    volume_rows = sorted({int(record.get("row_index", -1)) for record in volume_records})
    row_boundary_ids = {
        row_index: [
            str(record.get("face_id", "") or "")
            for record in list(runtime_boundary_index.get(row_index, []) or [])
        ]
        for row_index in (1, 3)
    }
    row_boundary_object_ids = {
        row_index: sorted(
            {
                str(record.get("object_id", "") or "")
                for record in list(runtime_boundary_index.get(row_index, []) or [])
            }
        )
        for row_index in (1, 3)
    }
    row_suggestion_labels = {
        row_index: [
            optical_solid_face_suggestion_label(record)
            for record in list(runtime_boundary_index.get(row_index, []) or [])
        ]
        for row_index in (1, 3)
    }
    volume_summary = {
        row_index: {
            "volume_id": str((runtime_volume_index.get(row_index, {}) or {}).get("volume_id", "") or ""),
            "material": str((runtime_volume_index.get(row_index, {}) or {}).get("material", "") or ""),
            "faces": list((runtime_volume_index.get(row_index, {}) or {}).get("boundary_face_ids", []) or []),
            "diagnostics": list((runtime_volume_index.get(row_index, {}) or {}).get("diagnostics", []) or []),
        }
        for row_index in (1, 3)
    }
    return [
        OpticalSolidChainedPortCheck(
            "output-port placer includes ordinary and CAD/STL followers",
            keys == [2, 3, 4],
            f"override_keys={keys}",
        ),
        OpticalSolidChainedPortCheck(
            "ordinary follower is anchored to the first optical-solid output port",
            _close(follower_pose.get("center", (np.nan, np.nan, np.nan)), (0.0, -20.0, 112.0))
            and _close(follower_pose.get("normal", (np.nan, np.nan, np.nan)), (0.0, -1.0, 0.0)),
            (
                f"center={np.asarray(follower_pose.get('center', (np.nan, np.nan, np.nan))).tolist()}, "
                f"normal={np.asarray(follower_pose.get('normal', (np.nan, np.nan, np.nan))).tolist()}"
            ),
        ),
        OpticalSolidChainedPortCheck(
            "downstream optical solid is left-face aligned to the active optical path",
            _close(chained_pose.get("center", (np.nan, np.nan, np.nan)), (0.0, -50.0, 112.0))
            and _close(chained_pose.get("normal", (np.nan, np.nan, np.nan)), (0.0, -1.0, 0.0)),
            (
                f"center={np.asarray(chained_pose.get('center', (np.nan, np.nan, np.nan))).tolist()}, "
                f"normal={np.asarray(chained_pose.get('normal', (np.nan, np.nan, np.nan))).tolist()}"
            ),
        ),
        OpticalSolidChainedPortCheck(
            "image plane is anchored to the second optical-solid output port",
            int(image_pose.get("source_index", -1)) == 3
            and _close(image_pose.get("center", (np.nan, np.nan, np.nan)), (20.0, -55.0, 112.0))
            and _close(image_pose.get("normal", (np.nan, np.nan, np.nan)), (1.0, 0.0, 0.0)),
            (
                f"source={image_pose.get('source_index')}, "
                f"center={np.asarray(image_pose.get('center', (np.nan, np.nan, np.nan))).tolist()}, "
                f"normal={np.asarray(image_pose.get('normal', (np.nan, np.nan, np.nan))).tolist()}"
            ),
        ),
        OpticalSolidChainedPortCheck(
            "runtime build preserves the authored image diameter in chained non-sequential layouts",
            abs(float(system.SDT[4].Diameter) - 20.0) < 1e-9,
            f"runtime_image_diameter={float(system.SDT[4].Diameter):.6g}",
        ),
        OpticalSolidChainedPortCheck(
            "runtime scene boundary index keeps cascaded optical-solid faces row-scoped",
            set(row_boundary_ids) == {1, 3}
            and row_boundary_ids[1] == ["IN", "OUT", "UP"]
            and row_boundary_ids[3] == ["IN", "OUT", "UP"]
            and row_boundary_object_ids[1] == ["surface:1"]
            and row_boundary_object_ids[3] == ["surface:3"],
            f"face_ids={row_boundary_ids}, object_ids={row_boundary_object_ids}",
        ),
        OpticalSolidChainedPortCheck(
            "runtime scene volume index keeps cascaded optical solids independent",
            volume_summary[1]["volume_id"] == "volume:1"
            and volume_summary[3]["volume_id"] == "volume:3"
            and volume_summary[1]["material"] == "BK7"
            and volume_summary[3]["material"] == "F2"
            and volume_summary[1]["faces"] == ["IN", "OUT", "UP"]
            and volume_summary[3]["faces"] == ["IN", "OUT", "UP"]
            and not volume_summary[1]["diagnostics"]
            and not volume_summary[3]["diagnostics"],
            f"volumes={volume_summary}",
        ),
        OpticalSolidChainedPortCheck(
            "scene bundle exports separate boundary and volume records for cascaded solids",
            boundary_rows == [1, 3]
            and volume_rows == [1, 3]
            and len(boundary_records) == 6
            and len(volume_records) == 2,
            (
                f"boundary_rows={boundary_rows}, volume_rows={volume_rows}, "
                f"boundary_count={len(boundary_records)}, volume_count={len(volume_records)}"
            ),
        ),
        OpticalSolidChainedPortCheck(
            "face-intent suggestions remain metadata on each cascaded optical solid",
            all(row_suggestion_labels[row_index] for row_index in (1, 3))
            and any("Input" in label for label in row_suggestion_labels[1])
            and any("Output" in label for label in row_suggestion_labels[3]),
            f"suggestions={row_suggestion_labels}",
        ),
    ]


def _print_table(checks: list[OpticalSolidChainedPortCheck]) -> None:
    print("KrakenOS optical-solid chained-port validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_optical_solid_chained_ports()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
