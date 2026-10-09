"""bugs/0993: is the Tk-rooted editor the same model before and after the change?

Runs the guard's own scripted session (`validate_editor_without_tk_root.session("tk", ...)`: 35
steps on a headless editor with a Tk root) three times -- with the working tree as it is, then
TWICE with the modified files put back to HEAD's -- and leaves three records to compare. Two runs
at HEAD that agree show the comparison means something.

    python bugs/0993_tk_before_after.py <a scratch folder>

The modified files are saved first and put back in a `finally`, at exit and on a signal; the
script says whether every file is byte for byte what it was.
"""
import atexit
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

S = Path(sys.argv[1])
(S / "records").mkdir(parents=True, exist_ok=True)
status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout
# the files of the product; the guards stay as they are, so the SAME session is run on both
FILES = [line[3:] for line in status.splitlines()
         if line[:2] == " M" and line[3:].startswith("KrakenOS/")
         and not line[3:].rsplit("/", 1)[-1].startswith("validate_")]
assert FILES, status
print("the product's modified files:", FILES, flush=True)
keep = S / "changed_files"
shutil.rmtree(keep, ignore_errors=True)
sha = {}
for name in FILES:
    (keep / name).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(name, keep / name)
    sha[name] = hashlib.sha256(Path(name).read_bytes()).hexdigest()
restored = False


def restore(*_args) -> None:
    global restored
    if restored:
        return
    for name in FILES:
        shutil.copy2(keep / name, name)
    restored = True
    wrong = [name for name in FILES if hashlib.sha256(Path(name).read_bytes()).hexdigest() != sha[name]]
    print("restored the change; files not as they were:", wrong or "none", flush=True)


atexit.register(restore)
for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(sig, lambda *_args: (restore(), os._exit(1)))


def run(out: Path) -> None:
    driver = ("import json, os\nfrom KrakenOS.UI.validate_editor_without_tk_root import session\n"
              f"print('META ' + json.dumps(session('tk', {str(out)!r})), flush=True)\nos._exit(0)\n")
    config = S / f"config_{out.stem}"
    config.mkdir(exist_ok=True)
    proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                          env=dict(os.environ, KRAKEN_CONFIG_DIR=str(config)))
    meta = [line for line in proc.stdout.splitlines() if line.startswith("META ")]
    print(out.name, "->", meta[0][:160] if meta else "FAILED: " + (proc.stderr or "")[-600:], flush=True)


try:
    run(S / "records/tk_after.json")
    for name in FILES:
        Path(name).write_bytes(subprocess.run(["git", "show", f"HEAD:{name}"], capture_output=True).stdout)
    run(S / "records/tk_before_1.json")
    run(S / "records/tk_before_2.json")
finally:
    restore()

sys.path.insert(0, ".")
from KrakenOS.UI.validate_editor_without_tk_root import _states  # noqa: E402

runs = {name: _states(str(S / f"records/tk_{name}.json"))[0] for name in ("before_1", "before_2", "after")}
for a, b in (("before_1", "before_2"), ("before_1", "after")):
    differ: dict = {}
    for (label, result_a, state_a), (_label, result_b, state_b) in zip(runs[a], runs[b]):
        if result_a != result_b:
            differ.setdefault("<a step's result>", []).append(label)
        for key in sorted(set(state_a) | set(state_b)):
            if state_a.get(key, "<absent>") != state_b.get(key, "<absent>"):
                differ.setdefault(key, []).append(label)
    print(f"{a} vs {b}: {len(runs[a])} and {len(runs[b])} steps, {len(runs[a][-1][2])} attributes at the end; "
          f"attributes that differ at any step: {({key: len(steps) for key, steps in differ.items()}) or 'none'}")
