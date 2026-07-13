"""Display-free guard for the folded IMAGE-distance split (bugs/0242 -- the "2+2" per-segment
constraint: after the object side (bugs/0234-0237), the user may also pin one leg of the IMAGE
conjugate at the 2nd periscope fold).

In a two-fold relay the image distance is bent by the image-side RA mirror:
image_total = near + far (last lens surface -> mirror -> sensor, along the folded beam). The optics
fix image_total (the conjugate / focus); the split is the mechanical freedom.
``_folded_image_conjugate_split`` reports the legs; ``_apply_folded_image_split`` pins one leg and
SLIDES the mirror (the leg INTO the mirror +delta against the mirror->sensor leg -delta) so
image_total -- and therefore the focus -- is untouched, and the FREE-PLACED trailing mirror is
carried onto the reflected leg (bugs/0236) so it stays on the beam.

Unlike the object mirror (a sequential fold), the image mirror is a free-placed promoted solid whose
``desp_z`` is a WORLD offset, so the split is read off the straight-equivalent gap ROWS (which sum to
``_paraxial_total_image_gap``); the object side's ``station + desp_z`` arithmetic does not apply.

  (A) SPLIT: near + far == image_total; near = the last-lens-surface -> mirror leg sum and far =
      the mirror -> sensor leg sum in the straight-equivalent.
  (B) SLIDE keeps the conjugate + mirror on beam: pinning ``near`` slides the mirror there, the
      image total is unchanged, and the trailing mirror keeps its beam offset (not thrown off-axis).
  (C) RANGE: a constraint that would need a negative gap is rejected, not applied.
  (C2) SAFE GAP: each leg has a collision floor (half the mirror body) -- a valid far applies, an
      unsafe one is rejected.
  (D) TRACE: after a valid slide the scene still images -- the real traced rays (bugs/0243)
      terminate on the folded Image-surface seat.
  (E) WIRED: the IMAGE FOV popup offers the image near/far segment checkboxes and the solve
      dispatches the pinned leg to ``_apply_folded_image_split``.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_image_segment_split
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.validate_open3d_two_fold_image_arm_follow import _two_fold_editor, _mirror_and_arm
from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _straight_legs(editor):
    """Reconstruct (near, far) from the straight-equivalent gap rows, independently of the split
    method, to pin the definition: near = last-lens-surface -> mirror, far = mirror -> sensor."""
    rows = editor.rows
    total, last_src, _ref = editor._paraxial_total_image_gap()
    gap_start = int(last_src)
    while gap_start > 1 and _row_is_promoted_mirror_fold(rows[gap_start]):
        gap_start -= 1
    image_row = next(
        (i for i in range(len(rows) - 1, -1, -1) if str(getattr(rows[i], "surface", "")) == "Image"),
        len(rows) - 1,
    )
    folds = [int(i) for i in editor._promoted_mirror_fold_row_indices()]
    mirror_row = next((m for m in folds if gap_start < m < image_row), None)
    th = [max(float(getattr(r, "thickness", 0.0) or 0.0), 0.0) for r in rows]
    near = float(sum(th[gap_start:mirror_row])) if mirror_row is not None else None
    far = float(sum(th[mirror_row:image_row])) if mirror_row is not None else None
    return total, near, far, mirror_row


def validate_folded_image_segment_split() -> list[Check]:
    checks: list[Check] = []
    editor = _two_fold_editor()

    split = _quiet(editor._folded_image_conjugate_split)
    total0, near_legs, far_legs, mirror_row = _straight_legs(editor)

    # ---- (A) split adds up + matches the straight-equivalent legs ---------------------------- #
    checks.append(Check(
        "SPLIT: near + far == image_total; near/far match the straight-equivalent fold legs",
        split is not None
        and abs((split["near"] + split["far"]) - split["total"]) < 1e-6
        and abs(split["total"] - total0) < 1e-6
        and near_legs is not None
        and abs(split["near"] - near_legs) < 1e-6
        and abs(split["far"] - far_legs) < 1e-6
        and int(split["mirror_row"]) == int(mirror_row),
        f"split={None if split is None else {k: round(v, 2) if isinstance(v, float) else v for k, v in split.items()}} "
        f"legs near={None if near_legs is None else round(near_legs, 2)} far={None if far_legs is None else round(far_legs, 2)}",
    ))

    # ---- (B) slide keeps the conjugate + trailing mirror stays on the beam ------------------- #
    m2b, armb = _mirror_and_arm(editor.rows)
    off_b = float(m2b[2] - armb[2])
    target_near = float(split["near"]) - 15.0 if split else 0.0
    ok, _msg = _quiet(editor._apply_folded_image_split, "near", target_near)
    total1, _n1, _f1, _mr1 = _straight_legs(editor)
    split1 = _quiet(editor._folded_image_conjugate_split)
    m2a, arma = _mirror_and_arm(editor.rows)
    off_a = float(m2a[2] - arma[2])
    moved = float(np.linalg.norm(m2a - m2b))
    checks.append(Check(
        "SLIDE: pinning near slides the mirror there; image total unchanged + mirror stays on beam",
        bool(ok)
        and split1 is not None
        and abs(split1["near"] - target_near) < 1e-4
        and abs(total1 - total0) < 1e-4
        and moved > 1.0
        and abs(off_a - off_b) < 1e-3,
        f"applied={ok} new_near={None if split1 is None else round(split1['near'], 2)} "
        f"(target {round(target_near, 2)}) total {round(total0, 2)}->{round(total1, 2)} "
        f"mirror_moved={moved:.2f} beam_offset {off_b:.4f}->{off_a:.4f}",
    ))

    # ---- (C) out-of-range rejected ---------------------------------------------------------- #
    ok_bad, msg_bad = _quiet(editor._apply_folded_image_split, "near", 1.0e6)
    checks.append(Check(
        "RANGE: a constraint that needs a negative gap is rejected, not applied",
        not ok_bad,
        f"rejected={not ok_bad} msg={msg_bad[:70]!r}",
    ))

    # ---- (C2) SAFE GAP: the mirror cannot slide into the lens (near) or the detector (far) --- #
    split_now = _quiet(editor._folded_image_conjugate_split)
    far_min = float(split_now.get("far_min", 0.0)) if split_now else 0.0
    ok_safe, _m_safe = _quiet(editor._apply_folded_image_split, "far", far_min + 8.0)
    ok_unsafe, msg_unsafe = _quiet(editor._apply_folded_image_split, "far", far_min - 3.0)
    checks.append(Check(
        "SAFE GAP: mirror->sensor has a collision floor -- a valid far applies, an unsafe one is rejected",
        far_min > 0 and ok_safe and (not ok_unsafe) and "Safe gap" in msg_unsafe,
        f"far_min={far_min:.2f} valid(far_min+8)={ok_safe} unsafe(far_min-3)_rejected={not ok_unsafe}",
    ))

    # ---- (D) still images after a valid slide ----------------------------------------------- #
    _s, _r, bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    # bugs/0243: the drawn rays ARE the real trace and terminate on the folded
    # Image-surface seat (the same pose-override plane the display seats the sensor
    # with), so assert the slide left a scene that still images onto that plane.
    # (The bundle's detector TARGET still derives from prescription-station
    # arithmetic that can disagree with the seat around a free-placed trailing
    # mirror; reconciling target/seat/prescription is the bugs/0244 follow-up.)
    overrides = getattr(editor.last_system, "_optical_solid_output_port_pose_overrides", {}) or {}
    image_pose = overrides.get(len(editor.rows) - 1)
    reach = 0
    if isinstance(image_pose, dict) and bundle.ray_paths:
        seat_c = np.asarray(image_pose.get("center"), dtype=float).reshape(3)
        seat_n = np.asarray(image_pose.get("rotation"), dtype=float).reshape(3, 3)[:, 2]
        seat_n = seat_n / max(float(np.linalg.norm(seat_n)), 1e-12)
        ends = np.asarray([np.asarray(p.points_world, dtype=float)[-1][:3] for p in bundle.ray_paths])
        reach = int((np.abs((ends - seat_c[None, :]) @ seat_n) < 1e-6).sum())
    checks.append(Check(
        "TRACE: after the slide the scene still images (rays terminate on the folded Image seat)",
        isinstance(image_pose, dict) and reach >= 8,
        f"rays={len(bundle.ray_paths or [])} image_seat={'set' if isinstance(image_pose, dict) else 'missing'} on_seat={reach}",
    ))

    # ---- (E) the IMAGE FOV popup offers the image near/far checkboxes + solve dispatches ------ #
    import inspect

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    popup_src = inspect.getsource(Kraken3DInspector._open_quick_estimation_fov_popup)
    apply_src = inspect.getsource(Kraken3DInspector._apply_quick_estimation_fov_solve)
    wired = (
        "_folded_image_conjugate_split()" in popup_src         # gate the image checkboxes on a fold
        and "Constrain lens rear" in popup_src              # the image near-leg label
        and "mirror → sensor" in popup_src                     # the image far-leg label
        and "segment=segment" in popup_src                     # threaded to the solve
        and "_apply_folded_image_split" in apply_src           # the solve slides the image mirror
    )
    checks.append(Check(
        "WIRED: the image FOV popup offers the image near/far checkboxes and the solve honors them",
        wired,
        f"popup_gate={'_folded_image_conjugate_split()' in popup_src} "
        f"popup_near={'Constrain lens rear' in popup_src} popup_far={'mirror → sensor' in popup_src} "
        f"solve_applies_split={'_apply_folded_image_split' in apply_src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_image_segment_split()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_image_segment_split()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded-image-segment-split validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
