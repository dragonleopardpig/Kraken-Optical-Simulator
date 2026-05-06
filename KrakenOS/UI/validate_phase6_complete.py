from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
from dataclasses import asdict, dataclass

from KrakenOS.UI.validate_branch_analysis import validate_branch_analysis
from KrakenOS.UI.validate_multi_scene_sources import validate_multi_scene_sources
from KrakenOS.UI.validate_phase6_path_workbench import validate_path_workbench
from KrakenOS.UI.validate_scene_row_mapping import validate_scene_row_mapping
from KrakenOS.UI.validate_scene_source_row_contract import validate_scene_source_row_contract


@dataclass
class Phase6ValidationCheck:
    area: str
    check: str
    ok: bool
    detail: str


def _stl_prism_media_check() -> Phase6ValidationCheck:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            module = importlib.import_module("KrakenOS.UI.validate_stl_prism_media")
            module.main()
    except Exception as exc:
        output = buffer.getvalue().strip()
        detail = f"{exc}"
        if output:
            detail = f"{detail}; output={output}"
        return Phase6ValidationCheck("STL optical solid", "media/refraction", False, detail)
    lines = [line.strip() for line in buffer.getvalue().splitlines() if line.strip()]
    detail = lines[-1] if lines else "STL prism media validation completed"
    return Phase6ValidationCheck("STL optical solid", "media/refraction", True, detail)


def validate_phase6_complete() -> list[Phase6ValidationCheck]:
    checks: list[Phase6ValidationCheck] = []
    checks.append(_stl_prism_media_check())
    checks.extend(
        Phase6ValidationCheck(
            "Path workbench",
            f"{check.component} / {check.path}",
            bool(check.ok),
            check.detail,
        )
        for check in validate_path_workbench()
    )
    checks.extend(
        Phase6ValidationCheck(
            "Branch analysis",
            f"{check.layout}: {check.check}",
            bool(check.ok),
            f"{check.filter}: {check.detail}",
        )
        for check in validate_branch_analysis()
    )
    checks.extend(
        Phase6ValidationCheck(
            "Scene sources",
            check.check,
            bool(check.ok),
            check.detail,
        )
        for check in validate_multi_scene_sources()
    )
    checks.extend(
        Phase6ValidationCheck(
            "Scene source rows",
            check.check,
            bool(check.ok),
            check.detail,
        )
        for check in validate_scene_source_row_contract()
    )
    checks.extend(
        Phase6ValidationCheck(
            "Scene row mapping",
            check.check,
            bool(check.ok),
            str(check.detail),
        )
        for check in validate_scene_row_mapping()
    )
    return checks


def _print_table(checks: list[Phase6ValidationCheck]) -> None:
    print("KrakenOS Phase 6 completion validation")
    print("area | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.area} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Phase 6 non-sequential-first closure validation suite."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_phase6_complete()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
