"""Ray-only Michelson interferometer branch diagnostic.

This example validates source-driven, non-sequential beam-splitter tracing for
a simple Michelson geometry:

* independent physical source at (0, 0, 0), direction +Z;
* 45 degree deterministic 50/50 splitter at z=50 mm;
* one return mirror on the transmitted arm;
* one return mirror on the reflected arm;
* second splitter encounter produces four ray-only recombination branches.

It does not compute coherent interference fringes. Use the printed branch paths,
power, phase, and optical path as the starting point for future coherent field
summation.
"""

from __future__ import annotations

import numpy as np

import KrakenOS as Kos


BEAM_SPLITTER = {
    "split_mode": "Deterministic branches",
    "reflectance": 0.5,
    "absorption": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-4,
    "max_branch_depth": 2,
}


def coating_from_splitter(settings):
    reflectance = min(max(float(settings["reflectance"]), 0.0), 1.0)
    absorption = min(max(float(settings["absorption"]), 0.0), 1.0 - reflectance)
    wavelengths = [0.55, 0.6328]
    angles = [0.0, 45.0, 70.0]
    r_table = [[reflectance for _wavelength in wavelengths] for _angle in angles]
    a_table = [[absorption for _wavelength in wavelengths] for _angle in angles]
    return [r_table, a_table, wavelengths, angles]


def build_system():
    obj = Kos.surf()
    obj.Name = "Object reference (not source)"
    obj.Thickness = 50.0
    obj.Diameter = 120.0
    obj.Glass = "AIR"
    obj.AxisMove = 0.0

    splitter = Kos.surf()
    splitter.Name = "Michelson splitter"
    splitter.Thickness = 80.0
    splitter.Diameter = 50.0
    splitter.TiltX = 45.0
    splitter.Glass = "AIR"
    splitter.AxisMove = 0.0
    splitter.BeamSplitter = dict(BEAM_SPLITTER)
    splitter.Coating = coating_from_splitter(splitter.BeamSplitter)

    transmit_mirror = Kos.surf()
    transmit_mirror.Name = "Transmit return mirror"
    transmit_mirror.Thickness = 0.0
    transmit_mirror.Diameter = 55.0
    transmit_mirror.Glass = "MIRROR"
    transmit_mirror.AxisMove = 0.0

    reflect_mirror = Kos.surf()
    reflect_mirror.Name = "Reflect return mirror"
    reflect_mirror.Thickness = 0.0
    reflect_mirror.Diameter = 55.0
    reflect_mirror.TiltX = -90.0
    reflect_mirror.DespY = 80.0
    reflect_mirror.DespZ = -80.0
    reflect_mirror.Glass = "MIRROR"
    reflect_mirror.AxisMove = 0.0

    image = Kos.surf()
    image.Name = "Ray-only output reference"
    image.Thickness = 0.0
    image.Diameter = 220.0
    image.Glass = "AIR"
    image.AxisMove = 0.0

    system = Kos.system([obj, splitter, transmit_mirror, reflect_mirror, image], Kos.Setup())
    system.energy_probability = 0
    system.NsLimit = 80
    return system


def collimated_meridional_source(radius=4.0, ray_count=5, wavelength=0.6328):
    count = max(1, int(ray_count))
    if count == 1:
        y_values = np.asarray([0.0], dtype=float)
    else:
        y_values = np.linspace(-float(radius), float(radius), count)
    x_values = np.zeros(count, dtype=float)
    z_values = np.zeros(count, dtype=float)
    l_values = np.zeros(count, dtype=float)
    m_values = np.zeros(count, dtype=float)
    n_values = np.ones(count, dtype=float)
    metadata = [
        {
            "source_model": "Collimated disk source",
            "source_xyz": [float(x_values[index]), float(y_values[index]), 0.0],
            "source_lmn": [0.0, 0.0, 1.0],
            "source_power": 1.0,
            "source_weight": 1.0 / float(count),
            "source_wavelength": float(wavelength),
        }
        for index in range(count)
    ]
    return x_values, y_values, z_values, l_values, m_values, n_values, metadata


def trace_demo(ray_count=5, wavelength=0.6328):
    system = build_system()
    rays = Kos.raykeeper(system)
    x, y, z, l, m, n, metadata = collimated_meridional_source(
        ray_count=ray_count,
        wavelength=wavelength,
    )
    Kos.NsTraceLoop(x, y, z, l, m, n, wavelength, rays, source_metadata=metadata)
    return rays


if __name__ == "__main__":
    traced_rays = trace_demo()
    for ray_index, surfaces in enumerate(traced_rays.SURFACE):
        surface_path = [int(value) for value in np.asarray(surfaces, dtype=int)]
        branch_path = str(np.asarray(traced_rays.BRANCH_PATH[ray_index]).ravel()[0])
        branch_power = float(np.asarray(traced_rays.BRANCH_POWER[ray_index]).ravel()[0])
        branch_phase = float(np.asarray(traced_rays.BRANCH_PHASE[ray_index]).ravel()[0])
        top = float(np.asarray(traced_rays.TOP[ray_index]).ravel()[0])
        print(
            f"ray {ray_index:02d}: path={branch_path!r} "
            f"surfaces={surface_path} power={branch_power:.6g} "
            f"phase={branch_phase:.6g} deg TOP={top:.6g} mm"
        )
