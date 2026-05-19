"""Validate the native non-sequential architecture closure contract."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
from dataclasses import asdict, dataclass
from typing import Callable

from KrakenOS.UI.validate_interaction_accounting import main as validate_interaction_accounting_main
from KrakenOS.UI.validate_optical_solid_uncoated_interaction_fold import (
    validate_optical_solid_uncoated_interaction_fold,
)
from KrakenOS.UI.validate_phase6_complete import validate_phase6_complete
from KrakenOS.UI.validate_phase7_complete import validate_phase7_complete
from KrakenOS.UI.validate_phase8_complete import validate_phase8_complete
from KrakenOS.UI.validate_scene_sources import validate_scene_sources


@dataclass
class NativeNonSeqClosureCheck:
    area: str
    check: str
    ok: bool
    detail: str


CheckSuite = Callable[[], list[object]]


def _last_output_line(output: str) -> str:
    for line in reversed(str(output or "").splitlines()):
        clean = line.strip()
        if clean:
            return clean
    return ""


def _check_name(raw_check: object) -> str:
    parts: list[str] = []
    for attr in ("layout", "component", "path", "check"):
        text = str(getattr(raw_check, attr, "") or "").strip()
        if text:
            parts.append(text)
    return ": ".join(parts) if parts else raw_check.__class__.__name__


def _run_check_suite(area: str, suite: CheckSuite) -> list[NativeNonSeqClosureCheck]:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            raw_checks = suite()
    except Exception as exc:
        output = _last_output_line(buffer.getvalue())
        detail = str(exc)
        if output:
            detail = f"{detail}; output={output}"
        return [NativeNonSeqClosureCheck(area, suite.__name__, False, detail)]

    results: list[NativeNonSeqClosureCheck] = []
    for raw_check in raw_checks:
        raw_area = str(getattr(raw_check, "area", "") or "").strip()
        detail = str(getattr(raw_check, "detail", "") or "").strip()
        results.append(
            NativeNonSeqClosureCheck(
                area=f"{area}: {raw_area}" if raw_area else area,
                check=_check_name(raw_check),
                ok=bool(getattr(raw_check, "ok", False)),
                detail=detail,
            )
        )
    return results


def _run_main(area: str, check: str, func: Callable[[], object]) -> list[NativeNonSeqClosureCheck]:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            result = func()
    except SystemExit as exc:
        code = exc.code if exc.code is not None else 0
        ok = code == 0
        detail = _last_output_line(buffer.getvalue()) or f"SystemExit({code})"
        return [NativeNonSeqClosureCheck(area, check, ok, detail)]
    except Exception as exc:
        output = _last_output_line(buffer.getvalue())
        detail = str(exc)
        if output:
            detail = f"{detail}; output={output}"
        return [NativeNonSeqClosureCheck(area, check, False, detail)]
    detail = _last_output_line(buffer.getvalue()) or str(result or "completed")
    return [NativeNonSeqClosureCheck(area, check, True, detail)]


def validate_native_nonseq_closure() -> list[NativeNonSeqClosureCheck]:
    """Return the full native non-sequential North Star closure checks."""
    checks: list[NativeNonSeqClosureCheck] = []
    checks.extend(_run_check_suite("Phase 6 non-sequential first", validate_phase6_complete))
    checks.extend(_run_check_suite("Phase 7 scene refinement", validate_phase7_complete))
    checks.extend(_run_check_suite("Phase 8 branch fields", validate_phase8_complete))
    checks.extend(_run_check_suite("Scene source contract", validate_scene_sources))
    checks.extend(_run_check_suite("Uncoated interaction fold", validate_optical_solid_uncoated_interaction_fold))
    checks.extend(
        _run_main(
            "Event accounting",
            "per-hit physics, media, scattering, detector, and CSV accounting",
            validate_interaction_accounting_main,
        )
    )
    return checks


def _print_table(checks: list[NativeNonSeqClosureCheck]) -> None:
    passed = sum(1 for check in checks if check.ok)
    total = len(checks)
    print(f"KrakenOS native non-sequential closure validation ({passed}/{total} pass)")
    print("area | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.area} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the full native non-sequential North Star closure validation suite."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_native_nonseq_closure()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
