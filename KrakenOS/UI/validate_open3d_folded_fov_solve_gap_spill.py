"""Display-free guard for bugs/0314 -- a SECOND Solve-for-Thickness on a two-fold periscope
must not silently no-op when a prior fold-leg constraint drained the primary conjugate gap row.

flag_20260715_105226_165 ("first time change FOV to 55x55 and make 2 constraint, it works. But
second time change to FOV 20x20, same constraints, not working... not doing any processing at
all"): the folded conjugate solve writes the whole object-distance correction onto ONE row
(object_gap_row = 0). A pinned "object -> mirror" leg from the first solve slides distance OUT of
row 0, so a subsequent FOV reduction (larger |m|, object nearer) needs a bigger negative delta
than row 0 can hold -> ``new_obj_gap < 0`` -> ``_apply_conjugate_pair`` returns False -> no
retrace -> "nothing happens", even though the object TOTAL has ample room in the far leg.

Fix (bugs/0314): ``_apply_conjugate_pair`` distributes each leg's correction with
``_distribute_folded_gap_delta`` -- when the primary row underflows, the overflow spills onto the
fold's OTHER leg (``_folded_conjugate_spill_row``), sliding the mirror instead of failing (what
the old error told the user to do by hand). The subsequent constraint split re-pins the leg.

  (A) SPILL MATH: the distributor absorbs an in-range delta on the primary row (no spill), spills
      a primary underflow onto the sibling leg preserving the TOTAL, and returns None only when
      both legs together cannot hold it (or there is no sibling).
  (B) SIBLING PICK: the spill row is the fold split's far leg, and only when its near leg IS the
      primary row (else None -- never trust an unrelated row).
  (C) NO SILENT NO-OP: the real two-solve sequence (FOV55 + pinned object->mirror, then FOV20 +
      same pin) now succeeds on the second solve and the pinned leg is honored -- where the
      pre-fix path returned False.
  (D) PLAIN UNCHANGED: with no constraint, two sequential solves still succeed and the primary
      row absorbs the delta directly (no spill, byte-for-byte the old single-row write).
  (E) WIRED: _apply_conjugate_pair routes through the distributor + sibling picker and carries the
      per-row changes.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_fov_solve_gap_spill
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
import types
from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
from KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover import _promote_mirror2


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _two_fold_editor():
    editor = _quiet(_build_editor, _AZ85)
    _quiet(_promote_mirror2, editor)
    return editor


def _row(thickness):
    return types.SimpleNamespace(thickness=float(thickness))


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService as Svc

    checks: list[Check] = []

    def add(name, ok, detail=""):
        checks.append(Check(name, bool(ok), str(detail)))

    svc = Svc.__new__(Svc)

    # ---- (A) spill math ----------------------------------------------------------------------- #
    # in-range: primary absorbs, no spill
    rows = [_row(100.0), _row(0.0), _row(200.0)]
    got = svc._distribute_folded_gap_delta(rows, 0, -40.0, 2)
    add("A in-range delta -> single primary write", got == [(0, -40.0)], str(got))
    # underflow: primary (37.5) can't hold -129 -> spill remainder onto sibling, total preserved
    rows = [_row(37.5), _row(0.0), _row(209.8)]
    got = svc._distribute_folded_gap_delta(rows, 0, -129.0, 2)
    total_before = 37.5 + 209.8
    ok_spill = (
        isinstance(got, list) and len(got) == 2
        and got[0] == (0, -37.5)
        and abs(got[1][0] - 2) < 1e-9 and abs(got[1][1] - (-91.5)) < 1e-6
    )
    if isinstance(got, list):
        total_after = (37.5 + got[0][1]) + (209.8 + got[1][1])
        ok_spill = ok_spill and abs(total_after - (total_before - 129.0)) < 1e-6
    add("A underflow spills to sibling, TOTAL preserved", ok_spill, str(got))
    # no sibling -> None
    add("A underflow with no spill row -> None",
        svc._distribute_folded_gap_delta([_row(10.0)], 0, -50.0, None) is None, "")
    # sibling can't hold -> None
    add("A underflow beyond both legs -> None",
        svc._distribute_folded_gap_delta([_row(10.0), _row(5.0)], 0, -50.0, 1) is None, "")

    # ---- (B) sibling pick keys off the split's near_gap_row --------------------------------- #
    svc_b = Svc.__new__(Svc)
    svc_b.editor = types.SimpleNamespace(
        _folded_object_conjugate_split=lambda: {"near_gap_row": 0, "far_gap_row": 2, "far_min": 20.0},
        _folded_image_conjugate_split=lambda: {"near_gap_row": 7, "far_gap_row": 8, "far_min": 12.5},
    )
    add("B object sibling = far leg for primary 0", svc_b._folded_conjugate_spill_row(0, "object") == 2, "")
    add("B image sibling = far leg for primary 7", svc_b._folded_conjugate_spill_row(7, "image") == 8, "")
    add("B None when near_gap_row != primary", svc_b._folded_conjugate_spill_row(5, "object") is None, "")
    svc_b2 = Svc.__new__(Svc)
    svc_b2.editor = types.SimpleNamespace(
        _folded_object_conjugate_split=lambda: None,
        _folded_image_conjugate_split=lambda: None,
    )
    add("B None when there is no fold split", svc_b2._folded_conjugate_spill_row(0, "object") is None, "")

    # ---- (C) no silent no-op: second solve succeeds + pin honored --------------------------- #
    editor = _two_fold_editor()
    qe = Svc(types.SimpleNamespace(editor=editor))
    osplit = editor._folded_object_conjugate_split()
    isplit = editor._folded_image_conjugate_split()
    img_far = round(float(isplit["far"]), 3)
    # solve 1: FOV 55 + pin a SHORT object->mirror leg (drains object gap row 0)
    ok1, _ = _quiet(qe.fov_solve, "object", "thickness", 55.0, 55.0, None)
    ok1o, _ = _quiet(editor._apply_folded_object_split, "near", 50.0)
    ok1i, _ = _quiet(editor._apply_folded_image_split, "far", img_far)
    # solve 2: FOV 20 + same pins -- the conjugate must NOT no-op
    ok2, msg2 = _quiet(qe.fov_solve, "object", "thickness", 20.0, 20.0, None)
    ok2o, _ = _quiet(editor._apply_folded_object_split, "near", 50.0)
    final_split = editor._folded_object_conjugate_split()
    pin_honored = abs(float(final_split["near"]) - 50.0) < 1e-3
    total_20 = abs(float(final_split["total"]) - 130.635) < 0.5  # FOV20 object total
    add(
        "C setup: FOV55 + short object pin succeeds (drains row 0)",
        ok1 and ok1o and ok1i, f"ok1={ok1} pin_obj={ok1o} pin_img={ok1i}",
    )
    add(
        "C FOV20 second solve succeeds (no silent no-op)",
        bool(ok2), f"ok2={ok2} :: {msg2}",
    )
    add(
        "C pinned object->mirror = 50 honored at the new FOV20 total",
        ok2o and pin_honored and total_20,
        f"near={float(final_split['near']):.4g} total={float(final_split['total']):.4g}",
    )

    # ---- (D) plain (no-constraint) sequence unchanged --------------------------------------- #
    editor_p = _two_fold_editor()
    qe_p = Svc(types.SimpleNamespace(editor=editor_p))
    okp1, _ = _quiet(qe_p.fov_solve, "object", "thickness", 55.0, 55.0, None)
    row0_before = float(editor_p.rows[0].thickness)
    okp2, _ = _quiet(qe_p.fov_solve, "object", "thickness", 20.0, 20.0, None)
    row0_after = float(editor_p.rows[0].thickness)
    # plain FOV20 solve keeps row 0 positive (no spill needed) -- single-row write path
    add(
        "D plain two-solve sequence both succeed, primary row absorbs (no spill)",
        okp1 and okp2 and row0_after > 0.0 and row0_after < row0_before,
        f"okp1={okp1} okp2={okp2} row0 {row0_before:.3f}->{row0_after:.3f}",
    )

    # ---- (E) wiring ------------------------------------------------------------------------- #
    src = inspect.getsource(Svc._apply_conjugate_pair)
    add(
        "E _apply_conjugate_pair routes through distributor + sibling picker + carries changes",
        "_distribute_folded_gap_delta" in src
        and "_folded_conjugate_spill_row" in src
        and "carry_free_placed_followers_after_fold(rows, changes)" in src,
        "",
    )

    _CHECKS[:] = checks
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


_CHECKS: list[Check] = []


def main() -> int:
    passed, failures = run_checks()
    for c in _CHECKS:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if not passed:
        print(f"\nFAILED ({len(failures)} checks)")
        return 1
    print("\nFolded FOV-solve gap-spill validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
