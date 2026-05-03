"""Ray-only Mach-Zehnder interferometer branch diagnostic.

This example demonstrates how to set up the two beam splitters, two fold
mirrors, and two detector ports used by a Mach-Zehnder interferometer in the
current ray-only branch metadata model. Both arms physically hit the second
splitter; the current interferogram is still the branch-average analytic
diagnostic rather than a detector-pixel coherent sum of every traced ray.
"""

from __future__ import annotations

import numpy as np

import KrakenOS as Kos

try:
    from .Examp_Michelson_Interferometer import (
        BEAM_SPLITTER,
        INTERFEROGRAM,
        _branch_value,
        coating_from_splitter,
        collimated_meridional_source,
        compute_detector_interferogram,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from Examp_Michelson_Interferometer import (
        BEAM_SPLITTER,
        INTERFEROGRAM,
        _branch_value,
        coating_from_splitter,
        collimated_meridional_source,
        compute_detector_interferogram,
    )


def build_system():
    obj = Kos.surf()
    obj.Name = "Input/reference"
    obj.Thickness = 50.0
    obj.Diameter = 18.0
    obj.Glass = "AIR"
    obj.AxisMove = 0.0

    bs1 = Kos.surf()
    bs1.Name = "BS1 input splitter"
    bs1.Thickness = 70.0
    bs1.Diameter = 28.0
    bs1.TiltX = -45.0
    bs1.Glass = "AIR"
    bs1.AxisMove = 0.0
    bs1.BeamSplitter = dict(BEAM_SPLITTER)
    bs1.Coating = coating_from_splitter(bs1.BeamSplitter)

    transmit_mirror = Kos.surf()
    transmit_mirror.Name = "Transmit-arm fold mirror"
    transmit_mirror.Thickness = 0.0
    transmit_mirror.Diameter = 28.0
    transmit_mirror.TiltX = -45.0
    transmit_mirror.Glass = "MIRROR"
    transmit_mirror.AxisMove = 2.0

    reflect_mirror = Kos.surf()
    reflect_mirror.Name = "Reflect-arm fold mirror"
    reflect_mirror.Thickness = 0.0
    reflect_mirror.Diameter = 28.0
    reflect_mirror.TiltX = -135.0
    reflect_mirror.DespY = 70.0
    reflect_mirror.DespZ = -70.0
    reflect_mirror.Glass = "MIRROR"
    reflect_mirror.AxisMove = 2.0

    bs2 = Kos.surf()
    bs2.Name = "BS2 output combiner"
    bs2.Thickness = 60.0
    bs2.Diameter = 28.0
    bs2.TiltX = -45.0
    bs2.DespY = 70.0
    bs2.DespZ = 140.0
    bs2.Glass = "AIR"
    bs2.AxisMove = 0.0
    bs2.BeamSplitter = dict(BEAM_SPLITTER)
    bs2.Coating = coating_from_splitter(bs2.BeamSplitter)

    detector_a = Kos.surf()
    detector_a.Name = "Output detector A"
    detector_a.Thickness = 0.0
    detector_a.Diameter = 24.0
    detector_a.DespY = 70.0
    detector_a.DespZ = 150.0
    detector_a.Glass = "AIR"
    detector_a.AxisMove = 0.0

    detector_b = Kos.surf()
    detector_b.Name = "Output detector B"
    detector_b.Thickness = 0.0
    detector_b.Diameter = 24.0
    detector_b.TiltX = -90.0
    detector_b.DespY = 0.0
    detector_b.DespZ = 80.0
    detector_b.Glass = "AIR"
    detector_b.AxisMove = 0.0

    image = Kos.surf()
    image.Name = "Global diagnostic image"
    image.Thickness = 0.0
    image.Diameter = 170.0
    image.Glass = "AIR"
    image.AxisMove = 0.0

    system = Kos.system(
        [obj, bs1, transmit_mirror, reflect_mirror, bs2, detector_a, detector_b, image],
        Kos.Setup(),
    )
    system.energy_probability = 0
    system.NsLimit = 140
    return system


def trace_demo(ray_count=1, wavelength=0.6328):
    system = build_system()
    rays = Kos.raykeeper(system)
    x, y, z, l, m, n, metadata = collimated_meridional_source(
        radius=2.0,
        ray_count=ray_count,
        wavelength=wavelength,
    )
    Kos.NsTraceLoop(x, y, z, l, m, n, wavelength, rays, source_metadata=metadata)
    return rays


if __name__ == "__main__":
    traced_rays = trace_demo()
    for ray_index, surfaces in enumerate(traced_rays.SURFACE):
        surface_path = [int(value) for value in np.asarray(surfaces, dtype=int)]
        branch_path = str(_branch_value(traced_rays, "BRANCH_PATH", ray_index, ""))
        branch_power = float(_branch_value(traced_rays, "BRANCH_POWER", ray_index, 0.0) or 0.0)
        print(
            f"ray {ray_index:02d}: path={branch_path!r} "
            f"surfaces={surface_path} power={branch_power:.6g}"
        )
    x_axis, y_axis, interferogram = compute_detector_interferogram(
        traced_rays,
        settings={**INTERFEROGRAM, "analysis_title": "Mach-Zehnder Interferogram", "fringe_tilt_x_mrad": 1.0},
    )
    print(
        "Mach-Zehnder branch-average interferogram: "
        f"{interferogram.shape[1]}x{interferogram.shape[0]} pixels, "
        f"Imin={float(np.nanmin(interferogram)):.6g}, Imax={float(np.nanmax(interferogram)):.6g}, "
        f"detector_x=[{x_axis[0]:.6g}, {x_axis[-1]:.6g}] mm, "
        f"detector_y=[{y_axis[0]:.6g}, {y_axis[-1]:.6g}] mm"
    )
