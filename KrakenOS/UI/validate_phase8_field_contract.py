from __future__ import annotations

import argparse
import csv
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.branch_field_analysis import (
    BRANCH_FIELD_CSV_COLUMNS,
    branch_field_analysis_data_from_coherent,
    iter_branch_field_csv_rows,
)
from KrakenOS.UI.validate_branch_analysis import _preferred_output_or_terminal_filter
from KrakenOS.UI.validate_diffraction_detector import _trace_dense_detector_bundle


@dataclass
class Phase8FieldContractCheck:
    check: str
    ok: bool
    detail: str


def _result(check: str, ok: bool, detail: str) -> Phase8FieldContractCheck:
    return Phase8FieldContractCheck(check=check, ok=bool(ok), detail=str(detail))


def _synthetic_field_checks() -> list[Phase8FieldContractCheck]:
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
    zero = Kos.propagate_branch_field(field, 0.0)
    propagated = Kos.propagate_branch_field(field, 250.0)
    same_overlap = Kos.gaussian_mode_overlap(field, waist_radius_mm=waist_mm)
    shifted_overlap = Kos.gaussian_mode_overlap(field, waist_radius_mm=waist_mm, center_x_mm=0.45)
    centroid_x, centroid_y = field.centroid_mm()
    return [
        _result(
            "TEM00 helper creates a finite normalized branch-field grid",
            field.shape == (128, 128)
            and np.all(np.isfinite(field.intensity))
            and abs(field.total_power - 1.0) < 1e-12
            and field.peak_intensity > 0.0,
            f"shape={field.shape}, power={field.total_power:.12g}, peak={field.peak_intensity:.6g}",
        ),
        _result(
            "BranchFieldGrid reports the intensity-weighted centroid",
            abs(centroid_x) < 1e-12 and abs(centroid_y) < 1e-12,
            f"centroid=({centroid_x:.6g}, {centroid_y:.6g}) mm",
        ),
        _result(
            "zero-distance scalar propagation leaves the sampled field unchanged",
            np.max(np.abs(zero.field - field.field)) < 1e-12
            and abs(zero.total_power - field.total_power) < 1e-12,
            f"maxdiff={float(np.max(np.abs(zero.field - field.field))):.6g}, power={zero.total_power:.12g}",
        ),
        _result(
            "paraxial scalar propagation conserves discrete field power",
            abs(propagated.total_power - field.total_power) < 1e-12
            and propagated.second_moment_radius_mm() > field.second_moment_radius_mm(),
            (
                f"input={field.total_power:.12g}, propagated={propagated.total_power:.12g}, "
                f"radius={field.second_moment_radius_mm():.6g}->{propagated.second_moment_radius_mm():.6g}"
            ),
        ),
        _result(
            "Gaussian mode-overlap returns unity for a matched mode",
            same_overlap.efficiency > 1.0 - 1e-12
            and abs(same_overlap.field_power - 1.0) < 1e-12
            and abs(same_overlap.mode_power - 1.0) < 1e-12,
            f"eff={same_overlap.efficiency:.12g}, phase={same_overlap.phase_rad:.6g}",
        ),
        _result(
            "Gaussian mode-overlap drops for a laterally shifted reference",
            0.0 < shifted_overlap.efficiency < 0.9,
            f"shifted_eff={shifted_overlap.efficiency:.12g}",
        ),
    ]


