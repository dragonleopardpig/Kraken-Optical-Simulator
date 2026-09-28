#!/usr/bin/env python3
"""Run the full penta-telescope suite as parallel SHARDS and gate the merged result.

The comprehensive validator runs every phase in ONE Python/VTK process -- effectively one
core, ~2.5 h for ~700 phases, and a process that grows past 8 GB. This splits the phases into
N contiguous ranges and runs each range as its own validator process on its own virtual
display, at the same time, then merges the phase states and applies the SAME baseline
comparison as ``tools/penta_validator_gate.py`` (whose functions it reuses).

Ranges stay CONTIGUOUS and in order, so a phase still runs after the phases before it in its
shard -- the closest a shard gets to the full run's order. They are balanced by each phase's
measured seconds from the last detailed log when one is available (the tail phases are far
slower than the rest), else by count.

Every shard must REPORT: a shard that crashes or parses nothing fails the whole run loudly
(the day-1 sequential runner once dropped a shard silently -- memory note). Phases absent from
the merged run count as regressions exactly as in the single-process gate.

Usage:
    python tools/penta_shard_gate.py                 # auto shard count (memory-capped)
    python tools/penta_shard_gate.py --shards 4
    python tools/penta_shard_gate.py --update-baseline
    python tools/penta_shard_gate.py --dry-run       # show the plan only

Run it inside ``devenv shell`` (Nix binaries), like the gate.
Exit: 0 = every shard reported and no PASS->FAIL regression; 1 otherwise.
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import penta_validator_gate as gate  # noqa: E402

VALIDATOR_SOURCE = gate.REPO_ROOT / "KrakenOS" / "UI" / "validate_open3d_penta_telescope_comprehensive.py"
PHASE_NAME_RE = re.compile(r"^\s+phase_(\d+)_[A-Za-z0-9_]+,\s*$", re.M)
SECONDS_RE = re.compile(r"^\s*\[(?:PASS|FAIL)\]\s+Phase\s+(\d+)\s*:.*?$\n(?:(?!\s*\[(?:PASS|FAIL)\]).*\n)*?\s*seconds:\s*([0-9.]+)", re.M)
#: GB a shard is budgeted for. Measured 2026-09-28: a shard's validator reaches ~6 GB, and the
#: tail shard also runs isolated child apps (run_module_isolated, several GB each) while its
#: parent waits. 4 GB/shard let 4 shards exhaust a 30 GB machine with NO swap -- the kernel
#: OOM killer fired and the desktop session was logged out.
GB_PER_SHARD = 7.0
#: The watchdog stops every shard when available memory drops below this, so a heavy run
#: fails loudly instead of taking the desktop session with it.
MIN_AVAILABLE_GB = 3.0
#: The shard runner's OWN timings, rewritten only by a complete sharded run. The single gate's
#: log is also rewritten by every --phases smoke run, which left a 2-phase log to balance by
#: and a 70-minute count-balanced run (2026-09-28).
TIMINGS_LOG = Path(tempfile.gettempdir()) / "penta_shard_timings.log"


def suite_phases() -> list[int]:
    """Every phase number in the validator's run list, in run order."""
    text = VALIDATOR_SOURCE.read_text(encoding="utf-8")
    seen: list[int] = []
    for match in PHASE_NAME_RE.finditer(text):
        number = int(match.group(1))
        if number not in seen:
            seen.append(number)
    return sorted(seen)


def phase_seconds(log_path: Path) -> dict[int, float]:
    """Per-phase seconds from a previous detailed log, if any."""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    return {int(num): float(sec) for num, sec in SECONDS_RE.findall(text)}


def plan_shards(phases: list[int], count: int, seconds: dict[int, float]) -> list[list[int]]:
    """Contiguous ranges of roughly equal cost (measured seconds, else one unit per phase)."""
    count = max(1, min(count, len(phases)))
    known = [seconds[p] for p in phases if p in seconds]
    fallback = (sum(known) / len(known)) if known else 1.0
    cost = [max(seconds.get(p, fallback), 0.01) for p in phases]
    target = sum(cost) / count
    shards: list[list[int]] = [[]]
    acc = 0.0
    for phase, c in zip(phases, cost):
        if acc >= target and len(shards) < count:
            shards.append([])
            acc = 0.0
        shards[-1].append(phase)
        acc += c
    return [s for s in shards if s]


