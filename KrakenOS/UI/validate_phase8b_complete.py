from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from KrakenOS.UI.validate_branch_gaussian_q_report import validate_branch_gaussian_q_report
from KrakenOS.UI.validate_oblique_astigmatic_q import validate_oblique_astigmatic_q


@dataclass
class Phase8BValidationCheck:
    area: str
    check: str
    ok: bool
    detail: str


def _result(area: str, check: str, ok: bool, detail: str) -> Phase8BValidationCheck:
    return Phase8BValidationCheck(area=area, check=check, ok=bool(ok), detail=str(detail))


def validate_phase8b_complete() -> list[Phase8BValidationCheck]:
    checks: list[Phase8BValidationCheck] = []
    oblique_checks = validate_oblique_astigmatic_q()
    report_checks = validate_branch_gaussian_q_report()

    checks.extend(
        _result(
            "8B oblique astigmatic q",
            f"{check.case}: {check.check}",
            bool(check.ok),
            check.detail,
        )
        for check in oblique_checks
    )
    checks.extend(
        _result(
            "8B Gaussian q report",
            f"{check.layout}: {check.check}",
            bool(check.ok),
            check.detail,
        )
        for check in report_checks
    )

    flat_tilted_ok = any(
        check.case == "flat tilted plate" and bool(check.ok)
        for check in oblique_checks
    )
    tir_ok = any(
        check.case == "TIR diagnostic" and bool(check.ok)
        for check in oblique_checks
    )
    report_ok = all(bool(check.ok) for check in report_checks)
    checks.append(
        _result(
            "8B scope decision",
            "finite tilted plates remain q-only until full branch-field propagation",
            flat_tilted_ok and tir_ok and report_ok,
            (
                "flat_tilted_q_only={flat}, tir_deferred={tir}, report_exposes_notes={report}; "
                "full thick tilted-plate wave propagation is deferred beyond the Phase 8B q-contract scope"
            ).format(flat=flat_tilted_ok, tir=tir_ok, report=report_ok),
        )
    )
    return checks


def _print_table(checks: list[Phase8BValidationCheck]) -> None:
    print("KrakenOS Phase 8B validation")
    print("area | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.area} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 8B Gaussian q validation suite.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_phase8b_complete()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
