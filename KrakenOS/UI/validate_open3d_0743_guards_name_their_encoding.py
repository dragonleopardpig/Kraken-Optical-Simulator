"""Guard for bugs/0743 -- a guard that reads source must name its encoding.

The penta gate blocked on Phase 536 (bugs/0738's own guard) and Phase 518 (bugs/0719), both of
which PASSED standalone. Cause: `Path(...).read_text()` with no encoding uses the locale, VTK/Tk
reset the C locale as the suite builds scenes, and the read then fails with
`UnicodeDecodeError('ascii', ...)` on source files that contain non-ascii bytes.

Checks:
  A  no validator reads source through the locale any more.
  B  the two files those guards read really do contain non-ascii, so the bug was real and would
     recur the moment the locale drifts again.
  C  a guard actually passes under an ascii locale (the class of bug is closed, not just patched
     at the call sites known today).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0743_guards_name_their_encoding
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    # ---- A: nobody reads source through the locale -----------------------------------------------
    offenders = []
    bare = ".read_text" + "()"          # split so this guard does not match itself
    for path in sorted(HERE.glob("validate_open3d_*.py")):
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        if bare in text:
            offenders.append(path.name)
    ok(
        not offenders,
        f"A1: no validator calls read_text() without an encoding ({', '.join(offenders) or 'none'})",
    )

    # ---- B: the bug was real ---------------------------------------------------------------------
    watched = {
        "validate_open3d_penta_telescope_comprehensive.py": HERE / "validate_open3d_penta_telescope_comprehensive.py",
        "KrakenSys.py": ROOT / "KrakenOS" / "KrakenSys.py",
    }
    for label, path in watched.items():
        try:
            raw = path.read_bytes()
        except Exception:
            raw = b""
        ok(
            any(byte > 127 for byte in raw),
            f"B[{label}]: contains non-ascii, so an ascii-locale read of it really does raise",
        )

    # ---- C: the class is closed --------------------------------------------------------------------
    # Run the same source-reading guard under the normal locale AND an ascii one, and require the SAME
    # outcome. The first version required an outright PASS under ascii, so when 0738 failed for a
    # reason that had nothing to do with encoding (a scaffolding row added to its scene), this guard
    # reported "fails under an ascii locale" -- a false cause. The question C asks is whether the
    # LOCALE changes anything.
    def _run(ascii_locale: bool):
        env = dict(os.environ)
        if ascii_locale:
            env["PYTHONUTF8"] = "0"
            env["LC_ALL"] = "C"
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        try:
            done = subprocess.run(
                [sys.executable, "-m", "KrakenOS.UI.validate_open3d_0738_phantom_spacer_surfaces"],
                cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=600,
            )
            return done.stdout, done.returncode
        except Exception as exc:  # pragma: no cover - defensive
            return f"{type(exc).__name__}: {exc}", -1

    def _verdicts(output: str) -> list[str]:
        return [line.strip() for line in output.splitlines()
                if line.strip().startswith(("PASS:", "FAIL:", "- FAIL:"))]

    normal_out, normal_code = _run(False)
    ascii_out, ascii_code = _run(True)
    ok(
        ascii_code == normal_code and _verdicts(ascii_out) == _verdicts(normal_out),
        f"C1: a source-reading guard gives the SAME result under an ascii locale as under the normal "
        f"one (exit {ascii_code} vs {normal_code}, {len(_verdicts(ascii_out))} vs "
        f"{len(_verdicts(normal_out))} verdicts)",
    )
    ok(
        "UnicodeDecodeError" not in ascii_out and "UnicodeEncodeError" not in ascii_out,
        "C2: and raises no decode or encode error there",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0743 guards-name-their-encoding validation PASSED")
        return 0
    print("0743 guards-name-their-encoding validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
