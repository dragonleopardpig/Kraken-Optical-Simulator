"""Guard for bugs/0135 -- an empty-space click cancels the armed CA pick.

Regression context
------------------
After arming **Set Clear Aperture** (bugs/0134) the one-shot pick mode trapped the
user: a click in empty canvas only re-printed the "click the window face" nag, and
the Escape key rarely reaches the handler because the embedded-VTK canvas owns
keyboard focus. The user filed *"unable to deselect components."*

The fix gives the CA-pick block in ``_on_left_button_press`` the same empty-space
escape every other modal pick already has -- ``if actor_key is None and
self.cancel_active_3d_operation(): return`` -- so a click on nothing exits the mode
and clears the selection, while a click on the wrong body still just nudges.

This guard is display-free. It pins two contracts:

1. ``cancel_active_3d_operation`` actually resets the CA-pick flag, and
   ``_active_3d_operation_labels`` reports it -- so the escape takes the cancel path,
   not the no-op deselect.
2. The CA-pick block in ``_on_left_button_press`` contains the ``actor_key is None``
   cancel escape BEFORE the status nag, gated on an empty pick.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_clear_aperture_pick_cancel

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    try:
        return (_REPO_ROOT / rel_path).read_text(encoding="utf-8")
    except Exception:
        return ""


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    # A. Cancel contract: the CA-pick flag is BOTH listed as an active operation and
    #    reset by cancel_active_3d_operation -- so an empty-space click that calls
    #    cancel_active_3d_operation takes the active-op path (clear + return True),
    #    rather than the "nothing to cancel" no-op.
    try:
        from KrakenOS.UI.open3d_inspector import Kraken3DInspector

        cancel_src = inspect.getsource(Kraken3DInspector.cancel_active_3d_operation)
        active_src = inspect.getsource(Kraken3DInspector._active_3d_operation_labels)
    except Exception as exc:
        notes.append(f"FAIL: could not read inspector cancel sources: {exc!r}")
        return False, notes

    if "self._step_clear_aperture_pick_mode = False" not in cancel_src:
        notes.append(
            "FAIL: cancel_active_3d_operation no longer resets _step_clear_aperture_pick_mode "
            "-- cancelling would leave the CA pick armed (bugs/0135)"
        )
        passed = False
    if "_step_clear_aperture_pick_mode" not in active_src:
        notes.append(
            "FAIL: _active_3d_operation_labels does not report the CA pick mode -- "
            "cancel_active_3d_operation would treat it as 'nothing to cancel' (bugs/0135)"
        )
        passed = False

    # B. Source contract: the CA-pick block in _on_left_button_press (defined in
    #    open3d_interaction.py) cancels on an empty pick BEFORE the status nag, and the
    #    escape is gated on actor_key None (so a wrong-body click still nudges).
    press_src = _read("KrakenOS/UI/services/open3d_interaction.py")

    marker = "if self._step_clear_aperture_pick_mode and ("
    idx = press_src.find(marker)
    if idx < 0:
        notes.append("FAIL: could not locate the CA-pick guard block in _on_left_button_press")
        passed = False
    else:
        # Slice from the block to the next top-level 'if step_label is not None:' that
        # follows it -- the CA block body lives in between.
        tail = press_src[idx:]
        end = tail.find("if step_label is not None:")
        block = tail[:end] if end > 0 else tail[:1200]
        cancel_line = "if actor_key is None and self.cancel_active_3d_operation():"
        nag = "Set Clear Aperture: click the"
        c_pos = block.find(cancel_line)
        n_pos = block.find(nag)
        if c_pos < 0:
            notes.append(
                "FAIL: the CA-pick block has no empty-space escape -- expected "
                "'if actor_key is None and self.cancel_active_3d_operation(): return' (bugs/0135)"
            )
            passed = False
        elif n_pos >= 0 and c_pos > n_pos:
            notes.append(
                "FAIL: the CA-pick cancel escape sits AFTER the status nag -- it must come first "
                "so an empty click exits before the nag (bugs/0135)"
            )
            passed = False
        if not re.search(r"actor_key is None and self\.cancel_active_3d_operation", block):
            notes.append(
                "FAIL: the CA-pick escape is not gated on 'actor_key is None' -- a wrong-body "
                "click must still nudge, not cancel (bugs/0135)"
            )
            passed = False

    if verbose:
        notes.append(
            "checked: cancel_active_3d_operation resets the CA pick flag and is listed as an "
            "active op; the CA-pick block escapes on an empty (actor_key None) click before the nag"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0135: CA-pick empty-click cancels")
        return 0
    print("[FAIL] bugs/0135 CA-pick cancel guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
