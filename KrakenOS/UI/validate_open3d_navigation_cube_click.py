#!/usr/bin/env python3
"""Display-free guard for bugs/0157: a click on the Open 3D navigation cube actually
snaps/rotates the camera.

Why it exists (user report, follow-up to bugs/0156):
  "I see XYZ with additional -X, -Y and -Z, How to use? I click the view never change."

The cube (``vtkCameraOrientationWidget``, bugs/0156) renders but was deaf: it reacts
to the interactor's ``LeftButtonPressEvent`` / ``MouseMoveEvent`` /
``LeftButtonReleaseEvent``, but the canvas's ``_install_pick_only_left_click_bindings``
REPLACES the interactor's Tk button bindings and dispatches a plain pick by calling
the app handler directly -- the interactor's button events are never fired, so the
cube never sees the click. The fix forwards press/move/release to the cube from the
Tk closures when the cursor is over its gizmo (``Open3DMouseBindingsService`` helpers
``_press_navigation_cube_if_hit`` / ``_drag_navigation_cube_if_active`` /
``_release_navigation_cube_if_active``), gated on the cube's interaction state so a
scene click falls through untouched, and skipped under Ctrl so Ctrl-drag still orbits.

What it checks (no display required) -- the forwarding contract against a fake cube +
fake interactor that record the VTK events the real widget listens for:
  A. No cube (or no interactor, or disabled) -> no press forwarded.
  B. Cursor over the cube (state != 0) -> a MouseMove probe THEN a LeftButtonPress is
     forwarded, the active flag is set, and the helper returns True (caller breaks).
  C. Cursor over the scene (state 0) -> the MouseMove probe runs but NO press is
     forwarded, flag stays clear, helper returns False (scene pick proceeds).
  D. Ctrl held -> no press forwarded even over the cube (Ctrl-drag orbits).
  E. Drag/release are no-ops unless a cube press is active; the release forwards
     exactly one LeftButtonReleaseEvent (the event that snaps) and clears the flag.
  F. Source contract -- _install_pick_only_left_click_bindings wires all three
     forwarding hooks.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_navigation_cube_click

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


class _FakeRepresentation:
    def __init__(self, state: int) -> None:
        self._state = state

    def GetInteractionState(self) -> int:
        return self._state


class _FakeCube:
    def __init__(self, enabled: bool = True, state: int = 1) -> None:
        self._enabled = enabled
        self._rep = _FakeRepresentation(state)

    def GetEnabled(self) -> int:
        return 1 if self._enabled else 0

    def GetRepresentation(self):
        return self._rep


class _FakeInteractor:
    def __init__(self, ctrl: int = 0) -> None:
        self._ctrl = ctrl
        self.calls: list[str] = []

    def GetControlKey(self) -> int:
        return self._ctrl

    def MouseMoveEvent(self) -> None:
        self.calls.append("MouseMoveEvent")

    def LeftButtonPressEvent(self) -> None:
        self.calls.append("LeftButtonPressEvent")

    def LeftButtonReleaseEvent(self) -> None:
        self.calls.append("LeftButtonReleaseEvent")


class _FakeInspector:
    """Bare attribute bag standing in for Kraken3DInspector. The service proxies all
    reads/writes here via __getattr__/__setattr__, so the helpers see/set these."""

    def __init__(self, cube, interactor) -> None:
        self._camera_orientation_widget = cube
        self._vtk_interactor = interactor
        self._nav_cube_press_active = False


def _service(cube, interactor):
    from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService

    return Open3DMouseBindingsService(_FakeInspector(cube, interactor))


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # --- A: nothing to forward when the cube is absent/disabled/no interactor ---
    for label, cube, inter in (
        ("no cube", None, _FakeInteractor()),
        ("disabled cube", _FakeCube(enabled=False), _FakeInteractor()),
        ("no interactor", _FakeCube(), None),
    ):
        svc = _service(cube, inter)
        got = svc._press_navigation_cube_if_hit()
        if got is not False:
            failures.append(f"A FAIL ({label}): press helper returned {got!r}, want False")
        if inter is not None and inter.calls:
            failures.append(
                f"A FAIL ({label}): forwarded {inter.calls!r} to the interactor, "
                "want nothing (no VTK button events when the cube is unavailable)"
            )
        if cube is not None and getattr(svc, "_nav_cube_press_active", None):
            failures.append(f"A FAIL ({label}): set the active flag with no real press")

    # --- B: cursor over a handle (state != 0) -> probe move THEN press, flag set --
    inter = _FakeInteractor()
    svc = _service(_FakeCube(state=1), inter)
    got = svc._press_navigation_cube_if_hit()
    if got is not True:
        failures.append(f"B FAIL: press over a handle returned {got!r}, want True")
    if inter.calls != ["MouseMoveEvent", "LeftButtonPressEvent"]:
        failures.append(
            f"B FAIL: forwarded {inter.calls!r}, want a MouseMove probe THEN a "
            "LeftButtonPress (the move resolves the handle, the press grabs it)"
        )
    if not getattr(svc, "_nav_cube_press_active", False):
        failures.append("B FAIL: _nav_cube_press_active not set after a cube press")

    # --- C: cursor over the scene (state 0) -> probe only, NO press, no flag ------
    inter = _FakeInteractor()
    svc = _service(_FakeCube(state=0), inter)
    got = svc._press_navigation_cube_if_hit()
    if got is not False:
        failures.append(f"C FAIL: press over the scene returned {got!r}, want False")
    if "LeftButtonPressEvent" in inter.calls:
        failures.append(
            "C FAIL: forwarded a LeftButtonPress over the scene (state 0) -- the "
            "scene pick would be stolen by the cube"
        )
    if inter.calls != ["MouseMoveEvent"]:
        failures.append(
            f"C FAIL: forwarded {inter.calls!r}, want exactly the MouseMove probe "
            "(needed to evaluate the handle) and nothing else"
        )
    if getattr(svc, "_nav_cube_press_active", False):
        failures.append("C FAIL: active flag set despite no handle under the cursor")

    # --- D: Ctrl held -> no press even over a handle (Ctrl-drag still orbits) -----
    inter = _FakeInteractor(ctrl=1)
    svc = _service(_FakeCube(state=1), inter)
    got = svc._press_navigation_cube_if_hit()
    if got is not False:
        failures.append(f"D FAIL: Ctrl-press over a handle returned {got!r}, want False")
    if inter.calls:
        failures.append(
            f"D FAIL: Ctrl-press forwarded {inter.calls!r}, want nothing -- Ctrl is "
            "the orbit modifier and must reach the camera-orbit path untouched"
        )
    if getattr(svc, "_nav_cube_press_active", False):
        failures.append("D FAIL: Ctrl-press set the active flag")

    # --- E: drag/release gate on the active flag; release snaps + clears ----------
    # Not active: both helpers no-op and forward nothing.
    inter = _FakeInteractor()
    svc = _service(_FakeCube(state=1), inter)
    if svc._drag_navigation_cube_if_active() is not False:
        failures.append("E FAIL: drag helper acted with no active cube press")
    if svc._release_navigation_cube_if_active() is not False:
        failures.append("E FAIL: release helper acted with no active cube press")
    if inter.calls:
        failures.append(f"E FAIL: idle drag/release forwarded {inter.calls!r}, want nothing")

    # Active: a full press -> drag -> release forwards move, press, move, release and
    # leaves the flag clean.
    inter = _FakeInteractor()
    svc = _service(_FakeCube(state=1), inter)
    svc._press_navigation_cube_if_hit()
    if svc._drag_navigation_cube_if_active() is not True:
        failures.append("E FAIL: drag helper returned non-True while a press is active")
    if svc._release_navigation_cube_if_active() is not True:
        failures.append("E FAIL: release helper returned non-True while a press is active")
    if inter.calls != [
        "MouseMoveEvent",
        "LeftButtonPressEvent",
        "MouseMoveEvent",
        "LeftButtonReleaseEvent",
    ]:
        failures.append(
            f"E FAIL: full press/drag/release forwarded {inter.calls!r}, want "
            "[MouseMove, LeftButtonPress, MouseMove, LeftButtonRelease]"
        )
    if inter.calls.count("LeftButtonReleaseEvent") != 1:
        failures.append("E FAIL: the release must forward exactly one LeftButtonReleaseEvent")
    if getattr(svc, "_nav_cube_press_active", True):
        failures.append("E FAIL: _nav_cube_press_active not cleared after the release")
    # A second release is now a no-op (flag already cleared).
    if svc._release_navigation_cube_if_active() is not False:
        failures.append("E FAIL: a second release acted despite the flag being clear")

    # --- F: the closures actually call the three forwarding hooks ----------------
    from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService

    install_src = inspect.getsource(
        Open3DMouseBindingsService._install_pick_only_left_click_bindings
    )
    for needle in (
        "self._press_navigation_cube_if_hit()",
        "self._drag_navigation_cube_if_active()",
        "self._release_navigation_cube_if_active()",
    ):
        if needle not in install_src:
            failures.append(
                f"F FAIL: _install_pick_only_left_click_bindings does not call "
                f"`{needle}` -- the cube forwarding hook is not wired into the closures"
            )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0157 Open 3D navigation cube click forwarding")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] bugs/0157: a click over the navigation cube forwards press/move/"
        "release so the camera snaps; a scene click and Ctrl-drag fall through"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
