"""Validate built-in Diffuse Object cosine-lobe branch spawning."""

import numpy as np

from KrakenOS.Examples.Examp_Diffuse_Object_Cosine_Lobe_Scatter import trace
from KrakenOS.common_optical_layouts.diffuse_object_cosine_lobe_scatter import COSINE_LOBE_SCATTER, SURFACES


def _as_text(value) -> str:
    arr = np.asarray(value, dtype=object).ravel()
    return str(arr[0]) if arr.size else ""


def _as_float(value) -> float:
    arr = np.asarray(value, dtype=float).ravel()
    return float(arr[0]) if arr.size else float("nan")


def main() -> None:
    diffuse_rows = [spec for spec in SURFACES if spec.get("surface") == "Diffuse Object"]
    assert diffuse_rows, "layout must expose a Diffuse Object surface"
    settings = diffuse_rows[0].get("advanced", {}).get("DiffuseScatter", {})
    assert settings.get("model") == "Cosine Lobe", "Diffuse Object should declare Cosine Lobe model"
    assert int(settings.get("sample_count", 0)) == int(COSINE_LOBE_SCATTER["sample_count"]), "layout sample count mismatch"
    assert float(settings.get("lobe_exponent", 0.0)) == float(COSINE_LOBE_SCATTER["lobe_exponent"]), "lobe exponent mismatch"

    _system, rays = trace()
    branch_paths = [_as_text(path) for path in getattr(rays, "BRANCH_PATH", [])]
    assert len(branch_paths) == int(COSINE_LOBE_SCATTER["sample_count"]), (
        f"expected {COSINE_LOBE_SCATTER['sample_count']} scatter branches, got {len(branch_paths)}"
    )
    assert all("/scatter" in path for path in branch_paths), f"unexpected branch paths: {branch_paths}"

    powers = [_as_float(power) for power in getattr(rays, "BRANCH_POWER", [])]
    expected_power = float(COSINE_LOBE_SCATTER["reflectance"]) / float(COSINE_LOBE_SCATTER["sample_count"])
    assert powers and all(abs(power - expected_power) < 1e-9 for power in powers), (
        f"scatter branch powers should be {expected_power}, got {powers}"
    )

    outgoing = [np.asarray(direction, dtype=float).reshape(-1, 3)[-1] for direction in getattr(rays, "R_LMN", [])]
    assert outgoing and all(np.isfinite(direction).all() for direction in outgoing), "scatter directions must be finite"
    specular_axis = np.asarray([0.0, 0.0, -1.0], dtype=float)
    cos_limit = float(np.cos(np.deg2rad(float(COSINE_LOBE_SCATTER["max_scatter_angle_deg"]))))
    assert all(float(np.dot(direction, specular_axis)) + 1e-9 >= cos_limit for direction in outgoing), (
        "Cosine Lobe samples should stay inside the configured glossy lobe cone"
    )
    assert any(abs(direction[0]) > 1e-6 or abs(direction[1]) > 1e-6 for direction in outgoing), (
        "Cosine Lobe samples should include off-axis glossy directions"
    )
    print("Diffuse Object Cosine Lobe scatter validation passed.")


if __name__ == "__main__":
    main()
