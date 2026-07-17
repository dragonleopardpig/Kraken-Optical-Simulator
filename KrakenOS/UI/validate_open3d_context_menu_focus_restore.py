#!/usr/bin/env python3
"""Display-free guard: dismissing a popup restores the 's' hotkey focus (bugs/0343).

User directive (imported LED, latest flag):
  "right click elsewhere closes the pop up, but shortcut 's' no longer woring. I right
   click again and click the menu grayed out item, it closes, then the 's' shorcut can
   flag again."

Root cause:
  bugs/0341 made a scene click tear the popup down by calling
  ``_dismiss_active_context_menu`` -> ``menu.destroy()``. But ``tk_popup`` had stolen
  keyboard focus for the menu, and destroying it OURSELVES (unlike a menu-item click)
  leaves focus in limbo, so the Toplevel-level ``<KeyPress-s>`` flag-bug hotkey stops
  firing until the user reopens a menu and dismisses it by clicking an item (which
  restores focus the Tk way).

Fix:
  After tearing down a live menu, ``_dismiss_active_context_menu`` hands keyboard focus
  back to the render pane (``_vtk_widget.focus_set()``) so ``s`` keeps working. Focus is
  only restored when a menu was actually dismissed -- the pre-post clear (no live menu)
  must NOT steal focus.

What it checks
--------------
  1. A live menu dismissed -> ``_vtk_widget.focus_set()`` is called (and the menu is
     unposted + destroyed).
  2. No live menu -> ``focus_set`` is NOT called (the pre-post clear leaves focus alone).
  3. Source contract: ``_dismiss_active_context_menu`` references both a ``_vtk_widget``
     lookup and ``focus_set``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_context_menu_focus_restore

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


class _FakeWidget:
    def __init__(self) -> None:
        self.focus_calls = 0

    def focus_set(self) -> None:
        self.focus_calls += 1


def _make_svc(*, menu, widget):
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService as FA

    inspector = types.SimpleNamespace(
        _active_context_menu=menu,
        _active_context_menu_binds=[],
        _vtk_widget=widget,
    )
    svc = types.SimpleNamespace(_inspector=inspector)
    svc._dismiss_active_context_menu = types.MethodType(FA._dismiss_active_context_menu, svc)
    return svc, inspector


def _check_behaviour() -> list[str]:
    failures: list[str] = []

    # 1. A live menu dismissed -> focus handed back to the render pane.
    menu = _FakeMenu()
    widget = _FakeWidget()
    svc, inspector = _make_svc(menu=menu, widget=widget)
    svc._dismiss_active_context_menu()
    if menu.destroyed < 1:
        failures.append("FAIL(1): dismissing a live menu must destroy it")
    if widget.focus_calls < 1:
        failures.append(
            "FAIL(1): dismissing a live menu must restore keyboard focus to the render "
            "pane so the 's' flag hotkey keeps firing (bugs/0343)"
        )
    if inspector._active_context_menu is not None:
        failures.append("FAIL(1): dismissing must clear _active_context_menu to None")

    # 2. No live menu -> the pre-post clear must not steal focus.
    widget2 = _FakeWidget()
    svc2, _ = _make_svc(menu=None, widget=widget2)
    svc2._dismiss_active_context_menu()
    if widget2.focus_calls != 0:
        failures.append(
            "FAIL(2): with no live menu, _dismiss_active_context_menu must NOT call "
            "focus_set (a pre-post clear should leave focus alone)"
        )
    return failures


def _check_source_contract() -> list[str]:
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService as FA

    failures: list[str] = []
    src = inspect.getsource(FA._dismiss_active_context_menu)
    if "_vtk_widget" not in src:
        failures.append("FAIL(3): _dismiss_active_context_menu must look up the _vtk_widget to refocus")
    if "focus_set" not in src:
        failures.append("FAIL(3): _dismiss_active_context_menu must call focus_set to restore the hotkey")
    return failures


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    failures.extend(_check_behaviour())
    failures.extend(_check_source_contract())
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] the 's' flag hotkey focus is not restored after a popup dismiss")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] dismissing a live right-click popup restores render-pane focus so the "
          "'s' flag hotkey keeps working; the pre-post clear leaves focus alone (bugs/0343)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
