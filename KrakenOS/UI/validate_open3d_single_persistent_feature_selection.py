#!/usr/bin/env python3
"""Display-free guard: only ONE persistent STEP feature selection at a time (bugs/0340).

User directive (imported LED, latest flag after the 0338 selection-mode work):
  "face and edge can be selected in sequence, which shouldn't be the case."

Fix:
  The two persistent pins -- a clear-aperture OPENING (bugs/0334,
  ``_set_selected_step_opening``) and a STEP FACE (bugs/0338,
  ``_set_selected_step_face``) -- live in separate slots on the inspector and each
  setter used to clear only its OWN slot. So a left-click that pinned a face left a
  previously-pinned opening (or edge) lit, and vice versa -- two cyan outlines at
  once. Each setter now ALSO clears the other slot, so pinning one feature drops the
  other and at most one persistent selection is ever live.

What it checks (renderer=None => no VTK actor, pure state round-trip)
--------------------------------------------------------------------
  1. Pin an opening -> opening pinned, face NOT pinned.
  2. Pin a face while the opening is pinned -> face pinned, opening CLEARED.
  3. Pin an opening again while the face is pinned -> opening pinned, face CLEARED.
  4. Symmetry: the two setters never leave both pinned simultaneously.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_single_persistent_feature_selection

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import types

import numpy as np


def _fresh_inspector():
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as K

    insp = types.SimpleNamespace(
        _renderer=None,
        _selected_opening_outline_actor=None,
        _selected_opening_label="",
        _selected_opening_face_id="",
        _selected_opening_center=None,
        _selected_opening_normal=None,
        _selected_face_outline_actor=None,
        _selected_face_label="",
        _selected_face_id="",
        _selected_face_center=None,
        _selected_face_normal=None,
        render=lambda *a, **k: None,
        _remove_renderer_view_prop=lambda *a, **k: None,
        _add_renderer_view_prop=lambda *a, **k: None,
    )
    for name in (
        "_set_selected_step_opening",
        "_clear_selected_step_opening",
        "_has_selected_step_opening",
        "_set_selected_step_face",
        "_clear_selected_step_face",
        "_has_selected_step_face",
    ):
        setattr(insp, name, types.MethodType(getattr(K, name), insp))
    return insp


def _pin_opening(insp):
    insp._set_selected_step_opening(
        "led", "F266", np.asarray([1.0, 2.0, 3.0]), np.asarray([0.0, 0.0, 1.0]), None
    )


def _pin_face(insp):
    insp._set_selected_step_face(
        "led", "F005", np.asarray([4.0, 5.0, 6.0]), np.asarray([0.0, 0.0, 1.0]), None
    )


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    insp = _fresh_inspector()

    # 1. Pin an opening -> opening only.
    _pin_opening(insp)
    if not insp._has_selected_step_opening():
        failures.append("FAIL(1): an opening must be pinned after _set_selected_step_opening")
    if insp._has_selected_step_face():
        failures.append("FAIL(1): pinning an opening must not leave a face pinned")

    # 2. Pin a face while the opening is pinned -> the opening must drop.
    _pin_face(insp)
    if not insp._has_selected_step_face():
        failures.append("FAIL(2): a face must be pinned after _set_selected_step_face")
    if insp._has_selected_step_opening():
        failures.append("FAIL(2): pinning a face must CLEAR the previously pinned opening (0340)")

    # 3. Pin an opening again while the face is pinned -> the face must drop.
    _pin_opening(insp)
    if not insp._has_selected_step_opening():
        failures.append("FAIL(3): an opening must be pinned after re-selecting it")
    if insp._has_selected_step_face():
        failures.append("FAIL(3): pinning an opening must CLEAR the previously pinned face (0340)")

    # 4. Never both at once, in either order.
    fresh = _fresh_inspector()
    _pin_face(fresh)
    _pin_opening(fresh)
    if fresh._has_selected_step_face() and fresh._has_selected_step_opening():
        failures.append("FAIL(4): face-then-opening left BOTH pinned")
    fresh2 = _fresh_inspector()
    _pin_opening(fresh2)
    _pin_face(fresh2)
    if fresh2._has_selected_step_face() and fresh2._has_selected_step_opening():
        failures.append("FAIL(4): opening-then-face left BOTH pinned")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] persistent STEP feature selection is not mutually exclusive")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] only one persistent STEP feature selection at a time: pinning a face "
          "drops a pinned opening and vice versa (no face+edge stacking)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
