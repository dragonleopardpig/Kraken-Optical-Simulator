"""Display-free guard for bugs/0237 -- the object-distance fold split is MERGED into the FOV solve.

flag_20260706_113107_413 on the two-fold AZ85 periscope: the user typed a 55x55 FOV, set the
object-segment constraint, and clicked the standalone bottom "Apply split (move mirror)" button.
The split moved the mirror ("the distance changed") but the FOV label stayed 23x23 -- because the
split button read ONLY the near/far leg and never the FOV boxes, and every FOV-consuming button
closed the dialog, so there was no "apply the FOV, then split" path (the user: "I can't separately
apply the FOV I have input, then click on split button next").

Fix (user-directed): the standalone split section is removed; the object-segment constraint is now
an OPTIONAL "Constrain object -> mirror distance" checkbox merged into the FOV section, and the
Solve buttons honor it in the SAME action. `_apply_quick_estimation_fov_solve` runs `qe.fov_solve`
(which fills the sensor AND sets the target FOV) and, when a segment is supplied, then runs
`_apply_folded_object_split` on the POST-solve geometry (it recomputes the total itself), so the
fold mirror slides to the pinned leg while the just-solved conjugate stays fixed and the trailing
periscope mirror is carried onto the beam (bugs/0236).

This guard drives that exact sequence on the two-fold fixture:

  (A) FOV CHANGES: fov_solve("object","thickness",55,55) sets the target object FOV to the 55x55
      diagonal semi (the label input moves -- no longer frozen at the old value).
  (B) SEGMENT PINS + TOTAL PRESERVED: the follow-on split pins the object->mirror leg to the
      requested value on the POST-solve geometry, and the just-solved total conjugate is unchanged
      by the split (a pure mechanical repackaging).
  (C) MIRROR ON BEAM: across the merged op the trailing free-placed mirror moves but keeps its
      axial offset from the lens arm (carried onto the beam, not frozen off-axis).
  (D) STILL IMAGES: after the merged op rays still reach the detector.
  (E) WIRED: the FOV solve threads `segment` and calls `_apply_folded_object_split`; the popup adds
      the merged checkbox and threads it to the solve (there is no standalone split section).

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_fov_segment_merge
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
import types
from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.services.quick_estimation import QuickEstimationService
from KrakenOS.UI.validate_open3d_two_fold_image_arm_follow import _mirror_and_arm, _two_fold_editor


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _qe(editor):
    return QuickEstimationService(
        types.SimpleNamespace(
            editor=editor,
            quick_estimation_var=types.SimpleNamespace(get=lambda: True),
        )
    )


def validate_folded_fov_segment_merge() -> list[Check]:
    checks: list[Check] = []
    editor = _two_fold_editor()
    qe = _qe(editor)

    m2_before, arm_before = _mirror_and_arm(editor.rows)
    off_before = float(m2_before[2] - arm_before[2])
    semi_before = qe._target_object_semi

    # ---- the MERGED sequence: fov_solve(object,thickness,55x55) then the object-segment split ---- #
    ok_fov, msg_fov = _quiet(qe.fov_solve, "object", "thickness", 55.0, 55.0, None)
    semi_after = qe._target_object_semi
    split1 = _quiet(editor._folded_object_conjugate_split)

    expected_semi = float(np.hypot(55.0, 55.0) / 2.0)  # object diagonal semi of a 55x55 field
    checks.append(Check(
        "FOV CHANGES: Solve-for-Thickness sets the target object FOV to the typed 55x55 (label input moves)",
        bool(ok_fov)
        and semi_after is not None
        and abs(float(semi_after) - expected_semi) < 0.5
        and (semi_before is None or abs(float(semi_after) - float(semi_before)) > 1.0),
        f"ok={ok_fov} target_semi {semi_before}->{None if semi_after is None else round(float(semi_after), 3)} "
        f"(expected {expected_semi:.3f}) msg={msg_fov[:50]!r}",
    ))

    # ---- (B) the follow-on split pins the leg on the post-solve geometry + keeps the total -------- #
    ok_split = False
    near_after = total1 = total2 = float("nan")
    target_near = float("nan")
    if split1 is not None:
        total1 = float(split1["total"])
        target_near = float(split1["near"]) - 10.0
        m2_pre, arm_pre = _mirror_and_arm(editor.rows)
        off_pre = float(m2_pre[2] - arm_pre[2])
        ok_split, _m = _quiet(editor._apply_folded_object_split, "near", target_near)
        split2 = _quiet(editor._folded_object_conjugate_split)
        near_after = float(split2["near"]) if split2 else float("nan")
        total2 = float(split2["total"]) if split2 else float("nan")
        m2_post, arm_post = _mirror_and_arm(editor.rows)
        off_post = float(m2_post[2] - arm_post[2])
        moved = float(np.linalg.norm(m2_post - m2_pre))
    else:
        off_pre = off_post = float("nan")
        moved = 0.0
    checks.append(Check(
        "SEGMENT PINS + TOTAL PRESERVED: the follow-on split pins object->mirror on the post-solve "
        "geometry and leaves the just-solved total unchanged",
        bool(ok_split)
        and abs(near_after - target_near) < 1e-4
        and abs(total2 - total1) < 1e-4,
        f"ok={ok_split} near->{round(near_after, 3)} (target {round(target_near, 3)}) "
        f"total {round(total1, 3)}->{round(total2, 3)}",
    ))

    # ---- (C) the trailing mirror is carried onto the beam across the whole merged op ------------- #
    m2_end, arm_end = _mirror_and_arm(editor.rows)
    off_after = float(m2_end[2] - arm_end[2])
    mirror_moved_total = float(np.linalg.norm(m2_end - m2_before))
    checks.append(Check(
        "MIRROR ON BEAM: across the merged op the trailing mirror moves but keeps its beam offset",
        mirror_moved_total > 1.0 and abs(off_after - off_before) < 1e-3,
        f"mirror_moved={mirror_moved_total:.3f} beam_offset {off_before:.4f}->{off_after:.4f}",
    ))

    # ---- (D) the scene still images after the merged op ----------------------------------------- #
    _s, _r, bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    det = next(
        (np.asarray(t.center_world, dtype=float).reshape(3) for t in bundle.targets if getattr(t, "is_detector", False)),
        None,
    )
    ends = np.asarray([np.asarray(p.points_world, dtype=float)[-1][:3] for p in bundle.ray_paths]) if bundle.ray_paths else np.zeros((0, 3))
    reach = int((np.linalg.norm(ends - det, axis=1) < 5.0).sum()) if det is not None and len(ends) else 0
    checks.append(Check(
        "STILL IMAGES: after the merged FOV solve + segment split rays still reach the detector",
        det is not None and reach >= 8,
        f"rays={len(bundle.ray_paths)} detector={None if det is None else np.round(det, 1)} within5mm={reach}",
    ))

    # ---- (E) wiring: the solve threads + applies the merged segment; the popup has the checkbox -- #
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    solve_src = inspect.getsource(Kraken3DInspector._apply_quick_estimation_fov_solve)
    popup_src = inspect.getsource(Kraken3DInspector._open_quick_estimation_fov_popup)
    wired = (
        "segment" in solve_src
        and "_apply_folded_object_split" in solve_src
        and "Constrain object" in popup_src
        and "segment=segment" in popup_src
        and "_add_folded_conjugate_split_section" not in popup_src  # the standalone section is gone
    )
    checks.append(Check(
        "WIRED: the FOV solve applies the merged segment and the popup adds the checkbox (no standalone split)",
        wired,
        f"solve_threads_segment={'segment' in solve_src} solve_applies_split={'_apply_folded_object_split' in solve_src} "
        f"popup_checkbox={'Constrain object' in popup_src} standalone_gone={'_add_folded_conjugate_split_section' not in popup_src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_fov_segment_merge()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_fov_segment_merge()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded FOV + segment-merge validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
