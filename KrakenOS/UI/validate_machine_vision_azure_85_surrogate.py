"""Validate the AZURE ELS-85/4.5V16K machine-vision blackbox surrogate.

Mirrors validate_machine_vision_pyrite_85_surrogate: the paraxial ABCD matrix built
from the two Thin-Lens groups must reproduce the stored Gaussian cardinals, the seven
rows must inherit the 150 mm-measured operational defaults, and the bundled vendor STEP
glass vertices (extracted with OpenCascade) must land on the optical vertex datums.

The screenshot/tutorial hard-check the PYRITE guard carries is intentionally dropped:
a faithful layout render needs a real GL display, so it is an in-app eyeball artifact,
not a headless correctness gate.  The docs page itself is still required.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_library import discover_layouts, load_python_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_PATH = (
    PROJECT_ROOT
    / "KrakenOS"
    / "common_optical_layouts"
    / "machine_vision_85mm_azure_datasheet_05x_20x.py"
)
REFERENCE_LAYOUT_PATH = (
    PROJECT_ROOT / "KrakenOS" / "common_optical_layouts" / "machine_vision_150mm_measured.py"
)
DOC_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "machine_vision_azure_85_surrogate.rst"
INDEX_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "index.rst"


def _extract_step_glass_fits(step_path: Path):
    from KrakenOS.UI.services.step_analytic_geometry import load_step_analytic_document
    from KrakenOS.UI.services.step_native_reconstruction import (
        _basis_from_axis,
        _candidate_faces,
        _document_axis,
        _fit_group,
        _group_candidates,
    )

    document = load_step_analytic_document(step_path)
    axis, axis_origin, aperture_diameter, _diagnostics = _document_axis(document)
    basis_x, basis_y = _basis_from_axis(axis)
    candidates, _candidate_diagnostics = _candidate_faces(document, axis, axis_origin, basis_x, basis_y)
    fits = []
    for group in _group_candidates(candidates, aperture_diameter):
        fit = _fit_group(
            group,
            axis_origin=axis_origin,
            axis=axis,
            aperture_diameter_mm=aperture_diameter,
            term_count=8,
        )
        if (
            fit.supported
            and fit.native_kind == "sphere_exact"
            and fit.diameter_mm < 30.0
            and fit.rms_error_mm < 0.2
        ):
            fits.append(fit)
    return sorted(fits, key=lambda item: float(item.vertex_z_mm))


def _translation(distance: float) -> np.ndarray:
    return np.asarray([[1.0, distance], [0.0, 1.0]], dtype=float)


def _thin_lens(focal_length: float) -> np.ndarray:
    return np.asarray([[1.0, 0.0], [-1.0 / focal_length, 1.0]], dtype=float)


def run_checks():
    """Return (passed, failures) without printing — usable as a penta phase."""
    module = importlib.import_module(
        "KrakenOS.common_optical_layouts.machine_vision_85mm_azure_datasheet_05x_20x"
    )
    info = load_python_data(LAYOUT_PATH)
    reference_info = load_python_data(REFERENCE_LAYOUT_PATH)
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

    doc = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else ""
    index = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.exists() else ""
    settings = dict(getattr(module, "SETTINGS", {}))
    reference_settings = dict(reference_info.get("settings", {}))
    override_keys = {
        "aperture_value",
        "field_value",
        "lens_step_path",
        "lens_step_largest_component_only",
        "lens_step_rotation_x_deg",
        "lens_step_rotation_y_deg",
        "lens_step_rotation_z_deg",
        "lens_step_axis_offset_xy",
        "lens_step_placement_offset_xyz",
        "optical_step_path",
        "optical_step_placement_offset_xyz",
    }
    inherited_mismatches = [
        key
        for key, value in reference_settings.items()
        if key not in override_keys and settings.get(key) != value
    ]
    step_path = PROJECT_ROOT / str(module.STEP_PATH)
    glass_fits = _extract_step_glass_fits(step_path)
    rear_fit = glass_fits[0] if glass_fits else None
    front_fit = glass_fits[-1] if glass_fits else None
    step_offset = settings.get("lens_step_placement_offset_xyz", [None, None, None])
    checks = [
        ("layout file exists", LAYOUT_PATH.exists()),
        ("layout has seven rows", len(info["surfaces"]) == 7),
        ("layout is in Machine Vision menu", module.TITLE in layouts.machine_vision_files),
        ("inherits 150 mm measured operational defaults", inherited_mismatches == []),
        (
            "inherits 150 mm measured camera",
            settings.get("camera_model") == reference_settings.get("camera_model")
            and settings.get("camera_step_path") == reference_settings.get("camera_step_path")
            and settings.get("camera_step_rotation_z_deg") == reference_settings.get("camera_step_rotation_z_deg"),
        ),
        ("does not preload auxiliary optical STEP overlay", settings.get("optical_step_path") == ""),
        ("docs page exists", DOC_PATH.exists() and "ELS-85/4.5V16K" in doc),
        ("docs page is indexed", "machine_vision_azure_85_surrogate" in index),
        ("vendor STEP exists", step_path.exists() and step_path.stat().st_size > 1024),
        ("layout stores vendor STEP overlay", settings.get("lens_step_path") == module.STEP_PATH),
        (
            "layout stores glass-vertex STEP Z offset",
            isinstance(step_offset, list)
            and len(step_offset) == 3
            and abs(float(step_offset[2]) - float(module.STEP_GLASS_ALIGNMENT_Z_OFFSET_MM)) < 1e-9,
        ),
        ("STEP glass fit count", len(glass_fits) >= 2),
        (
            "STEP front glass face matches",
            front_fit is not None
            and module.STEP_FRONT_GLASS_FACE_ID in set(front_fit.face_ids)
            and abs(float(front_fit.vertex_z_mm) - float(module.STEP_FRONT_GLASS_VERTEX_Z_MM)) < 1e-3,
        ),
        (
            "STEP rear glass face matches",
            rear_fit is not None
            and module.STEP_REAR_GLASS_FACE_ID in set(rear_fit.face_ids)
            and abs(float(rear_fit.vertex_z_mm) - float(module.STEP_REAR_GLASS_VERTEX_Z_MM)) < 1e-3,
        ),
        (
            "surrogate vertex span matches STEP glass span",
            front_fit is not None
            and rear_fit is not None
            and abs(
                (float(front_fit.vertex_z_mm) - float(rear_fit.vertex_z_mm))
                - float(module.FRONT_VERTEX_TO_REAR_VERTEX)
            )
            < 1e-6,
        ),
        (
            # Datasheet has no explicit Sigma d; TTL (196.8, rounded to 0.1 mm)
            # minus back focus (141.85) = 54.95.  Allow the TTL rounding.
            "STEP glass span rounds to datasheet Sigma d",
            abs(float(module.FRONT_VERTEX_TO_REAR_VERTEX) - float(module.DATASHEET_FRONT_VERTEX_TO_REAR_VERTEX)) < 0.1,
        ),
        ("effective focal length matches", abs(effective_focal_length - float(module.EFFECTIVE_FOCAL_LENGTH)) < 1e-6),
        ("front focal distance matches", abs(front_focal_distance - float(module.FRONT_FOCAL_DISTANCE)) < 1e-6),
        ("back focal distance matches", abs(back_focal_distance - float(module.BACK_FOCAL_DISTANCE)) < 1e-6),
        ("front principal plane matches", abs(h1 - float(module.FRONT_PRINCIPAL_PLANE_Z)) < 1e-6),
        ("rear principal plane matches", abs(h2 - float(module.REAR_PRINCIPAL_PLANE_Z)) < 1e-6),
        ("effective focal length is 85 mm", abs(effective_focal_length - 85.0) < 1e-6),
        ("symmetric design (equal groups)", abs(float(module.GROUP_1_FOCAL_LENGTH) - float(module.GROUP_2_FOCAL_LENGTH)) < 1e-9),
        ("max image circle is 68 mm", abs(float(module.MAX_SENSOR_DIAMETER) - 68.0) < 1e-9),
    ]
    failures = [name for name, ok in checks if not ok]
    if inherited_mismatches:
        failures.extend(f"inherited-setting mismatch: {key}" for key in inherited_mismatches[:20])
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("AZURE ELS-85 mm surrogate validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    module = importlib.import_module(
        "KrakenOS.common_optical_layouts.machine_vision_85mm_azure_datasheet_05x_20x"
    )
    print(
        "AZURE ELS-85 mm surrogate validation passed: "
        f"EFL={float(module.EFFECTIVE_FOCAL_LENGTH):.6f} mm, "
        f"SF={float(module.FRONT_FOCAL_DISTANCE):.6f} mm, "
        f"S'F'={float(module.BACK_FOCAL_DISTANCE):.6f} mm, "
        f"H1={float(module.FRONT_PRINCIPAL_PLANE_Z):.6f} mm, "
        f"H2={float(module.REAR_PRINCIPAL_PLANE_Z):.6f} mm, "
        f"STEP glass span={float(module.STEP_GLASS_VERTEX_SPAN_MM):.6f} mm."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
