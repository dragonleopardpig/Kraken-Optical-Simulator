from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

from KrakenOS.UI.validate_branch_analysis import _preferred_output_or_terminal_filter
from KrakenOS.UI.validate_diffraction_detector import _trace_dense_detector_bundle


@dataclass
class DetectorSamplingStabilityCheck:
    layout: str
    check: str
    ok: bool
    detail: str


def _result(layout: str, check: str, ok: bool, detail: str) -> DetectorSamplingStabilityCheck:
    return DetectorSamplingStabilityCheck(layout=layout, check=check, ok=bool(ok), detail=str(detail))


def _coherent_data_for_bins(editor, system, wavelength: float, filter_text: str, bins: int, mode: str) -> dict[str, object]:
    editor.detector_bins_var.set(str(int(bins)))
    editor.coherent_sum_mode_var.set(str(mode))
    return editor._coherent_detector_field_data(system, wavelength, filter_text, coherence_mode=mode)


def _diffraction_data_for_bins(editor, system, wavelength: float, filter_text: str, bins: int) -> dict[str, object]:
    editor.detector_bins_var.set(str(int(bins)))
    editor.coherent_sum_mode_var.set("By source ray")
    return editor._diffraction_detector_field_data(system, wavelength, filter_text)


def _branch_code_tuple(data: dict[str, object]) -> tuple[str, ...]:
    return tuple(str(code) for code in data.get("branch_codes", []) or [])


def _validate_layout(
    layout: str,
    *,
    ray_count: int,
    source_radius: float,
    detector_bins: tuple[int, ...] = (16, 32, 64),
) -> list[DetectorSamplingStabilityCheck]:
    editor, system, _rays, wavelength = _trace_dense_detector_bundle(
        layout,
        ray_count=ray_count,
        source_radius=source_radius,
    )
    filter_text = _preferred_output_or_terminal_filter(editor)
    by_source_ray = [
        _coherent_data_for_bins(editor, system, wavelength, filter_text, bins, "By source ray")
        for bins in detector_bins
    ]
    incoherent = [
        _coherent_data_for_bins(editor, system, wavelength, filter_text, bins, "Incoherent power only")
        for bins in detector_bins
    ]
    all_coherent = _coherent_data_for_bins(editor, system, wavelength, filter_text, detector_bins[1], "All rays coherent")
    diffraction = [
        _diffraction_data_for_bins(editor, system, wavelength, filter_text, bins)
        for bins in detector_bins
    ]

    sample_counts = [int(data.get("sample_count", 0) or 0) for data in by_source_ray]
    input_powers = [float(data.get("total_input_power", np.nan)) for data in by_source_ray]
    branch_codes = [_branch_code_tuple(data) for data in by_source_ray]
    group_counts = [int(data.get("coherence_group_count", 0) or 0) for data in by_source_ray]
    occupied_bins = [int(data.get("occupied_bins", 0) or 0) for data in by_source_ray]

    incoherent_input = np.asarray([float(data.get("total_input_power", np.nan)) for data in incoherent], dtype=float)
    incoherent_display = np.asarray([float(data.get("total_coherent_power", np.nan)) for data in incoherent], dtype=float)
    all_intensity = np.asarray(all_coherent.get("intensity", np.asarray([])), dtype=float)
    all_vector = np.asarray(all_coherent.get("all_coherent_intensity", np.asarray([])), dtype=float)

    checks: list[DetectorSamplingStabilityCheck] = [
        _result(
            layout,
            "detector-bin changes keep the same traced detector sample set",
            all(count == sample_counts[0] and count > 0 for count in sample_counts)
            and all(np.isclose(power, input_powers[0], rtol=1e-12, atol=1e-12) for power in input_powers)
            and all(codes == branch_codes[0] for codes in branch_codes),
            (
                f"bins={list(detector_bins)}, samples={sample_counts}, "
                f"input={[round(power, 12) for power in input_powers]}, codes={branch_codes[0]}"
            ),
        ),
        _result(
            layout,
            "source-ray coherence grouping is stable across detector-bin choices",
            all(count == group_counts[0] and count >= 2 for count in group_counts),
            f"bins={list(detector_bins)}, groups={group_counts}",
        ),
        _result(
            layout,
            "occupied detector bins do not collapse as the detector grid is refined",
            all(earlier <= later for earlier, later in zip(occupied_bins, occupied_bins[1:])),
            f"bins={list(detector_bins)}, occupied={occupied_bins}",
        ),
        _result(
            layout,
            "incoherent mode conserves total power independent of detector binning",
            np.all(np.isfinite(incoherent_input))
            and np.all(np.isfinite(incoherent_display))
            and np.allclose(incoherent_input, incoherent_input[0], rtol=1e-12, atol=1e-12)
            and np.allclose(incoherent_display, incoherent_input, rtol=1e-10, atol=1e-12),
            (
                f"input={[round(float(value), 12) for value in incoherent_input]}, "
                f"displayed={[round(float(value), 12) for value in incoherent_display]}"
            ),
        ),
        _result(
            layout,
            "all-rays coherent mode matches accumulated Jones-vector intensity",
            all_intensity.shape == all_vector.shape
            and all_intensity.size > 0
            and np.allclose(all_intensity, all_vector, rtol=1e-10, atol=1e-12),
            (
                f"shape={all_intensity.shape}, "
                f"maxdiff={float(np.max(np.abs(all_intensity - all_vector))) if all_intensity.shape == all_vector.shape and all_intensity.size else np.nan:.6g}"
            ),
        ),
    ]

    for data in diffraction:
        bins = int(data.get("bins", 0) or 0)
        near = float(data.get("diffraction_near_field_power", np.nan))
        far = float(data.get("diffraction_far_field_power", np.nan))
        intensity = np.asarray(data.get("diffraction_intensity", np.asarray([])), dtype=float)
        checks.append(
            _result(
                layout,
                f"diffraction FFT is finite and unitary at {bins} detector bins",
                intensity.shape == (bins, bins)
                and bins > 0
                and np.all(np.isfinite(intensity))
                and np.isfinite(near)
                and np.isfinite(far)
                and near > 0.0
                and np.isclose(near, far, rtol=1e-9, atol=1e-12),
                f"shape={intensity.shape}, near={near:.12g}, far={far:.12g}, diff={abs(near - far):.6g}",
            )
        )

    return checks


def validate_detector_sampling_stability() -> list[DetectorSamplingStabilityCheck]:
    checks: list[DetectorSamplingStabilityCheck] = []
    checks.extend(_validate_layout("Michelson Interferometer (Interferogram)", ray_count=21, source_radius=10.0))
    checks.extend(_validate_layout("Mach-Zehnder Interferometer (Interferogram)", ray_count=11, source_radius=4.0))
    return checks


def _print_table(checks: list[DetectorSamplingStabilityCheck]) -> None:
    print("KrakenOS detector sampling-stability validation")
    print("layout | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.layout} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate coherent/diffraction detector stability across detector-bin settings.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_detector_sampling_stability()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
