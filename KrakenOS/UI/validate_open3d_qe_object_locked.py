"""Display-free guard: a glued LED+BS is EXCLUDED from Quick Estimation.

flag_20260628_212404 / recording_20260628_212459: with the LED glued to the promoted BS, a FOV
"solve for thickness" wrote the object gap (rows[0]) -- which IS the LED+BS position -- so the unit
moved and the one-directional glue left the LED behind, detaching it from the BS and defocusing the
detector. The fix redirects the object-distance change to the air gap AFTER the solid (move the
LENS), which yields an IDENTICAL object->lens + lens->detector conjugate (same focus/FOV) while the
LED+BS stays put.

Binds the REAL ``QuickEstimationService._apply_conjugate_pair`` onto a light fake editor (mocking
only ``_conjugate_pair``) and checks the model: glued -> the object gap is untouched, the lens gap
absorbs the delta, the conjugate is preserved; unglued -> the object gap still moves.
"""

from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data
from KrakenOS.UI.services.quick_estimation import QuickEstimationService as Q


class _Ed:
    def __init__(self, rows, glued: bool):
        self.rows = rows
        self._optical_led_glued = glued


class _QE:
    _apply_conjugate_pair = Q._apply_conjugate_pair
    _object_locked_redirect_row = Q._object_locked_redirect_row
    object_thickness_row = Q.object_thickness_row
    image_thickness_row = Q.image_thickness_row

    def __init__(self, editor, pair):
        self.editor = editor
        self._pair = pair

    def _conjugate_pair(self, _object_semi, _image_semi):
        return self._pair


def _object_to_lens(rows):
    # object at z=0; the lens sits one solid + one air gap past the object gap.
    return float(rows[0].thickness) + float(rows[1].thickness) + float(rows[2].thickness)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal passed
        if not cond:
            passed = False
            notes.append(f"FAIL: {label}{(' -- ' + detail) if detail else ''}")
        elif verbose:
            notes.append(f"ok: {label}")

    path = Path("attachment/machine_vision_150mm_test.py")
    if not path.exists():
        return True, ["skip: MV150 test layout not present"]
    data = _load_python_data(path)

    def fresh_rows():
        return [KrakenLayoutEditor._row_from_layout_item(it) for it in data["surfaces"]]

    target_object_distance = 322.0  # pretend the FOV solve wants to push the object gap to 322
    image_distance = 210.0
    pair = (target_object_distance, image_distance, 2.0)

    # --- GLUED: the LED+BS is locked, QE redirects to the lens gap ---
    rows = fresh_rows()
    qe = _QE(_Ed(rows, glued=True), pair)
    check("A glued + promoted solid -> redirect row is the air gap after the solid (row 2)",
          qe._object_locked_redirect_row(0) == 2, f"got {qe._object_locked_redirect_row(0)}")
    obj_before = float(rows[0].thickness)
    lens_before = float(rows[2].thickness)
    lz_normal = target_object_distance + float(rows[1].thickness) + lens_before  # where a plain solve puts the lens
    ok, msg = qe._apply_conjugate_pair(1.0, 2.0)
    check("B apply returns True", bool(ok), msg)
    check("C the LED+BS object gap is UNCHANGED (unit held fixed)", abs(float(rows[0].thickness) - obj_before) < 1e-9,
          f"rows[0]={rows[0].thickness}")
    check("D the lens gap absorbed the object-distance delta",
          abs(float(rows[2].thickness) - (lens_before + (target_object_distance - obj_before))) < 1e-6,
          f"rows[2]={rows[2].thickness}")
    check("E the back focal was set to the image distance", abs(float(rows[7].thickness) - image_distance) < 1e-9)
    check("F object->lens conjugate IDENTICAL to the plain solve (focus + FOV preserved)",
          abs(_object_to_lens(rows) - lz_normal) < 1e-6, f"{_object_to_lens(rows):.5g} vs {lz_normal:.5g}")
    check("F2 status says the LED+BS was held fixed", "held fixed" in str(msg).lower())

    # --- UNGLUED: the normal behavior (the object gap moves) ---
    rows2 = fresh_rows()
    qe2 = _QE(_Ed(rows2, glued=False), pair)
    check("G unglued -> no redirect row", qe2._object_locked_redirect_row(0) is None)
    qe2._apply_conjugate_pair(1.0, 2.0)
    check("H unglued -> the object gap moves to the solved object distance",
          abs(float(rows2[0].thickness) - target_object_distance) < 1e-9, f"rows[0]={rows2[0].thickness}")

    # --- refuse rather than separate when the lens can't go that close ---
    rows3 = fresh_rows()
    qe3 = _QE(_Ed(rows3, glued=True), (-500.0, image_distance, 2.0))  # would need a negative lens gap
    ok3, msg3 = qe3._apply_conjugate_pair(1.0, 2.0)
    check("I glued + impossible FOV -> refuses (does not separate), object gap untouched",
          (not ok3) and abs(float(rows3[0].thickness) - obj_before) < 1e-9, msg3)

    # source contract
    src = _inspect.getsource(Q._apply_conjugate_pair)
    check("source consults _object_locked_redirect_row", "_object_locked_redirect_row" in src)

    return passed, notes


if __name__ == "__main__":
    import sys

    result_ok, all_notes = run_checks(verbose=True)
    for line in all_notes:
        print(line)
    print("PASS" if result_ok else "FAIL")
    sys.exit(0 if result_ok else 1)
