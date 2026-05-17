from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.coherent_detector_analysis import diffraction_detector_field_data_from_coherent
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor, _preferred_output_or_terminal_filter


@dataclass
class DiffractionDetectorCheck:
    layout: str
    check: str
    ok: bool
    detail: str


def _result(layout: str, check: str, ok: bool, detail: str) -> DiffractionDetectorCheck:
    return DiffractionDetectorCheck(layout=layout, check=check, ok=bool(ok), detail=str(detail))


def _trace_dense_detector_bundle(layout: str, *, ray_count: int, source_radius: float):
    editor, system, _rays, wavelength = _load_traced_editor(layout)
    editor.ray_count_var.set(str(int(ray_count)))
    editor.source_radius_var.set(str(float(source_radius)))
    editor.coherent_sum_mode_var.set("By source ray")
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    return editor, system, rays, wavelength


def _validate_layout(layout: str, *, ray_count: int, source_radius: float) -> list[DiffractionDetectorCheck]:
    editor, system, rays, wavelength = _trace_dense_detector_bundle(
        layout,
        ray_count=ray_count,
        source_radius=source_radius,
    )
    filter_text = _preferred_output_or_terminal_filter(editor)
    ray_records = editor._ray_analysis_records_for_trace(system=system, rays=rays)
    detector_records = [
        record
        for record in ray_records
        if editor._ray_record_branch_filter_matches(record, filter_text)
        and editor._surface_index_is_detector(record.get("last_surface"))
    ]
    coherent = editor._coherent_detector_field_data(system, wavelength, filter_text, ray_records=ray_records)
    data = editor._diffraction_detector_field_data(system, wavelength, filter_text, ray_records=ray_records)
    service_data = diffraction_detector_field_data_from_coherent(coherent, wavelength)
    intensity = np.asarray(data.get("diffraction_intensity", np.asarray([])), dtype=float)
    service_intensity = np.asarray(service_data.get("diffraction_intensity", np.asarray([])), dtype=float)
    angle_x = np.asarray(data.get("angle_x_mrad", np.asarray([])), dtype=float)
    angle_y = np.asarray(data.get("angle_y_mrad", np.asarray([])), dtype=float)
    near_power = float(data.get("diffraction_near_field_power", np.nan))
    far_power = float(data.get("diffraction_far_field_power", np.nan))
    peak = float(data.get("diffraction_peak_intensity", np.nan))
    bins = int(data.get("bins", 0) or 0)
    return [
        _result(
            layout,
            "diffraction detector uses explicit ray-event records for the active trace",
            int(data.get("sample_count", 0) or 0) == len(detector_records)
            and set(str(source) for source in data.get("analysis_sources", []) or []) == {"ray_events"},
            (
                f"samples={int(data.get('sample_count', 0) or 0)}, "
                f"records={len(detector_records)}, sources={sorted(set(str(source) for source in data.get('analysis_sources', []) or []))}"
            ),
        ),
        _result(
            layout,
            "diffraction detector returns a finite angular spectrum",
            intensity.shape == (bins, bins)
            and bins >= 8
            and np.all(np.isfinite(intensity))
            and peak > 0.0,
            f"shape={intensity.shape}, bins={bins}, peak={peak:.6g}",
        ),
        _result(
            layout,
            "diffraction detector angular axes are finite and ordered",
            angle_x.size == bins
            and angle_y.size == bins
            and np.all(np.isfinite(angle_x))
            and np.all(np.isfinite(angle_y))
            and np.all(np.diff(angle_x) > 0.0)
            and np.all(np.diff(angle_y) > 0.0),
            (
                f"x=[{float(angle_x[0]) if angle_x.size else np.nan:.6g}, "
                f"{float(angle_x[-1]) if angle_x.size else np.nan:.6g}] mrad, "
                f"y=[{float(angle_y[0]) if angle_y.size else np.nan:.6g}, "
                f"{float(angle_y[-1]) if angle_y.size else np.nan:.6g}] mrad"
            ),
        ),
        _result(
            layout,
            "diffraction detector conserves vector-field power under unitary FFT",
            np.isfinite(near_power)
            and np.isfinite(far_power)
            and near_power > 0.0
            and np.isclose(near_power, far_power, rtol=1e-9, atol=1e-12),
            f"near={near_power:.12g}, far={far_power:.12g}, diff={abs(near_power - far_power):.6g}",
        ),
        _result(
            layout,
            "diffraction detector uses coherent source-ray grouping",
            int(data.get("diffraction_group_count", 0) or 0) >= 2
            and str(data.get("coherence_mode", "")) == "By source ray",
            f"groups={int(data.get('diffraction_group_count', 0) or 0)}, mode={data.get('coherence_mode', '-')}",
        ),
        _result(
            layout,
            "extracted diffraction detector service matches UI wrapper",
            service_intensity.shape == intensity.shape
            and service_intensity.size > 0
            and np.allclose(service_intensity, intensity, rtol=0.0, atol=0.0)
            and np.allclose(
                np.asarray(service_data.get("angle_x_mrad", np.asarray([])), dtype=float),
                angle_x,
                rtol=0.0,
                atol=0.0,
            )
            and np.allclose(
                np.asarray(service_data.get("angle_y_mrad", np.asarray([])), dtype=float),
                angle_y,
                rtol=0.0,
                atol=0.0,
            )
            and float(service_data.get("diffraction_near_field_power", np.nan)) == near_power
            and float(service_data.get("diffraction_far_field_power", np.nan)) == far_power,
            f"shape={service_intensity.shape}, near={float(service_data.get('diffraction_near_field_power', np.nan)):.12g}, far={float(service_data.get('diffraction_far_field_power', np.nan)):.12g}",
        ),
    ]


def validate_diffraction_detector() -> list[DiffractionDetectorCheck]:
    checks: list[DiffractionDetectorCheck] = []
    checks.extend(_validate_layout("Michelson Interferometer (Interferogram)", ray_count=21, source_radius=10.0))
    checks.extend(_validate_layout("Mach-Zehnder Interferometer (Interferogram)", ray_count=11, source_radius=4.0))
    return checks


def _print_table(checks: list[DiffractionDetectorCheck]) -> None:
    print("KrakenOS diffraction-detector validation")
    print("layout | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.layout} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate detector angular-spectrum diffraction analysis.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_diffraction_detector()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
