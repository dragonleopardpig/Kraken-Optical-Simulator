#!/usr/bin/env python3
"""Ray-only galvo scanner / F-theta laser layout.

This example mirrors the UI preset:
Common Optical Layouts -> Sources / Illumination -> Galvo F-Theta Laser Scanner

It is a ray-layout example: a Gaussian source is converted from
manufacturer-style diameter/divergence data, representative rays pass through a
two-lens beam expander, reflect from a 45 degree galvo mirror, then propagate
to the 50 mm F-theta prescription transcribed from attachment/F-theta.pdf Figure 8.
"""

from __future__ import annotations

import os

import numpy as np

import KrakenOS as Kos
from KrakenOS.common_optical_layouts.galvo_f_theta_laser_scanner import SETTINGS, SURFACES, TITLE


WAVELENGTH_UM = float(SETTINGS["wavelength"])


def _surface(
    name: str,
    *,
    rc: float = 0.0,
    thickness: float = 0.0,
    glass: str = "AIR",
    diameter: float = 25.0,
    tilt_x: float = 0.0,
    axis_move: float = 0.0,
) -> Kos.surf:
    surface = Kos.surf()
    surface.Name = name
    surface.Rc = float(rc)
    surface.Thickness = float(thickness)
    surface.Glass = glass
    surface.Diameter = float(diameter)
    surface.TiltX = float(tilt_x)
    surface.AxisMove = float(axis_move)
    return surface


def _surface_from_spec(spec: dict) -> Kos.surf:
    return _surface(
        str(spec.get("name") or spec.get("surface") or "Surface"),
        rc=float(spec.get("rc", 0.0)),
        thickness=float(spec.get("thickness", 0.0)),
        glass=str(spec.get("glass", "AIR")),
        diameter=float(spec.get("diameter", 25.0)),
        tilt_x=float(spec.get("tilt_x", 0.0)),
        axis_move=float(spec.get("axis_move", 0.0)),
    )


def build_system() -> Kos.system:
    return Kos.system([_surface_from_spec(spec) for spec in SURFACES], Kos.Setup())


def gaussian_datasheet_input() -> Kos.GaussianBeamInput:
    return Kos.gaussian_beam_from_diameter_divergence(
        wavelength_um=WAVELENGTH_UM,
        beam_diameter_mm=float(SETTINGS["gaussian_beam_diameter"]),
        full_divergence_mrad=float(SETTINGS["gaussian_full_divergence"]),
        m2=float(SETTINGS["gaussian_m2"]),
        waist_after_input=str(SETTINGS.get("gaussian_waist_side", "")).strip() == "Waist after source",
    )


def trace_representative_laser_rays(
    system: Kos.system,
    *,
    ray_count: int = int(SETTINGS["ray_count"]),
) -> Kos.raykeeper:
    beam = gaussian_datasheet_input()
    wavelength_mm = WAVELENGTH_UM * 1e-3
    z_rayleigh = np.pi * beam.waist_radius_mm * beam.waist_radius_mm / (wavelength_mm * beam.m2)
    q_value = complex(beam.waist_offset_mm, z_rayleigh)
    inverse_q = 1.0 / q_value
    wavefront_radius = np.inf if abs(np.real(inverse_q)) < 1e-18 else 1.0 / np.real(inverse_q)
    launch_radius = beam.waist_radius_mm * np.sqrt(1.0 + (beam.waist_offset_mm / z_rayleigh) ** 2)
    ray_heights = np.linspace(-launch_radius, launch_radius, max(1, int(ray_count)))

    rays = Kos.raykeeper(system)
    for height in ray_heights:
        slope = 0.0 if not np.isfinite(wavefront_radius) else height / wavefront_radius
        direction = np.array([0.0, slope, 1.0], dtype=float)
        direction /= np.linalg.norm(direction)
        system.Trace([0.0, float(height), 0.0], direction, WAVELENGTH_UM)
        rays.push()
    return rays


def main() -> None:
    system = build_system()
    rays = trace_representative_laser_rays(system)
    beam = gaussian_datasheet_input()
    print(
        "Gaussian source from datasheet: "
        f"w0={beam.waist_radius_mm:.6g} mm, "
        f"waist_offset={beam.waist_offset_mm:.6g} mm, "
        f"M2={beam.m2:.4g}"
    )
    print("Rows: beam expander -> 45 deg galvo mirror -> Figure 8 F-theta lens -> scan plane")
    if not os.environ.get("DISPLAY") and os.name != "nt":
        print("Headless session detected; skipping interactive Kos.display2d.")
        return
    Kos.display2d(system, rays, 0, arrow=1)


if __name__ == "__main__":
    main()
