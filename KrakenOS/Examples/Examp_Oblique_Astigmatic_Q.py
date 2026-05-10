"""Phase 8B oblique astigmatic Gaussian-q diagnostics.

This example uses synthetic Ray Inspector style hits so it can focus on the
Gaussian-q contract without requiring a full UI layout. It demonstrates the
current supported/refused cases:

- oblique spherical reflection applies different tangential/sagittal powers,
- near-normal refraction applies symmetric first-order power,
- oblique powered refraction applies first-order Coddington T/S powers,
- flat tilted refractive plates are marked as q-only index steps,
- above-critical transmit hits are marked as TIR-deferred diagnostics.
"""

from __future__ import annotations

import KrakenOS as Kos


def _beam() -> Kos.GaussianBeamInput:
    return Kos.GaussianBeamInput(
        wavelength_um=0.6328,
        waist_radius_mm=0.50,
        waist_offset_mm=0.0,
        input_index=1.0,
    )


def _trace(name: str, hits, surfaces) -> None:
    hit_list = [hits] if isinstance(hits, dict) else list(hits)
    surface_list = [surfaces] if isinstance(surfaces, dict) else list(surfaces)
    record = {
        "ray_index": 0,
        "source_ray_index": 0,
        "branch_id": 0,
        "branch_path": name,
        "hits": hit_list,
    }
    trace = Kos.propagate_branch_gaussian_q(record, _beam(), surfaces=surface_list)
    final = trace.final
    if final is None:
        print(f"{name}: no q step")
        return
    print(
        f"{name}: note={final.note}, "
        f"Ct={final.tangential_C:.8g}, Cs={final.sagittal_C:.8g}, "
        f"qT={final.tangential_q_real_mm:.6g}+{final.tangential_q_imag_mm:.6g}j mm, "
        f"qS={final.sagittal_q_real_mm:.6g}+{final.sagittal_q_imag_mm:.6g}j mm"
    )


def main() -> None:
    _trace(
        "oblique spherical mirror",
        {
            "step": 0,
            "branch": 0,
            "surface": 0,
            "event": "reflect",
            "distance": 0.0,
            "op": 0.0,
            "n0": 1.0,
            "n1": 1.0,
            "gb_incidence_deg": 30.0,
        },
        {"rc": 200.0, "diameter": 50.0},
    )
    _trace(
        "near-normal refractive surface",
        {
            "step": 0,
            "branch": 0,
            "surface": 0,
            "event": "transmit",
            "distance": 0.0,
            "op": 0.0,
            "n0": 1.0,
            "n1": 1.5,
            "gb_incidence_deg": 0.0,
        },
        {"rc": 120.0, "diameter": 50.0},
    )
    _trace(
        "flat tilted plate diagnostic",
        [
            {
                "step": 0,
                "branch": 0,
                "surface": 0,
                "event": "transmit",
                "distance": 0.0,
                "op": 0.0,
                "n0": 1.0,
                "n1": 1.5,
                "gb_incidence_deg": 35.0,
            },
            {
                "step": 1,
                "branch": 0,
                "surface": 1,
                "event": "transmit",
                "distance": 8.0,
                "op": 12.0,
                "n0": 1.5,
                "n1": 1.0,
                "gb_incidence_deg": 35.0,
            },
        ],
        [{"rc": 0.0, "diameter": 50.0}, {"rc": 0.0, "diameter": 50.0}],
    )
    _trace(
        "TIR diagnostic",
        {
            "step": 0,
            "branch": 0,
            "surface": 0,
            "event": "transmit",
            "distance": 0.0,
            "op": 0.0,
            "n0": 1.5,
            "n1": 1.0,
            "gb_incidence_deg": 50.0,
        },
        {"rc": 120.0, "diameter": 50.0},
    )
    _trace(
        "oblique powered refraction",
        {
            "step": 0,
            "branch": 0,
            "surface": 0,
            "event": "transmit",
            "distance": 0.0,
            "op": 0.0,
            "n0": 1.0,
            "n1": 1.5,
            "gb_incidence_deg": 25.0,
        },
        {"rc": 120.0, "diameter": 50.0},
    )


if __name__ == "__main__":
    main()
