#!/usr/bin/env python3
"""Display-free guard for the Alt-hover edge mode actually FIRING live (bugs/0324).

Follow-up to bugs/0323. That fix gated the whole-face->nearest-edge refinement on
``_edge_pick_alt_active`` and every display-free check passed -- yet in the running
app holding Alt did nothing. Root cause (two coupled event streams):

  * The scene FEATURE hover runs on the VTK ``MouseMoveEvent`` observer
    (``_on_mouse_move``). The vtkTkRenderWindowInteractor fires that from its OWN
    ``<Motion>`` Tk binding, installed at widget construction -- BEFORE KrakenOS's
    ``hover_motion`` (bound with add="+"), the one that records the Alt flag.
  * So on the frame Alt first changes, the pick read the flag from the PREVIOUS
    motion (one frame stale). And pressing Alt with the mouse perfectly still
    produced no ``<Motion>`` at all -> neither the flag update nor a re-pick ran.
    "Alt hover does not work."

Fix (both focus-independent, no dependence on a mouse nudge):
  1. ``_refresh_edge_pick_alt_state(active)`` sets the flag and, ONLY when it
     actually changed, calls ``_refire_scene_hover_pick`` -- which resets the move
     throttle and re-invokes the VTK ``MouseMoveEvent`` at the cursor's last
     position, so the highlight promotes (face->edge) / demotes immediately.
  2. ``hover_motion`` remembers the previous Alt state and, on a transition while
     passively hovering the scene, re-fires the pick (closes the one-frame lag for
     the moving-mouse case).
  3. The Alt key itself is tracked on the inspector Toplevel via
     ``<KeyPress/KeyRelease-Alt_L/Alt_R>`` (X11 modifier keys don't auto-repeat),
     so a STATIONARY Alt press/release flips the mode with the mouse still.
  4. ``_refire_scene_hover_pick`` is guarded on the pointer being over the 3D
     widget so an Alt tap while the cursor rests on the tree can't re-pick a stale
     scene position; a ``<FocusOut>`` drops the mode so an Alt-Tab can't wedge it.

What it checks (all display-free, real methods on fake state)
------------------------------------------------------------
  A. No-op: ``_refresh_edge_pick_alt_state`` with the SAME value sets the flag but
     does NOT re-fire (no synthetic MouseMoveEvent).
  B. Transition + pointer over widget: sets the flag, resets the throttle to 0,
     and fires exactly one MouseMoveEvent.
  C. Transition + pointer NOT over widget: flag still set, but NO re-fire.
  D. Transition + no interactor: flag set, no crash, no re-fire.
  E. ``_pointer_over_vtk_widget`` geometry: True inside, False outside.
  F. Source wiring: ``hover_motion`` computes ``alt_changed`` and calls
     ``_refire_scene_hover_pick`` on a change; the four Alt_L/Alt_R KeyPress/
     KeyRelease sequences are bound on the Toplevel; ``_refresh_edge_pick_alt_state``
     re-fires only on a change.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_alt_hover_refire

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types


class _FakeInteractor:
    def __init__(self) -> None:
        self.move_events = 0

    def MouseMoveEvent(self) -> None:
        self.move_events += 1


class _FakeWidget:
    """Minimal winfo_* surface; ``over`` decides if the pointer sits inside."""

    def __init__(self, over: bool) -> None:
        self._over = bool(over)

    def winfo_pointerx(self) -> int:
        return 50 if self._over else 5000

    def winfo_pointery(self) -> int:
        return 50

    def winfo_rootx(self) -> int:
        return 0

    def winfo_rooty(self) -> int:
        return 0

    def winfo_width(self) -> int:
        return 100

    def winfo_height(self) -> int:
        return 100


def _stub(*, alt=False, over=True, interactor=True):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    class _Stub:
        _refresh_edge_pick_alt_state = Kraken3DInspector._refresh_edge_pick_alt_state
        _refire_scene_hover_pick = Kraken3DInspector._refire_scene_hover_pick
        _pointer_over_vtk_widget = Kraken3DInspector._pointer_over_vtk_widget

    s = _Stub()
    s._edge_pick_alt_active = bool(alt)
    s._mouse_move_last_ts = 123.0
    s._vtk_widget = _FakeWidget(over)
    s._vtk_interactor = _FakeInteractor() if interactor else None
    return s


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services import open3d_mouse_bindings as mb_mod
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    failures: list[str] = []

    # A) No change -> flag set, but no synthetic re-pick.
    s = _stub(alt=False, over=True)
    s._refresh_edge_pick_alt_state(False)
    if s._edge_pick_alt_active is not False:
        failures.append("FAIL(A): equal-value call must leave the flag set (False)")
    if s._vtk_interactor.move_events != 0:
        failures.append("FAIL(A): equal-value call must NOT re-fire the hover pick")
    if s._mouse_move_last_ts != 123.0:
        failures.append("FAIL(A): equal-value call must not touch the move throttle")

    # B) Transition, pointer over the widget -> flag set, throttle reset, ONE re-fire.
    s = _stub(alt=False, over=True)
    s._refresh_edge_pick_alt_state(True)
    if s._edge_pick_alt_active is not True:
        failures.append("FAIL(B): transition must set the Alt flag True")
    if s._vtk_interactor.move_events != 1:
        failures.append(
            f"FAIL(B): transition over the widget must fire exactly one MouseMoveEvent, got {s._vtk_interactor.move_events}"
        )
    if s._mouse_move_last_ts != 0.0:
        failures.append("FAIL(B): re-fire must reset the move throttle so it isn't swallowed")

    # B2) The reverse transition (Alt release) also re-fires to demote edge->face.
    s = _stub(alt=True, over=True)
    s._refresh_edge_pick_alt_state(False)
    if s._edge_pick_alt_active is not False or s._vtk_interactor.move_events != 1:
        failures.append("FAIL(B2): releasing Alt must clear the flag and re-fire once")

    # C) Transition but pointer NOT over the widget -> flag set, but NO re-fire.
    s = _stub(alt=False, over=False)
    s._refresh_edge_pick_alt_state(True)
    if s._edge_pick_alt_active is not True:
        failures.append("FAIL(C): flag must still flip even when the pointer is off the widget")
    if s._vtk_interactor.move_events != 0:
        failures.append("FAIL(C): must NOT re-pick a stale scene position when the pointer is off-widget")

    # D) Transition with no interactor -> flag set, no crash, no re-fire.
    s = _stub(alt=False, over=True, interactor=False)
    try:
        s._refresh_edge_pick_alt_state(True)
    except Exception as exc:
        failures.append(f"FAIL(D): must tolerate a missing interactor, raised {exc!r}")
    else:
        if s._edge_pick_alt_active is not True:
            failures.append("FAIL(D): flag must flip even with no interactor")

    # E) Pointer-over geometry.
    if not _stub(over=True)._pointer_over_vtk_widget():
        failures.append("FAIL(E): pointer inside the widget rect must read as over")
    if _stub(over=False)._pointer_over_vtk_widget():
        failures.append("FAIL(E): pointer outside the widget rect must read as NOT over")

    # F) Source wiring.
    mb_src = inspect.getsource(mb_mod.Open3DMouseBindingsService._install_pick_only_left_click_bindings)
    if "alt_changed" not in mb_src or "self._refire_scene_hover_pick()" not in mb_src:
        failures.append("FAIL(F): hover_motion must re-fire the pick on an Alt transition (alt_changed)")
    for seq in ('"<KeyPress-Alt_L>"', '"<KeyPress-Alt_R>"', '"<KeyRelease-Alt_L>"', '"<KeyRelease-Alt_R>"'):
        if seq not in mb_src:
            failures.append(f"FAIL(F): the Toplevel Alt tracker must bind {seq} (stationary Alt press)")
    if "self._refresh_edge_pick_alt_state(True)" not in mb_src or "self._refresh_edge_pick_alt_state(False)" not in mb_src:
        failures.append("FAIL(F): Alt key press/release must drive _refresh_edge_pick_alt_state(True/False)")

    refresh_src = inspect.getsource(Kraken3DInspector._refresh_edge_pick_alt_state)
    if "_edge_pick_alt_active" not in refresh_src or "return" not in refresh_src:
        failures.append("FAIL(F): _refresh_edge_pick_alt_state must early-return when the state is unchanged")
    if "_refire_scene_hover_pick" not in refresh_src:
        failures.append("FAIL(F): _refresh_edge_pick_alt_state must re-fire the hover pick on a change")

    refire_src = inspect.getsource(Kraken3DInspector._refire_scene_hover_pick)
    if "_pointer_over_vtk_widget" not in refire_src or "MouseMoveEvent" not in refire_src:
        failures.append("FAIL(F): _refire_scene_hover_pick must guard on pointer-over and re-invoke MouseMoveEvent")
    if "_mouse_move_last_ts" not in refire_src:
        failures.append("FAIL(F): _refire_scene_hover_pick must reset the move throttle before re-firing")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] Alt-hover edge mode does not fire live (bugs/0324)")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Alt press/release flips edge-refine hover immediately -- re-fires the "
          "VTK pick on the transition (moving OR stationary), no mouse nudge needed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
