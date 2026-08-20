"""Guard for bugs/0638 — right-click on an optical axis offers add-element / axis verbs.

User: "add right click to Optical Axis, add relevant action, for example: add elements."
A right-click on a (pickable) optical-axis actor now opens a menu whose primary verbs ADD
ELEMENTS onto that axis (stock lens, CAD/STL solid, path component), plus the axis-to-axis
move. On a branched scene the stock lens is placed onto THIS axis via its branch_path.

Checks:
  A  BEHAVIOUR — on an axis-actor pick the menu builds the expected entries, and the
     "Add Stock Lens on this axis" command routes to
     open_stock_lens_importer(path_placement={"branch_path": ...}).
  B  BEHAVIOUR — no axis actor under the cursor → returns False (the empty-space menu
     still runs), and a bare (branchless) axis uses the plain importer.
  C  CONTRACT — the right-click dispatch calls _maybe_show_optical_axis_menu before the
     empty-space fallback.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0638_optical_axis_menu
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def _stub_inspector(root, axis_map, calls):
    import tkinter as tk

    class _Picker:
        def Pick(self, *a):
            pass

        def GetActor(self):
            return "AX"

    class _Interactor:
        def SetEventInformationFlipY(self, *a):
            pass

        def GetEventPosition(self):
            return (10, 10)

    insp = tk.Frame(root)  # a real widget = valid menu master
    for k, v in dict(
        _picker=_Picker(), _renderer=object(), _vtk_interactor=_Interactor(),
        _actor_optical_axis_map=axis_map, _vtk_widget=None, append_debug=lambda *a: None,
        start_axis_to_axis_move=lambda: calls.append("axis_move"),
        open_stock_lens_importer=lambda **k: calls.append(("stock", k)),
        import_optical_stl_solid=lambda: calls.append("stl"),
        open_current_path_component_placement=lambda: calls.append("comp"),
    ).items():
        setattr(insp, k, v)
    insp.editor = insp
    return insp


def run_checks():
    notes: list[str] = []
    ok = True

    try:
        import tkinter as tk
    except Exception as exc:  # noqa: BLE001
        return True, [f"SKIP: tkinter unavailable ({exc!r})"]
    try:
        root = tk.Tk()
        root.withdraw()
    except Exception as exc:  # noqa: BLE001
        return True, [f"SKIP: no display ({exc!r})"]

    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService as S

    saved = (S._popup_context_menu, S._restore_canvas_focus, getattr(S, "_actor_key", None))
    built: dict = {}

    def _fake_popup(self, menu, event):
        n = menu.index("end")
        built["labels"] = [
            menu.entrycget(i, "label") if menu.type(i) == "command" else "—"
            for i in range(n + 1)
        ]
        for i in range(n + 1):
            if menu.type(i) == "command" and "Add Stock Lens" in str(menu.entrycget(i, "label")):
                menu.invoke(i)
                break

    try:
        S._popup_context_menu = _fake_popup
        S._restore_canvas_focus = lambda self: None
        S._actor_key = staticmethod(lambda a: a)

        # ------------------------------------------------------------ A: branch axis
        calls: list = []
        insp = _stub_inspector(root, {"AX": {"axis_label": "Optical Axis", "branch_path": "T"}}, calls)
        svc = S(insp)
        handled = svc._maybe_show_optical_axis_menu(SimpleNamespace(x=10, y=10))
        labels = built.get("labels", [])
        need = ["Add Stock Lens", "Import Optical CAD/STL Solid", "Add Component", "Move Elements Axis"]
        if not handled:
            ok = False
            notes.append("FAIL: A (bugs/0638): axis-actor pick was not handled")
        elif not all(any(kw in l for l in labels) for kw in need):
            ok = False
            notes.append(f"FAIL: A (bugs/0638): axis menu missing entries ({labels})")
        elif calls != [("stock", {"path_placement": {"branch_path": "T"}})]:
            ok = False
            notes.append(f"FAIL: A (bugs/0638): Add Stock Lens did not route to this axis ({calls})")
        else:
            notes.append("PASS: A: axis menu adds elements; stock lens routes to this axis's branch")

        # ------------------------------------------------------------ B: no axis / bare axis
        empty = S(_stub_inspector(root, {}, []))
        handled_empty = empty._maybe_show_optical_axis_menu(SimpleNamespace(x=1, y=1))
        built.clear()
        bare_calls: list = []
        bare = S(_stub_inspector(root, {"AX": {"axis_label": "Optical Axis", "branch_path": ""}}, bare_calls))
        bare._maybe_show_optical_axis_menu(SimpleNamespace(x=1, y=1))
        if handled_empty is not False:
            ok = False
            notes.append("FAIL: B (bugs/0638): no-axis pick did not fall through (blocks empty-space menu)")
        elif bare_calls != [("stock", {})]:
            ok = False
            notes.append(f"FAIL: B (bugs/0638): a branchless axis did not use the plain importer ({bare_calls})")
        else:
            notes.append("PASS: B: no-axis falls through; a bare axis uses the plain importer")
    finally:
        S._popup_context_menu, S._restore_canvas_focus = saved[0], saved[1]
        if saved[2] is not None:
            S._actor_key = saved[2]
        try:
            root.destroy()
        except Exception:
            pass

    # ---------------------------------------------------------------- C: dispatch contract
    dispatch = inspect.getsource(S._show_surface_function_context_menu)
    if "_maybe_show_optical_axis_menu" not in dispatch:
        ok = False
        notes.append("FAIL: C (bugs/0638): the right-click dispatch never offers the optical-axis menu")
    else:
        notes.append("PASS: C: the right-click dispatch offers the optical-axis menu")

    # ---------------------------------------------------------------- C2: axis is not a CAD context
    # The highlighted-axis dead-end: _right_click_pick_context must report NO context for an
    # optical-axis / highlight actor, so the dispatch reaches the axis menu instead of the
    # (useless) CAD-face branch.
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    pick_ctx = inspect.getsource(Kraken3DInspector._right_click_pick_context)
    if "_optical_axis_highlight_actor" not in pick_ctx or "_actor_optical_axis_map" not in pick_ctx:
        ok = False
        notes.append(
            "FAIL: C2 (bugs/0638): _right_click_pick_context does not skip an axis/highlight "
            "actor -- a right-click on the highlighted axis dead-ends before the axis menu"
        )
    else:
        notes.append("PASS: C2: an optical-axis / highlight actor is treated as no CAD context")

    # ---------------------------------------------------------------- D: screen-space proximity
    # A thin axis crossing a body: resolve by proximity to the polyline, not the picked actor.
    import numpy as np

    from KrakenOS.UI.services.open3d_face_assignment import _point_segment_distance_2d

    class _Renderer:
        def SetWorldPoint(self, *a):
            self._w = a

        def WorldToDisplay(self):
            pass

        def GetDisplayPoint(self):
            return (self._w[0], self._w[1], 0.0)  # identity world->display for the test

    try:
        proot = tk.Tk()
        proot.withdraw()
        pinsp = tk.Frame(proot)
        pinsp._renderer = _Renderer()
        pinsp._optical_axis_pick_records = [
            {"axis_label": "Optical Axis", "branch_path": "B", "points": np.array([[0, 0, 0], [100, 0, 0]], float)}
        ]
        pinsp.append_debug = lambda *a: None
        pinsp.editor = pinsp
        psvc = S(pinsp)
        near = psvc._optical_axis_record_near_display_xy(50, 3, tol_px=12)
        far = psvc._optical_axis_record_near_display_xy(50, 40, tol_px=12)
        if abs(_point_segment_distance_2d((5, 5), (0, 0), (10, 0)) - 5.0) > 1e-9:
            ok = False
            notes.append("FAIL: D (bugs/0638): point-segment distance is wrong")
        elif near is None or near.get("branch_path") != "B":
            ok = False
            notes.append("FAIL: D (bugs/0638): a click near the axis line did not resolve")
        elif far is not None:
            ok = False
            notes.append("FAIL: D (bugs/0638): a click far from the axis wrongly resolved")
        else:
            notes.append("PASS: D: screen-space proximity resolves a near-axis click, rejects a far one")
    finally:
        try:
            proot.destroy()
        except Exception:
            pass

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Optical-axis-menu validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
