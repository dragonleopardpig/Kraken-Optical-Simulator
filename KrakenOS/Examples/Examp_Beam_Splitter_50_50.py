"""50/50 beam splitter setup using the current KrakenOS coating split.

This example is intentionally explicit about the current limitation: KrakenOS
can stochastically choose a reflected or transmitted coating path when
``energy_probability`` is enabled, but it does not yet spawn both child rays
from one incident ray. The ``BeamSplitter`` attribute preserves the metadata
needed by the planned deterministic branch queue.
"""

import random

import numpy as np

import KrakenOS as Kos


BEAM_SPLITTER = {
    "split_mode": "Monte Carlo coating split",
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

    splitter = Kos.surf()
    splitter.Name = "50/50 beam splitter"
    splitter.Rc = 0.0
    splitter.Thickness = 45.0
    splitter.Diameter = 25.0
    splitter.TiltX = 45.0
    splitter.Glass = "AIR"
    splitter.BeamSplitter = dict(BEAM_SPLITTER)
    splitter.Coating = coating_from_splitter(splitter.BeamSplitter)

    image = Kos.surf()
    image.Name = "Large diagnostic target"
    image.Thickness = 0.0
    image.Diameter = 100.0
    image.Glass = "AIR"

    system = Kos.system([obj, splitter, image], setup)
    system.energy_probability = 1
    system.NsLimit = 120
    return system


def trace_demo():
    random.seed(3)
    system = build_system()
    rays = Kos.raykeeper(system)
    wavelength = 0.55
    x = np.zeros(25)
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
        print(
            f"ray {ray_index:02d}: surfaces={surface_path} "
            f"TT={float(np.asarray(traced_rays.TT[ray_index]).ravel()[-1]):.6g}"
        )
