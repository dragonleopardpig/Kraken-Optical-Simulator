"""Display-free guard: a flagged-bug bundle can be DISCARDED (cancel the flag).

The in-app ``s`` bug-flag writes a bundle (screenshot + state.json + an empty description.txt)
immediately, then opens a non-modal description dialog. Previously both buttons (Save / Close)
kept the bundle on disk, so an accidental or changed-mind flag left clutter behind with no way to
cancel it. The fix adds ``Kraken3DInspector._discard_flag_bundle`` (delete the bundle dir + mark any
recording flag event discarded), wires a ``Discard`` button, and auto-discards when the dialog is
dismissed (Escape / window-close) with an EMPTY description box.

This guard pins (headless, no Tk/VTK):

  * FUNCTIONAL: discard deletes the whole bundle dir and sets ``payload['discarded']=True``;
    a missing dir / None payload is safe (no raise), returns True (already gone).
  * SOURCE CONTRACT: the description dialog offers Discard, calls ``_discard_flag_bundle``, binds
    Escape AND ``WM_DELETE_WINDOW`` to the dismiss handler, and the dismiss handler discards on an
    empty box but saves typed-but-unsaved text (words are never thrown away).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_flag_discard

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

from KrakenOS.UI.open3d_inspector import Kraken3DInspector


def _check_functional(failures: list[str]) -> None:
    root = Path(tempfile.mkdtemp(prefix="flag_discard_guard_"))
    try:
        bundle = root / "flag_20260629_000000_001"
        bundle.mkdir()
        (bundle / "screenshot.png").write_bytes(b"\x89PNG\r\n")
        (bundle / "state.json").write_text("{}", encoding="utf-8")
        (bundle / "description.txt").write_text("", encoding="utf-8")
        payload: dict[str, object] = {"bundle_dir": str(bundle)}

        ok = Kraken3DInspector._discard_flag_bundle(bundle, payload)
        if not ok or bundle.exists():
            failures.append("FUNCTIONAL: discard did not delete the bundle directory")
        if payload.get("discarded") is not True:
            failures.append("FUNCTIONAL: discard did not mark the recording flag event discarded")

        # Already-gone dir + None payload must be safe and report success.
        if not Kraken3DInspector._discard_flag_bundle(bundle, None):
            failures.append("FUNCTIONAL: discarding a missing bundle should be a safe no-op (True)")
    finally:
        import shutil

        shutil.rmtree(root, ignore_errors=True)


def _check_source_contract(failures: list[str]) -> None:
    src = inspect.getsource(Kraken3DInspector._open_flag_description_dialog)
    required = {
        "a Discard button": 'text="Discard"',
        "the discard helper": "_discard_flag_bundle(",
        "a Keep-screenshot button (mid-drag safety net)": 'text="Keep screenshot"',
        "Escape bound to dismiss": '"<Escape>", _dismiss',
        "window-close bound to dismiss": '"WM_DELETE_WINDOW", _dismiss',
    }
    for label, needle in required.items():
        if needle not in src:
            failures.append(f"CONTRACT: flag dialog is missing {label} ({needle!r})")

    # The dismiss handler discards on empty but saves typed text (no lost words).
    if "_dismiss" in src:
        body = src.split("def _dismiss", 1)[1].split("def ", 1)[0]
        if "_do_discard()" not in body or "_do_save()" not in body:
            failures.append("CONTRACT: _dismiss must discard on empty and save typed text")

    helper_src = inspect.getsource(Kraken3DInspector._discard_flag_bundle)
    if "rmtree" not in helper_src or "discarded" not in helper_src:
        failures.append("CONTRACT: _discard_flag_bundle must delete the dir and mark the event discarded")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    _check_functional(failures)
    _check_source_contract(failures)
    return (not failures), failures


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] flag bundle discard (cancel the flag)")
        return 1
    print("[PASS] a flagged-bug bundle can be discarded (cancel the flag)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
