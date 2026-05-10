from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from KrakenOS.UI.validate_branch_gaussian_q_report import validate_branch_gaussian_q_report
from KrakenOS.UI.validate_oblique_astigmatic_q import validate_oblique_astigmatic_q
from KrakenOS.UI.validate_phase8_field_contract import validate_phase8_field_contract


@dataclass
class Phase8ValidationCheck:
    area: str
    check: str
    ok: bool
    detail: str


def validate_phase8_complete() -> list[Phase8ValidationCheck]:
    checks: list[Phase8ValidationCheck] = []
    checks.extend(
        Phase8ValidationCheck(
            area="8A branch field propagation",
            check=check.check,
            ok=bool(check.ok),
            detail=check.detail,
        )
        for check in validate_phase8_field_contract()
    )
    checks.extend(
        Phase8ValidationCheck(
            area="8B oblique astigmatic q",
            check=f"{check.case}: {check.check}",
            ok=bool(check.ok),
            detail=check.detail,
        )
        for check in validate_oblique_astigmatic_q()
    )
    checks.extend(
        Phase8ValidationCheck(
            area="8B Gaussian q report",
            check=f"{check.layout}: {check.check}",
            ok=bool(check.ok),
            detail=check.detail,
        )
        for check in validate_branch_gaussian_q_report()
    )
    return checks


def _print_table(checks: list[Phase8ValidationCheck]) -> None:
    print("KrakenOS Phase 8 validation")
    print("area | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.area} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 8 validation suite.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_phase8_complete()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
