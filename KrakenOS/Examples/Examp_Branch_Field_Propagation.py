"""Phase 8 scalar branch-field propagation helper.

This example is intentionally independent of the UI. It builds a sampled TEM00
field, propagates it with the first Phase 8 paraxial branch-field helper, and
reports power conservation plus overlap against the original waist mode.
"""

from __future__ import annotations

import numpy as np

import KrakenOS as Kos


def main() -> None:
    x_edges = np.linspace(-4.0, 4.0, 129)
    y_edges = np.linspace(-4.0, 4.0, 129)
    waist_mm = 0.55
    field = Kos.make_gaussian_tem00_field(
        x_edges_mm=x_edges,
        y_edges_mm=y_edges,
        wavelength_um=0.6328,
        waist_radius_mm=waist_mm,
        power=1.0,
    )
    propagated = Kos.propagate_branch_field(field, 250.0)
    overlap = Kos.gaussian_mode_overlap(propagated, waist_radius_mm=waist_mm)
    print("Phase 8 scalar branch-field propagation")
    print(f"grid: {field.shape[0]} x {field.shape[1]}")
    print(f"input power: {field.total_power:.12g}")
    print(f"propagated power: {propagated.total_power:.12g}")
    print(f"input second-moment radius [mm]: {field.second_moment_radius_mm():.6g}")
    print(f"propagated second-moment radius [mm]: {propagated.second_moment_radius_mm():.6g}")
    print(f"TEM00 waist-mode overlap efficiency: {overlap.efficiency:.6g}")


if __name__ == "__main__":
    main()
