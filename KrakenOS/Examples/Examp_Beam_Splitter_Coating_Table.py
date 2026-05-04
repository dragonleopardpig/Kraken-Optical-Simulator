"""Deterministic beam splitter driven by a coating table.

This example is intentionally small: the splitter is an AIR/AIR ideal divider
so the printed branch powers isolate the coating-table interpolation. At
45 degrees and 0.55 um the table below gives R=0.70 and A=0.05, so the
deterministic child branches should carry reflected power 0.70 and transmitted
power 0.25.
"""

from __future__ import annotations

import numpy as np

import KrakenOS as Kos


BEAM_SPLITTER = {
    "split_mode": "Deterministic coating table",
    "reflectance": 0.2,
    "absorption": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-5,
    "max_branch_depth": 2,
}


COATING = [
    [
        [0.20],
        [0.70],
        [0.85],
    ],
    [
        [0.00],
        [0.05],
        [0.05],
    ],
    [0.55],
    [0.0, 45.0, 70.0],
]


def build_system():
    obj = Kos.surf()
    obj.Name = "Input reference"
    obj.Thickness = 50.0
    obj.Diameter = 30.0
    obj.Glass = "AIR"
    obj.AxisMove = 0.0

    splitter = Kos.surf()
    splitter.Name = "Coating-table splitter"
    splitter.Thickness = 80.0
    splitter.Diameter = 30.0
    splitter.TiltX = 45.0
    splitter.Glass = "AIR"
    splitter.AxisMove = 0.0
    splitter.BeamSplitter = dict(BEAM_SPLITTER)
    splitter.Coating = COATING

    image = Kos.surf()
    image.Name = "Diagnostic image"
    image.Thickness = 0.0
    image.Diameter = 100.0
    image.Glass = "AIR"
    image.AxisMove = 0.0

    system = Kos.system([obj, splitter, image], Kos.Setup())
    system.energy_probability = 0
    system.NsLimit = 80
    return system


def trace_demo(wavelength=0.55):
    system = build_system()
    rays = Kos.raykeeper(system)
    x = np.asarray([0.0], dtype=float)
    y = np.asarray([0.0], dtype=float)
    z = np.asarray([0.0], dtype=float)
    l = np.asarray([0.0], dtype=float)
    m = np.asarray([0.0], dtype=float)
    n = np.asarray([1.0], dtype=float)
    source_metadata = [
        {
            "source_model": "Collimated single ray",
            "source_xyz": [0.0, 0.0, 0.0],
            "source_lmn": [0.0, 0.0, 1.0],
            "source_power": 1.0,
            "source_weight": 1.0,
            "source_wavelength": float(wavelength),
        }
    ]
    Kos.NsTraceLoop(x, y, z, l, m, n, wavelength, rays, source_metadata=source_metadata)
    return rays


def branch_power_summary(rays):
    summary = {}
    for ray_index, labels in enumerate(rays.BRANCH_LABEL):
        label = str(np.asarray(labels).ravel()[0])
        power = float(np.asarray(rays.BRANCH_POWER[ray_index]).ravel()[0])
        summary[label] = max(summary.get(label, 0.0), power)
    return summary


if __name__ == "__main__":
    traced_rays = trace_demo()
    for label, power in sorted(branch_power_summary(traced_rays).items()):
        print(f"{label}: branch_power={power:.6f}")
