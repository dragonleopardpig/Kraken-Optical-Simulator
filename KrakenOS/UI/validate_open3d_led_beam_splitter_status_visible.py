#!/usr/bin/env python3
"""Display-free guard for bugs/0322: the LED right-click "Add Beam Splitter to LED"
outcome must be shown on the 3D-INSPECTOR's OWN status bar, never only on the editor's
main-window bar.

Why (bugs/0322 -- "right click add BS cube still shows nothing"): the one-click command
``editor.add_beam_splitter_to_led`` narrates success AND every graceful stop (no
clear-aperture opening, overlay failed, promotion failed, ...) on ``editor.status_var``,
which is the MAIN window's status bar. But the user is looking at the separate 3D
inspector Toplevel, whose visible bar is the inspector's own ``status_var``. The old
context handler ignored the command's return value and only echoed to ``editor.status_var``
on an exception -- so a graceful stop, or even a success, left the inspector silent: no BS
and no message == "nothing happened". The command itself works headless (5 auto-detect
candidates on the AZ85/ILS0202 scene, promotes a real 85 mm BS row); the defect is that
its feedback is invisible where the user is looking. The service proxies attribute access
to the inspector, so inside it ``self.status_var`` IS the inspector bar and
``self.editor.status_var`` is the hidden main-window bar.

What it checks (behavioural, tk-free): invoking ``_add_beam_splitter_to_led_from_context``
mirrors the command's message onto the INSPECTOR bar for
  A. success (command returns a summary dict) -- the rich success line is shown;
  B. graceful stop (command returns None with a reason on the main bar) -- the exact
     reason is relayed (not swallowed), and the stop is logged;
  C. graceful stop with NO reason set -- a computed non-empty fallback is shown;
  D. exception -- a visible "Add Beam Splitter to LED failed: ..." line is shown + logged.
  E. source contract: the handler reads ``self.editor.status_var`` and routes through
     ``_set_inspector_status`` -> ``self.status_var`` (the visible inspector bar).

Red/green: the pre-0322 handler leaves the inspector bar untouched in A/B/C (and only sets
the *editor* bar in D), so A-D all fail on the old source and pass on the fixed source.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_beam_splitter_status_visible

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace


class _Var:
    """A minimal tk.StringVar stand-in that stores the last value set."""

    def __init__(self, value: str = "") -> None:
        self.value = str(value)

    def set(self, value) -> None:
        self.value = str(value)

    def get(self) -> str:
        return self.value


def _build_service(command):
    """Wire a service whose editor.add_beam_splitter_to_led is ``command`` (a callable
    ``kind -> value`` that may set editor.status_var and/or raise). Returns
    (service, editor_bar, inspector_bar, debug_log)."""
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    editor_bar = _Var()
    inspector_bar = _Var()
    debug_log: list[str] = []
    editor = SimpleNamespace(
        add_beam_splitter_to_led=command,
        status_var=editor_bar,
        append_debug=lambda msg, *a, **k: debug_log.append(str(msg)),
    )
    inspector = SimpleNamespace(
        editor=editor,
        status_var=inspector_bar,
        append_debug=lambda *a, **k: None,
    )
    return Open3DFaceAssignmentService(inspector), editor_bar, inspector_bar, debug_log


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    SUCCESS_LINE = "Added cube beam splitter to the LED (S9, side 85.0 mm); coating on S001/F003."
    STOP_LINE = (
        "Add Beam Splitter to LED: could not find the LED clear-aperture opening. "
        "Right-click the LED window -> Set as Clear Aperture, then retry."
    )

    # A) success: command sets the rich success line on the (hidden) editor bar + returns a dict.
    def _ok(kind):
        editor_bar_ref["bar"].set(SUCCESS_LINE)
        return {"row_index": 9, "kind": kind}

    editor_bar_ref: dict = {}
    svc, editor_bar, inspector_bar, _dbg = _build_service(_ok)
    editor_bar_ref["bar"] = editor_bar
    svc._add_beam_splitter_to_led_from_context("cube")
    if inspector_bar.get() != SUCCESS_LINE:
        failures.append(
            f"A FAIL: success not mirrored to the inspector bar; got {inspector_bar.get()!r}"
        )

    # B) graceful stop: command sets a reason on the editor bar + returns None.
    def _stop(kind):
        editor_bar_ref2["bar"].set(STOP_LINE)
        return None

    editor_bar_ref2: dict = {}
    svc, editor_bar, inspector_bar, dbg = _build_service(_stop)
    editor_bar_ref2["bar"] = editor_bar
    svc._add_beam_splitter_to_led_from_context("cube")
    if inspector_bar.get() != STOP_LINE:
        failures.append(
            f"B FAIL: graceful-stop reason not relayed to the inspector bar; got {inspector_bar.get()!r}"
        )
    if not any("added nothing" in m.lower() or "clear-aperture" in m.lower() for m in dbg):
        failures.append(f"B FAIL: graceful stop was not logged to append_debug; log={dbg}")

    # C) graceful stop with NO reason set anywhere -> a non-empty computed fallback shows.
    def _stop_silent(kind):
        return None

    svc, editor_bar, inspector_bar, _dbg = _build_service(_stop_silent)
    svc._add_beam_splitter_to_led_from_context("plate")
    shown = inspector_bar.get()
    if not shown.strip():
        failures.append("C FAIL: silent graceful stop left the inspector bar EMPTY (still 'nothing')")
    if "nothing" not in shown.lower() and "add beam splitter" not in shown.lower():
        failures.append(f"C FAIL: fallback message not informative; got {shown!r}")

    # D) exception -> visible failure line on the inspector bar + logged.
    def _boom(kind):
        raise ValueError("cache write blew up")

    svc, editor_bar, inspector_bar, dbg = _build_service(_boom)
    svc._add_beam_splitter_to_led_from_context("cube")
    shown = inspector_bar.get()
    if "add beam splitter to led failed" not in shown.lower():
        failures.append(f"D FAIL: exception not shown on the inspector bar; got {shown!r}")
    if "cache write blew up" not in shown:
        failures.append(f"D FAIL: exception detail missing from the inspector bar; got {shown!r}")
    if not any("failed" in m.lower() for m in dbg):
        failures.append(f"D FAIL: exception not logged to append_debug; log={dbg}")

    # E) source contract.
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    handler_src = inspect.getsource(
        Open3DFaceAssignmentService._add_beam_splitter_to_led_from_context
    )
    if "self.editor.status_var.get()" not in handler_src:
        failures.append("E FAIL: handler no longer reads the command's message from self.editor.status_var")
    if "_set_inspector_status" not in handler_src:
        failures.append("E FAIL: handler no longer routes through _set_inspector_status")
    setter = getattr(Open3DFaceAssignmentService, "_set_inspector_status", None)
    if setter is None:
        failures.append("E FAIL: _set_inspector_status helper is missing (feedback cannot reach the inspector bar)")
    elif "self.status_var.set(" not in inspect.getsource(setter):
        failures.append(
            "E FAIL: _set_inspector_status does not set self.status_var (the visible inspector bar)"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0322 Add Beam Splitter to LED must show its outcome on the 3D-inspector bar")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] Add Beam Splitter to LED mirrors success/stop/error to the visible 3D-inspector "
        "status bar (bugs/0322)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
