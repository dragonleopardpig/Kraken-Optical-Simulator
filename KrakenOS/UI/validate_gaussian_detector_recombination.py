from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor, _preferred_output_or_terminal_filter


@dataclass
class GaussianDetectorRecombinationCheck:
    layout: str
    check: str
    ok: bool
    detail: str


def _result(layout: str, check: str, ok: bool, detail: str) -> GaussianDetectorRecombinationCheck:
    return GaussianDetectorRecombinationCheck(layout=layout, check=check, ok=bool(ok), detail=str(detail))


def _trace_gaussian_layout(layout: str, *, ray_count: int, detector_bins: int):
    editor, system, _rays, wavelength = _load_traced_editor(layout)
    editor.source_model_var.set("Gaussian beam")
    editor.gaussian_input_mode_var.set("Waist + offset")
    editor.gaussian_waist_radius_var.set("0.5")
    editor.gaussian_waist_offset_var.set("0")
    editor.gaussian_m2_var.set("1")
    editor.source_power_var.set("1")
    editor.ray_count_var.set(str(int(ray_count)))
    editor.detector_bins_var.set(str(int(detector_bins)))
    editor.coherent_sum_mode_var.set("By source ray")
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    return editor, system, rays, wavelength


def _reconstructed_intensity(data: dict[str, object]) -> np.ndarray:
    self_total = np.asarray(data.get("self_intensity_total", np.asarray([])), dtype=float)
    pair_total = np.asarray(data.get("pair_interference_total", np.zeros_like(self_total)), dtype=float)
    visibility = float(data.get("visibility_scale", 1.0) or 1.0)
    return np.where(self_total + visibility * pair_total > 0.0, self_total + visibility * pair_total, 0.0)


