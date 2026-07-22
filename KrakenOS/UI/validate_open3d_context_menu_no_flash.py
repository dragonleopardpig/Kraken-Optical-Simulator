"""Guard: a 3D right-click context menu does not flash-and-disappear on post (bugs/0413).

User: "sometime right click the pop up just flash and disappear."

Root cause -- focus churn the instant the menu posts. ``_popup_context_menu`` posts via
``menu.tk_popup`` (which grabs pointer+focus) and USED to release the grab synchronously in the same
``finally``. On a focus-follows-mouse WM that lets focus bounce off the just-posted menu, and Tk's
built-in Menu ``<FocusOut>`` binding then auto-unposts it -> the menu appears and vanishes in the same
breath. Intermittent because it depends on WM focus timing.

Fix (two guards, both display-free-checkable here):
* GRAB-DEFERRED  -- hold tk_popup's grab for a short settle window (``_CONTEXT_MENU_GRAB_SETTLE_MS``)
  before releasing it, so focus stays pinned on the menu through the post-time churn. Released
  afterwards so the bugs/0336 click-on-VTK dismiss still works.
* FOCUSOUT-GUARDED -- our own ``<FocusOut>`` dismiss ignores a focus-out inside that settle window
  (the spurious bounce), while ``<Unmap>`` (a real unpost / an entry-click invoke, bugs/0348) stays
  UNguarded so menu-entry delivery is untouched.

Checks
------
* SETTLE-POSITIVE -- the default settle window is > 0 (a 0 reinstates the synchronous-release flash).
* GRAB-DEFERRED   -- ``_popup_context_menu`` schedules the grab release via ``menu.after(...)`` and does
  NOT drop it synchronously in the post ``finally``.
* FOCUSOUT-GUARDED -- ``<FocusOut>`` binds to the settle-guarded handler; ``<Unmap>`` binds to the plain
  (entry-safe) deferred dismiss.
* GRACE-LOGIC     -- a focus-out at +0 s is ignored; one well after the settle dismisses.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_context_menu_no_flash

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def _grace_ignores(focus_out_delay_s: float, settle_s: float) -> bool:
    """Reference reimplementation of _deferred_dismiss_focus's grace test: a focus-out within the
    settle window is IGNORED (spurious post-time bounce); at/after it, it dismisses."""
    return focus_out_delay_s < settle_s


def _check_settle_positive(failures, notes):
    from KrakenOS.UI.services.open3d_face_assignment import _CONTEXT_MENU_GRAB_SETTLE_MS as ms
    if not (ms > 0):
        failures.append(f"SETTLE-POSITIVE: default grab-settle window must be > 0 (got {ms})")
        return
    notes.append(f"settle-positive = grab-settle window {ms} ms (> 0)")


def _check_grab_deferred(failures, notes):
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
    src = inspect.getsource(Open3DFaceAssignmentService._popup_context_menu)
    if "menu.after(_CONTEXT_MENU_GRAB_SETTLE_MS, _release_menu_grab)" not in src:
        failures.append("GRAB-DEFERRED: the grab release must be scheduled via menu.after(settle, ...)")
    # the synchronous form the flash regression would reintroduce
    if "finally:\n            try:\n                menu.grab_release()\n            except Exception:\n                pass\n" in src:
        failures.append("GRAB-DEFERRED: the post finally must NOT release the grab synchronously")
    if not [f for f in failures if f.startswith("GRAB-DEFERRED")]:
        notes.append("grab-deferred = tk_popup grab released on a settle timer, not synchronously")


def _check_focusout_guarded(failures, notes):
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
    src = inspect.getsource(Open3DFaceAssignmentService._popup_context_menu)
    if 'menu.bind("<FocusOut>", _deferred_dismiss_focus' not in src:
        failures.append("FOCUSOUT-GUARDED: <FocusOut> must bind the settle-guarded dismiss handler")
    if 'menu.bind("<Unmap>", _deferred_dismiss,' not in src:
        failures.append("FOCUSOUT-GUARDED: <Unmap> must stay the plain (entry-safe) deferred dismiss")
    if "if (time.monotonic() - post_ts) < settle_s:" not in src:
        failures.append("FOCUSOUT-GUARDED: the focus-out handler must gate on the settle window")
    if not [f for f in failures if f.startswith("FOCUSOUT-GUARDED")]:
        notes.append("focusout-guarded = <FocusOut> gated by settle; <Unmap> stays entry-safe")


def _check_grace_logic(failures, notes):
    settle_s = 0.150
    if _grace_ignores(0.0, settle_s) is not True:
        failures.append("GRACE-LOGIC: a focus-out at +0 s must be IGNORED (spurious post-time bounce)")
    if _grace_ignores(2 * settle_s, settle_s) is not False:
        failures.append("GRACE-LOGIC: a focus-out well after the settle must DISMISS")
    if not [f for f in failures if f.startswith("GRACE-LOGIC")]:
        notes.append("grace-logic = focus-out ignored during settle, honoured after")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_settle_positive, _check_grab_deferred, _check_focusout_guarded, _check_grace_logic):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_context_menu_no_flash (bugs/0413) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll context-menu no-flash checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
