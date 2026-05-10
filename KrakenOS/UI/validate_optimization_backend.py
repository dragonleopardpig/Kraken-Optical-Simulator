from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from queue import Empty

os.environ.setdefault("MPLCONFIGDIR", str(Path("/tmp/kraken-mpl")))

from KrakenOS.Optimization import EffectiveFocalLengthOperand, MeritFunction, OpticalVariable
from KrakenOS.Optimization.pygmo_backend import probe_pygmo_backend
from KrakenOS.UI.layout_editor import SurfaceRow, _run_optimization_job


@dataclass
class OptimizationBackendCheck:
    check: str
    ok: bool
    detail: str


def _smoke_rows() -> list[SurfaceRow]:
    return [
        SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
        SurfaceRow(
            surface="Standard",
            name="PCX front",
            rc=75.0,
            thickness=5.0,
            diameter=25.0,
            glass="BK7",
        ),
        SurfaceRow(
            surface="Standard",
            name="PCX back",
            rc=0.0,
            thickness=95.0,
            diameter=25.0,
            glass="AIR",
        ),
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
    ]


def _run_worker_smoke(timeout_s: float) -> tuple[list[dict[str, object]], int | None, bool]:
    rows = [asdict(row) for row in _smoke_rows()]
    merit = MeritFunction(
        operands=[
            EffectiveFocalLengthOperand(
                name="EFFL smoke",
                weight=1e-4,
                target=100.0,
                wavelength=0.55,
            )
        ]
    )
    variables = [OpticalVariable(1, "Rc", 40.0, 140.0, name="PCX front Rc")]
    x0 = [75.0]

    ctx = mp.get_context("spawn")
    progress_queue = ctx.Queue()
    stop_event = ctx.Event()
    process = ctx.Process(
        target=_run_optimization_job,
        args=(
            progress_queue,
            stop_event,
            rows,
            merit,
            variables,
            x0,
            1,
            0,
            6,
            1,
            False,
        ),
    )
    process.start()
    events: list[dict[str, object]] = []
    timed_out = False
    deadline = time.monotonic() + max(1.0, float(timeout_s))
    terminal_seen = False
    while time.monotonic() < deadline:
        try:
            payload = progress_queue.get(timeout=0.2)
        except Empty:
            payload = None
        if isinstance(payload, dict):
            events.append(payload)
            if payload.get("type") in {"complete", "error"}:
                terminal_seen = True
                break
        if not process.is_alive() and progress_queue.empty():
            break
    if not terminal_seen:
        timed_out = process.is_alive()
    if process.is_alive():
        try:
            stop_event.set()
        except Exception:
            pass
        process.join(timeout=1.0)
    if process.is_alive():
        process.terminate()
        process.join(timeout=2.0)
    else:
        process.join(timeout=2.0)
    return events, process.exitcode, timed_out


def validate_optimization_backend(timeout_s: float = 30.0) -> list[OptimizationBackendCheck]:
    probe_ok, probe_detail = probe_pygmo_backend()
    checks = [
        OptimizationBackendCheck(
            "pygmo backend imports in active environment",
            probe_ok,
            probe_detail,
        )
    ]
    if not probe_ok:
        return checks

    events, exitcode, timed_out = _run_worker_smoke(timeout_s)
    bootstrap = next((event for event in events if event.get("type") == "bootstrap"), {})
    complete = next((event for event in events if event.get("type") == "complete"), {})
    error = next((event for event in events if event.get("type") == "error"), {})
    initial = float(complete.get("initial_total", math.nan)) if complete else math.nan
    final = float(complete.get("final_total", math.nan)) if complete else math.nan

    checks.extend(
        [
            OptimizationBackendCheck(
                "optimization worker process exits cleanly",
                exitcode == 0 and not timed_out,
                f"exitcode={exitcode} timed_out={timed_out} events={len(events)}",
            ),
            OptimizationBackendCheck(
                "optimization worker emits bootstrap status",
                bool(bootstrap) and str(bootstrap.get("compute_backend", "")) == "sequential",
                f"backend={bootstrap.get('compute_backend', 'missing')} workers={bootstrap.get('workers', 'missing')}",
            ),
            OptimizationBackendCheck(
                "optimization worker completes without error event",
                bool(complete) and not error,
                str(error.get("message", "")) if error else f"complete={bool(complete)}",
            ),
            OptimizationBackendCheck(
                "optimization merit values are finite",
                math.isfinite(initial) and math.isfinite(final),
                f"initial={initial:.6g} final={final:.6g}",
            ),
            OptimizationBackendCheck(
                "one-generation pygmo run does not regress the seeded prescription",
                math.isfinite(initial) and math.isfinite(final) and final <= initial + 1e-9,
                f"initial={initial:.6g} final={final:.6g}",
            ),
        ]
    )
    return checks


def _print_table(checks: list[OptimizationBackendCheck]) -> None:
    print("KrakenOS optimization backend validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the UI optimization backend and spawned worker path.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Worker timeout in seconds.")
    args = parser.parse_args()

    checks = validate_optimization_backend(timeout_s=float(args.timeout))
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
