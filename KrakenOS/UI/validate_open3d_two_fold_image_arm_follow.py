"""Display-free guard for bugs/0236 -- image-arm-follow: on a TWO-FOLD periscope a folded
conjugate solve must carry the free-placed trailing fold mirror onto the moved beam instead
of leaving it pinned along global +Z (thrown off the optical axis).

flag_20260706_083512_730 ("I click the solve thickness, 2nd RA mirror seems thrown out of the
optical axis" + "Why 2-fold periscope can't specify object segment constraint?"): the trailing
mirror is a free-placed promoted solid pinned at ``[desp_x, desp_y, z_positions[i] + desp_z]``
-- its station advance feeds ONLY global +Z. A gap delta on a leg AFTER the first fold (the
Solve-for-Thickness image gap, or the object-split far spacer) walks the beam along the first
fold's REFLECTED direction, not +Z, so the pinned mirror advanced in +Z while the beam walked
the reflected leg -> off-axis. bugs/0234 gated the object-segment split OFF for this reason.

Fix (bugs/0236): ``carry_free_placed_followers_after_fold`` (nonseq_output_ports) adds
``post_fold_delta * (r_hat - z_hat)`` to each free-placed follower's desp after a folded solve
-- redirecting the post-fold portion of the walk from +Z onto the reflected leg r_hat, so the
mirror re-seats on the beam. Wired into ``_apply_conjugate_pair`` (Solve-for-Thickness) and
``_apply_folded_object_split`` (object-segment split, now UN-GATED on the two-fold).

  (A) THICKNESS ON BEAM: the folded conjugate solve moves the trailing mirror but its axial
      offset from the lens arm is preserved (stays on the beam), not left frozen off-axis.
  (B) SPLIT UN-GATED + ON BEAM: the object-segment split is now offered on a two-fold and the
      trailing mirror is carried onto the beam by the slide.
  (C) PRE-FOLD NO-OP: a delta BEFORE the first fold is not redirected (it correctly stays a
      global-+Z fold-vertex slide); a plain (non-free-placed) follower is never moved.
  (D) WIRED: the carry is called from both solve paths and the bugs/0234 two-fold gate is gone.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_two_fold_image_arm_follow
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
from KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover import _promote_mirror2
from KrakenOS.UI.nonseq_output_ports import (
    build_optical_solid_output_port_pose_overrides,
    carry_free_placed_followers_after_fold,
)


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


def _centers(rows):
    ov = build_optical_solid_output_port_pose_overrides(list(rows))
    return {fi: np.asarray(ov[fi].get("center"), dtype=float).reshape(3) for fi in sorted(ov)}


def _mirror_and_arm(rows):
    """(trailing-mirror centre, last-lens-block-row centre). The mirror's axial (Z) offset
    from the lens arm is the on-beam invariant: preserved <=> mirror stays on the beam."""
    centers = _centers(rows)
    promoted = [i for i, r in enumerate(rows)
                if isinstance(getattr(r, "advanced", {}) or {}, dict)
                and (isinstance((getattr(r, "advanced", {}) or {}).get("StepOverlayPromotion"), dict)
                     or isinstance((getattr(r, "advanced", {}) or {}).get("StepNativePromotion"), dict))]
    mirror2 = promoted[-1]
    arm_row = mirror2 - 1  # the lens-block row immediately upstream of the trailing mirror
    while arm_row not in centers and arm_row > 0:
        arm_row -= 1
    return centers[mirror2], centers[arm_row]


def validate_two_fold_image_arm_follow() -> list[Check]:
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    checks: list[Check] = []

    # ---- (A) Solve-for-Thickness carries the trailing mirror onto the beam --------------------- #
    import types
    editor = _two_fold_editor()
    qe = QuickEstimationService(types.SimpleNamespace(editor=editor))
    m2_before, arm_before = _mirror_and_arm(editor.rows)
    off_before = float(m2_before[2] - arm_before[2])
    ok_solve, _msg = _quiet(qe._apply_conjugate_pair, 30.0, 21.0)
    m2_after, arm_after = _mirror_and_arm(editor.rows)
    off_after = float(m2_after[2] - arm_after[2])
    moved = float(np.linalg.norm(m2_after - m2_before))
    checks.append(Check(
        "THICKNESS ON BEAM: folded conjugate solve moves the trailing mirror but keeps its "
        "beam offset (not frozen off-axis)",
        bool(ok_solve) and moved > 1.0 and abs(off_after - off_before) < 1e-3,
        f"ok={ok_solve} mirror_moved={moved:.3f} beam_offset {off_before:.4f}->{off_after:.4f}",
    ))

    # ---- (B) the object-segment split is un-gated on a two-fold AND carries the mirror --------- #
    editor2 = _two_fold_editor()
    split = editor2._folded_object_conjugate_split()
    ungated = split is not None
    off_b = off_a = float("nan")
    moved2 = 0.0
    ok_split = False
    if ungated:
        m2b, armb = _mirror_and_arm(editor2.rows)
        off_b = float(m2b[2] - armb[2])
        ok_split, _m = _quiet(editor2._apply_folded_object_split, "near", float(split["near"]) + 15.0)
        m2a, arma = _mirror_and_arm(editor2.rows)
        off_a = float(m2a[2] - arma[2])
        moved2 = float(np.linalg.norm(m2a - m2b))
    checks.append(Check(
        "SPLIT UN-GATED + ON BEAM: the object-segment split is offered on a two-fold and the "
        "slide carries the trailing mirror onto the beam",
        ungated and bool(ok_split) and moved2 > 1.0 and abs(off_a - off_b) < 1e-3,
        f"ungated={ungated} ok={ok_split} mirror_moved={moved2:.3f} beam_offset {off_b:.4f}->{off_a:.4f}",
    ))

    # ---- (C) a PRE-fold delta is not redirected, and a plain follower is never carried -------- #
    editor3 = _two_fold_editor()
    rows3 = editor3.rows
    promoted3 = [i for i, r in enumerate(rows3)
                 if isinstance((getattr(r, "advanced", {}) or {}).get("StepOverlayPromotion"), dict)]
    first_fold = promoted3[0]
    desp_snapshot = {i: (float(getattr(r, "desp_x", 0.0) or 0.0),
                         float(getattr(r, "desp_y", 0.0) or 0.0),
                         float(getattr(r, "desp_z", 0.0) or 0.0)) for i, r in enumerate(rows3)}
    # a delta only on row 0 (before the first fold): nothing should be carried.
    carried_prefold = carry_free_placed_followers_after_fold(rows3, [(0, 7.5)])
    # a delta on a plain (non-free-placed) air-gap row does not move that plain row.
    plain_row = next(i for i, r in enumerate(rows3)
                     if first_fold < i and i not in promoted3
                     and str(getattr(r, "surface", "")) not in ("Object", "Image"))
    unchanged = all(
        (float(getattr(rows3[i], "desp_x", 0.0) or 0.0),
         float(getattr(rows3[i], "desp_y", 0.0) or 0.0),
         float(getattr(rows3[i], "desp_z", 0.0) or 0.0)) == desp_snapshot[i]
        for i in range(len(rows3))
    )
    checks.append(Check(
        "PRE-FOLD NO-OP: a delta before the first fold redirects nothing; plain followers untouched",
        carried_prefold == [] and unchanged and plain_row not in promoted3,
        f"carried_prefold={carried_prefold} all_desp_unchanged={unchanged}",
    ))

    # ---- (D) wiring: both solve paths call the carry; the bugs/0234 two-fold gate is gone ------ #
    import KrakenOS.UI.services.quick_estimation as qe_mod
    import KrakenOS.UI.services.paraxial_tools as px_mod
    import KrakenOS.UI.nonseq_output_ports as ports_mod

    qe_src = inspect.getsource(qe_mod)
    px_src = inspect.getsource(px_mod)
    ports_src = inspect.getsource(ports_mod)
    fn_name = "carry_free_placed_followers_after_fold"
    wired = (
        fn_name in qe_src and fn_name in px_src and f"def {fn_name}" in ports_src
        # the bugs/0234 two-fold gate ("any fold beyond the object mirror -> None") is removed
        and "if any(int(f) > int(mirror_row) for f in folds):" not in px_src
    )
    checks.append(Check(
        "WIRED: the carry is called from both solve paths and the bugs/0234 two-fold gate is gone",
        wired,
        f"in_qe={fn_name in qe_src} in_paraxial={fn_name in px_src} "
        f"defined={f'def {fn_name}' in ports_src} gate_removed="
        f"{'if any(int(f) > int(mirror_row) for f in folds):' not in px_src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_two_fold_image_arm_follow()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_two_fold_image_arm_follow()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Two-fold image-arm-follow validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
