"""50/50 finite-plate beam splitter with deterministic child branches.

The front coated face has ``BeamSplitter`` metadata, ``Glass='BK7'``, and a
3 mm thickness to a following rear ``AIR`` face. Non-sequential tracing now
spawns both the transmitted branch through the plate and the reflected branch
from the coating interface.
"""

import random

import numpy as np

import KrakenOS as Kos


BEAM_SPLITTER = {
    "split_mode": "Deterministic branches",
    "reflectance": 0.5,
    "absorption": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-3,
    "max_branch_depth": 8,
}


def coating_from_splitter(settings):
    reflectance = min(max(float(settings["reflectance"]), 0.0), 1.0)
    absorption = min(max(float(settings["absorption"]), 0.0), 1.0 - reflectance)
    wavelengths = [0.45, 0.55, 0.65]
    angles = [0.0, 45.0, 70.0]
    r_table = [[reflectance for _wavelength in wavelengths] for _angle in angles]
    a_table = [[absorption for _wavelength in wavelengths] for _angle in angles]
    return [r_table, a_table, wavelengths, angles]


def build_system():
    setup = Kos.Setup()

    obj = Kos.surf()
    obj.Name = "Input reference"
    obj.Thickness = 45.0
    obj.Diameter = 30.0
    obj.Glass = "AIR"
    obj.AxisMove = 0.0

    splitter = Kos.surf()
    splitter.Name = "50/50 coated front face"
    splitter.Rc = 0.0
    splitter.Thickness = 3.0
    splitter.Diameter = 25.0
    splitter.TiltX = 45.0
    splitter.Glass = "BK7"
    splitter.AxisMove = 0.0
    splitter.BeamSplitter = dict(BEAM_SPLITTER)
    splitter.Coating = coating_from_splitter(splitter.BeamSplitter)

    rear = Kos.surf()
    rear.Name = "BK7 plate rear face"
    rear.Rc = 0.0
    rear.Thickness = 60.0
    rear.Diameter = 25.0
    rear.TiltX = 45.0
    rear.Glass = "AIR"
    rear.AxisMove = 0.0

    image = Kos.surf()
    image.Name = "Large diagnostic target"
    image.Thickness = 0.0
    image.Diameter = 100.0
    image.Glass = "AIR"
    image.AxisMove = 0.0

    system = Kos.system([obj, splitter, rear, image], setup)
    system.energy_probability = 0
    system.NsLimit = 120
    return system


def trace_demo():
    random.seed(3)
    system = build_system()
    rays = Kos.raykeeper(system)
    wavelength = 0.55
    x = np.zeros(3)
    y = np.zeros_like(x)
    z = np.zeros_like(x)
    l = np.zeros_like(x)
    m = np.zeros_like(x)
    n = np.ones_like(x)
    Kos.NsTraceLoop(x, y, z, l, m, n, wavelength, rays)
    return rays


if __name__ == "__main__":
    traced_rays = trace_demo()
    for ray_index, surfaces in enumerate(traced_rays.SURFACE):
        surface_path = [int(value) for value in np.asarray(surfaces, dtype=int)]
        branch = int(np.asarray(traced_rays.BRANCH_ID[ray_index]).ravel()[0])
        parent = int(np.asarray(traced_rays.PARENT_BRANCH_ID[ray_index]).ravel()[0])
        label = str(np.asarray(traced_rays.BRANCH_LABEL[ray_index]).ravel()[0])
        power = float(np.asarray(traced_rays.BRANCH_POWER[ray_index]).ravel()[0])
        print(
            f"ray {ray_index:02d}: branch={branch} parent={parent} {label} "
            f"surfaces={surface_path} power={power:.6g} "
            f"TT={float(np.asarray(traced_rays.TT[ray_index]).ravel()[-1]):.6g}"
        )
