from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

from KrakenOS.UI.branch_gaussian_q_report import (
    BRANCH_GAUSSIAN_Q_CSV_COLUMNS,
    branch_gaussian_q_report_text,
    collect_branch_gaussian_q_records,
)
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor


@dataclass
class BranchGaussianQReportCheck:
    layout: str
    check: str
    ok: bool
    detail: str


def _result(layout: str, check: str, ok: bool, detail: str) -> BranchGaussianQReportCheck:
    return BranchGaussianQReportCheck(layout=layout, check=check, ok=bool(ok), detail=str(detail))


def _validate_layout(title: str) -> list[BranchGaussianQReportCheck]:
    editor, _system, _rays, wavelength = _load_traced_editor(title)
    ray_records = editor._collect_ray_analysis_records()
    source_model = editor._current_source_model()
    beam = editor._branch_gaussian_q_input_beam(wavelength)
    service_rows, service_summary = collect_branch_gaussian_q_records(
        ray_records,
        surfaces=editor.rows,
        beam=beam,
        wavelength_um=wavelength,
        source_model=source_model,
    )
    service_report_text = branch_gaussian_q_report_text(service_rows, service_summary)
    rows, summary = editor._collect_branch_gaussian_q_records(wavelength=wavelength)
    report_text = editor._branch_gaussian_q_report_text()
    notes = {str(row.get("note", "")) for row in rows}
    finite_rows = [
        row
        for row in rows
        if np.isfinite(float(row.get("tangential_q_real_mm", np.nan)))
        and np.isfinite(float(row.get("tangential_q_imag_mm", np.nan)))
        and np.isfinite(float(row.get("sagittal_q_real_mm", np.nan)))
        and np.isfinite(float(row.get("sagittal_q_imag_mm", np.nan)))
    ]
    final_rows = [row for row in rows if bool(row.get("trace_final", False))]
    records_with_hits = [record for record in ray_records if list(record.get("hits", []) or [])]
    return [
        _result(
            title,
            "Branch Gaussian q report uses canonical ray events",
            bool(records_with_hits)
            and all(str(record.get("analysis_source", "") or "") == "ray_events" for record in records_with_hits),
            f"sources={sorted({str(record.get('analysis_source', '') or '') for record in records_with_hits})}",
        ),
        _result(
            title,
            "Branch Gaussian q report produces per-hit rows",
            len(rows) > 0
            and int(summary.get("trace_count", 0) or 0) > 0
            and int(summary.get("failure_count", 0) or 0) == 0,
            (
                f"rows={len(rows)}, traces={int(summary.get('trace_count', 0) or 0)}, "
                f"stable={int(summary.get('stable_count', 0) or 0)}, failures={int(summary.get('failure_count', 0) or 0)}"
            ),
        ),
        _result(
            title,
            "Branch Gaussian q report includes surface-power diagnostics",
            "oblique spherical refraction" in notes
            and "near-normal spherical refraction" in notes
            and int(summary.get("diagnostic_count", 0) or 0) >= 0,
            f"notes={sorted(notes)}",
        ),
        _result(
            title,
            "Branch Gaussian q report rows carry finite astigmatic q states",
            len(finite_rows) == len(rows) and len(final_rows) > 0,
            f"finite={len(finite_rows)}/{len(rows)}, final_rows={len(final_rows)}",
        ),
        _result(
            title,
            "Branch Gaussian q report text is copy/export ready",
            "KrakenOS Branch Gaussian Q Report" in report_text
            and "oblique spherical refraction" in report_text,
            f"chars={len(report_text)}",
        ),
        _result(
            title,
            "extracted Branch Gaussian q service matches UI wrapper",
            service_rows == rows
            and service_summary == summary
            and service_report_text == branch_gaussian_q_report_text(rows, summary),
            f"service_rows={len(service_rows)}, ui_rows={len(rows)}, service_chars={len(service_report_text)}",
        ),
        _result(
            title,
            "Branch Gaussian q CSV contract is service-owned",
            bool(rows)
            and set(rows[0]).issubset(set(BRANCH_GAUSSIAN_Q_CSV_COLUMNS))
            and "trace_final" in BRANCH_GAUSSIAN_Q_CSV_COLUMNS,
            f"columns={len(BRANCH_GAUSSIAN_Q_CSV_COLUMNS)}, row_keys={len(rows[0]) if rows else 0}",
        ),
    ]


def validate_branch_gaussian_q_report() -> list[BranchGaussianQReportCheck]:
    return _validate_layout("Galvo F-Theta Laser Scanner")


def _print_table(checks: list[BranchGaussianQReportCheck]) -> None:
    print("KrakenOS Branch Gaussian q report validation")
    print("layout | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.layout} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the UI Branch Gaussian q report/export data contract.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_branch_gaussian_q_report()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
