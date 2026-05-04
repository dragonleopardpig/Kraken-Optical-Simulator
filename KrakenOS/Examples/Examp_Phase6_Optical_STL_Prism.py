#!/usr/bin/env python3
"""Phase 6 optical STL prism scene.

This example shows the direct KrakenOS core workflow behind the UI command:
File -> Import Optical STL Solid...

The STL is treated as an optical solid. Refraction follows KrakenOS
non-sequential tracing through the row material, mesh, pose, AxisMove, and
Thickness settings. For user-made prisms, keep the STL closed/manifold, use
millimetre units, and check face normals if rays exit the wrong side.
"""

from pathlib import Path

import numpy as np

import KrakenOS as Kos


EXAMPLE_DIR = Path(__file__).resolve().parent
PRISM_STL = EXAMPLE_DIR / "prism.stl"


P_Obj = Kos.surf()
P_Obj.Name = "Source reference"
P_Obj.Thickness = 30.0
P_Obj.Diameter = 8.0
P_Obj.Drawing = 0

Prism_Solid = Kos.surf()
Prism_Solid.Name = "Phase 6 STL prism"
Prism_Solid.Solid_3d_stl = str(PRISM_STL)
Prism_Solid.Glass = "BK7"
Prism_Solid.Diameter = 25.0
Prism_Solid.Thickness = 40.0
Prism_Solid.DespY = -5.0
Prism_Solid.AxisMove = 2.0

P_Ima = Kos.surf()
P_Ima.Name = "Detector plane"
P_Ima.Glass = "AIR"
P_Ima.Diameter = 25.0
P_Ima.Drawing = 1

SURFACES = [P_Obj, Prism_Solid, P_Ima]


def build_system():
    return Kos.system(SURFACES, Kos.Setup())


def trace_collimated_grid(system, grid_count=5, radius_mm=0.6, wavelength_um=0.55):
    rays = Kos.raykeeper(system)
    coordinates = np.linspace(-float(radius_mm), float(radius_mm), int(grid_count))
    system.energy_probability = 0
    for x0 in coordinates:
        for y0 in coordinates:
            system.NsTrace([float(x0), float(y0), 0.0], [0.0, 0.0, 1.0], float(wavelength_um))
            rays.push()
    return rays


if __name__ == "__main__":
    optical_system = build_system()
    ray_bundle = trace_collimated_grid(optical_system, grid_count=5, radius_mm=0.6, wavelength_um=0.55)
    Kos.display2d(optical_system, ray_bundle, 0, arrow=1)
