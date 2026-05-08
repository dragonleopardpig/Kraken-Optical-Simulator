"""Validate pySCATMECH Diffuse Object integration."""

import numpy as np

from KrakenOS.Examples.Examp_Diffuse_Object_pySCATMECH_Microroughness import trace
from KrakenOS.common_optical_layouts.diffuse_object_pyscatmech_microroughness import (
    PYSCATMECH_SCATTER,
    SURFACES,
)
from KrakenOS.scatter_backend import pyscatmech_status


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
    assert settings.get("model") == "pySCATMECH BRDF", "Diffuse Object should declare pySCATMECH BRDF model"
    assert settings.get("backend") == "pySCATMECH", "Diffuse Object should request pySCATMECH backend"
    assert settings.get("backend_model") == "Microroughness_BRDF_Model", "backend_model mismatch"

    _system, rays = trace()
    branch_paths = [_as_text(path) for path in getattr(rays, "BRANCH_PATH", [])]
    assert len(branch_paths) == int(PYSCATMECH_SCATTER["sample_count"]), (
        f"expected {PYSCATMECH_SCATTER['sample_count']} scatter branches, got {len(branch_paths)}"
    )
    assert all("/scatter" in path for path in branch_paths), f"unexpected branch paths: {branch_paths}"

    powers = np.asarray([_as_float(power) for power in getattr(rays, "BRANCH_POWER", [])], dtype=float)
    assert powers.size == int(PYSCATMECH_SCATTER["sample_count"])
    assert np.all(np.isfinite(powers)) and np.all(powers > 0.0), f"scatter powers must be finite and positive, got {powers}"
    assert abs(float(np.sum(powers)) - float(PYSCATMECH_SCATTER["reflectance"])) < 1e-9, (
        f"scatter branch powers should sum to reflectance={PYSCATMECH_SCATTER['reflectance']}, got {float(np.sum(powers))}"
    )

    interaction_models = [_as_text(value) for value in getattr(rays, "INTERACTION_MODEL", [])]
    assert interaction_models, "expected interaction-model metadata"
    status = pyscatmech_status()
    if bool(status.get("available")):
        assert all(model == "pySCATMECH:Microroughness_BRDF_Model" for model in interaction_models), (
            f"expected pySCATMECH interaction model labels, got {interaction_models}"
        )
    else:
        assert all(model.startswith("pySCATMECH fallback") for model in interaction_models), (
            f"expected fallback interaction labels, got {interaction_models}"
        )
    print("Diffuse Object pySCATMECH validation passed.")


if __name__ == "__main__":
    main()
