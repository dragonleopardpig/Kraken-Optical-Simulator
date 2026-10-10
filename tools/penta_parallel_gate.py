#!/usr/bin/env python3
"""Run the penta-telescope suite as many small GROUPS, several at a time (bugs/0956).

`tools/penta_shard_gate.py` splits the suite into a few big shards and budgets 7 GB for each -- the
size one long-lived validator process grows to. On a 14 GB machine that budget allows one shard, so
the sharded gate cannot run in parallel there at all, and the sequential gate uses one core of
fourteen for almost two hours.

This runner takes the other road: MANY small contiguous groups. A group's validator process is
young when it ends, so it stays small (measured 2026-10-04 on M90aPro: most groups of ~60 phases
peak at 2-3 GB), and several fit side by side. What keeps it safe is not a budget guessed in
advance but the machine's own free memory:

  * admission -- a group starts only while `MemAvailable` is above `--start-gb` (and there is a
    free worker slot); with nothing running, the next one always starts;
  * watchdog -- if `MemAvailable` falls under `--min-gb`, the group started LAST is killed and
    queued again (it starts once there is clear room for it), so a heavy coincidence -- another
    program taking 3 GB mid-run did exactly that on the first run -- costs a re-run, not the
    desktop session.

Each group is one `penta_validator_gate.py --phases a-b` run: its own virtual display (passed
explicitly, so two groups cannot pick the same one), its own temp directory (the gate's log and
the validators' scratch files do not collide), and its own cores. Results are compared to the
baseline by the gate itself; this runner only adds them up. It never writes the baseline: a phase
that needs recording is re-run through the single gate with `--update-baseline`.

BOTH INTERFACES (bugs/1001, docs/design_qt_migration.md phase 7g). There are two suites, each with
its own baseline: every phase on the Tk interface, and the harness's own phases run again with the
3D inspector hosted in the Qt shell (`penta_validator_gate.py --shell qt`). "The full gate" used
to mean the first only, and the second was run by hand, rarely. One run does both now -- the Qt
groups are queued after the Tk ones and reported beside them -- unless `--shell tk` or `--shell qt`
asks for one.

Usage (inside `devenv shell`, like the gate):
    python tools/penta_parallel_gate.py                    # both interfaces, 3 groups at a time
    python tools/penta_parallel_gate.py --jobs 4
    python tools/penta_parallel_gate.py --shell tk         # the Tk suite only, as before bugs/1001
    python tools/penta_parallel_gate.py --phases 633-727   # part of it (of each suite that has it)
    python tools/penta_parallel_gate.py --dry-run          # show the groups only

Exit: 0 = every group reported and none had a PASS->FAIL regression; 1 otherwise.
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE = REPO_ROOT / "tools" / "penta_validator_gate.py"
#: the suite hosted in the Qt shell is the phases its own baseline holds: the harness's
QT_BASELINE = REPO_ROOT / "tools" / "penta_validator_baseline_qt.json"
#: interface -> what the reports call it
SHELLS = {"tk": "Tk", "qt": "Qt-hosted"}
VALIDATOR_SOURCE = REPO_ROOT / "KrakenOS" / "UI" / "validate_open3d_penta_telescope_comprehensive.py"
PHASE_NAME_RE = re.compile(r"^\s+phase_(\d+)_[A-Za-z0-9_]+,\s*$", re.M)
RESULT_RE = re.compile(r"\[gate\] phases: (\d+) pass, (\d+) fail")
#: (first phase of a band, phases per group). The early phases take ~3 s each; the slow ones --
#: the solves around 448-474 and the Qt shell guards, each its own subprocess -- take 50-130 s. A
#: slow band therefore gets SMALL groups, or one worker holds the whole run. Measured on the first
#: parallel run (2026-10-04, M90aPro, 4 at a time, 44.5 min for 726 phases): 448-474 took 1409 s
#: as one group of 27, 689-696 took 1077 s as one group of 8, 721-727 took 746 s as one of 7.
BANDS = ((0, 60), (421, 9), (526, 60), (633, 8), (689, 4))
#: the first display number handed out; each group gets its own, counting up
FIRST_DISPLAY = 140


def available_gb() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / (1024 * 1024)
    return 0.0


def all_phases() -> list[int]:
    """Every phase number the comprehensive validator runs, ascending."""
    return sorted({int(number) for number in PHASE_NAME_RE.findall(VALIDATOR_SOURCE.read_text(encoding="utf-8"))})


def qt_hosted_phases() -> list[int]:
    """The phases that are run again hosted in the Qt shell: the ones the Qt baseline records."""
    import json

    try:
        recorded = json.loads(QT_BASELINE.read_text(encoding="utf-8")).get("phases", {})
    except (OSError, ValueError):
        return []
    known = set(all_phases())
    return sorted(int(number) for number in recorded if int(number) in known)


def parse_phases(spec: "str | None", known: list[int]) -> list[int]:
    if not spec:
        return list(known)
    wanted: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            low, high = part.split("-", 1)
            wanted.update(range(int(low), int(high) + 1))
        elif part:
            wanted.add(int(part))
    return [phase for phase in known if phase in wanted]


def parse_cpu_list(spec: str) -> list[int]:
    """"0-5,8-13" or "0,8,1,9" -> the CPUs, in the order given."""
    cpus: list[int] = []
    for part in str(spec).split(","):
        part = part.strip()
        if "-" in part:
            low, high = part.split("-", 1)
            cpus.extend(range(int(low), int(high) + 1))
        elif part:
            cpus.append(int(part))
    return cpus


def physical_cores() -> list[list[int]]:
    """The CPUs grouped by physical core -- hyperthread siblings together -- in core order. On
    X299-SSD (i7-7820X) CPU N and N+8 are ONE core: groups handed "two cores" that were siblings
    each got about one, and the run took 90 min instead of ~45 (bugs/0961)."""
    cores: dict = {}
    for path in Path("/sys/devices/system/cpu").glob("cpu[0-9]*/topology/thread_siblings_list"):
        try:
            siblings = tuple(parse_cpu_list(path.read_text().strip()))
        except (OSError, ValueError):
            continue
        cores.setdefault(siblings, None)
    if not cores:
        return [[cpu] for cpu in range(os.cpu_count() or 4)]
    return [list(siblings) for siblings in sorted(cores)]


def core_sets_for(jobs: int, cores_spec: "str | None") -> list[str]:
    """Each group's CPUs. Given ``--cores``, its CPUs in the order given, dealt out in equal runs.
    Otherwise whole physical cores per group (both threads of each), leaving the last physical
    core(s) -- at least two CPUs -- for the desktop."""
    if cores_spec:
        cpus = parse_cpu_list(cores_spec)
        jobs = max(1, min(int(jobs), len(cpus)))
        per_job = len(cpus) // jobs
        return [",".join(str(cpu) for cpu in cpus[slot * per_job:(slot + 1) * per_job]) for slot in range(jobs)]
    physical = physical_cores()
    spare = 0
    while physical and spare < 2 and len(physical) > 1:
        spare += len(physical.pop())
    jobs = max(1, min(int(jobs), len(physical)))
    sets, start = [], 0
    for slot in range(jobs):                    # the remainder goes one core each to the first groups
        size = len(physical) // jobs + (1 if slot < len(physical) % jobs else 0)
        sets.append(",".join(str(cpu) for core in physical[start:start + size] for cpu in core))
        start += size
    return sets


def plan_groups(phases: list[int]) -> list[list[int]]:
    """Contiguous groups, sized by the band their first phase falls in."""
    groups: list[list[int]] = []
    current: list[int] = []
    size = BANDS[0][1]
    for phase in phases:
        band_size = next(count for start, count in reversed(BANDS) if phase >= start)
        if current and (len(current) >= size or band_size != size):
            groups.append(current)
            current = []
        if not current:
            size = band_size
        current.append(phase)
    if current:
        groups.append(current)
    return groups


def spec_of(group: list[int]) -> str:
    """"a-b" for a contiguous run, else the numbers."""
    if group == list(range(group[0], group[-1] + 1)):
        return f"{group[0]}-{group[-1]}"
    return ",".join(str(phase) for phase in group)


def plan(shell: str, spec: "str | None") -> list[tuple[str, list[int]]]:
    """[(interface, group)] in the order they are queued: the Tk suite's groups, then the
    Qt-hosted one's. `shell` is "tk", "qt" or "both"; `spec` narrows each suite to the phases it
    has of those named."""
    planned: list[tuple[str, list[int]]] = []
    if shell in ("tk", "both"):
        planned += [("tk", group) for group in plan_groups(parse_phases(spec, all_phases()))]
    if shell in ("qt", "both"):
        planned += [("qt", group) for group in plan_groups(parse_phases(spec, qt_hosted_phases()))]
    return planned


def command_for(shell: str, group: list[int], *, index: int, cores: str, python: str, timeout: int) -> list[str]:
    """One group's command: the single gate on its phases, its own display, its own cores -- and,
    for the Qt-hosted suite, `--shell qt` (which also selects that suite's baseline)."""
    command = ["taskset", "-c", cores, "nice", "-n", "15", python, str(GATE),
               "--phases", spec_of(group), "--display", str(FIRST_DISPLAY + index),
               "--timeout", str(timeout)]
    if shell == "qt":
        command += ["--shell", "qt"]
    return command


def summarize(planned: list[tuple[str, list[int]]], results: dict) -> tuple[bool, list[str]]:
    """(everything passed, the lines to print). `results` maps a group's index in `planned` to
    {"pass", "fail", "regressed", "reported", "exit", "log"}; a group with no result did not run."""
    lines, problems = [], []
    for shell, label in SHELLS.items():
        indexes = [index for index, (group_shell, _group) in enumerate(planned) if group_shell == shell]
        if not indexes:
            continue
        phases = sum(len(planned[index][1]) for index in indexes)
        passed = sum(results.get(index, {}).get("pass", 0) for index in indexes)
        failed = sum(results.get(index, {}).get("fail", 0) for index in indexes)
        lines.append(f"[parallel] {label}: {passed} pass, {failed} fail of {phases} phases in {len(indexes)} groups")
    for index, (shell, group) in enumerate(planned):
        result = results.get(index)
        if result is None:
            problems.append(f"{SHELLS[shell]} group {index} ({spec_of(group)}): did not run")
        elif not result["reported"] or result["fail"] or result["regressed"] or result["exit"] != 0:
            problems.append(f"{SHELLS[shell]} group {index} ({spec_of(group)}): {result['pass']} pass, {result['fail']} fail, "
                            f"reported {result['reported']}, exit {result['exit']} -- {result['log']}")
    total = sum(len(group) for _shell, group in planned)
    total_pass = sum(result.get("pass", 0) for result in results.values())
    lines.append(f"[parallel] groups with a problem: {len(problems)}")
    lines += [f"[parallel]   {line}" for line in problems]
    ok = not problems and total_pass == total and total > 0
    lines.append("[parallel] OK -- every group reported, no failure." if ok else "[parallel] NOT OK.")
    return ok, lines


class Running:
    def __init__(self, index: int, shell: str, group: list[int], process, log: Path, cores: str, started: float) -> None:
        self.index, self.shell, self.group, self.process, self.log, self.cores, self.started = (
            index, shell, group, process, log, cores, started)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=int, default=3, help="groups run at the same time (default 3)")
    parser.add_argument("--cores", default=None,
                        help='the CPUs to share out, e.g. "0-11" or "0,8,1,9" (default: whole physical '
                             'cores per group, hyperthread siblings together, the last core left for the '
                             'desktop)')
    # 6.5, not 5.5: with four groups in the Qt tail the watchdog fired twice in one run (2026-10-04);
    # a higher admission mark keeps the fourth out until there is room, which costs less than a
    # killed group's re-run
    parser.add_argument("--start-gb", type=float, default=6.5,
                        help="start another group only while this much memory is available")
    parser.add_argument("--min-gb", type=float, default=2.5,
                        help="below this, the group started last is killed and queued again")
    parser.add_argument("--phases", default=None, help='a subset: "633-727" or "12,88,400-420"')
    parser.add_argument("--shell", choices=("both", "tk", "qt"), default="both",
                        help="the interfaces to gate: every phase on Tk, the harness's phases hosted in "
                             "the Qt shell, or both (default)")
    parser.add_argument("--timeout", type=int, default=7200, help="seconds allowed per group")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--out", type=Path, default=None, help="where the group logs go (default: a temp dir)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    planned = plan(args.shell, args.phases)
    groups = [group for _shell, group in planned]
    phase_total = sum(len(group) for group in groups)
    core_sets = core_sets_for(int(args.jobs), args.cores)
    jobs = len(core_sets)
    out = args.out or Path(tempfile.mkdtemp(prefix="penta_parallel_"))
    out.mkdir(parents=True, exist_ok=True)
    suites = ", ".join(f"{sum(len(group) for shell, group in planned if shell == key)} {label}"
                       for key, label in SHELLS.items() if any(shell == key for shell, _group in planned))
    print(f"[parallel] {phase_total} phases ({suites}) in {len(groups)} groups, {jobs} at a time on cores {core_sets}; "
          f"start above {args.start_gb:g} GB free, kill below {args.min_gb:g} GB; logs in {out}", flush=True)
    if args.dry_run:
        for index, (shell, group) in enumerate(planned):
            print(f"  group {index:2d} {SHELLS[shell]:>9s}: {spec_of(group)} ({len(group)} phases)")
        return 0

    queue = list(enumerate(groups))
    alone: list = []                 # groups the watchdog killed: each waits for clear room
    running: list[Running] = []
    free_slots = list(range(jobs))
    slot_of: dict = {}
    results: dict = {}
    lowest = available_gb()
    began = time.time()

    def start(index: int, group: list[int]) -> None:
        slot = free_slots.pop(0)
        scratch = out / f"tmp_{index:02d}"
        scratch.mkdir(exist_ok=True)
        shell = planned[index][0]
        log = out / f"group_{index:02d}_{shell}_{spec_of(group).replace(',', '_')[:40]}.log"
        env = dict(os.environ)
        env["TMPDIR"] = str(scratch)             # the gate's own log and the validators' scratch files
        command = command_for(shell, group, index=index, cores=core_sets[slot], python=args.python,
                              timeout=int(args.timeout))
        with log.open("w") as handle:
            process = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT, cwd=str(REPO_ROOT),
                                       env=env, start_new_session=True)
        entry = Running(index, shell, group, process, log, core_sets[slot], time.time())
        running.append(entry)
        slot_of[index] = slot

    def finish(entry: Running, *, killed: bool = False, was_alone: bool = False) -> None:
        running.remove(entry)
        free_slots.append(slot_of.pop(entry.index))
        free_slots.sort()
        text = entry.log.read_text(errors="replace") if entry.log.exists() else ""
        match = RESULT_RE.search(text)
        took = time.time() - entry.started
        if killed and was_alone:
            # nothing else was running: starting it again would only be killed again
            results[entry.index] = {"group": entry.group, "pass": 0, "fail": 0, "regressed": False,
                                    "reported": False, "exit": "killed for memory while running alone",
                                    "seconds": took, "log": str(entry.log)}
            print(f"[parallel] {SHELLS[entry.shell]} group {entry.index} ({spec_of(entry.group)}) killed by the memory "
                  f"watchdog while it ran ALONE ({available_gb():.1f} GB free): this machine cannot run it now [PROBLEM]",
                  flush=True)
            return
        if killed:
            alone.append((entry.index, entry.group))
            print(f"[parallel] {SHELLS[entry.shell]} group {entry.index} ({spec_of(entry.group)}) killed by the memory "
                  f"watchdog after {took:.0f} s; queued again", flush=True)
            return
        passed, failed = (int(match.group(1)), int(match.group(2))) if match else (0, 0)
        regressed = "REGRESSED" in text or "BLOCKED" in text
        reported = match is not None and passed + failed == len(entry.group)
        results[entry.index] = {"group": entry.group, "pass": passed, "fail": failed, "regressed": regressed,
                                "reported": reported, "exit": entry.process.returncode, "seconds": took,
                                "log": str(entry.log)}
        mark = "ok" if reported and not failed and not regressed and entry.process.returncode == 0 else "PROBLEM"
        print(f"[parallel] group {entry.index:2d} {SHELLS[entry.shell]:>9s} {spec_of(entry.group):>9s}: {passed} pass, "
              f"{failed} fail in {took:.0f} s [{mark}] ({len(results)}/{len(groups)} done, {available_gb():.1f} GB free)",
              flush=True)

    while queue or alone or running:
        free = available_gb()
        lowest = min(lowest, free)
        for entry in list(running):
            if entry.process.poll() is not None:
                finish(entry)
        if running and free < args.min_gb:
            victim = max(running, key=lambda entry: entry.started)
            try:
                os.killpg(victim.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            victim.process.wait()
            finish(victim, killed=True, was_alone=len(running) == 1)
            time.sleep(5.0)
            continue
        if queue and free_slots and (not running or free >= args.start_gb):
            start(*queue.pop(0))
            time.sleep(2.0)              # let it claim its memory before the next is admitted
            continue
        # a group the watchdog killed comes back when there is clear room: nothing running, or a
        # free slot and well over the admission mark
        if alone and free_slots and (not running or free >= args.start_gb + 2.0):
            start(*alone.pop(0))
            time.sleep(2.0)
            continue
        time.sleep(2.0)

    total_pass = sum(result["pass"] for result in results.values())
    total_fail = sum(result["fail"] for result in results.values())
    minutes = (time.time() - began) / 60.0
    print(f"[parallel] {total_pass} pass, {total_fail} fail of {phase_total} phases in {minutes:.1f} min; lowest "
          f"free memory {lowest:.1f} GB", flush=True)
    ok, lines = summarize(planned, results)
    for line in lines:
        print(line, flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
