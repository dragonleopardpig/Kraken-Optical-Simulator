"""Astigmatic Gaussian beams and cavity eigenmodes.

This example covers the laser-specific helpers that sit on top of the same
KrakenOS ABCD/q-parameter machinery used by the UI Gaussian Beam Report.
"""

from __future__ import annotations

import numpy as np

import KrakenOS as Kos


def symmetric_two_mirror_round_trip(length_mm: float, mirror_radius_mm: float) -> np.ndarray:
    """Return the ABCD matrix for one round trip in a symmetric mirror cavity."""
    propagation = np.array([[1.0, length_mm], [0.0, 1.0]], dtype=float)
    mirror = np.array([[1.0, 0.0], [-2.0 / mirror_radius_mm, 1.0]], dtype=float)
    return mirror @ propagation @ mirror @ propagation


def build_lens_system():
    setup = Kos.Setup()

    obj = Kos.surf()
    obj.Name = "Laser output"
    obj.Thickness = 75.0
    obj.Diameter = 20.0
    obj.Glass = "AIR"

    lens = Kos.surf()
    lens.Name = "Beam shaping lens f=120"
    lens.Thin_Lens = 120.0
    lens.Thickness = 180.0
    lens.Diameter = 30.0
    lens.Glass = "AIR"

    image = Kos.surf()
    image.Name = "Readout plane"
    image.Thickness = 0.0
    image.Diameter = 24.0
    image.Glass = "AIR"

    return Kos.system([obj, lens, image], setup)


def main() -> None:
    wavelength_um = 0.6328

    system = build_lens_system()
    paraxial_trace = system.ParaxMatrices(wavelength_um)
    astigmatic_beam = Kos.astigmatic_gaussian_beam_from_diameter_divergence(
        wavelength_um=wavelength_um,
        tangential_beam_diameter_mm=1.2,
        tangential_full_divergence_mrad=0.9,
        sagittal_beam_diameter_mm=0.8,
        sagittal_full_divergence_mrad=1.4,
        tangential_m2=1.1,
        sagittal_m2=1.3,
        waist_after_input=False,
    )
    astigmatic_trace = Kos.propagate_astigmatic_gaussian_beam(paraxial_trace, astigmatic_beam)
    final_t = astigmatic_trace.final_tangential
    final_s = astigmatic_trace.final_sagittal

    print("Astigmatic / elliptical Gaussian source")
    print(
        "input tangential: "
        f"w0={astigmatic_beam.tangential.waist_radius_mm:.6g} mm, "
        f"offset={astigmatic_beam.tangential.waist_offset_mm:.6g} mm"
    )
    print(
        "input sagittal:   "
        f"w0={astigmatic_beam.sagittal.waist_radius_mm:.6g} mm, "
        f"offset={astigmatic_beam.sagittal.waist_offset_mm:.6g} mm"
    )
    if final_t is not None and final_s is not None:
        print(
            "final beam radii: "
            f"tangential={final_t.beam_radius_mm:.6g} mm, "
            f"sagittal={final_s.beam_radius_mm:.6g} mm"
        )

    round_trip = symmetric_two_mirror_round_trip(length_mm=300.0, mirror_radius_mm=1000.0)
    eigenmode = Kos.solve_gaussian_cavity_eigenmode(round_trip, wavelength_um=wavelength_um)
    print("\nSymmetric two-mirror cavity eigenmode")
    print(f"stable={eigenmode.stable}, g={eigenmode.stability_parameter:.6g}")
    print(
        f"q={eigenmode.q_real_mm:.6g}+i{eigenmode.q_imag_mm:.6g} mm, "
        f"w0={eigenmode.waist_radius_mm:.6g} mm, "
        f"w(reference)={eigenmode.beam_radius_mm:.6g} mm, "
        f"Gouy/RT={eigenmode.round_trip_gouy_rad:.6g} rad"
    )


if __name__ == "__main__":
    main()
