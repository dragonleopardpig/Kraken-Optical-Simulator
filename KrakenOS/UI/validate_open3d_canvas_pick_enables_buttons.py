"""Guard: a direct 3D-canvas pick enables the "Selected Element" buttons
(bugs/0063).

The embedded Open 3D inspector has two ways to select an imported STEP solid (or
any drawn scene row): clicking the right-panel browser tree, or clicking the body
directly in the 3D canvas. The browser click enabled the *Selected Element*
action buttons; the canvas pick left them grayed out.

Root cause: the button-enable logic (`Open3DStepAdminPanel._update_properties`)
keys off the browser tree IID. `_on_tree_select` sets it; the canvas-pick
handlers (`Open3DInteractionService._on_left_button_press`) applied the editor
selection + rotation gizmo but never synced the admin panel, so its
`_selected_item_id` stayed empty and every button stayed disabled.

Fix: the canvas pick mirrors its selection into the browser via
`Open3DStepAdminPanel.select_from_canvas(iid)` (routed through
`Kraken3DInspector.sync_step_admin_canvas_selection`), so both entry points land
on the same IID and light the same buttons.

Checks
------
Source contracts (always run, no display):
A. `_on_left_button_press` syncs *both* the STEP-overlay pick (`overlay:<label>`)
   and the editable-table row pick (via `_open3d_browser_iid_for_table_row`).
B. the inspector's `sync_step_admin_canvas_selection` forwards to
   `panel.select_from_canvas`.
C. `Open3DStepAdminPanel.select_from_canvas` sets `_selected_item_id` and calls
   `_update_properties`.

Behaviour (display-free, fake editor/inspector):
D. `_compute_selection_button_states` lights the right buttons per selection
   kind (overlay / promoted row / scene row / nothing).
E. `_selection_flags_for_iid` derives overlay / promoted-row / file-backed /
   centerable correctly from IID + editor state.
F. PARITY: `select_from_canvas("overlay:lens")` sets `_selected_item_id` and
   yields the *same* button states the browser path produces for that IID --
   the reported buttons (Promote etc.) now enable for a canvas pick. An empty
   selection grays every button (the reported "grayed out" state), proving the
   fix flips it.
G. `_open3d_browser_iid_for_table_row` maps a promoted STEP optical solid to
   `row:N` and every other drawn row to `scene-row:N`, and
   `sync_step_admin_canvas_selection` reaches `select_from_canvas` on a built
   panel.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_canvas_pick_enables_buttons

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any


def _src(obj) -> str:
    try:
        return inspect.getsource(obj)
    except Exception:
        return ""


def _method_source(func) -> str:
    """Source of a method, unwrapping the timing decorator that captures the
    real method as a ``method`` free variable (it uses no ``functools.wraps``,
    so ``__wrapped__`` is absent and a plain ``getsource`` returns the wrapper)."""
    cur = func
    seen: set[int] = set()
    while True:
        try:
            freevars = cur.__code__.co_freevars
            closure = cur.__closure__ or ()
        except Exception:
            break
        if "method" in freevars and closure:
            inner = dict(zip(freevars, closure))["method"].cell_contents
            if not callable(inner) or id(inner) in seen:
                break
            seen.add(id(inner))
            cur = inner
            continue
        break
    return _src(cur)


@dataclass
class _Row:
    surface: str = "Standard"
    name: str = "Surface"
    advanced: dict[str, Any] = field(default_factory=dict)
    thickness: float = 0.0
    desp_x: float = 0.0
    desp_y: float = 0.0
    desp_z: float = 0.0


class _Editor:
    """Minimal editor: overlay 'lens' resolves; rows 0=Object, 1=file-backed
    Standard, 2=Image; row 3 is a promoted STEP optical solid."""

    def __init__(self) -> None:
        self.rows = [
            _Row("Object", "Object"),
            _Row("Standard", "Lens front", {"Solid_3d_stl": "/tmp/a.stl"}),
            _Row("Image", "Image"),
            _Row(
                "Standard",
                "Penta prism",
                {
                    "Solid_3d_stl": "/tmp/promoted.stl",
                    "OpticalSolidSourcePath": "/tmp/penta.step",
                    "OpticalSolidSourceFormat": "STEP",
                },
            ),
        ]

    # overlay
    def _step_path_for_label(self, label: str):
        return "/tmp/lens.step" if str(label).strip().lower() == "lens" else None

    def _step_overlay_display_label(self, label: str) -> str:
        return str(label).title()

    def _step_placement_offset_xyz(self, _label: str):
        return (0.0, 0.0, 0.0)

    def _step_x_rotation_deg(self, _label: str) -> float:
        return 0.0

    _step_y_rotation_deg = _step_x_rotation_deg
    _step_roll_deg = _step_x_rotation_deg

    # rows
    def _file_backed_stl_row_at(self, index: int):
        return object() if index in (1, 3) else None

    def _scene_row_display_name(self, index: int, _row) -> str:
        return f"S{index}"

    @staticmethod
    def _is_open3d_promoted_optical_solid_row(row: _Row) -> bool:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        return KrakenLayoutEditor._is_open3d_promoted_optical_solid_row(row)

    def append_debug(self, *_a, **_k) -> None:
        pass


class _Inspector:
    def __init__(self) -> None:
        self.editor = _Editor()
        self._selected_step_labels: set[str] = set()


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.open3d_interaction import Open3DInteractionService

    # --- A. canvas-pick handler syncs both pick kinds -----------------------
    press_src = _method_source(Open3DInteractionService._on_left_button_press)
    ok("sync_step_admin_canvas_selection(f\"overlay:" in press_src,
       "A1: STEP-overlay canvas pick syncs the admin browser")
    ok("_open3d_browser_iid_for_table_row(" in press_src
       and "sync_step_admin_canvas_selection(self._open3d_browser_iid_for_table_row(" in press_src,
       "A2: editable-table row canvas pick syncs the admin browser")

    # --- B. inspector sync forwards to the panel ----------------------------
    sync_src = _src(Kraken3DInspector.sync_step_admin_canvas_selection)
    ok("panel.select_from_canvas(" in sync_src,
       "B: sync_step_admin_canvas_selection forwards to panel.select_from_canvas")

    # --- C. select_from_canvas sets the selection + refreshes buttons -------
    sfc_src = _src(Open3DStepAdminPanel.select_from_canvas)
    ok("self._selected_item_id = iid" in sfc_src and "_update_properties(iid)" in sfc_src,
       "C: select_from_canvas sets _selected_item_id and calls _update_properties")

    # --- D. button-state mapping per selection kind -------------------------
    bs = Open3DStepAdminPanel._compute_selection_button_states
    overlay = bs({"overlay": True})
    ok(all(overlay[k] for k in ("carry", "accept", "promote", "native", "delete",
                                "center", "normal", "pick_normal", "surface_center"))
       and overlay["faces"] is False,
       "D1: overlay lights every action button except Faces")
    promoted = bs({"promoted_row": True, "file_backed_row": True})
    ok(promoted["delete"] and promoted["faces"] and promoted["center"]
       and not promoted["promote"],
       "D2: promoted row lights Delete/Faces/Center, not Promote")
    scene = bs({"file_backed_row": True, "centerable_row": True})
    ok(scene["faces"] and scene["center"] and not scene["promote"] and not scene["delete"],
       "D3: file-backed scene row lights Faces/Center only")
    none = bs({})
    ok(not any(none.values()), "D4: no selection disables every button")

    # --- E. flag derivation from IID + editor state -------------------------
    panel = Open3DStepAdminPanel(_Inspector())
    f_overlay = panel._selection_flags_for_iid("overlay:lens")
    ok(f_overlay["overlay"] is True, "E1: overlay:lens -> overlay flag")
    ok(panel._selection_flags_for_iid("overlay:nope")["overlay"] is False,
       "E2: unknown overlay -> not selected")
    f_obj = panel._selection_flags_for_iid("scene-row:0")  # Object: not centerable
    ok(f_obj["centerable_row"] is False and f_obj["file_backed_row"] is False,
       "E3: scene-row Object is neither centerable nor file-backed")
    f_lens = panel._selection_flags_for_iid("scene-row:1")  # Standard + file-backed
    ok(f_lens["centerable_row"] is True and f_lens["file_backed_row"] is True,
       "E4: scene-row Standard CAD/STL is centerable + file-backed")
    f_row = panel._selection_flags_for_iid("row:3")
    ok(f_row["promoted_row"] and f_row["file_backed_row"],
       "E5: row:N promoted optical solid is promoted + file-backed")

    # --- F. canvas pick == browser pick parity (+ grayed-out baseline) ------
    panel.select_from_canvas("overlay:lens")
    canvas_states = bs(panel._selection_flags_for_iid(panel._selected_item_id))
    browser_states = bs(panel._selection_flags_for_iid("overlay:lens"))
    ok(panel._selected_item_id == "overlay:lens",
       "F1: select_from_canvas sets _selected_item_id to the picked overlay")
    ok(canvas_states == browser_states and canvas_states["promote"] is True,
       "F2: canvas pick lights the SAME buttons as the browser (Promote now enabled)")
    panel.select_from_canvas("")
    ok(panel._selected_item_id == ""
       and not any(bs(panel._selection_flags_for_iid("")).values()),
       "F3: empty canvas selection grays every button (the reported state)")

    # --- G. inspector row->iid mapping + sync reaches the panel -------------
    fake = _Inspector()
    iid_promoted = Kraken3DInspector._open3d_browser_iid_for_table_row(fake, 3)
    iid_scene = Kraken3DInspector._open3d_browser_iid_for_table_row(fake, 1)
    ok(iid_promoted == "row:3", "G1: promoted optical-solid row -> row:N")
    ok(iid_scene == "scene-row:1", "G2: ordinary drawn row -> scene-row:N")

    captured: dict[str, str] = {}

    class _PanelSpy:
        def select_from_canvas(self, iid: str) -> None:
            captured["iid"] = iid

    fake._open3d_step_admin_panel_instance = _PanelSpy()
    Kraken3DInspector.sync_step_admin_canvas_selection(fake, "overlay:lens")
    ok(captured.get("iid") == "overlay:lens",
       "G3: sync_step_admin_canvas_selection reaches panel.select_from_canvas")

    passed = not any(n.startswith("FAIL") for n in notes)
    if verbose:
        for n in notes:
            print(n)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Open 3D canvas-pick Selected-Element button validation passed.")
        return 0
    print("Open 3D canvas-pick Selected-Element button validation FAILED:")
    for n in notes:
        if n.startswith("FAIL"):
            print(f"- {n}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
