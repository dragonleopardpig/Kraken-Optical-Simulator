#!/usr/bin/env python3
"""Display-free guard: a scene click dismisses a live right-click popup (bugs/0341).

User directive (imported LED, latest flag):
  "clicking elsewhere still not destroying right click pop up menu."

Root cause:
  bugs/0336 tried to dismiss the popup by binding ``<Button-1/2/3>`` on the VTK Tk
  widget with ``add="+"``. But ``left_press`` / ``middle_press`` / ``right_press``
  are bound on the SAME widget FIRST and ``return "break"`` on nearly every path,
  which aborts the trailing add="+" dismiss handler before it runs. So a left-click
  elsewhere in the scene never tore the popup down -- it stuck.

Fix:
  Dismiss from the PRIMARY press handlers themselves. ``left_press`` and
  ``middle_press`` now call ``_dismiss_active_context_menu`` at the top, before any
  pick / orbit / nav-cube snap -- those handlers always fire on a scene click, so the
  dismiss can no longer be shadowed. (A right-click elsewhere already replaced the
  popup via ``_popup_context_menu`` -> ``_dismiss_active_context_menu``.)

What it checks
--------------
  1. Source contract: BOTH ``left_press`` and ``middle_press`` (inside
     ``_install_pick_only_left_click_bindings``) call ``_dismiss_active_context_menu``.
  2. Behavioural: the ``_dismiss_active_context_menu`` primitive unposts the live menu
     and clears ``_active_context_menu`` / ``_active_context_menu_binds`` to empty,
     and is re-entrancy safe (a second call is a harmless no-op).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_context_menu_dismiss_on_click

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types


class _FakeMenu:
    def __init__(self) -> None:
        self.unposted = 0
        self.grab_released = 0
        self.destroyed = 0

    def unpost(self) -> None:
        self.unposted += 1

    def grab_release(self) -> None:
        self.grab_released += 1

    def destroy(self) -> None:
        self.destroyed += 1


def _check_source_contract() -> list[str]:
    from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService as MB

    failures: list[str] = []
    src = inspect.getsource(MB._install_pick_only_left_click_bindings)

    # Slice out each closure body so a stray reference elsewhere can't mask a miss.
    def _closure_body(name: str) -> str:
        marker = f"def {name}(event):"
        start = src.find(marker)
        if start < 0:
            return ""
        rest = src[start + len(marker):]
        # Next top-level "def <name>(" at the same indentation ends the closure.
        nxt = rest.find("\n        def ")
        return rest if nxt < 0 else rest[:nxt]

    for handler in ("left_press", "middle_press"):
        body = _closure_body(handler)
        if not body:
            failures.append(f"FAIL(1): could not locate the {handler} closure in the mouse bindings")
            continue
        if "_dismiss_active_context_menu" not in body:
            failures.append(
                f"FAIL(1): {handler} must call _dismiss_active_context_menu so a scene "
                f"click tears down a live right-click popup (bugs/0341)"
            )
    return failures


def _check_dismiss_primitive() -> list[str]:
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService as FA

    failures: list[str] = []
    inspector = types.SimpleNamespace(_active_context_menu=None, _active_context_menu_binds=[])
    svc = types.SimpleNamespace(_inspector=inspector)
    svc._dismiss_active_context_menu = types.MethodType(FA._dismiss_active_context_menu, svc)

    menu = _FakeMenu()
    inspector._active_context_menu = menu
    inspector._active_context_menu_binds = []  # no real widgets to unbind in a headless run

    svc._dismiss_active_context_menu()
    if menu.unposted < 1:
        failures.append("FAIL(2): _dismiss_active_context_menu must unpost the live menu")
    if inspector._active_context_menu is not None:
        failures.append("FAIL(2): _dismiss_active_context_menu must clear _active_context_menu to None")
    if inspector._active_context_menu_binds:
        failures.append("FAIL(2): _dismiss_active_context_menu must clear _active_context_menu_binds")

    # Re-entrancy: a second call (as our own unpost's <Unmap> would trigger) is a no-op.
    try:
        svc._dismiss_active_context_menu()
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"FAIL(2): a second _dismiss_active_context_menu must be a no-op, raised {exc!r}")
    return failures


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    failures.extend(_check_source_contract())
    failures.extend(_check_dismiss_primitive())
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] a scene click does not reliably dismiss the right-click popup")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] left_press/middle_press dismiss any live right-click popup, and the "
          "_dismiss_active_context_menu primitive unposts + clears re-entrantly (bugs/0341)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
