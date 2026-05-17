from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor


@dataclass
class InterferogramDetectorAccumulationCheck:
    layout: str
    check: str
    ok: bool
    detail: str


def _retrace_editor(editor, system, wavelength: float):
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    return rays


def _result(layout: str, check: str, ok: bool, detail: str) -> InterferogramDetectorAccumulationCheck:
    return InterferogramDetectorAccumulationCheck(layout=layout, check=check, ok=bool(ok), detail=str(detail))


def _dense_bundle_checks(layout: str, *, ray_count: int, source_radius: float) -> list[InterferogramDetectorAccumulationCheck]:
    editor, system, rays, wavelength = _load_traced_editor(layout)
    baseline = editor._interferogram_analysis_data(system, rays, wavelength)
    checks = [
        _result(
            layout,
            "default Interf falls back when detector sampling is sparse",
            str(baseline.get("data_source", "")) == "analytic_path_average",
            f"source={baseline.get('data_source')}, reason={baseline.get('fallback_reason', '-')}",
        ),
        _result(
            layout,
            "sparse analytic fallback averages canonical ray-event branch records",
            set(str(item) for item in baseline.get("analysis_sources", []) or []) == {"ray_events"},
            f"sources={list(baseline.get('analysis_sources', []) or [])}",
        ),
    ]

    editor.ray_count_var.set(str(int(ray_count)))
    editor.source_radius_var.set(str(float(source_radius)))
    editor.coherent_sum_mode_var.set("By source ray")
    rays = _retrace_editor(editor, system, wavelength)
    data = editor._interferogram_analysis_data(system, rays, wavelength)
    pair_key = str(data.get("pair_key", "") or "")
    pair_map = np.asarray(
        (data.get("pair_interference_by_codepair", {}) or {}).get(pair_key, np.asarray([])),
        dtype=float,
    )
    self_total = np.asarray(data.get("self_intensity_total", np.asarray([])), dtype=float)
    visibility_scale = float(data.get("visibility_scale", 1.0) or 1.0)
    reconstructed = np.asarray(self_total, dtype=float)
    if pair_map.size:
        reconstructed = reconstructed + (visibility_scale * pair_map)
    reconstructed = np.where(reconstructed > 0.0, reconstructed, 0.0)
    intensity = np.asarray(data.get("intensity", np.asarray([])), dtype=float)
    checks.extend(
        [
            _result(
                layout,
                "dense bundle Interf promotes to coherent detector accumulation",
                str(data.get("data_source", "")) == "coherent_detector",
                (
                    f"source={data.get('data_source')}, filter={data.get('filter_text', '-')}, "
                    f"samples={int(data.get('sample_count', 0) or 0)}, occupied={int(data.get('occupied_bins', 0) or 0)}"
                ),
            ),
            _result(
                layout,
                "dense bundle coherent detector exposes both complementary branch codes",
                {str(code) for code in data.get("branch_codes", []) or []} >= {"TR", "RT"},
                f"codes={list(data.get('branch_codes', []) or [])}",
            ),
            _result(
                layout,
                "dense bundle coherent detector reports a non-zero interference pair",
                pair_map.size > 0 and float(np.max(np.abs(pair_map))) > 1e-12,
                f"pair={pair_key or '-'}, peak={float(np.max(np.abs(pair_map))) if pair_map.size else 0.0:.6g}",
            ),
            _result(
                layout,
                "dense bundle displayed interferogram matches self plus pair decomposition",
                intensity.shape == reconstructed.shape and intensity.size > 0 and np.allclose(intensity, reconstructed, rtol=1e-9, atol=1e-9),
                (
                    f"shape={intensity.shape}, visibility={visibility_scale:.6g}, "
                    f"diff={float(np.max(np.abs(intensity - reconstructed))) if intensity.shape == reconstructed.shape and intensity.size else float('nan'):.6g}"
                ),
            ),
        ]
    )
    return checks


def validate_interferogram_detector_accumulation() -> list[InterferogramDetectorAccumulationCheck]:
    checks: list[InterferogramDetectorAccumulationCheck] = []
    checks.extend(_dense_bundle_checks("Michelson Interferometer (Interferogram)", ray_count=21, source_radius=10.0))
    checks.extend(_dense_bundle_checks("Mach-Zehnder Interferometer (Interferogram)", ray_count=11, source_radius=4.0))
    return checks


def _print_table(checks: list[InterferogramDetectorAccumulationCheck]) -> None:
    print("KrakenOS interferogram detector-accumulation validation")
    print("layout | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.layout} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate detector-binned coherent interferogram promotion and decomposition.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_interferogram_detector_accumulation()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
