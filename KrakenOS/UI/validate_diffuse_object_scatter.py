"""Validate built-in Diffuse Object Lambertian branch spawning."""

import numpy as np

from KrakenOS.Examples.Examp_Diffuse_Object_Lambertian_Scatter import trace
from KrakenOS.common_optical_layouts.diffuse_object_lambertian_scatter import DIFFUSE_SCATTER, SURFACES


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
    assert settings.get("model") == "Lambertian", "Diffuse Object should declare Lambertian model"
    assert int(settings.get("sample_count", 0)) == int(DIFFUSE_SCATTER["sample_count"]), "layout sample count mismatch"

    _system, rays = trace()
    branch_paths = [_as_text(path) for path in getattr(rays, "BRANCH_PATH", [])]
    assert len(branch_paths) == int(DIFFUSE_SCATTER["sample_count"]), (
        f"expected {DIFFUSE_SCATTER['sample_count']} scatter branches, got {len(branch_paths)}"
    )
    assert all("/scatter" in path for path in branch_paths), f"unexpected branch paths: {branch_paths}"
    powers = [_as_float(power) for power in getattr(rays, "BRANCH_POWER", [])]
    expected_power = float(DIFFUSE_SCATTER["reflectance"]) / float(DIFFUSE_SCATTER["sample_count"])
    assert powers and all(abs(power - expected_power) < 1e-9 for power in powers), (
        f"scatter branch powers should be {expected_power}, got {powers}"
    )
    outgoing = [np.asarray(direction, dtype=float).reshape(-1, 3)[-1] for direction in getattr(rays, "R_LMN", [])]
    assert outgoing and all(np.isfinite(direction).all() for direction in outgoing), "scatter directions must be finite"
    assert any(abs(direction[0]) > 1e-6 or abs(direction[1]) > 1e-6 for direction in outgoing), (
        "Lambertian samples should include off-axis scattered directions"
    )
    print("Diffuse Object Lambertian scatter validation passed.")


if __name__ == "__main__":
    main()
