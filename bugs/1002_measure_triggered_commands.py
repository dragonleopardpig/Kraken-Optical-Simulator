"""bugs/1002: which of the Qt shell's commands does a guard in the gate really TRIGGER?

Reading the guards does not answer it (a guard can loop over names, click a ribbon button, send a
shortcut), so this measures it: every gated guard that builds a Qt shell is run, ONE at a time and
at low priority, from a scratch copy of the tree whose `ActionManager` writes each triggered
command's name to a log. Nothing in the real tree is changed; the copy reads the real attachment/
scenes through a link, which is removed before the copy is.

Usage (inside `devenv shell`, needs a display; about 80 minutes):
    python bugs/1002_measure_triggered_commands.py <scratch folder> [guard ...]

Result of 2026-10-10 at d85a0ce9: 87 guards, all PASS, 47 of them trigger a command; of the 102
commands 76 are triggered by at least one guard and 26 by none.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HARNESS = REPO / "KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py"
BUILDS_QT_SHELL = re.compile(r"qt\.app import build|KrakenQtMainWindow|action_manager")
HOOK_AFTER = "            action.triggered.connect(handler)\n"
HOOK = ('            import os as _os\n\n'
        '            _log = _os.environ.get("KRAKEN_QT_ACTION_LOG")       # MEASUREMENT ONLY (bugs/1002)\n'
        '            if _log:\n'
        '                action.triggered.connect(lambda _checked=False, n=name, f=_log: open(f, "a").write(n + "\\n"))\n')


def gated_qt_guards() -> list[str]:
    names = sorted(set(re.findall(r"KrakenOS\.UI\.(validate_\w+)", HARNESS.read_text(encoding="utf-8"))))
    return [name for name in names if name != HARNESS.stem and (REPO / "KrakenOS/UI" / f"{name}.py").exists()
            and BUILDS_QT_SHELL.search((REPO / "KrakenOS/UI" / f"{name}.py").read_text(encoding="utf-8", errors="replace"))]


def main() -> int:
    scratch = Path(sys.argv[1]).resolve()
    guards = sys.argv[2:] or gated_qt_guards()
    tree, logs, outs = scratch / "tree", scratch / "logs", scratch / "out"
    for folder in (logs, outs):
        folder.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", str(tree), "HEAD"], check=True)
    link = tree / "attachment"
    try:
        actions = tree / "KrakenOS/UI/qt/actions.py"
        text = actions.read_text(encoding="utf-8")
        assert text.count(HOOK_AFTER) == 1, "the place for the log line moved"
        actions.write_text(text.replace(HOOK_AFTER, HOOK_AFTER + HOOK), encoding="utf-8")
        subprocess.run(["rm", "-rf", str(link)], check=True)          # the copy's checked-out part of attachment/
        link.symlink_to(REPO / "attachment")                          # the scenes git does not hold
        results = {}
        for guard in guards:
            env = dict(os.environ, PYTHONPATH=str(tree), PYTHONDONTWRITEBYTECODE="1", QT_QPA_PLATFORM="xcb",
                       KRAKEN_QT_ACTION_LOG=str(logs / f"{guard}.log"),
                       KRAKEN_CONFIG_DIR=tempfile.mkdtemp(prefix="measure1002_"))
            for name in ("WAYLAND_DISPLAY", "KRAKEN_UI_SHELL", "KRAKEN_QT_TK_FREE"):
                env.pop(name, None)
            started = time.time()
            with (outs / f"{guard}.out").open("w") as handle:
                code = subprocess.run(["nice", "-n", "15", sys.executable, "-m", f"KrakenOS.UI.{guard}"], cwd=str(tree),
                                      env=env, stdout=handle, stderr=subprocess.STDOUT, timeout=1800).returncode
            said = (outs / f"{guard}.out").read_text(errors="replace")
            verdict = (re.findall(r"^(PASS|FAIL)$", said, flags=re.M) or ["none"])[-1]
            log = logs / f"{guard}.log"
            triggered = sorted(set(log.read_text().split())) if log.exists() else []
            results[guard] = {"exit": code, "verdict": verdict, "skipped": bool(re.search(r"^SKIP|SKIP = ", said, flags=re.M)),
                              "commands": triggered, "seconds": round(time.time() - started)}
            print(f"{guard:58s} {verdict:5s} {len(triggered):3d} command(s) {results[guard]['seconds']:5d} s", flush=True)
    finally:
        if link.is_symlink():
            link.unlink()                                             # the link, never what it points to
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(tree)], check=False)
        subprocess.run(["git", "-C", str(REPO), "worktree", "prune"], check=False)
    sys.path.insert(0, str(REPO))
    from KrakenOS.UI.qt.actions import ACTIONS

    names = [entry[0] for entry in ACTIONS]
    by_command = {name: [guard for guard, result in results.items() if name in result["commands"]] for name in names}
    never = [name for name in names if not by_command[name]]
    (scratch / "coverage.json").write_text(json.dumps({"guards": results, "never": never, "by_command": by_command}, indent=1))
    print(f"{len(results)} guards, {sum(r['verdict'] == 'PASS' for r in results.values())} PASS, "
          f"{sum(bool(r['commands']) for r in results.values())} trigger a command, "
          f"{sum(r['skipped'] for r in results.values())} skipped something; of {len(names)} commands "
          f"{len(names) - len(never)} are triggered by at least one guard, {len(never)} by none: {never}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
