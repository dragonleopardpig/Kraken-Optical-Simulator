"""Validate non-sequential STL prism media handling.

Run with:

    python -m KrakenOS.UI.validate_stl_prism_media

This regression covers the Phase 6 optical-STL case where a prism rotated
into the classic dispersion pose must still use the row material at the first
STL boundary.  A bad trace reports n=1 -> 1 and passes straight through.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import KrakenOS as Kos


def _build_dispersion_pose_system():
    prism_path = Path(__file__).resolve().parents[1] / "Examples" / "prism.stl"

    obj = Kos.surf()
    obj.Name = "Object"
    obj.Thickness = 90.0
    obj.Diameter = 25.0
    obj.Drawing = 0

    prism = Kos.surf()
    prism.Name = "Dispersion pose STL prism"
    prism.Solid_3d_stl = str(prism_path)
    prism.Glass = "BK7"
    prism.Diameter = 25.0
    prism.Thickness = 40.0
    prism.TiltX = -90.0
    prism.DespY = -5.0
    prism.DespZ = 10.0
    prism.AxisMove = 2.0

    image = Kos.surf()
    image.Name = "Image"
    image.Glass = "AIR"
    image.Diameter = 50.0
    image.Drawing = 1

    return Kos.system([obj, prism, image], Kos.Setup())


def main() -> None:
    system = _build_dispersion_pose_system()
    system.energy_probability = 0
    system.NsTrace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)

    surfaces = np.asarray(system.SURFACE, dtype=int)
    stl_hits = np.flatnonzero(surfaces == 1)
    if stl_hits.size == 0:
        raise AssertionError("Dispersion-pose ray did not hit the STL prism row.")

    first = int(stl_hits[0])
    n0 = float(system.N0[first])
    n1 = float(system.N1[first])
    out = np.asarray(system.R_LMN[first], dtype=float)
    if not (abs(n0 - 1.0) < 1e-6 and n1 > 1.1):
        raise AssertionError(f"STL prism entry used wrong media: n={n0:.8g}->{n1:.8g}")
    if not (out[1] < -0.05 and out[2] > 0.5):
        raise AssertionError(f"STL prism entry did not bend downward/forward: R_LMN={out}")
    if len(system.RAY) < len(system.SURFACE) + 1:
        raise AssertionError(
            f"Displayed ray path is truncated: RAY={len(system.RAY)} hits={len(system.SURFACE)}"
        )

    print(
        "STL prism media validation OK: "
        f"entry n={n0:.6g}->{n1:.6g}, direction={np.round(out, 6).tolist()}, "
        f"ray_points={len(system.RAY)}"
    )


if __name__ == "__main__":
    main()
