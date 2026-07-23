"""Guard: selecting a promoted solid FROM THE BROWSER raises its move/rotate gizmo (bugs/0424).

Flag flag_20260723_131812 + follow-up "click the right browser only highlight it, no gizmo": clicking a
promoted optical solid (e.g. a beam splitter occluded by the LED) in the Scene Components browser only
highlighted it -- no in-canvas placement handles -- so the user could not move it without hiding the LED
and 3D-picking. The gizmo builds during a scene rebuild for `_placement_handle_selected_row_index` in
whole-body handle mode; a 3D pick set both, the browser path set neither.

Checks
------
* WIRING -- `select_promoted_step_row_from_admin` sets `_placement_handle_selected_row_index`, enables the
  whole-body handle mode, and rebuilds the scene (`refresh_from_editor`).
* GATE   -- `_show_scene_placement_handles` builds the gizmo for `_placement_handle_selected_row_index`
  (so setting it actually raises the handles), gated on the handle mode + a promoted-solid row.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_browser_select_gizmo

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def _check_wiring(failures, notes):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    src = inspect.getsource(Kraken3DInspector.select_promoted_step_row_from_admin)
    need = {
        "the gizmo target row": "_placement_handle_selected_row_index = row_index",
        "the whole-body handle mode": "show_rotation_handles_var.set(True)",
        "the scene rebuild": "self.refresh_from_editor()",
    }
    missing = [label for label, token in need.items() if token not in src]
    if missing:
        failures.append("WIRING: select_promoted_step_row_from_admin is missing " + ", ".join(missing))
    else:
        notes.append("wiring = browser-select sets the gizmo row + handle mode + rebuilds the scene")


def _check_gate(failures, notes):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    src = inspect.getsource(Kraken3DInspector._show_scene_placement_handles)
    if "_placement_handle_selected_row_index" not in src:
        failures.append("GATE: _show_scene_placement_handles must build the gizmo for _placement_handle_selected_row_index")
    if "_show_rotation_handles()" not in src:
        failures.append("GATE: the gizmo must stay gated on the whole-body handle mode")
    if not [f for f in failures if f.startswith("GATE")]:
        notes.append("gate = the gizmo builds for the selected-handle row in whole-body mode")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_wiring, _check_gate):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_browser_select_gizmo (bugs/0424) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll browser-select-gizmo checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
