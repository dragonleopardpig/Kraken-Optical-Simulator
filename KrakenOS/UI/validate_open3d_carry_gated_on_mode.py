"""Guard: the long-press whole-body CARRY only arms in "Move/Rotate whole body" mode (bugs/0425).

User: "with 'Move/Rotate Whole Body' unchecked, clicking a STEP long enough will highlight the whole body,
dragging it will move the body. This is not good, easy to move the body by mistake."

The left-press handler armed the step-carry / row-carry (long-press grab-and-drag of the whole body)
whenever a STEP was under the cursor, regardless of the mode -- so in face/edge-select mode a long press
+ drag moved the body by accident. Fix: gate the carry arming on ``_show_rotation_handles()`` (the
"Move/Rotate whole body" toggle). Explicit gizmo-widget drags (placement handles, thickness, axis slide)
are resolved earlier and are unaffected.

Checks
------
* GATE  -- the left-press carry arming (``_arm_step_carry_hold`` / ``_arm_row_carry_hold``) is guarded by
  ``_show_rotation_handles()``.
* TOGGLE -- the "Move/Rotate whole body" checkbox drives ``show_rotation_handles_var`` (what
  ``_show_rotation_handles`` reads), so unchecking it disarms the carry.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_carry_gated_on_mode

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import re


def _check_gate(failures, notes):
    from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService
    src = inspect.getsource(Open3DMouseBindingsService)
    if "self._arm_step_carry_hold(" not in src or "self._arm_row_carry_hold(" not in src:
        failures.append("GATE: the left-press carry arming is missing")
        return
    # the arming block must be guarded by the whole-body mode. Check the guard condition sits with the
    # placement/thickness guard right before the step-carry arm.
    guard = re.search(
        r"self\._placement_drag_state is None\s*\n\s*and self\._thickness_drag_state is None\s*\n\s*and self\._show_rotation_handles\(\)",
        src,
    )
    if guard is None:
        failures.append("GATE: the carry arming must be guarded by _show_rotation_handles() (whole-body mode)")
    else:
        notes.append("gate = long-press carry only arms when 'Move/Rotate whole body' is ON")


def _check_toggle(failures, notes):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    src = inspect.getsource(Kraken3DInspector._show_rotation_handles)
    if "show_rotation_handles_var" not in src:
        failures.append("TOGGLE: _show_rotation_handles must read show_rotation_handles_var")
    import KrakenOS.UI.panels.open3d_top_controls as controls_mod
    controls_src = inspect.getsource(controls_mod)
    if "Move/Rotate whole body" not in controls_src or "show_rotation_handles_var" not in controls_src:
        failures.append("TOGGLE: the 'Move/Rotate whole body' checkbox must drive show_rotation_handles_var")
    if not [f for f in failures if f.startswith("TOGGLE")]:
        notes.append("toggle = 'Move/Rotate whole body' drives show_rotation_handles_var / _show_rotation_handles")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_gate, _check_toggle):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_carry_gated_on_mode (bugs/0425) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll carry-gated-on-mode checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
