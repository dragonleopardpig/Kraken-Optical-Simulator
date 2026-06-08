#!/usr/bin/env python3
"""Pre-push gate around the comprehensive penta-telescope validator.

Runs ``KrakenOS.UI.validate_open3d_penta_telescope_comprehensive`` on a
private virtual X display and blocks a push only on a *new* failure --
a phase that flips PASS -> FAIL relative to a stored baseline. Phases
that were already failing in the baseline (e.g. because an optional
vendor STEP fixture isn't checked out) do not block the push, so the
gate catches regressions without getting in the way of unrelated work.

Usage:
    python tools/penta_validator_gate.py            # run + compare baseline
    python tools/penta_validator_gate.py --update-baseline
    python tools/penta_validator_gate.py --install   # wire up the git hook

Exit codes: 0 = no regression (push allowed), 1 = regression (blocked).
When the environment can't run the validator (no Xvfb, no interpreter)
the gate prints a warning and allows the push unless --require-env.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = REPO_ROOT / "tools" / "penta_validator_baseline.json"
HOOKS_DIR = REPO_ROOT / ".githooks"
VALIDATOR_MODULE = "KrakenOS.UI.validate_open3d_penta_telescope_comprehensive"
PHASE_RE = re.compile(r"^\s*\[(PASS|FAIL)\]\s+Phase\s+(\d+)\s*:\s*(.*?)\s*$")


def _find_interpreter(explicit: str | None) -> str | None:
    if explicit:
        return explicit if Path(explicit).exists() else None
    venv = REPO_ROOT / ".devenv" / "state" / "venv" / "bin" / "python"
    if venv.exists():
        return str(venv)
    return shutil.which("python3") or shutil.which("python")


def _free_display(preferred: int | None) -> int:
    candidates = [preferred] if preferred is not None else []
    candidates += [99, 98, 97, 96, 95]
    for num in candidates:
        if num is None:
            continue
        if not Path(f"/tmp/.X11-unix/X{num}").exists():
            return int(num)
    # Fall back to a high number unlikely to collide.
    return 123


def _start_xvfb(display: int, timeout: float = 15.0):
    xvfb = shutil.which("Xvfb")
    if xvfb is None:
        return None, "Xvfb not found on PATH"
    proc = subprocess.Popen(
        [xvfb, f":{display}", "-screen", "0", "1600x1000x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    sock = Path(f"/tmp/.X11-unix/X{display}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return None, f"Xvfb exited early (code {proc.returncode})"
        if sock.exists():
            return proc, None
        time.sleep(0.2)
    proc.terminate()
    return None, f"Xvfb :{display} did not come up within {timeout:.0f}s"


def _parse_phase_states(log_text: str) -> dict[str, dict[str, str]]:
    """Map phase-number string -> {status, title}. Last occurrence wins."""
    states: dict[str, dict[str, str]] = {}
    for line in log_text.splitlines():
        match = PHASE_RE.match(line)
        if match is None:
            continue
        status, number, title = match.group(1), match.group(2), match.group(3)
        states[number] = {"status": status.lower(), "title": title}
    return states


def run_validator(
    *, interpreter: str, display: int | None, timeout: int, log_path: Path
) -> tuple[int, dict[str, dict[str, str]], str | None]:
    """Boot Xvfb, run the validator, return (exit_code, phase_states, env_error)."""
    chosen = _free_display(display)
    proc, err = _start_xvfb(chosen)
    if proc is None:
        return 0, {}, err
    env = dict(os.environ)
    env["DISPLAY"] = f":{chosen}"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    try:
        completed = subprocess.run(
            [interpreter, "-m", VALIDATOR_MODULE],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            text=True,
        )
        log_text = completed.stdout or ""
        code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        log_text = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        log_text += f"\n[gate] validator timed out after {timeout}s\n"
        code = 124
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    log_path.write_text(log_text, encoding="utf-8")
    return code, _parse_phase_states(log_text), None


def load_baseline(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    phases = data.get("phases", {})
    return {str(k): str(v).lower() for k, v in phases.items()}


def write_baseline(path: Path, states: dict[str, dict[str, str]]) -> None:
    payload = {
        "_comment": (
            "Baseline phase states for the penta-telescope pre-push gate. "
            "A push is blocked only when a phase that is 'pass' here flips "
            "to 'fail'. Regenerate with: python tools/penta_validator_gate.py "
            "--update-baseline"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "phases": {num: st["status"] for num, st in sorted(states.items(), key=lambda kv: int(kv[0]))},
        "titles": {num: st["title"] for num, st in sorted(states.items(), key=lambda kv: int(kv[0]))},
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def compare(
    baseline: dict[str, str], current: dict[str, dict[str, str]]
) -> tuple[list[str], list[str], list[str]]:
    """Return (regressions, fixed, still_failing) as phase-number lists."""
    regressions: list[str] = []
    fixed: list[str] = []
    still_failing: list[str] = []
    # New failures vs baseline (unknown phases default to must-pass).
    for num, st in current.items():
        base = baseline.get(num, "pass")
        if st["status"] == "fail" and base == "pass":
            regressions.append(num)
        elif st["status"] == "fail":
            still_failing.append(num)
        elif st["status"] == "pass" and base == "fail":
            fixed.append(num)
    # Baseline-pass phases that vanished from the run = the run didn't
    # reach them; treat as a regression so a crash mid-run blocks.
    for num, base in baseline.items():
        if base == "pass" and num not in current:
            regressions.append(num)
    return sorted(set(regressions), key=int), sorted(set(fixed), key=int), sorted(set(still_failing), key=int)


def _install_hook() -> int:
    HOOKS_DIR.mkdir(exist_ok=True)
    hook = HOOKS_DIR / "pre-push"
    if not hook.exists():
        print(f"error: {hook} missing -- commit the hook file first", file=sys.stderr)
        return 1
    hook.chmod(0o755)
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=str(REPO_ROOT), check=True)
    print("Installed: core.hooksPath -> .githooks (pre-push gate active).")
    print("Disable for one push with:  git push --no-verify")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--update-baseline", action="store_true",
                        help="run, then overwrite the baseline with the current phase states")
    parser.add_argument("--install", action="store_true",
                        help="set git core.hooksPath to .githooks and exit")
    parser.add_argument("--display", type=int, default=None, help="force a specific Xvfb display number")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--python", default=None, help="interpreter to run the validator with")
    parser.add_argument("--require-env", action="store_true",
                        help="treat a missing Xvfb/interpreter as a failure (exit 1) instead of skipping")
    args = parser.parse_args(argv)

    if args.install:
        return _install_hook()

    interpreter = _find_interpreter(args.python)
    if interpreter is None:
        msg = "no usable Python interpreter (.devenv venv or python3) found"
        print(f"[gate] SKIP: {msg}", file=sys.stderr)
        return 1 if args.require_env else 0

    log_path = Path(tempfile.gettempdir()) / "penta_validator_last.log"
    print("[gate] running penta-telescope validator on a virtual display ...")
    code, states, env_error = run_validator(
        interpreter=interpreter, display=args.display, timeout=args.timeout, log_path=log_path
    )
    if env_error is not None:
        print(f"[gate] SKIP: {env_error}", file=sys.stderr)
        return 1 if args.require_env else 0

    if not states:
        print("[gate] no phase results parsed -- see", log_path, file=sys.stderr)
        return 1

    passed = sum(1 for s in states.values() if s["status"] == "pass")
    failed = sum(1 for s in states.values() if s["status"] == "fail")
    print(f"[gate] phases: {passed} pass, {failed} fail (validator exit {code})")

    if args.update_baseline:
        write_baseline(args.baseline, states)
        print(f"[gate] baseline written to {args.baseline}")
        return 0

    baseline = load_baseline(args.baseline)
    if not baseline:
        print(f"[gate] no baseline at {args.baseline}; treating all phases as must-pass.")
    regressions, fixed, still_failing = compare(baseline, states)

    for num in fixed:
        print(f"[gate]   fixed: Phase {num} ({states.get(num, {}).get('title', '')})")
    for num in still_failing:
        print(f"[gate]   known-failing (allowed): Phase {num} ({states.get(num, {}).get('title', '')})")
    if regressions:
        print("[gate] BLOCKED -- new failure(s) vs baseline:", file=sys.stderr)
        for num in regressions:
            title = states.get(num, {}).get("title", "(phase missing from run)")
            print(f"[gate]   REGRESSED: Phase {num}: {title}", file=sys.stderr)
        print(f"[gate] full log: {log_path}", file=sys.stderr)
        print("[gate] override with: git push --no-verify", file=sys.stderr)
        return 1

    print("[gate] OK -- no PASS->FAIL regressions. Push allowed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
