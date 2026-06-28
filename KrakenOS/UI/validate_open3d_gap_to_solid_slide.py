"""Display-free guard: editing the 'gap to solid' dimension SLIDES the promoted solid only.

flag_20260628_203139 / recording_20260628_201449: editing the Object->BS 'gap to solid' used to
shift the BS + the whole downstream surrogate + detector rigidly (a cumulative thickness change),
shortening the object->lens conjugate with the object fixed -> the detector DEFOCUSED. The fix
slides ONLY the solid: change this gap and compensate the air gap right after the solid, so the
downstream + the focus stay put (and skip the QE re-solve).

Binds the REAL ``Open3DThicknessDimensionService.apply_dimension_value`` onto a light fake editor /
inspector and checks the MODEL: the solid slides, the trailing gap compensates, and every
downstream surface's cumulative z is preserved.
"""

from __future__ import annotations

import inspect as _inspect
from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data
from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService as S


def _zpos(rows):
    z = [0.0]
    for r in rows[:-1]:
        z.append(z[-1] + float(getattr(r, "thickness", 0.0)))
    return z


class _QE:
    def is_enabled(self):
        return False

    def solve_dependent(self, _i):
        return True, ""

    def update_readout(self):
        pass


class _Var:
    def set(self, message):
        self.last = message


class _Ed:
    def __init__(self, rows):
        self.rows = rows
        self.status_var = _Var()

    def _dimension_anchor_override_for_row(self, _i):
        return None

    def _begin_history_capture(self):
        pass

    def _commit_history_capture(self):
        pass

    def _sync_table(self):
        pass

    def _select_table_row(self, _i):
        pass

    def _invalidate_preview_scene_trace(self):
        pass

    def _sync_trace_state_badge(self):
        pass

    def append_debug(self, _m):
        pass


class _Insp:
    def __init__(self):
        self.status_var = _Var()

    def _quick_estimation_service(self):
        return _QE()

    def refresh_from_editor(self, **_k):
        pass


class _Svc:
    # Bind the REAL methods under test so the guard exercises production code.
    apply_dimension_value = S.apply_dimension_value
    _solid_slide_compensation_row = S._solid_slide_compensation_row
    _row_optical_solid_stl = staticmethod(S._row_optical_solid_stl)

    def __init__(self, editor, inspector):
        self.editor = editor
        self.inspector = inspector


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
    rows = [KrakenLayoutEditor._row_from_layout_item(it) for it in data["surfaces"]]
    # MV150: row 0 Object, row 1 promoted BS, row 2 air gap, then surrogate + detector.

    svc = _Svc(_Ed(rows), _Insp())
    check("A compensation row is the air gap right after the solid (row 2)",
          svc._solid_slide_compensation_row(0) == 2, f"got {svc._solid_slide_compensation_row(0)}")

    z_before = _zpos(rows)
    t2_before = float(rows[2].thickness)
    bs_before = z_before[1]
    ok = svc.apply_dimension_value(0, 150.0)
    z_after = _zpos(rows)

    check("B apply returns True", bool(ok))
    check("C the solid slid (BS z ~202 -> 150)", abs(z_after[1] - 150.0) < 1e-6, f"BS z {z_after[1]:.5g}")
    check("D the edited gap is exactly 150", abs(float(rows[0].thickness) - 150.0) < 1e-9)
    check("E the trailing gap absorbed the slide delta",
          abs((bs_before - z_after[1]) - (float(rows[2].thickness) - t2_before)) < 1e-3,
          f"slide={bs_before - z_after[1]:.5g} trailing_delta={float(rows[2].thickness) - t2_before:.5g}")
    preserved = all(abs(z_before[k] - z_after[k]) < 1e-6 for k in range(3, len(z_before)))
    check("F downstream surrogate + detector z PRESERVED (no rigid shift)", preserved,
          f"deltas={[round(z_after[k] - z_before[k], 3) for k in range(3, len(z_before))]}")
    check("F2 status reports the solid slide", "slid the solid" in str(getattr(svc.inspector.status_var, "last", "")))

    # Fallback: a solid with no editable air gap after it -> no compensation row (plain edit).
    term = _Svc(_Ed(rows[:2]), _Insp())  # [object, BS] -> BS is terminal, nothing to compensate into
    check("G no air gap after the solid -> compensation None (cumulative + QE fallback)",
          term._solid_slide_compensation_row(0) is None)

    # Source contract: skip QE on a slide, consult the compensation helper.
    src = _inspect.getsource(S.apply_dimension_value)
    check("source consults _solid_slide_compensation_row", "_solid_slide_compensation_row" in src)
    check("source gates QE on 'not slid'", "if not slid" in src)

    return passed, notes


if __name__ == "__main__":
    import sys

    result_ok, all_notes = run_checks(verbose=True)
    for line in all_notes:
        print(line)
    print("PASS" if result_ok else "FAIL")
    sys.exit(0 if result_ok else 1)
