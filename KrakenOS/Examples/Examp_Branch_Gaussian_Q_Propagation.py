"""Branch-carried Gaussian q propagation from traced non-sequential paths.

This example uses the UI's common Michelson layout only as a convenient source
of deterministic branch records. The propagation itself is the public
``KrakenOS.propagate_branch_gaussian_q`` helper: it consumes Ray Inspector style
hit dictionaries and advances independent tangential/sagittal Gaussian q states
through each branch segment.

Current scope: flat folded paths, branch path bookkeeping, and centered
Gaussian aperture/obscuration loss estimates are handled directly. Detector
side Gaussian recombination remains later Phase 7 work.
"""

from __future__ import annotations

import KrakenOS as Kos
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor


def main() -> None:
    editor, _system, _rays, wavelength = _load_traced_editor("Michelson Interferometer (Interferogram)")
    beam = Kos.GaussianBeamInput(
        wavelength_um=float(wavelength),
        waist_radius_mm=0.50,
        waist_offset_mm=0.0,
        m2=1.0,
        input_index=1.0,
    )
    print("ray | branch path | hits | distance [mm] | qT [mm] | qS [mm] | wT/wS [mm] | clip T")
    for record in editor._collect_ray_inspector_records():
        if not list(record.get("hits", []) or []):
            continue
        trace = Kos.propagate_branch_gaussian_q(record, beam, surfaces=editor.rows)
        final = trace.final
        if final is None:
            continue
        print(
            "{ray} | {path} | {hits} | {distance:.6g} | "
            "{qt:.6g}+i{qti:.6g} | {qs:.6g}+i{qsi:.6g} | {wt:.6g}/{ws:.6g} | {clip:.6g}".format(
                ray=int(trace.ray_index),
                path=trace.branch_path or "-",
                hits=len(trace.steps),
                distance=float(trace.total_distance_mm),
                qt=float(final.tangential_q_real_mm),
                qti=float(final.tangential_q_imag_mm),
                qs=float(final.sagittal_q_real_mm),
                qsi=float(final.sagittal_q_imag_mm),
                wt=float(final.tangential_beam_radius_mm),
                ws=float(final.sagittal_beam_radius_mm),
                clip=float(trace.cumulative_clip_transmission),
            )
        )


if __name__ == "__main__":
    main()
