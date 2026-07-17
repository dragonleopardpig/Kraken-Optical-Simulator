#!/usr/bin/env python3
"""Display-free guard for the "Move/Rotate whole body" selection-mode toggle (bugs/0338).

User directive (imported LED, after the 0334-0337 opening work):
  "Left click a Face will cause whole body selected, is this intended?" ... "I think
  any click on a STEP will either pick edge or surface. So in order to select whole
  body with gizmo, the current checkbox should also disable selection of edges and
  surface once checked in addition to showing gizmo." ... "that means with the
  checkbox unchecked, user can either select face or edge, but not whole body."
Plus the earlier constraint (bugs/0334): "still want [the] gizmo to move the body,
but activate it with some other toggle."

Fix:
  The "Move/Rotate whole body" checkbox (``show_rotation_handles_var``) becomes a
  selection-MODE switch:
    * UNCHECKED (the new DEFAULT) -> a left-click on a STEP pins a FACE or a
      clear-aperture opening as a PERSISTENT selection; NO whole-body select, NO
      gizmo. The face pin mirrors the 0334 opening pin
      (``_set_selected_step_face`` / ``_clear_selected_step_face`` /
      ``_has_selected_step_face`` on the inspector; ``_select_step_face_from_feature``
      on the interaction service).
    * CHECKED -> a left-click selects the whole body and shows its Move/Rotate
      handles; face/edge picking is disabled.
  Flipping the checkbox clears the live selection so the two modes never cross
  (``_toggle_rotation_handles`` -> ``_clear_open3d_selection``), and every deselect
  path drops the pinned face (``_clear_open3d_selection`` -> ``_clear_selected_step_face``).

What it checks
--------------
  1. Inspector state round-trip for the persistent face pin (set / has / clear,
     idempotent second clear).
  2. The interaction service's ``_select_step_face_from_feature`` pins finite
     geometry (centre = surface centre, remembers the feature, status names the
     face) and refuses non-finite geometry.
  3. Source contracts: the left-click idle branch gates on ``_show_rotation_handles()``
     and routes a face/opening pick BEFORE ``select_step_component`` when unchecked;
     ``_clear_open3d_selection`` folds in the face clear; ``_toggle_rotation_handles``
     resets the selection on a mode flip; the checkbox DEFAULT is unchecked.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_selection_mode_toggle

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types

import numpy as np


class _Status:
    def __init__(self):
        self.text = ""

    def set(self, value):
        self.text = str(value)

    def get(self):
        return self.text


def _section1(failures: list[str]) -> None:
    """Inspector persistent-face state round-trip (renderer=None => no actor)."""
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as K

    insp = types.SimpleNamespace(
        _renderer=None,
        _selected_face_outline_actor=None,
        _selected_face_label="",
        _selected_face_id="",
        _selected_face_center=None,
        _selected_face_normal=None,
        render=lambda *a, **k: None,
        _remove_renderer_view_prop=lambda *a, **k: None,
        _add_renderer_view_prop=lambda *a, **k: None,
    )
    insp._set_selected_step_face = types.MethodType(K._set_selected_step_face, insp)
    insp._clear_selected_step_face = types.MethodType(K._clear_selected_step_face, insp)
    insp._has_selected_step_face = types.MethodType(K._has_selected_step_face, insp)

    insp._set_selected_step_face(
        "led", "F005", np.asarray([4.0, 5.0, 6.0]), np.asarray([0.0, 0.0, 1.0]), None
    )
    if insp._selected_face_label != "led":
        failures.append("FAIL(1): _set_selected_step_face must store the STEP label")
    if insp._selected_face_id != "F005":
        failures.append("FAIL(1): _set_selected_step_face must store the face_id")
    if insp._selected_face_center is None or not np.allclose(insp._selected_face_center, [4.0, 5.0, 6.0]):
        failures.append("FAIL(1): _set_selected_step_face must store the face centre")
    if not insp._has_selected_step_face():
        failures.append("FAIL(1): _has_selected_step_face must be True after a set")
    if not insp._clear_selected_step_face():
        failures.append("FAIL(1): _clear_selected_step_face must report a change on the first clear")
    if insp._has_selected_step_face():
        failures.append("FAIL(1): _has_selected_step_face must be False after a clear")
    if insp._clear_selected_step_face():
        failures.append("FAIL(1): a second _clear_selected_step_face must be a no-op (idempotent)")


def _section2(failures: list[str]) -> None:
    """The interaction service pins finite face geometry, refuses non-finite."""
    from KrakenOS.UI.services.open3d_interaction import Open3DInteractionService

    class _Rec:
        def __init__(self):
            self.calls = []

        def __call__(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    setter = _Rec()
    remember = _Rec()
    svc_insp = types.SimpleNamespace(
        _set_selected_step_face=setter,
        _remember_selected_step_feature=remember,
        status_var=_Status(),
        render=lambda *a, **k: None,
    )
    svc = Open3DInteractionService(svc_insp)
    good_pick = {
        "feature": (np.asarray([9.0, 9.0, 9.0]), None, np.asarray([0.0, 0.0, 1.0])),
        "surface_center": np.asarray([1.0, 2.0, 3.0]),
        "face_id": "F005",
    }
    if svc._select_step_face_from_feature("led", good_pick) is not True:
        failures.append("FAIL(2): _select_step_face_from_feature must return True for finite face geometry")
    if not setter.calls:
        failures.append("FAIL(2): a finite face must call _set_selected_step_face")
    else:
        args = setter.calls[-1][0]  # (label, face_id, center, normal, outline_mesh)
        if str(args[0]) != "led" or str(args[1]) != "F005":
            failures.append("FAIL(2): face pin must carry the label + face_id")
        if not np.allclose(np.asarray(args[2], dtype=float), [1.0, 2.0, 3.0]):
            failures.append("FAIL(2): face pin must use surface_center as the centre")
    if not remember.calls:
        failures.append("FAIL(2): pinning a face must still remember the feature (for the menu/snap)")
    if "face" not in svc_insp.status_var.text.lower():
        failures.append(f"FAIL(2): status must name the selected face, got {svc_insp.status_var.text!r}")

    setter2 = _Rec()
    svc_insp2 = types.SimpleNamespace(
        _set_selected_step_face=setter2,
        _remember_selected_step_feature=_Rec(),
        status_var=_Status(),
        render=lambda *a, **k: None,
    )
    svc2 = Open3DInteractionService(svc_insp2)
    bad_pick = {
        "feature": (np.asarray([np.nan, 2.0, 3.0]), None, np.asarray([0.0, 0.0, 1.0])),
        "surface_center": np.asarray([np.nan, 2.0, 3.0]),
        "face_id": "F005",
    }
    if svc2._select_step_face_from_feature("led", bad_pick) is not False:
        failures.append("FAIL(2): a non-finite face centre must return False")
    if setter2.calls:
        failures.append("FAIL(2): a non-finite face must NOT pin a selection")


def _section3(failures: list[str]) -> None:
    """Source contracts: the mode gate, the clear hook, the toggle reset, the default."""
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as K
    import KrakenOS.UI.services.open3d_interaction as interaction_mod

    # 3a) The left-click idle branch gates on the checkbox and routes face/opening
    #     picks BEFORE select_step_component (no whole-body pick when unchecked).
    #     _on_left_button_press is decorated WITHOUT functools.wraps, so read module text.
    src = inspect.getsource(interaction_mod)
    if "if not self._show_rotation_handles():" not in src:
        failures.append("FAIL(3a): the left-click idle branch must gate on _show_rotation_handles()")
    if "_select_step_face_from_feature(step_label, feature_pick)" not in src:
        failures.append("FAIL(3a): the unchecked branch must route a face to _select_step_face_from_feature")
    idx_gate = src.find("if not self._show_rotation_handles():")
    idx_face = src.find("_select_step_face_from_feature(step_label, feature_pick)")
    idx_open = src.find("_select_step_opening_from_feature(step_label, feature_pick)")
    idx_body = src.find("self.editor.select_step_component(step_label)")
    if idx_gate < 0 or idx_body < 0 or idx_gate > idx_body:
        failures.append("FAIL(3a): the mode gate must precede the whole-body select")
    if idx_open < 0 or idx_open > idx_body:
        failures.append("FAIL(3a): the opening pin must precede the whole-body select")
    if idx_face < 0 or idx_face > idx_body:
        failures.append("FAIL(3a): the face pin must precede the whole-body select")

    # 3b) Every deselect path drops the pinned face.
    clear_src = inspect.getsource(K._clear_open3d_selection)
    if "_clear_selected_step_face" not in clear_src:
        failures.append("FAIL(3b): _clear_open3d_selection must drop the pinned face (click-elsewhere)")

    # 3c) Flipping the mode resets the live selection so modes never cross.
    toggle_src = inspect.getsource(K._toggle_rotation_handles)
    if "_clear_open3d_selection" not in toggle_src:
        failures.append("FAIL(3c): _toggle_rotation_handles must clear the selection on a mode flip")
    if "_remove_step_rotation_handle_actors" not in toggle_src:
        failures.append("FAIL(3c): unchecking must still remove the gizmo handle actors")

    # 3d) The checkbox DEFAULT is unchecked -> face/edge select is the primary mode;
    #     whole-body move + gizmo is opt-in ("activate the gizmo with some other toggle").
    init_src = inspect.getsource(K.__init__)
    if "show_rotation_handles_var = tk.BooleanVar(value=False)" not in init_src:
        failures.append("FAIL(3d): the 'Move/Rotate whole body' checkbox must default UNCHECKED (value=False)")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    _section1(failures)
    _section2(failures)
    _section3(failures)
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] Move/Rotate-whole-body checkbox = selection-mode toggle")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] 'Move/Rotate whole body' is a selection-mode switch: unchecked pins a "
          "face/opening only (no body, no gizmo), checked selects the whole body + gizmo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
