"""Validate the PYRITE 85 mm machine-vision blackbox surrogate."""

from __future__ import annotations

import importlib
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_library import discover_layouts, load_python_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_PATH = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts" / "machine_vision_85mm_pyrite_datasheet_1x.py"
DOC_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "machine_vision_pyrite_85_surrogate.rst"
INDEX_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "index.rst"
STATIC_IMAGE = (
    PROJECT_ROOT
    / "docs"
    / "source"
    / "_static"
    / "tutorials"
    / "machine_vision_pyrite_85_surrogate"
    / "01_pyrite_85_surrogate_layout.png"
)


def _translation(distance: float) -> np.ndarray:
    return np.asarray([[1.0, distance], [0.0, 1.0]], dtype=float)


def _thin_lens(focal_length: float) -> np.ndarray:
    return np.asarray([[1.0, 0.0], [-1.0 / focal_length, 1.0]], dtype=float)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    module = importlib.import_module("KrakenOS.common_optical_layouts.machine_vision_85mm_pyrite_datasheet_1x")
    info = load_python_data(LAYOUT_PATH)
    layouts = discover_layouts(PROJECT_ROOT / "KrakenOS" / "common_optical_layouts")

    group_1_z = float(module.GROUP_1_Z)
    group_2_z = float(module.GROUP_2_Z)
    span = float(module.FRONT_VERTEX_TO_REAR_VERTEX)
    matrix = (
        _translation(span - group_2_z)
        @ _thin_lens(float(module.GROUP_2_FOCAL_LENGTH))
        @ _translation(group_2_z - group_1_z)
        @ _thin_lens(float(module.GROUP_1_FOCAL_LENGTH))
        @ _translation(group_1_z)
    )
    a, _b, c, d = matrix.ravel()
    effective_focal_length = -1.0 / c
    front_focal_distance = d / c
    back_focal_distance = -a / c
    h1 = front_focal_distance + effective_focal_length
    h2 = span + back_focal_distance - effective_focal_length

    doc = DOC_PATH.read_text(encoding="utf-8")
    index = INDEX_PATH.read_text(encoding="utf-8")
    checks = [
        ("layout file exists", LAYOUT_PATH.exists()),
        ("layout has seven rows", len(info["surfaces"]) == 7),
        ("layout is in Machine Vision menu", module.TITLE in layouts.machine_vision_files),
        ("docs page exists", DOC_PATH.exists() and "PYRITE 4.5/85/0.5x-2.0x V38" in doc),
        ("docs page is indexed", "machine_vision_pyrite_85_surrogate" in index),
        ("layout screenshot exists", STATIC_IMAGE.exists() and STATIC_IMAGE.stat().st_size > 2048),
        ("effective focal length matches", abs(effective_focal_length - float(module.EFFECTIVE_FOCAL_LENGTH)) < 1e-6),
        ("front focal distance matches", abs(front_focal_distance - float(module.FRONT_FOCAL_DISTANCE)) < 1e-6),
        ("back focal distance matches", abs(back_focal_distance - float(module.BACK_FOCAL_DISTANCE)) < 1e-6),
        ("front principal plane matches", abs(h1 - float(module.FRONT_PRINCIPAL_PLANE_Z)) < 1e-6),
        ("rear principal plane matches", abs(h2 - float(module.REAR_PRINCIPAL_PLANE_Z)) < 1e-6),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        print("PYRITE 85 mm surrogate validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print(
        "PYRITE 85 mm surrogate validation passed: "
        f"EFL={effective_focal_length:.6f} mm, "
        f"SF={front_focal_distance:.6f} mm, "
        f"S'F'={back_focal_distance:.6f} mm, "
        f"H1={h1:.6f} mm, H2={h2:.6f} mm."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