def _detector_field_checks() -> list[Phase8FieldContractCheck]:
    editor, system, rays, wavelength = _trace_dense_detector_bundle(
        "Michelson Interferometer (Interferogram)",
        ray_count=21,
        source_radius=10.0,
    )
    filter_text = _preferred_output_or_terminal_filter(editor)
    ray_records = editor._ray_analysis_records_for_trace(system=system, rays=rays)
    data = editor._coherent_detector_field_data(system, wavelength, filter_text, ray_records=ray_records)
    data = dict(data)
    data["wavelength_um"] = float(wavelength)
    grid = Kos.branch_field_from_detector_data(data, component="field_x")
    propagated = Kos.propagate_branch_field(grid, 10.0)
    expected_power = float(np.sum(np.abs(np.asarray(data["field_x"], dtype=np.complex128)) ** 2))
    branch_field_data = editor._branch_field_analysis_data(system, wavelength, filter_text, ray_records=ray_records)
    service_branch_field_data = branch_field_analysis_data_from_coherent(
        data,
        wavelength_um=wavelength,
        propagation_mm=editor._current_branch_field_propagation_mm(),
    )
    editor.branch_field_propagation_mm_var.set("25.0")
    propagated_branch_field_data = editor._branch_field_analysis_data(system, wavelength, filter_text, ray_records=ray_records)
    service_csv_rows = list(iter_branch_field_csv_rows(propagated_branch_field_data, wavelength))
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "branch_field.csv"
        editor._write_branch_field_csv(csv_path, propagated_branch_field_data, wavelength)
        with open(csv_path, newline="", encoding="utf-8") as handle:
            csv_rows = list(csv.DictReader(handle))
    return [
        _result(
            "UI branch-field analysis uses explicit ray-event records for the active trace",
            set(str(source) for source in branch_field_data.get("analysis_sources", []) or []) == {"ray_events"}
            and int(branch_field_data.get("sample_count", 0) or 0) == int(data.get("sample_count", 0) or 0),
            (
                f"samples={int(branch_field_data.get('sample_count', 0) or 0)}, "
                f"sources={sorted(set(str(source) for source in branch_field_data.get('analysis_sources', []) or []))}"
            ),
        ),
        _result(
            "coherent detector data converts to the Phase 8 branch-field contract",
            grid.shape == (int(data["bins"]), int(data["bins"]))
            and int(grid.metadata.get("sample_count", 0) or 0) == int(data.get("sample_count", 0) or 0)
            and abs(grid.total_power - expected_power) < 1e-12,
            (
                f"shape={grid.shape}, samples={grid.metadata.get('sample_count')}, "
                f"component={grid.component}, power={grid.total_power:.12g}"
            ),
        ),
        _result(
            "detector-derived branch field propagates without changing power",
            abs(propagated.total_power - grid.total_power) < 1e-12
            and propagated.shape == grid.shape
            and float(propagated.z_mm) == 10.0,
            f"input={grid.total_power:.12g}, propagated={propagated.total_power:.12g}, z={propagated.z_mm:.6g}",
        ),
        _result(
            "UI branch-field analysis exposes intensity phase and TEM00 overlap",
            np.asarray(branch_field_data["branch_field_intensity"]).shape == grid.shape
            and np.asarray(branch_field_data["branch_field_phase_rad"]).shape == grid.shape
            and 0.0 <= float(branch_field_data["branch_field_tem00_overlap_efficiency"]) <= 1.0 + 1e-12
            and float(branch_field_data["branch_field_total_power"]) > 0.0,
            (
                f"power={float(branch_field_data['branch_field_total_power']):.12g}, "
                f"overlap={float(branch_field_data['branch_field_tem00_overlap_efficiency']):.6g}, "
                f"waist={float(branch_field_data['branch_field_tem00_waist_mm']):.6g}"
            ),
        ),
        _result(
            "UI branch-field analysis applies requested propagation distance",
            abs(float(propagated_branch_field_data["branch_field_propagation_mm"]) - 25.0) < 1e-12
            and abs(
                float(propagated_branch_field_data["branch_field_total_power"])
                - float(propagated_branch_field_data["branch_field_source_power"])
            )
            < 1e-9,
            (
                f"z={float(propagated_branch_field_data['branch_field_propagation_mm']):.6g}, "
                f"source={float(propagated_branch_field_data['branch_field_source_power']):.12g}, "
                f"propagated={float(propagated_branch_field_data['branch_field_total_power']):.12g}"
            ),
        ),
        _result(
            "extracted branch-field service matches UI wrapper",
            np.allclose(
                np.asarray(service_branch_field_data["branch_field_intensity"], dtype=float),
                np.asarray(branch_field_data["branch_field_intensity"], dtype=float),
                rtol=0.0,
                atol=0.0,
            )
            and np.allclose(
                np.asarray(service_branch_field_data["branch_field_phase_rad"], dtype=float),
                np.asarray(branch_field_data["branch_field_phase_rad"], dtype=float),
                rtol=0.0,
                atol=0.0,
            )
            and float(service_branch_field_data["branch_field_total_power"])
            == float(branch_field_data["branch_field_total_power"])
            and float(service_branch_field_data["branch_field_tem00_overlap_efficiency"])
            == float(branch_field_data["branch_field_tem00_overlap_efficiency"]),
            (
                f"power={float(service_branch_field_data['branch_field_total_power']):.12g}, "
                f"overlap={float(service_branch_field_data['branch_field_tem00_overlap_efficiency']):.6g}"
            ),
        ),
        _result(
            "Branch-field CSV export writes one row per field bin",
            len(csv_rows) == int(propagated_branch_field_data["bins"]) ** 2
            and "field_real" in (csv_rows[0] if csv_rows else {})
            and "phase_rad" in (csv_rows[0] if csv_rows else {})
            and "tem00_overlap_efficiency" in (csv_rows[0] if csv_rows else {})
            and len(service_csv_rows) == len(csv_rows)
            and bool(service_csv_rows)
            and tuple(service_csv_rows[0].keys()) == BRANCH_FIELD_CSV_COLUMNS,
            (
                f"rows={len(csv_rows)}, service_rows={len(service_csv_rows)}, "
                f"columns={len(BRANCH_FIELD_CSV_COLUMNS)}, bins={int(propagated_branch_field_data['bins'])}"
            ),
        ),
    ]


def validate_phase8_field_contract() -> list[Phase8FieldContractCheck]:
    checks: list[Phase8FieldContractCheck] = []
    checks.extend(_synthetic_field_checks())
    checks.extend(_detector_field_checks())
    return checks


def _print_table(checks: list[Phase8FieldContractCheck]) -> None:
    print("KrakenOS Phase 8 branch-field contract validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the first Phase 8 branch-field data contract.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_phase8_field_contract()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
