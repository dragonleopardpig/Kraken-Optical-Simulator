"""Diffuse Object Lambertian scatter example.

This is the first dependency-free diffuse-surface slice.  The surface carries
``DiffuseScatter`` metadata, the core non-sequential tracer spawns deterministic
Lambertian child branches, and the raykeeper stores the branch power/path
metadata for UI inspection.
"""

import numpy as np

import KrakenOS as Kos
from KrakenOS.common_optical_layouts.diffuse_object_lambertian_scatter import (
    DIFFUSE_SCATTER,
    SURFACES,
)

WAVELENGTH_UM = 0.55


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
            s.DiffuseScatter = dict(spec.get("advanced", {}).get("DiffuseScatter", DIFFUSE_SCATTER))
        runtime_surfaces.append(s)
    return Kos.system(runtime_surfaces, Kos.Setup())


def trace():
    system = build_system()
    rays = Kos.raykeeper(system)
    system.NsTrace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], WAVELENGTH_UM)
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
    print("ray | branch path | power | outgoing direction")
    for ray_index, path in enumerate(getattr(traced_rays, "BRANCH_PATH", [])):
        power = float(_value(getattr(traced_rays, "BRANCH_POWER", []), ray_index, 0.0) or 0.0)
        direction = np.asarray(getattr(traced_rays, "R_LMN", [])[ray_index], dtype=float).reshape(-1, 3)[-1]
        print(f"{ray_index:02d} | {str(np.asarray(path).ravel()[0])} | {power:.6g} | {direction.tolist()}")
