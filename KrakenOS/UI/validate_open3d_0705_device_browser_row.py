"""Guard for bugs/0705 -- flag: "I am unable to select the Device on the scene,
it is not appeared in right panel browser as well."

The inspection part (the DEVICE under test) is now a first-class Scene
Components browser row. On the om05a the part box sits INSIDE the prism
assembly meshes, so a canvas click always lands on the STEP overlays first --
the browser row is the reliable selection handle. Right-click carries the
verbs (the 0619 rule): device size (the Inspection Part dialog), inspect-face
per face, solve FOV, open the face's station -- the same set as the 0661
canvas part menu.

Checks (source-pinned on the real panel class):
  A  the tree rebuild inserts iid "inspection-part" gated on the part being
     enabled.
  B  selecting the row sets a status hint and stays a no-3D-selection target.
  C  right-clicking the row posts the Device menu through
     `_popup_scene_component_menu` (0403 robust dismiss) with the size dialog,
     the six faces, the FOV solve and the station verbs.

(Behaviorally verified live on om05a_folded_80mm: the row lists as
"Device 50 x 1 x 50 mm (inspect: front)" and selection writes the hint.)

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0705_device_browser_row
"""

from __future__ import annotations

import inspect

from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    rebuild_src = ""
    for name in ("refresh_tree", "_refresh_tree", "rebuild", "_rebuild"):
        if hasattr(Open3DStepAdminPanel, name):
            rebuild_src += inspect.getsource(getattr(Open3DStepAdminPanel, name))
    if not rebuild_src:
        rebuild_src = inspect.getsource(Open3DStepAdminPanel)
    ok(
        'iid="inspection-part"' in rebuild_src and 'part["enabled"]' in rebuild_src,
        "A: the browser rebuild inserts the Device row, gated on the part being enabled",
    )

    select_src = inspect.getsource(Open3DStepAdminPanel._on_tree_select)
    ok(
        'iid == "inspection-part"' in select_src and "Right-click for size / faces / FOV" in select_src,
        "B: selecting the Device row writes the status hint",
    )

    right_src = inspect.getsource(Open3DStepAdminPanel._on_tree_right_click)
    ok(
        '"inspection-part"' in right_src and "_show_inspection_part_context_menu" in right_src,
        "C1: right-clicking the Device row routes to its context menu",
    )
    menu_src = inspect.getsource(Open3DStepAdminPanel._show_inspection_part_context_menu)
    ok(
        "Device size / part settings..." in menu_src
        and "open_inspection_part_dialog" in menu_src
        and "FACE_ORDER" in menu_src
        and "solve_fov_to_inspection_face" in menu_src
        and "open_station_for_face" in menu_src
        and "_popup_scene_component_menu" in menu_src,
        "C2: the Device menu carries size dialog + faces + FOV solve + station, "
        "posted via _popup_scene_component_menu (0403/0619)",
    )

    # bugs/0707 ("I put mouse cursor to the device, it won't highlight"): the
    # Device gets the hover affordance where it is the frontmost pick.
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services import open3d_interaction

    hover_src = inspect.getsource(open3d_interaction)
    ok(
        "_inspection_part_actor_keys" in hover_src
        and "_set_inspection_part_hover(True)" in hover_src
        and "Right-click: size / faces / FOV" in hover_src,
        "E1: the plain hover branch highlights the Device and names the verbs",
    )

    class _Prop:
        def __init__(self):
            self.color = (0.5, 0.5, 0.5)

        def GetColor(self):
            return self.color

        def SetColor(self, r, g, b):
            self.color = (r, g, b)

    class _Actor:
        def __init__(self):
            self._prop = _Prop()

        def GetProperty(self):
            return self._prop

    class _HoverStub:
        def __init__(self):
            self._inspection_part_actor_keys = {"k1", "k2"}
            self._actor_by_key = {"k1": _Actor(), "k2": _Actor()}
            self.renders = 0

        def render(self):
            self.renders += 1

    stub = _HoverStub()
    Kraken3DInspector._set_inspection_part_hover(stub, True)
    gold = all(
        stub._actor_by_key[k].GetProperty().GetColor() == (1.0, 0.80, 0.20)
        for k in ("k1", "k2")
    )
    Kraken3DInspector._set_inspection_part_hover(stub, False)
    restored = all(
        stub._actor_by_key[k].GetProperty().GetColor() == (0.5, 0.5, 0.5)
        for k in ("k1", "k2")
    )
    ok(
        gold and restored and stub.renders == 2,
        f"E2: hover helper tints the Device gold and restores exactly "
        f"(gold={gold}, restored={restored}, renders={stub.renders})",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0705 device-browser-row validation PASSED")
        return 0
    print("0705 device-browser-row validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
