"""Polarization-weighted Fresnel beam-splitter branch powers.

``Deterministic Fresnel P/S`` mode uses KrakenOS Fresnel P and S coefficients
at the splitter hit instead of a fixed 50/50 ratio. The scalar
``polarization_p_fraction`` setting weights the branch power:

* ``1.0`` means pure P polarization.
* ``0.0`` means pure S polarization.
* ``0.5`` is an equal P/S Jones input; for branch power it matches the usual
  unpolarized Fresnel average when the relative phase is not important.

The example also demonstrates simple coating retardance controls:
``transmit_s_phase_deg`` and ``reflect_s_phase_deg`` add an output S phase
relative to P for the transmitted and reflected child branches.
"""

from __future__ import annotations

import numpy as np

import KrakenOS as Kos


def beam_splitter_settings(
    p_fraction: float,
    transmit_s_phase_deg: float = 0.0,
    reflect_s_phase_deg: float = 0.0,
) -> dict[str, float | str]:
    return {
        "split_mode": "Deterministic Fresnel P/S",
        "reflectance": 0.5,
        "absorption": 0.0,
        "polarization_p_fraction": float(p_fraction),
        "polarization_s_phase_deg": 0.0,
        "transmit_phase_deg": 0.0,
        "reflect_phase_deg": 180.0,
        "transmit_s_phase_deg": float(transmit_s_phase_deg),
        "reflect_s_phase_deg": float(reflect_s_phase_deg),
        "min_branch_power": 1e-8,
        "max_branch_depth": 2,
    }


def build_system(
    p_fraction: float,
    transmit_s_phase_deg: float = 0.0,
    reflect_s_phase_deg: float = 0.0,
):
    setup = Kos.Setup()

    obj = Kos.surf()
    obj.Name = "Input reference"
    obj.Thickness = 45.0
    obj.Diameter = 20.0
    obj.Glass = "AIR"
    obj.AxisMove = 0.0

    splitter = Kos.surf()
    splitter.Name = f"BK7 Fresnel splitter Pfrac={p_fraction:.2f}"
    splitter.Rc = 0.0
    splitter.Thickness = 3.0
    splitter.Diameter = 25.0
    splitter.TiltX = 45.0
    splitter.Glass = "BK7"
    splitter.AxisMove = 0.0
    splitter.BeamSplitter = beam_splitter_settings(
        p_fraction,
        transmit_s_phase_deg=transmit_s_phase_deg,
        reflect_s_phase_deg=reflect_s_phase_deg,
    )

    rear = Kos.surf()
    rear.Name = "BK7 plate rear face"
    rear.Rc = 0.0
    rear.Thickness = 60.0
    rear.Diameter = 25.0
    rear.TiltX = 45.0
    rear.Glass = "AIR"
    rear.AxisMove = 0.0

    image = Kos.surf()
    image.Name = "Diagnostic image"
    image.Thickness = 0.0
    image.Diameter = 100.0
    image.Glass = "AIR"
    image.AxisMove = 0.0

    system = Kos.system([obj, splitter, rear, image], setup)
    system.energy_probability = 0
    system.NsLimit = 120
    return system


def trace_demo(
    p_fraction: float,
    wavelength: float = 0.55,
    transmit_s_phase_deg: float = 0.0,
    reflect_s_phase_deg: float = 0.0,
):
    system = build_system(
        p_fraction,
        transmit_s_phase_deg=transmit_s_phase_deg,
        reflect_s_phase_deg=reflect_s_phase_deg,
    )
    rays = Kos.raykeeper(system)
    x = np.asarray([0.0], dtype=float)
    y = np.asarray([0.0], dtype=float)
    z = np.asarray([0.0], dtype=float)
    l = np.asarray([0.0], dtype=float)
    m = np.asarray([0.0], dtype=float)
    n = np.asarray([1.0], dtype=float)
    metadata = [
        {
            "source_model": "Collimated single ray",
            "source_xyz": [0.0, 0.0, 0.0],
            "source_lmn": [0.0, 0.0, 1.0],
            "source_power": 1.0,
            "source_weight": 1.0,
            "source_wavelength": float(wavelength),
        }
    ]
    Kos.NsTraceLoop(x, y, z, l, m, n, wavelength, rays, source_metadata=metadata)
    return rays


def branch_power_summary(rays) -> dict[str, tuple[float, complex, complex, np.ndarray]]:
    summary: dict[str, tuple[float, complex, complex, np.ndarray]] = {}
    for ray_index, labels in enumerate(rays.BRANCH_LABEL):
        label = str(np.asarray(labels).ravel()[0])
        power = float(np.asarray(rays.BRANCH_POWER[ray_index]).ravel()[0])
        jones_p = complex(np.asarray(rays.BRANCH_JONES_P[ray_index]).ravel()[0])
        jones_s = complex(np.asarray(rays.BRANCH_JONES_S[ray_index]).ravel()[0])
        polarization = np.asarray(rays.BRANCH_POLARIZATION_XYZ[ray_index], dtype=np.complex128).reshape(-1)[:3]
        previous = summary.get(label)
        if previous is None or power > previous[0]:
            summary[label] = (power, jones_p, jones_s, polarization)
    return summary


if __name__ == "__main__":
    for p_fraction in (1.0, 0.5, 0.0):
        traced_rays = trace_demo(p_fraction)
        print(f"\npolarization_p_fraction={p_fraction:.1f}")
        for label, (power, jones_p, jones_s, polarization) in sorted(branch_power_summary(traced_rays).items()):
            print(
                f"{label}: branch_power={power:.8f} "
                f"Jones(P,S)=({jones_p.real:.6f}{jones_p.imag:+.6f}j, "
                f"{jones_s.real:.6f}{jones_s.imag:+.6f}j) "
                f"E=({polarization[0].real:.6f}{polarization[0].imag:+.6f}j, "
                f"{polarization[1].real:.6f}{polarization[1].imag:+.6f}j, "
                f"{polarization[2].real:.6f}{polarization[2].imag:+.6f}j)"
            )

    traced_rays = trace_demo(0.5, reflect_s_phase_deg=90.0)
    print("\npolarization_p_fraction=0.5, reflect_s_phase_deg=90.0")
    for label, (power, jones_p, jones_s, polarization) in sorted(branch_power_summary(traced_rays).items()):
        print(
            f"{label}: branch_power={power:.8f} "
            f"Jones(P,S)=({jones_p.real:.6f}{jones_p.imag:+.6f}j, "
            f"{jones_s.real:.6f}{jones_s.imag:+.6f}j) "
            f"E=({polarization[0].real:.6f}{polarization[0].imag:+.6f}j, "
            f"{polarization[1].real:.6f}{polarization[1].imag:+.6f}j, "
            f"{polarization[2].real:.6f}{polarization[2].imag:+.6f}j)"
        )
