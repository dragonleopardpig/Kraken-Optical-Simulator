"""Validate output-port placement across chained CAD/STL optical solids."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

from KrakenOS.UI.nonseq_output_ports import build_optical_solid_output_port_pose_overrides
from KrakenOS.UI.optical_solid_metadata import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    normalize_optical_solid_face_metadata,
)


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
    return normalize_optical_solid_face_metadata(
        {
            "faces": [
                _face(
                    "IN",
                    side="Left",
                    function=OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
                    normal=(0.0, 0.0, -1.0),
                    centroid=(0.0, 0.0, 0.0),
                ),
                _face(
                    "OUT",
                    side=output_side,
                    function=OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
                    normal=output_normal,
                    centroid=output_centroid,
                ),
                _face(
                    "UP",
                    side="Up",
                    function="Unassigned",
                    normal=(0.0, 1.0, 0.0),
                    centroid=(0.0, 5.0, 0.0),
                    area=10.0,
                ),
            ]
        }
    )


def _close(actual, expected, *, atol: float = 1e-9) -> bool:
    return bool(np.allclose(np.asarray(actual, dtype=float), np.asarray(expected, dtype=float), atol=atol))


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
            "thickness": 20.0,
            "diameter": 20.0,
            "advanced": {OPTICAL_SOLID_FACES_ADVANCED_ATTR: first_metadata, "Solid_3d_stl": "synthetic_first.stl"},
        },
        {"surface": "Standard", "name": "Follower lens", "thickness": 30.0, "diameter": 20.0, "advanced": {}},
        {
            "surface": "Standard",
            "name": "Synthetic chained prism",
            "thickness": 15.0,
            "diameter": 20.0,
            "advanced": {OPTICAL_SOLID_FACES_ADVANCED_ATTR: second_metadata, "Solid_3d_stl": "synthetic_second.stl"},
        },
        {"surface": "Image", "name": "Image", "thickness": 0.0, "diameter": 20.0, "advanced": {}},
    ]
    overrides = build_optical_solid_output_port_pose_overrides(rows)
    keys = sorted(int(key) for key in overrides)
    follower_pose = overrides.get(2, {})
    chained_pose = overrides.get(3, {})
    image_pose = overrides.get(4, {})
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
