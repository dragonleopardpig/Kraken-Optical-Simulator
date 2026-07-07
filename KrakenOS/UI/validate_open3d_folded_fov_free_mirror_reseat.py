"""Display-free guard for bugs/0244 -- the folded FOV/conjugate solve must RE-SEAT a
free-placed trailing fold mirror at its prescription distance past the lens, not slide it by
the raw gap delta (which, on a fixture that authors the mirror closer than its prescription
rear gap, throws the mirror clean PAST the lens -- "the lens crashes into the RA mirror").

flag(PYRITE 55x55 object-FOV Solve-for-Thickness): the object gap grows and the lens->mirror
rear gap shrinks by a large negative delta. bugs/0236 carried the free-placed mirror by
``post_fold_delta * (r_hat - z_hat)`` -- a RAW-delta slide along the reflected leg. But both
the PYRITE (~89 mm) and AZ85 (~92 mm) fixtures author the trailing mirror CLOSER to the lens
than its prescription rear gap (a real CAD pose vs the corner-spanning bugs/0242 leg
convention). Sliding by the raw delta preserves that stale offset, so a large rear-gap shrink
drives the mirror's along-beam coordinate BELOW the lens rear -> the on-axis cone folds at the
mirror before it ever reaches the lens.

Fix (bugs/0244): ``carry_free_placed_followers_after_fold`` re-seats the along-beam (r_hat)
coordinate at the LEG-WALK follower position -- ``pred_center . r_hat + near_leg`` from
``build_optical_solid_output_port_pose_overrides`` (the same walk that seats plain followers) --
while keeping the perpendicular (z_hat) drift term. The mirror rides the beam at the solved
rear gap regardless of the stale authored offset. On a fixture with no stale offset the r_hat
coefficient equals the old raw delta, so the bugs/0236 two-fold behaviour is unchanged.

  (A) RE-SEAT AT PRESCRIPTION: after a large rear-gap shrink + carry the mirror's along-beam
      coordinate == lens-rear-along + the (new) rear gap -- it rides at the prescription
      distance, not at the stale authored offset.
  (B) NOT PAST THE LENS: the fix seats the mirror AFTER the lens rear; the OLD raw-delta slide
      would have seated it BEFORE the lens (the reported crash). Ordered vs disordered.
  (C) PERP PRESERVED: the carry leaves the mirror's perpendicular (z_hat) beam offset
      untouched -- it only re-seats along the beam (same on-beam invariant bugs/0236 checks).
  (D) END-TO-END ORDERED: the REAL Solve-for-Thickness conjugate solve leaves the trailing
      mirror after the lens along the beam (guards the reported symptom through production).
  (E) WIRED: the carry re-seats via the leg-walk anchor (near_leg), not a raw ``r_hat - z_hat``
      slide -- a refactor back to the raw-delta form trips this guard.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_fov_free_mirror_reseat
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
import types
from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.validate_open3d_two_fold_image_arm_follow import _two_fold_editor
from KrakenOS.UI.nonseq_output_ports import (
    build_optical_solid_output_port_pose_overrides,
    carry_free_placed_followers_after_fold,
    _row_advanced,
)
from KrakenOS.UI.services.folded_sequential_fold import mirror_fold_face_normal


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _reflected_leg(rows):
    """(first_fold_index, r_hat) for the first mirror fold -- the direction the image arm
    walks along after the object fold."""
    for index, row in enumerate(rows):
        normal = mirror_fold_face_normal(_row_advanced(row))
        if normal is not None:
            zhat = np.array([0.0, 0.0, 1.0])
            rhat = zhat - 2.0 * float(np.dot(zhat, normal)) * normal
            return index, rhat / float(np.linalg.norm(rhat))
    return None, None


def _promoted_rows(rows):
    return [i for i, r in enumerate(rows)
            if isinstance((getattr(r, "advanced", {}) or {}).get("StepOverlayPromotion"), dict)
            or isinstance((getattr(r, "advanced", {}) or {}).get("StepNativePromotion"), dict)]


def _centers(rows):
    ov = build_optical_solid_output_port_pose_overrides(list(rows))
    return ov


def _along(ov, row_i, rhat):
    c = ov.get(row_i, {}).get("center")
    return float(np.dot(np.asarray(c, dtype=float).reshape(3), rhat)) if c is not None else float("nan")


def _perp(ov, row_i):
    c = ov.get(row_i, {}).get("center")
    return float(np.asarray(c, dtype=float).reshape(3)[2]) if c is not None else float("nan")


def validate_folded_fov_free_mirror_reseat() -> list[Check]:
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    checks: list[Check] = []

    # ---- controlled shrink of the rear gap + carry (simulates the large-negative image delta) --
    editor = _two_fold_editor()
    rows = editor.rows
    first_fold, rhat = _reflected_leg(rows)
    promoted = _promoted_rows(rows)
    m2 = promoted[-1]
    rear_gap = m2 - 1

    ov0 = _centers(rows)
    m2_along0 = _along(ov0, m2, rhat)
    lens_rear_along = _along(ov0, rear_gap, rhat)
    m2_perp0 = _perp(ov0, m2)

    old_th = float(rows[rear_gap].thickness)
    new_th = 15.0
    delta = new_th - old_th
    rows[rear_gap].thickness = new_th
    carried = carry_free_placed_followers_after_fold(rows, [(rear_gap, delta)])

    ov1 = _centers(rows)
    m2_along1 = _along(ov1, m2, rhat)
    m2_perp1 = _perp(ov1, m2)
    old_would_be = m2_along0 + delta  # what the bugs/0236 raw-delta slide produced

    checks.append(Check(
        "RE-SEAT AT PRESCRIPTION: after a large rear-gap shrink the trailing mirror rides the "
        "beam at lens-rear + the new rear gap, not at its stale authored offset",
        carried == [m2] and abs(m2_along1 - (lens_rear_along + new_th)) < 1e-2,
        f"carried={carried} m2_along={m2_along1:.3f} target(rear+gap)={lens_rear_along + new_th:.3f}",
    ))

    checks.append(Check(
        "NOT PAST THE LENS: the fix seats the mirror AFTER the lens rear; the old raw-delta "
        "slide would have thrown it BEFORE the lens (the reported crash)",
        old_would_be < lens_rear_along < m2_along1,
        f"old_raw_slide={old_would_be:.3f} lens_rear={lens_rear_along:.3f} fix={m2_along1:.3f}",
    ))

    checks.append(Check(
        "PERP PRESERVED: the carry re-seats only along the beam -- the perpendicular (z) beam "
        "offset is untouched",
        abs(m2_perp1 - m2_perp0) < 1e-3,
        f"perp {m2_perp0:.4f}->{m2_perp1:.4f}",
    ))

    # ---- (D) end-to-end: the REAL conjugate solve keeps the mirror after the lens ------------- #
    editor2 = _two_fold_editor()
    qe = QuickEstimationService(types.SimpleNamespace(editor=editor2))
    rows2 = editor2.rows
    first_fold2, rhat2 = _reflected_leg(rows2)
    m2b = _promoted_rows(rows2)[-1]
    rear2 = m2b - 1
    ok_solve, _msg = _quiet(qe._apply_conjugate_pair, 30.0, 21.0)
    ovd = _centers(rows2)
    m2_along_d = _along(ovd, m2b, rhat2)
    lens_rear_d = _along(ovd, rear2, rhat2)
    checks.append(Check(
        "END-TO-END ORDERED: the real Solve-for-Thickness leaves the trailing mirror after the "
        "lens along the beam",
        bool(ok_solve) and m2_along_d > lens_rear_d + 1e-3,
        f"ok={ok_solve} m2_along={m2_along_d:.3f} lens_rear={lens_rear_d:.3f}",
    ))

    # ---- (E) wiring: the carry re-seats via the leg-walk anchor, not a raw r_hat-z_hat slide -- #
    carry_src = inspect.getsource(carry_free_placed_followers_after_fold)
    reseats = (
        "build_optical_solid_output_port_pose_overrides" in carry_src
        and "near_leg" in carry_src
        # the bugs/0236 raw-delta slide form is gone
        and "rhat - zhat" not in carry_src
        and "delta_dir" not in carry_src
    )
    checks.append(Check(
        "WIRED: the carry re-seats the along-beam coordinate at the leg-walk follower position "
        "(near_leg), not by a raw r_hat-z_hat slide of the stale pose",
        reseats,
        f"leg_walk={'build_optical_solid_output_port_pose_overrides' in carry_src} "
        f"near_leg={'near_leg' in carry_src} raw_slide_gone="
        f"{'rhat - zhat' not in carry_src and 'delta_dir' not in carry_src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_fov_free_mirror_reseat()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_fov_free_mirror_reseat()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded-FOV free-mirror-reseat validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
