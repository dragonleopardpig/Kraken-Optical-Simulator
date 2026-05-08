"""Diffuse Object pySCATMECH microroughness scatter example."""

import numpy as np

import KrakenOS as Kos
from KrakenOS.common_optical_layouts.diffuse_object_pyscatmech_microroughness import (
    PYSCATMECH_SCATTER,
    SURFACES,
)

WAVELENGTH_UM = 0.532
INCIDENT_DIRECTION = np.asarray((0.0, 0.4, 0.916515138991168), dtype=float)


def build_system():
    runtime_surfaces = []
    for spec in SURFACES:
        s = Kos.surf()
        s.Name = spec["name"]
        s.Rc = spec["rc"]
        s.Thickness = spec["thickness"]
        s.Diameter = spec["diameter"]
        s.Glass = spec["glass"]
        s.AxisMove = spec.get("axis_move", 0.0)
        if spec["surface"] == "Diffuse Object":
            s.Glass = "MIRROR"
            s.DiffuseScatter = dict(spec.get("advanced", {}).get("DiffuseScatter", PYSCATMECH_SCATTER))
        runtime_surfaces.append(s)
    return Kos.system(runtime_surfaces, Kos.Setup())


def trace():
    system = build_system()
    rays = Kos.raykeeper(system)
    direction = INCIDENT_DIRECTION / max(float(np.linalg.norm(INCIDENT_DIRECTION)), 1e-15)
    system.NsTrace([0.0, 0.0, 0.0], direction, WAVELENGTH_UM)
    rays.push()
    return system, rays


def _value(sequence, index, default=None):
    try:
        arr = np.asarray(sequence[index]).ravel()
    except Exception:
        return default
    return arr[0] if arr.size else default


if __name__ == "__main__":
    _system, traced_rays = trace()
    print("ray | branch path | power | interaction model")
    for ray_index, path in enumerate(getattr(traced_rays, "BRANCH_PATH", [])):
        power = float(_value(getattr(traced_rays, "BRANCH_POWER", []), ray_index, 0.0) or 0.0)
        interaction_model = _value(getattr(traced_rays, "INTERACTION_MODEL", []), ray_index, "")
        print(f"{ray_index:02d} | {str(np.asarray(path).ravel()[0])} | {power:.6g} | {interaction_model}")
