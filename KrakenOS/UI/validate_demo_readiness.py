"""Run a compact pre-demo readiness suite for the KrakenOS UI."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class DemoCheck:
    name: str
    command: tuple[str, ...]
    full_only: bool = False


@dataclass(frozen=True)
class DemoCheckResult:
    name: str
    ok: bool
    seconds: float
    detail: str


DEFAULT_CHECKS: tuple[DemoCheck, ...] = (
    DemoCheck(
        "embedded 3D interaction",
        ("-m", "KrakenOS.UI.validate_3d_interaction_contract"),
    ),
    DemoCheck(
        "STEP axis surface pick",
        ("-m", "KrakenOS.UI.validate_step_axis_surface_pick"),
    ),
    DemoCheck(
        "lens drawing PDF case study",
        ("-m", "KrakenOS.UI.validate_lens_drawing_pdf_case_study"),
    ),
    DemoCheck(
        "vendor prism CAD placement",
        ("-m", "KrakenOS.UI.validate_vendor_prism_42779"),
    ),
    DemoCheck(
        "3D hardware alignment case study",
        ("-m", "KrakenOS.UI.validate_3d_hardware_alignment_case_study"),
    ),
    DemoCheck(
        "branch analysis",
        ("-m", "KrakenOS.UI.validate_branch_analysis"),
    ),
    DemoCheck(
        "menu display smoke",
        ("-m", "KrakenOS.UI.validate_menu_smoke"),
        full_only=True,
    ),
    DemoCheck(
        "Sphinx documentation",
        ("-m", "sphinx", "-b", "html", "docs/source", "docs/build/html"),
        full_only=True,
    ),
)


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _last_line(text: object, limit: int = 180) -> str:
    text = _text(text)
    for line in reversed(text.splitlines()):
        clean = line.strip()
        if clean:
            return clean if len(clean) <= limit else f"{clean[: limit - 3]}..."
    return ""


def _run_check(check: DemoCheck, timeout: float, env: dict[str, str]) -> DemoCheckResult:
    command = (sys.executable, *check.command)
    start = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=Path(__file__).resolve().parents[2],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        seconds = time.monotonic() - start
        detail = _last_line(f"{_text(exc.stdout)}\n{_text(exc.stderr)}") or f"timeout after {timeout:g}s"
        return DemoCheckResult(check.name, False, seconds, detail)

    seconds = time.monotonic() - start
    detail = _last_line(completed.stdout) or _last_line(completed.stderr) or f"exit {completed.returncode}"
    return DemoCheckResult(check.name, completed.returncode == 0, seconds, detail)


def run_demo_readiness(*, full: bool = False, timeout: float = 240.0) -> list[DemoCheckResult]:
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", "/tmp/kraken-mpl-demo-readiness")
    checks = [check for check in DEFAULT_CHECKS if full or not check.full_only]
    return [_run_check(check, timeout=timeout, env=env) for check in checks]


def _print_table(results: Sequence[DemoCheckResult]) -> None:
    print("KrakenOS demo readiness")
    print("check | status | seconds | detail")
    print("--- | --- | --- | ---")
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"{result.name} | {status} | {result.seconds:.1f} | {result.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pre-demo KrakenOS UI checks.")
    parser.add_argument("--full", action="store_true", help="Include slower menu smoke and Sphinx documentation checks.")
    parser.add_argument("--timeout", type=float, default=240.0, help="Per-check timeout in seconds.")
    args = parser.parse_args()

    results = run_demo_readiness(full=bool(args.full), timeout=max(1.0, float(args.timeout)))
    _print_table(results)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
