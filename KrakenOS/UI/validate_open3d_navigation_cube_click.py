#!/usr/bin/env python3
"""Display-free guard for bugs/0156: a click on the Open 3D navigation cube actually
snaps the camera (a face/edge/corner orientation) or applies a discrete-step arrow.

Why it exists (user report on the old widget):
  "I click the view never change."

The app owns every left-click at the Tk level -- ``_install_pick_only_left_click_
bindings`` REPLACES the interactor's Tk button bindings and dispatches a plain pick by
calling the app handler directly, so the interactor's button events never fire. The
custom :class:`NavigationCube` therefore does its OWN picking: ``left_press`` asks the
inspector's ``_handle_navigation_cube_left_press`` for first refusal after
``set_event_info``, and the widget's ``handle_left_press`` picks the arrow renderer
first (a roll/azimuth/elevation step) then the cube surface (classified into one of the
26 face/edge/corner orientations). A Ctrl-click is left to the camera-orbit path.

What it checks (no display required):
  Widget ``handle_left_press`` (a NavigationCube with faked pickers/renderers):
    A. Out-of-viewport / unavailable -> False, nothing picked.
    B. An arrow hit -> ``apply_step(kind)`` fires, returns True, the cube is NOT picked.
    C. A cube-face hit -> the local point is classified and ``apply_orientation`` fires
       with the matching pose, returns True.
    D. A miss (no arrow, cube pick misses) -> False, neither callback fires.
  Inspector seam ``_handle_navigation_cube_left_press`` (real method, fake self):
    E. No cube / unavailable cube -> False (no pick attempted).
    F. Ctrl held -> False, the widget is NOT asked (Ctrl still orbits).
    G. Plain click -> forwards the interactor event position to the widget and
       returns the widget's verdict.
  Source contract:
    H. ``left_press`` calls ``_handle_navigation_cube_left_press``; the retired
       press/drag/release forwarding helpers are GONE (no VTK button-event forwarding).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_navigation_cube_click

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np


class _FakeActor:
    """A stand-in prop; identity (``is``) is what the widget matches on."""


class _FakePicker:
    def __init__(self, actor=None, hit=1, local=(0.0, 0.0, 0.0)) -> None:
        self._actor = actor
        self._hit = hit
        self._local = tuple(float(c) for c in local)
        self.pick_calls = 0

    def Pick(self, x, y, z, renderer) -> int:
        self.pick_calls += 1
        return int(self._hit)

    def GetActor(self):
        return self._actor

    def GetPickPosition(self):
        return self._local


class _FakeWindow:
    def __init__(self, size=(200, 200)) -> None:
        self._size = size

    def GetSize(self):
        return self._size


def _widget(*, available=True, arrow_actor=None, arrow_kind=None,
            cube_hit=1, cube_actor=None, local=(0.0, 0.0, 0.0)):
    """A NavigationCube built via __new__ (no VTK window) with faked pickers so the
    real handle_left_press logic runs display-free."""
    from KrakenOS.UI.services.nav_cube_widget import NavigationCube

    cube = NavigationCube.__new__(NavigationCube)
    cube.available = available
    cube._render_window = _FakeWindow()
    cube._arrow_renderer = object()
    cube._cube_renderer = object()
    cube._pick_cube_actor = cube_actor if cube_actor is not None else _FakeActor()
    cube._arrow_picker = _FakePicker(actor=arrow_actor)
    cube._cube_picker = _FakePicker(actor=cube._pick_cube_actor if cube_hit else _FakeActor(),
                                    hit=cube_hit, local=local)
    cube._arrow_actors = [(arrow_actor, arrow_kind)] if arrow_actor is not None else []
    cube.orient_hits = []
    cube.step_hits = []
    cube._apply_orientation = lambda offset, up: cube.orient_hits.append((tuple(offset), tuple(up)))
    cube._apply_step = lambda kind: cube.step_hits.append(kind)
    return cube


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services.nav_cube_orientation import classify_pick, orientation_pose

    failures: list[str] = []

    # --- A: out of the corner viewport / unavailable -> False, no pick ----------
    cube = _widget()
    if cube.handle_left_press(5, 5) is not False:  # (5,5) is outside the 0.80..0.995 corner
        failures.append("A FAIL: a click outside the corner viewport was consumed")
    if cube._arrow_picker.pick_calls or cube._cube_picker.pick_calls:
        failures.append("A FAIL: an out-of-viewport click still ran a picker")
    cube = _widget(available=False)
    if cube.handle_left_press(195, 195) is not False:
        failures.append("A FAIL: an unavailable cube consumed a click")

    # --- B: an arrow hit -> apply_step, returns True, cube NOT picked -----------
    arrow = _FakeActor()
    cube = _widget(arrow_actor=arrow, arrow_kind="az_left")
    got = cube.handle_left_press(195, 195)
    if got is not True:
        failures.append(f"B FAIL: an arrow click returned {got!r}, want True")
    if cube.step_hits != ["az_left"]:
        failures.append(f"B FAIL: arrow click routed steps {cube.step_hits!r}, want ['az_left']")
    if cube.orient_hits:
        failures.append(f"B FAIL: an arrow click also fired an orientation {cube.orient_hits!r}")
    if cube._cube_picker.pick_calls:
        failures.append("B FAIL: an arrow hit still went on to pick the cube surface")

    # --- C: a cube-face hit -> classify + apply_orientation with the pose -------
    cube = _widget(local=(0.5, 0.0, 0.0))  # +X face centre in the unit pick-cube
    got = cube.handle_left_press(195, 195)
    if got is not True:
        failures.append(f"C FAIL: a cube-face click returned {got!r}, want True")
    if cube.step_hits:
        failures.append(f"C FAIL: a cube-face click fired a step {cube.step_hits!r}")
    want_offset, want_up = orientation_pose(classify_pick((0.5, 0.0, 0.0)))
    if not cube.orient_hits:
        failures.append("C FAIL: a cube-face click did not fire apply_orientation")
    else:
        got_offset, got_up = cube.orient_hits[0]
        if float(np.linalg.norm(np.array(got_offset) - np.array(want_offset))) > 1e-9:
            failures.append(
                f"C FAIL: face pick offset {got_offset!r} != orientation_pose {want_offset!r}"
            )

    # --- D: a miss (no arrow, cube pick misses) -> False, no callbacks ----------
    cube = _widget(cube_hit=0)
    got = cube.handle_left_press(195, 195)
    if got is not False:
        failures.append(f"D FAIL: a miss returned {got!r}, want False")
    if cube.step_hits or cube.orient_hits:
        failures.append(f"D FAIL: a miss still fired a callback ({cube.step_hits!r}/{cube.orient_hits!r})")

    # --- E/F/G: the inspector seam _handle_navigation_cube_left_press -----------
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    class _FakeInteractor:
        def __init__(self, ctrl=0, pos=(30, 40)):
            self._ctrl = ctrl
            self._pos = pos
        def GetControlKey(self):
            return self._ctrl
        def GetEventPosition(self):
            return self._pos

    class _RecordingCube:
        def __init__(self, available=True, verdict=True):
            self.available = available
            self.verdict = verdict
            self.calls = []
        def handle_left_press(self, x, y):
            self.calls.append((x, y))
            return self.verdict

    class _SeamFake:
        def __init__(self, cube, interactor):
            self._navigation_cube = cube
            self._vtk_interactor = interactor

    # E: no cube / unavailable cube -> False
    if Kraken3DInspector._handle_navigation_cube_left_press(_SeamFake(None, _FakeInteractor())) is not False:
        failures.append("E FAIL: a missing cube did not yield False")
    unavail = _RecordingCube(available=False)
    if Kraken3DInspector._handle_navigation_cube_left_press(_SeamFake(unavail, _FakeInteractor())) is not False:
        failures.append("E FAIL: an unavailable cube did not yield False")
    if unavail.calls:
        failures.append("E FAIL: an unavailable cube was still asked to pick")

    # F: Ctrl held -> False, widget not asked
    ctrl_cube = _RecordingCube()
    if Kraken3DInspector._handle_navigation_cube_left_press(
        _SeamFake(ctrl_cube, _FakeInteractor(ctrl=1))
    ) is not False:
        failures.append("F FAIL: a Ctrl-click was consumed by the cube (must orbit instead)")
    if ctrl_cube.calls:
        failures.append("F FAIL: a Ctrl-click still asked the widget to pick")

    # G: plain click -> forwards the event position, returns the widget verdict
    ok_cube = _RecordingCube(verdict=True)
    got = Kraken3DInspector._handle_navigation_cube_left_press(
        _SeamFake(ok_cube, _FakeInteractor(pos=(30, 40)))
    )
    if got is not True:
        failures.append(f"G FAIL: a consumed click returned {got!r}, want True")
    if ok_cube.calls != [(30, 40)]:
        failures.append(f"G FAIL: forwarded {ok_cube.calls!r} to the widget, want [(30, 40)]")
    miss_cube = _RecordingCube(verdict=False)
    if Kraken3DInspector._handle_navigation_cube_left_press(
        _SeamFake(miss_cube, _FakeInteractor())
    ) is not False:
        failures.append("G FAIL: a widget-declined click did not return False")

    # --- H: source contract -- new hook wired, old forwarding helpers gone ------
    from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService

    install_src = inspect.getsource(
        Open3DMouseBindingsService._install_pick_only_left_click_bindings
    )
    if "self._handle_navigation_cube_left_press()" not in install_src:
        failures.append(
            "H FAIL: left_press does not call _handle_navigation_cube_left_press -- the "
            "cube would never see a click (bugs/0156 regressed)"
        )
    mod_src = inspect.getsource(Open3DMouseBindingsService)
    for dead in (
        "_press_navigation_cube_if_hit",
        "_drag_navigation_cube_if_active",
        "_release_navigation_cube_if_active",
    ):
        if dead in mod_src:
            failures.append(
                f"H FAIL: the retired forwarding helper `{dead}` is still present -- the "
                "custom cube does its own picking, no VTK button-event forwarding remains"
            )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0156 Open 3D navigation cube click routing")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] bugs/0156: a click over the navigation cube snaps the camera (face/edge/"
        "corner) or applies a step arrow; a scene click and Ctrl-click fall through"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
