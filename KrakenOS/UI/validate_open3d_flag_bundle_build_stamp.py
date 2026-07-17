#!/usr/bin/env python3
"""Display-free guard: every flag bundle stamps the running code's git build.

Motivation (bugs/0345):
  Two recording cycles in a row re-flagged bugs that were already fixed AND
  guarded (0343 's' hotkey, 0344 CA snap). The flag bundle's state.json carried
  no fingerprint of the CODE the app was launched from, so a STALE app (running
  pre-fix code) could not be told apart from a genuine post-fix regression from
  the bundle alone -- the diagnosis stalled on "is this even on the new build?".

Fix:
  ``_open3d_running_build_stamp()`` returns a best-effort git fingerprint
  (short HEAD + branch + dirty flag), computed once per process and never
  raising, and ``flag_bug`` writes it into state.json under ``"build"``.

What it checks
--------------
  1. ``_open3d_running_build_stamp()`` returns a dict with a ``"git"`` key and
     never raises; run inside this checkout it resolves a short SHA.
  2. Source contract: the ``flag_bug`` state.json payload includes
     ``"build": _open3d_running_build_stamp()``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_flag_bundle_build_stamp

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def _check_stamp_callable() -> list[str]:
    from KrakenOS.UI.open3d_inspector import _open3d_running_build_stamp

    failures: list[str] = []
    try:
        stamp = _open3d_running_build_stamp()
    except Exception as exc:  # must never raise -- it runs on every flag
        return [f"FAIL(1): _open3d_running_build_stamp() raised {exc!r}"]
    if not isinstance(stamp, dict) or "git" not in stamp:
        failures.append(f"FAIL(1): build stamp must be a dict with a 'git' key, got {stamp!r}")
        return failures
    # Inside this git checkout the stamp must resolve a short SHA (not None).
    git = stamp.get("git")
    if not (isinstance(git, str) and git):
        failures.append(
            f"FAIL(1): run inside the checkout the stamp must resolve a short git SHA, got {git!r}"
        )
    return failures


def _check_payload_contract() -> list[str]:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    failures: list[str] = []
    src = inspect.getsource(Kraken3DInspector.flag_bug)
    if '"build": _open3d_running_build_stamp()' not in src:
        failures.append(
            "FAIL(2): flag_bug state.json payload must include "
            "'\"build\": _open3d_running_build_stamp()' so a re-recorded bug can be "
            "told apart from a stale pre-fix app"
        )
    return failures


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    failures.extend(_check_stamp_callable())
    failures.extend(_check_payload_contract())
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] flag bundles do not stamp the running git build")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] every flag bundle stamps the running code's git build so stale-app "
          "recordings are distinguishable from real regressions (bugs/0345)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
