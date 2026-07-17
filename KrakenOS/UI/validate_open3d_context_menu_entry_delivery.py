#!/usr/bin/env python3
"""Display-free guard: a 3D right-click menu ENTRY CLICK must deliver its command
(bugs/0348).

User report (flag_20260717_204504_767, LED-only scene, build-stamped 8cfb0aad):
"still unable to right click and snap the CA to optical axis." The opening menu
posted WITH the snap entry, the handler passed every probe -- yet clicking the
entry in the live app did nothing, silently, and had done so for the whole
0339/0344/0346/0347 saga.

Root cause
----------
  Tk delivers a clicked entry's command only AFTER unposting the menu (Tk
  menu.tcl ``tk::MenuInvoke``: ``MenuUnpost $menu`` first, then ``$menu invoke``).
  ``_popup_context_menu`` bound the menu's ``<Unmap>`` to the bugs/0336
  click-elsewhere dismiss, whose ``menu.destroy()`` therefore landed BETWEEN the
  unpost and the invoke: the command died with the widget as a background
  TclError ("invalid command name") the user never sees. EVERY entry of the two
  menus posted through ``_popup_context_menu`` (STEP body menu + pinned-opening
  menu) was a silent no-op, while probes calling ``menu.invoke()`` or the
  handlers directly kept passing. Reproduced end-to-end by
  ``bugs/probe_0348_menu_entry_click_delivery.py``.

Fix
---
  The MENU-bound ``<Unmap>``/``<FocusOut>`` teardown is DEFERRED one event-loop
  turn (``after_idle``) and identity-guarded (a newer menu posted meanwhile is
  left alone), so Tk's unpost -> invoke completes before the destroy. Scene-click
  dismissal (the widget ``<Button-*>`` backups and the primary press handlers)
  stays synchronous -- no entry invoke is pending on a scene click. The bugs/0343
  focus restore also skips ``focus_set`` while a modal grab is held, so an entry
  that opens a dialog keeps its keyboard focus.

What it checks (real methods on fake Tk objects)
------------------------------------------------
  1. Firing the menu's ``<Unmap>`` handler does NOT destroy the menu
     synchronously -- it schedules exactly one ``after_idle`` teardown.
  2. Running that deferred callback THEN tears the menu down (destroy + active
     cleared + focus restored).
  3. Identity guard: a NEWER menu posted before the old menu's deferred callback
     runs is left alone.
  4. The widget ``<Button-1>`` backup bind still dismisses synchronously.
  5. Focus restore honours a live modal grab (``grab_current`` non-None -> no
     ``focus_set``).
  6. Source contract: ``_popup_context_menu`` defers the menu-bound dismiss via
     ``after_idle``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_context_menu_entry_delivery

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


class _FakeWidget:
    def __init__(self):
        self.binds: dict[str, list[object]] = {}
        self.focus_set_calls = 0
        self.grab = None

    def bind(self, sequence, handler, add=None):
        self.binds.setdefault(str(sequence), []).append(handler)
        return f"bind{len(self.binds[str(sequence)])}"

    def unbind(self, sequence, bind_id):
        return None

    def grab_current(self):
        return self.grab

    def focus_set(self):
        self.focus_set_calls += 1


class _FakeMenu:
    def __init__(self, name="menu"):
        self.name = name
        self.binds: dict[str, list[object]] = {}
        self.destroyed = False
        self.unposted = False
        self.popup_calls = 0

    def bind(self, sequence, handler, add=None):
        self.binds.setdefault(str(sequence), []).append(handler)

    def tk_popup(self, x, y):
        self.popup_calls += 1

    def unpost(self):
        self.unposted = True

    def grab_release(self):
        return None

    def destroy(self):
        self.destroyed = True


class _FakeInspector:
    def __init__(self, widget):
        self._active_context_menu = None
        self._active_context_menu_binds = []
        self._vtk_widget = widget
        self.idle_callbacks: list[object] = []

    def after_idle(self, callback):
        self.idle_callbacks.append(callback)
        return f"after#{len(self.idle_callbacks)}"


class _FakeEvent:
    x_root = 100
    y_root = 100


def _make_service():
    from KrakenOS.UI.services import open3d_face_assignment as fa_mod

    Svc = fa_mod.Open3DFaceAssignmentService
    widget = _FakeWidget()
    insp = _FakeInspector(widget)
    svc = Svc.__new__(Svc)
    object.__setattr__(svc, "_inspector", insp)
    return svc, insp, widget


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services import open3d_face_assignment as fa_mod

    Svc = fa_mod.Open3DFaceAssignmentService
    failures: list[str] = []

    # 1) The menu <Unmap> handler must NOT destroy synchronously; it defers.
    svc, insp, widget = _make_service()
    menu = _FakeMenu("A")
    Svc._popup_context_menu(svc, menu, _FakeEvent())
    if insp._active_context_menu is not menu:
        failures.append("FAIL(1): posting must record the menu as active")
    unmap_handlers = menu.binds.get("<Unmap>", [])
    if len(unmap_handlers) != 1:
        failures.append(f"FAIL(1): expected one <Unmap> bind on the menu, got {len(unmap_handlers)}")
    else:
        unmap_handlers[0](None)  # Tk fires this DURING MenuUnpost, before the invoke
        if menu.destroyed:
            failures.append(
                "FAIL(1): <Unmap> destroyed the menu synchronously -- Tk has not delivered "
                "the clicked entry's command yet, so every menu entry becomes a silent no-op (bugs/0348)"
            )
        if len(insp.idle_callbacks) != 1:
            failures.append(f"FAIL(1): <Unmap> must schedule exactly one after_idle teardown, got {len(insp.idle_callbacks)}")

    # 2) The deferred callback then tears the menu down and restores focus.
    if not failures[:1] and insp.idle_callbacks:
        insp.idle_callbacks[0]()
        if not menu.destroyed:
            failures.append("FAIL(2): the deferred teardown must destroy the menu")
        if insp._active_context_menu is not None:
            failures.append("FAIL(2): the deferred teardown must clear the active menu")
        if widget.focus_set_calls < 1:
            failures.append("FAIL(2): the deferred teardown must hand focus back to the render pane (bugs/0343)")

    # 3) Identity guard: an old menu's deferred teardown leaves a newer menu alone.
    svc, insp, widget = _make_service()
    menu_a = _FakeMenu("A")
    Svc._popup_context_menu(svc, menu_a, _FakeEvent())
    menu_a.binds["<Unmap>"][0](None)  # entry click on A begins: teardown deferred
    menu_b = _FakeMenu("B")
    Svc._popup_context_menu(svc, menu_b, _FakeEvent())  # user right-clicks again fast
    for callback in list(insp.idle_callbacks):
        callback()  # A's deferred teardown fires now
    if menu_b.destroyed:
        failures.append("FAIL(3): an old menu's deferred teardown must NOT destroy the newer active menu")
    if insp._active_context_menu is not menu_b:
        failures.append("FAIL(3): the newer menu must stay active after the old deferred teardown runs")

    # 4) The widget <Button-1> backup bind still dismisses synchronously.
    svc, insp, widget = _make_service()
    menu = _FakeMenu("A")
    Svc._popup_context_menu(svc, menu, _FakeEvent())
    button_handlers = widget.binds.get("<Button-1>", [])
    if not button_handlers:
        failures.append("FAIL(4): the widget <Button-1> click-elsewhere backup bind is gone")
    else:
        button_handlers[-1](None)
        if not menu.destroyed:
            failures.append("FAIL(4): a scene click must still dismiss the menu synchronously (bugs/0336)")

    # 5) Focus restore honours a modal grab.
    svc, insp, widget = _make_service()
    menu = _FakeMenu("A")
    Svc._popup_context_menu(svc, menu, _FakeEvent())
    widget.grab = object()  # a modal dialog holds the grab
    Svc._dismiss_active_context_menu(svc)
    if widget.focus_set_calls != 0:
        failures.append("FAIL(5): dismiss must NOT steal focus while a modal grab is held (bugs/0348)")

    # 6) Source contract.
    src = inspect.getsource(Svc._popup_context_menu)
    if "after_idle" not in src:
        failures.append("FAIL(6): _popup_context_menu must defer the menu-bound dismiss via after_idle (bugs/0348)")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] 3D right-click menu entry clicks do not reliably deliver their commands")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] the menu-bound dismiss is deferred past Tk's unpost->invoke sequence, so a "
          "right-click menu entry click actually runs its command (bugs/0348)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