def _validate_layout(layout: str, *, ray_count: int, detector_bins: int = 32) -> list[GaussianDetectorRecombinationCheck]:
    editor, system, rays, wavelength = _trace_gaussian_layout(layout, ray_count=ray_count, detector_bins=detector_bins)
    filter_text = _preferred_output_or_terminal_filter(editor)
    plain = editor._coherent_detector_field_data(
        system,
        wavelength,
        filter_text,
        coherence_mode="By source ray",
        gaussian_q_weighting=False,
    )
    gaussian = editor._coherent_detector_field_data(
        system,
        wavelength,
        filter_text,
        coherence_mode="By source ray",
        gaussian_q_weighting=True,
    )
    interferogram = editor._interferogram_analysis_data(system, rays, wavelength)

    weights = np.asarray(gaussian.get("gaussian_q_weights", np.asarray([])), dtype=float)
    clips = np.asarray(gaussian.get("gaussian_q_clip_transmissions", np.asarray([])), dtype=float)
    weighted_power = np.asarray(gaussian.get("powers", np.asarray([])), dtype=float)
    plain_power = np.asarray(gaussian.get("powers_unweighted", np.asarray([])), dtype=float)
    gaussian_intensity = np.asarray(gaussian.get("intensity", np.asarray([])), dtype=float)
    reconstructed = _reconstructed_intensity(gaussian)
    plain_intensity = np.asarray(plain.get("intensity", np.asarray([])), dtype=float)
    pair_total = np.asarray(gaussian.get("pair_interference_total", np.asarray([])), dtype=float)

    return [
        _result(
            layout,
            "Gaussian detector recombination applies branch q weights",
            bool(gaussian.get("gaussian_q_weighted", False))
            and int(gaussian.get("gaussian_q_trace_count", 0) or 0) == int(gaussian.get("sample_count", -1) or -1)
            and int(gaussian.get("gaussian_q_stable_count", 0) or 0) > 0,
            (
                f"weighted={gaussian.get('gaussian_q_weighted')}, "
                f"traces={int(gaussian.get('gaussian_q_trace_count', 0) or 0)}, "
                f"stable={int(gaussian.get('gaussian_q_stable_count', 0) or 0)}, "
                f"samples={int(gaussian.get('sample_count', 0) or 0)}"
            ),
        ),
        _result(
            layout,
            "Gaussian detector weights are finite, non-negative, and spatially non-uniform",
            weights.size == weighted_power.size
            and weights.size > 0
            and np.all(np.isfinite(weights))
            and float(np.min(weights)) >= 0.0
            and float(np.std(weights)) > 1e-9,
            (
                f"count={weights.size}, min={float(np.min(weights)) if weights.size else np.nan:.6g}, "
                f"max={float(np.max(weights)) if weights.size else np.nan:.6g}, "
                f"std={float(np.std(weights)) if weights.size else np.nan:.6g}"
            ),
        ),
        _result(
            layout,
            "Gaussian clipping terms are bounded and included in detector power",
            clips.size == weights.size
            and clips.size > 0
            and np.all(np.isfinite(clips))
            and float(np.min(clips)) >= -1e-12
            and float(np.max(clips)) <= 1.0 + 1e-12
            and np.isclose(float(np.sum(weighted_power)), float(gaussian.get("total_input_power", np.nan)), rtol=1e-12, atol=1e-12)
            and float(np.sum(weighted_power)) <= float(np.sum(plain_power)) + 1e-9,
            (
                f"clip=[{float(np.min(clips)) if clips.size else np.nan:.6g}, "
                f"{float(np.max(clips)) if clips.size else np.nan:.6g}], "
                f"weighted={float(np.sum(weighted_power)) if weighted_power.size else np.nan:.12g}, "
                f"plain={float(np.sum(plain_power)) if plain_power.size else np.nan:.12g}"
            ),
        ),
        _result(
            layout,
            "Gaussian coherent intensity matches self plus pair recombination",
            gaussian_intensity.shape == reconstructed.shape
            and gaussian_intensity.size > 0
            and np.allclose(gaussian_intensity, reconstructed, rtol=1e-9, atol=1e-9)
            and pair_total.size > 0
            and float(np.max(np.abs(pair_total))) > 1e-12,
            (
                f"shape={gaussian_intensity.shape}, "
                f"diff={float(np.max(np.abs(gaussian_intensity - reconstructed))) if gaussian_intensity.shape == reconstructed.shape and gaussian_intensity.size else np.nan:.6g}, "
                f"pair_peak={float(np.max(np.abs(pair_total))) if pair_total.size else np.nan:.6g}"
            ),
        ),
        _result(
            layout,
            "Gaussian weighting changes the detector field distribution without changing samples",
            gaussian_intensity.shape == plain_intensity.shape
            and gaussian_intensity.size > 0
            and int(gaussian.get("sample_count", 0) or 0) == int(plain.get("sample_count", -1) or -1)
            and not np.allclose(gaussian_intensity, plain_intensity, rtol=1e-7, atol=1e-12),
            (
                f"samples={int(gaussian.get('sample_count', 0) or 0)}, "
                f"shape={gaussian_intensity.shape}, "
                f"delta={float(np.max(np.abs(gaussian_intensity - plain_intensity))) if gaussian_intensity.shape == plain_intensity.shape and gaussian_intensity.size else np.nan:.6g}"
            ),
        ),
        _result(
            layout,
            "Interf auto-selects Gaussian-q detector recombination for Gaussian sources",
            str(interferogram.get("data_source", "")) == "coherent_detector"
            and bool(interferogram.get("gaussian_q_weighted", False))
            and bool(interferogram.get("reliable", False)),
            (
                f"source={interferogram.get('data_source')}, "
                f"gaussian={interferogram.get('gaussian_q_weighted')}, "
                f"reliable={interferogram.get('reliable')}, "
                f"filter={interferogram.get('filter_text', '-')}"
            ),
        ),
    ]


def validate_gaussian_detector_recombination() -> list[GaussianDetectorRecombinationCheck]:
    checks: list[GaussianDetectorRecombinationCheck] = []
    checks.extend(_validate_layout("Michelson Interferometer (Interferogram)", ray_count=21))
    checks.extend(_validate_layout("Mach-Zehnder Interferometer (Interferogram)", ray_count=21))
    return checks


def _print_table(checks: list[GaussianDetectorRecombinationCheck]) -> None:
    print("KrakenOS Gaussian detector-recombination validation")
    print("layout | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.layout} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate detector-side Gaussian q coherent recombination.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_gaussian_detector_recombination()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