def available_gb() -> float:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024 / 1024
    except OSError:
        pass
    return 8.0


def _descendants(root: int) -> list[int]:
    """Every live descendant pid of ``root`` (read from /proc; no psutil)."""
    children: dict[int, list[int]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            children.setdefault(int(fields[1]), []).append(int(entry.name))
        except (OSError, IndexError, ValueError):
            continue
    found, stack = [], [root]
    while stack:
        for child in children.get(stack.pop(), []):
            found.append(child)
            stack.append(child)
    return found


class MemoryWatchdog(threading.Thread):
    """Kill every descendant process when MemAvailable falls below ``floor_gb``."""

    def __init__(self, floor_gb: float, interval: float = 2.0) -> None:
        super().__init__(daemon=True)
        self.floor_gb = float(floor_gb)
        self.interval = float(interval)
        self.tripped_at_gb: float | None = None
        self.lowest_gb = float("inf")
        self._stop = threading.Event()

    def run(self) -> None:
        while not self._stop.wait(self.interval):
            available = available_gb()
            self.lowest_gb = min(self.lowest_gb, available)
            if available >= self.floor_gb:
                continue
            self.tripped_at_gb = available
            print(f"[shards] MEMORY WATCHDOG: {available:.1f} GB available < {self.floor_gb:g} GB "
                  "-- stopping every shard", file=sys.stderr, flush=True)
            for pid in reversed(_descendants(os.getpid())):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
            return

    def stop(self) -> None:
        self._stop.set()


def silent_shards(results, shards) -> list[int]:
    """Shards that reported none of their phases (crashed / env error)."""
    out = []
    for index, _code, states, env_error, _elapsed in results:
        if env_error or not (set(states) & {str(p) for p in shards[index]}):
            out.append(index)
    return out


def free_displays(count: int, start: int = 110) -> list[int]:
    out, num = [], start
    while len(out) < count:
        if not Path(f"/tmp/.X11-unix/X{num}").exists():
            out.append(num)
        num += 1
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--shards", type=int, default=None, help="shard count (default: memory-capped, max 4)")
    parser.add_argument("--min-available-gb", type=float, default=MIN_AVAILABLE_GB,
                        help="stop every shard when available memory falls below this (default %(default)s)")
    parser.add_argument("--baseline", type=Path, default=gate.DEFAULT_BASELINE)
    parser.add_argument("--update-baseline", action="store_true",
                        help="write the merged states as the baseline (only if EVERY shard reported)")
    parser.add_argument("--timings-log", type=Path, default=TIMINGS_LOG,
                        help="a previous detailed log to balance shards by measured seconds")
    parser.add_argument("--timeout", type=int, default=10800)
    parser.add_argument("--python", default=None)
    parser.add_argument("--dry-run", action="store_true", help="print the shard plan and exit")
    args = parser.parse_args(argv)

    phases = suite_phases()
    if not phases:
        print(f"[shards] no phases found in {VALIDATOR_SOURCE}", file=sys.stderr)
        return 1
    memory_cap = max(1, int(available_gb() // GB_PER_SHARD))
    count = args.shards if args.shards else min(4, memory_cap)
    if args.shards and args.shards > memory_cap:
        print(f"[shards] WARNING: {args.shards} shards but only ~{available_gb():.1f} GB available "
              f"(~{GB_PER_SHARD:g} GB each) -- the desktop may stall")
    seconds = phase_seconds(args.timings_log)
    shards = plan_shards(phases, count, seconds)
    print(f"[shards] {len(phases)} phases -> {len(shards)} shard(s) "
          f"({'balanced by measured seconds' if seconds else 'balanced by count'})")
    for index, shard in enumerate(shards):
        est = sum(seconds.get(p, 0.0) for p in shard)
        print(f"[shards]   shard {index}: phases {shard[0]}-{shard[-1]} ({len(shard)})"
              + (f", ~{est / 60:.0f} min measured" if seconds else ""))
    if args.dry_run:
        return 0

    interpreter = gate._find_interpreter(args.python)
    if interpreter is None:
        print("[shards] no usable Python interpreter", file=sys.stderr)
        return 1
    displays = free_displays(len(shards))
    log_dir = Path(tempfile.mkdtemp(prefix="penta_shards_"))

    def run_one(index: int):
        shard = shards[index]
        started = time.time()
        code, states, env_error = gate.run_validator(
            interpreter=interpreter, display=displays[index], timeout=args.timeout,
            log_path=log_dir / f"shard_{index}.log", phases=",".join(str(p) for p in shard))
        return index, code, states, env_error, time.time() - started

    started = time.time()
    watchdog = MemoryWatchdog(args.min_available_gb)
    watchdog.start()
    with ThreadPoolExecutor(max_workers=len(shards)) as pool:
        results = sorted(pool.map(run_one, range(len(shards))))
    watchdog.stop()
    print(f"[shards] lowest available memory during the run: {watchdog.lowest_gb:.1f} GB")
    if watchdog.tripped_at_gb is not None:
        print(f"[shards] FAILED -- the memory watchdog stopped the run at {watchdog.tripped_at_gb:.1f} GB "
              "available; rerun with fewer --shards", file=sys.stderr)
        return 1

    merged: dict[str, dict[str, str]] = {}
    silent: list[int] = []
    for index, code, states, env_error, elapsed in results:
        shard = shards[index]
        expected = {str(p) for p in shard}
        got = set(states) & expected
        passed = sum(1 for n in got if states[n]["status"] == "pass")
        failed = sum(1 for n in got if states[n]["status"] == "fail")
        missing = len(expected - got)
        note = f" ENV: {env_error}" if env_error else ""
        print(f"[shards] shard {index} ({shard[0]}-{shard[-1]}): {passed} pass, {failed} fail, "
              f"{missing} missing, exit {code}, {elapsed / 60:.1f} min{note}")
        if env_error or not got:
            silent.append(index)
        merged.update({n: states[n] for n in got})
    # the full-suite logs, joined, where the single gate leaves its log
    joined = "\n".join((log_dir / f"shard_{i}.log").read_text(encoding="utf-8", errors="replace")
                       for i in range(len(shards)) if (log_dir / f"shard_{i}.log").exists())
    (Path(tempfile.gettempdir()) / "penta_validator_last.log").write_text(joined, encoding="utf-8")
    if not silent_shards(results, shards) and watchdog.tripped_at_gb is None:
        TIMINGS_LOG.write_text(joined, encoding="utf-8")
    print(f"[shards] wall time {(time.time() - started) / 60:.1f} min; logs in {log_dir}")

    if silent:
        print(f"[shards] FAILED -- shard(s) {silent} reported no phases; the run is incomplete",
              file=sys.stderr)
        return 1

    passed = sum(1 for s in merged.values() if s["status"] == "pass")
    failed = sum(1 for s in merged.values() if s["status"] == "fail")
    print(f"[gate] phases: {passed} pass, {failed} fail (merged from {len(shards)} shards)")

    if args.update_baseline:
        gate.write_baseline(args.baseline, merged)
        print(f"[gate] baseline written to {args.baseline}")
        return 0

    baseline = gate.load_baseline(args.baseline)
    regressions, fixed, still_failing = gate.compare(baseline, merged)
    for num in fixed:
        print(f"[gate]   fixed: Phase {num} ({merged.get(num, {}).get('title', '')})")
    for num in still_failing:
        print(f"[gate]   known-failing (allowed): Phase {num} ({merged.get(num, {}).get('title', '')})")
    if regressions:
        print("[gate] BLOCKED -- new failure(s) vs baseline:", file=sys.stderr)
        for num in regressions:
            title = merged.get(num, {}).get("title", "(phase missing from run)")
            print(f"[gate]   REGRESSED: Phase {num}: {title}", file=sys.stderr)
        return 1
    print("[gate] OK -- no PASS->FAIL regressions. Push allowed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
