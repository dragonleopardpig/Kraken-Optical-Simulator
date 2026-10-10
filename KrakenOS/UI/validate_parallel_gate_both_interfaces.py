"""Guard for bugs/1001: the full gate covers BOTH interfaces (docs/design_qt_migration.md phase 7g).

There are two suites, each with its own baseline: every phase on the Tk interface, and the
harness's own phases run again with the 3D inspector hosted in the Qt shell
(`penta_validator_gate.py --shell qt`). "Run the full gate" meant `tools/penta_parallel_gate.py`,
which ran the first only; the second was run by hand -- twice in a month. Both interfaces stay
(the user's decision, 2026-10-06), so both are gated by the one command now.

This guard holds the runner's own logic without running a single phase (it needs no display):

  P  the plan: asked for nothing, it queues every Tk phase once and every Qt-hosted phase once,
     the Tk groups first; `--shell tk` and `--shell qt` queue one suite; a list of phases narrows
     each suite to what it has of them
  C  the commands: a Qt-hosted group is run with `--shell qt` (which selects that suite's
     baseline too) and a Tk group without; every group has a display of its own across both
     suites, its phases and its cores
  R  the summary: one line per interface with its own totals; OK only when every group ran,
     reported and passed -- a failed Qt-hosted group, a group that did not run, one that did not
     report, one that regressed and an empty plan are each NOT OK, and the failing group is
     named with its interface
  D  the real command line: `--dry-run` prints both suites with the counts the sources give,
     and `--shell tk` prints the Tk one alone
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "tools" / "penta_parallel_gate.py"


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def _runner():
    spec = importlib.util.spec_from_file_location("penta_parallel_gate_under_guard", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_checks() -> tuple[bool, list[str]]:
    gate = _runner()
    tk_phases = gate.all_phases()
    qt_phases = sorted(int(number) for number in json.loads(gate.QT_BASELINE.read_text(encoding="utf-8"))["phases"])

    def flat(planned, shell):
        return [phase for group_shell, group in planned if group_shell == shell for phase in group]

    def claim_p():
        both, only_tk, only_qt = gate.plan("both", None), gate.plan("tk", None), gate.plan("qt", None)
        shells = [shell for shell, _group in both]
        narrowed = gate.plan("both", "300-306,700")
        return (flat(both, "tk") == tk_phases and flat(both, "qt") == qt_phases and len(qt_phases) > 300 < len(tk_phases)
                and shells == sorted(shells, key=["tk", "qt"].index) and "qt" in shells
                and flat(only_tk, "tk") == tk_phases and not flat(only_tk, "qt")
                and flat(only_qt, "qt") == qt_phases and not flat(only_qt, "tk")
                and flat(narrowed, "tk") == [300, 301, 302, 303, 304, 305, 306, 700]
                and flat(narrowed, "qt") == [300, 301, 302, 303, 304, 305, 306]
                and all(len(group) <= 60 for _shell, group in both),
                f"asked for nothing the runner queues {len(flat(both, 'tk'))} Tk phases and {len(flat(both, 'qt'))} Qt-hosted "
                f"ones in {len(both)} groups, each phase of each suite once, the Tk groups first; --shell tk queues "
                f"{len(only_tk)} groups of Tk alone, --shell qt {len(only_qt)} of Qt-hosted alone; '300-306,700' leaves "
                f"{len(flat(narrowed, 'tk'))} Tk and {len(flat(narrowed, 'qt'))} Qt-hosted phases")

    def claim_c():
        planned = gate.plan("both", "300-306,700")
        commands = [gate.command_for(shell, group, index=index, cores="2,3", python="python-x", timeout=77)
                    for index, (shell, group) in enumerate(planned)]
        displays = [command[command.index("--display") + 1] for command in commands]
        qt = [command for (shell, _group), command in zip(planned, commands) if shell == "qt"]
        tk = [command for (shell, _group), command in zip(planned, commands) if shell == "tk"]
        return (qt and tk and all(command[-2:] == ["--shell", "qt"] for command in qt)
                and all("--shell" not in command for command in tk) and len(set(displays)) == len(displays)
                and all(command[:6] == ["taskset", "-c", "2,3", "nice", "-n", "15"] and command[6] == "python-x"
                        and command[7].endswith("penta_validator_gate.py") and "--phases" in command
                        and command[command.index("--timeout") + 1] == "77" for command in commands)
                and [command[command.index("--phases") + 1] for command in commands][-1] == "300-306",
                f"{len(qt)} Qt-hosted group(s) are run with --shell qt and {len(tk)} Tk group(s) without; displays "
                f"{displays} are each a group's own; a command: {' '.join(qt[0][3:])}")

    def claim_r():
        planned = [("tk", [1, 2, 3]), ("tk", [4, 5]), ("qt", [1, 2, 3]), ("qt", [4])]

        def result(passed, failed=0, **changes):
            base = {"pass": passed, "fail": failed, "regressed": False, "reported": True, "exit": 0, "log": "a.log"}
            base.update(changes)
            return base

        good = {0: result(3), 1: result(2), 2: result(3), 3: result(1)}
        cases = {
            "all passed": gate.summarize(planned, good),
            "a Qt-hosted group failed": gate.summarize(planned, {**good, 2: result(2, 1, exit=1)}),
            "a group did not run": gate.summarize(planned, {key: value for key, value in good.items() if key != 3}),
            "a group did not report": gate.summarize(planned, {**good, 1: result(0, reported=False, exit=1)}),
            "a group regressed": gate.summarize(planned, {**good, 0: result(3, regressed=True, exit=1)}),
            "nothing planned": gate.summarize([], {}),
        }
        verdicts = {name: ok for name, (ok, _lines) in cases.items()}
        lines = cases["all passed"][1]
        failed_lines = "\n".join(cases["a Qt-hosted group failed"][1])
        missing_lines = "\n".join(cases["a group did not run"][1])
        return (verdicts == {"all passed": True, "a Qt-hosted group failed": False, "a group did not run": False,
                             "a group did not report": False, "a group regressed": False, "nothing planned": False}
                and "[parallel] Tk: 5 pass, 0 fail of 5 phases in 2 groups" in lines
                and "[parallel] Qt-hosted: 4 pass, 0 fail of 4 phases in 2 groups" in lines
                and lines[-1].startswith("[parallel] OK") and "Qt-hosted group 2 (1-3): 2 pass, 1 fail" in failed_lines
                and "[parallel] Qt-hosted: 3 pass, 1 fail of 4 phases" in failed_lines
                and "Qt-hosted group 3 (4-4): did not run" in missing_lines and failed_lines.endswith("[parallel] NOT OK."),
                f"the summary adds each interface up on its own ({lines[0][11:]}; {lines[1][11:]}) and is OK only when "
                f"every group ran, reported and passed: {verdicts}")

    def claim_d():
        def dry(*args):
            proc = subprocess.run([sys.executable, str(RUNNER), "--dry-run", *args], capture_output=True, text=True,
                                  timeout=120, cwd=str(REPO_ROOT))
            head = next((line for line in proc.stdout.splitlines() if line.startswith("[parallel]")), "")
            groups = [line.split()[2].rstrip(":") for line in proc.stdout.splitlines() if re.match(r"\s+group\s+\d+", line)]
            return proc.returncode, head, groups

        code, head, groups = dry()
        code_tk, head_tk, groups_tk = dry("--shell", "tk")
        expected = f"{len(tk_phases) + len(qt_phases)} phases ({len(tk_phases)} Tk, {len(qt_phases)} Qt-hosted)"
        return (code == 0 == code_tk and expected in head and set(groups) == {"Tk", "Qt-hosted"}
                and f"{len(tk_phases)} phases ({len(tk_phases)} Tk)" in head_tk and set(groups_tk) == {"Tk"},
                f"`--dry-run` plans {head[11:head.index(' in ')] if ' in ' in head else head!r} with "
                f"{groups.count('Tk')} Tk and {groups.count('Qt-hosted')} Qt-hosted groups; `--shell tk` plans "
                f"{head_tk[11:head_tk.index(' in ')] if ' in ' in head_tk else head_tk!r}")

    rows = _claims((("P", claim_p), ("C", claim_c), ("R", claim_r), ("D", claim_d)))
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
