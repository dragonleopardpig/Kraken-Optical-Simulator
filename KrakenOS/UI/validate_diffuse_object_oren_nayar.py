"""Validate built-in Diffuse Object Oren-Nayar branch spawning."""

import numpy as np

from KrakenOS.Examples.Examp_Diffuse_Object_Oren_Nayar_Scatter import trace
from KrakenOS.common_optical_layouts.diffuse_object_oren_nayar_scatter import OREN_NAYAR_SCATTER, SURFACES


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
    assert settings.get("model") == "Oren-Nayar", "Diffuse Object should declare Oren-Nayar model"
    assert int(settings.get("sample_count", 0)) == int(OREN_NAYAR_SCATTER["sample_count"]), "layout sample count mismatch"
    assert float(settings.get("roughness_deg", 0.0)) == float(OREN_NAYAR_SCATTER["roughness_deg"]), "roughness mismatch"

    _system, rays = trace()
    branch_paths = [_as_text(path) for path in getattr(rays, "BRANCH_PATH", [])]
    assert len(branch_paths) == int(OREN_NAYAR_SCATTER["sample_count"]), (
        f"expected {OREN_NAYAR_SCATTER['sample_count']} scatter branches, got {len(branch_paths)}"
    )
    assert all("/scatter" in path for path in branch_paths), f"unexpected branch paths: {branch_paths}"

    powers = np.asarray([_as_float(power) for power in getattr(rays, "BRANCH_POWER", [])], dtype=float)
    assert powers.size == int(OREN_NAYAR_SCATTER["sample_count"])
    assert np.all(np.isfinite(powers)) and np.all(powers > 0.0), f"scatter powers must be finite and positive, got {powers}"
    assert abs(float(np.sum(powers)) - float(OREN_NAYAR_SCATTER["reflectance"])) < 1e-9, (
        f"scatter branch powers should sum to reflectance={OREN_NAYAR_SCATTER['reflectance']}, got {float(np.sum(powers))}"
    )
    assert float(np.ptp(powers)) > 1e-4, f"Oren-Nayar branch powers should vary with rough diffuse weighting, got {powers}"

    outgoing = [np.asarray(direction, dtype=float).reshape(-1, 3)[-1] for direction in getattr(rays, "R_LMN", [])]
    assert outgoing and all(np.isfinite(direction).all() for direction in outgoing), "scatter directions must be finite"
    assert any(abs(direction[1]) > 1e-6 for direction in outgoing), "oblique Oren-Nayar sample set should retain Y spread"

    interaction_models = [_as_text(value) for value in getattr(rays, "INTERACTION_MODEL", [])]
    assert interaction_models and all(model == "Oren-Nayar" for model in interaction_models), (
        f"interaction models should all be Oren-Nayar, got {interaction_models}"
    )
    print("Diffuse Object Oren-Nayar scatter validation passed.")


if __name__ == "__main__":
    main()
