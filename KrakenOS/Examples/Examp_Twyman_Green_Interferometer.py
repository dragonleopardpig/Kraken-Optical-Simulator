"""Ray-only Twyman-Green interferometer path diagnostic.

This example uses the same deterministic beam-splitter path machinery as the
Michelson example, with Twyman-Green naming:

* the transmitted return path is the test optic;
* the reflected return path is the reference flat;
* the cross output port is used as the detector port;
* the current interferogram is a path-average analytic diagnostic, not yet a
  detector-pixel coherent sum of every traced ray.
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
    obj.Name = "Input/source reference"
    obj.Thickness = 50.0
    obj.Diameter = 35.0
    obj.Glass = "AIR"
    obj.AxisMove = 0.0

    splitter = Kos.surf()
    splitter.Name = "Twyman-Green splitter"
    splitter.Thickness = 80.0
    splitter.Diameter = 35.0
    splitter.TiltX = 45.0
    splitter.Glass = "AIR"
    splitter.AxisMove = 0.0
    splitter.BeamSplitter = dict(BEAM_SPLITTER)
    splitter.Coating = coating_from_splitter(splitter.BeamSplitter)

    test_optic = Kos.surf()
    test_optic.Name = "Test optic mirror"
    test_optic.Thickness = 0.0
    test_optic.Diameter = 35.0
    test_optic.Glass = "MIRROR"
    test_optic.AxisMove = 0.0

    reference_flat = Kos.surf()
    reference_flat.Name = "Reference flat"
    reference_flat.Thickness = 0.0
    reference_flat.Diameter = 35.0
    reference_flat.TiltX = -90.0
    reference_flat.DespY = 80.0
    reference_flat.DespZ = -80.0
    reference_flat.Glass = "MIRROR"
    reference_flat.AxisMove = 0.0

    detector = Kos.surf()
    detector.Name = "Detector path / output port"
    detector.Thickness = 0.0
    detector.Diameter = 24.0
    detector.Glass = "AIR"
    detector.AxisMove = 0.0

    system = Kos.system([obj, splitter, test_optic, reference_flat, detector], Kos.Setup())
    system.energy_probability = 0
    system.NsLimit = 80
    return system


def trace_demo(ray_count=1, wavelength=0.6328):
    system = build_system()
    rays = Kos.raykeeper(system)
    x, y, z, l, m, n, metadata = collimated_meridional_source(
        radius=4.0,
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
        branch_phase = float(_branch_value(traced_rays, "BRANCH_PHASE", ray_index, 0.0) or 0.0)
        top = float(_branch_value(traced_rays, "TOP", ray_index, 0.0) or 0.0)
        print(
            f"ray {ray_index:02d}: path={branch_path!r} "
            f"surfaces={surface_path} power={branch_power:.6g} "
            f"phase={branch_phase:.6g} deg TOP={top:.6g} mm"
        )

    x_axis, y_axis, interferogram = compute_detector_interferogram(
        traced_rays,
        settings={**INTERFEROGRAM, "fringe_tilt_x_mrad": 2.0},
    )
    print(
        "Twyman-Green path-average interferogram: "
        f"{interferogram.shape[1]}x{interferogram.shape[0]} pixels, "
        f"Imin={float(np.nanmin(interferogram)):.6g}, Imax={float(np.nanmax(interferogram)):.6g}, "
        f"detector_x=[{x_axis[0]:.6g}, {x_axis[-1]:.6g}] mm, "
        f"detector_y=[{y_axis[0]:.6g}, {y_axis[-1]:.6g}] mm"
    )
