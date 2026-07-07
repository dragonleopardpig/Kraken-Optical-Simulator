"""Display-free guard for bugs/0247 -- the OBJECT Plane FOV dialog now pins BOTH fold legs in
one solve. The object fold and the image fold are INDEPENDENT mechanical freedoms (the object
mirror is a sequential fold; the image mirror is a free-placed promoted solid, on a different
pair of gap rows), so the object popup offers two checkbox groups -- object-side (object ->
mirror / mirror -> first surface) AND image-side (last surface -> mirror / mirror -> sensor) --
and a single "Solve for Thickness" fills the sensor, then slides the object mirror to the pinned
object leg AND the image mirror to the pinned image leg. Before bugs/0247 the image leg could
only be pinned from the separate IMAGE popup, so a user could not constrain both in one action.

The production path is ``_apply_quick_estimation_fov_solve(plane="object", ..., segment=<object
leg>, image_segment=<image leg>)`` which runs ``fov_solve`` -> ``_apply_folded_object_split`` ->
``_apply_folded_image_split``. Each split preserves its conjugate TOTAL (the focus), pins its
leg, and carries the free-placed trailing mirror onto the beam via the bugs/0244 leg-walk carry.

This guard replicates that sequence on the AZ85 two-fold fixture (object mirror = row 1, image
mirror = row 8, reflected leg r_hat = +X) and pins:

  (A) BOTH CONJUGATES HELD: after fov_solve + object split(near) + image split(near), each
      conjugate's TOTAL is unchanged from the post-fov_solve value (focus preserved on both
      sides) and each pinned near leg equals the requested value.
  (B) IMAGE MIRROR RIDES THE BEAM: the free-placed image mirror re-seats at
      ``last-lens-surface + image near`` along r_hat (the bugs/0244 re-seat) -- ordered after
      the lens, not frozen at its stale authored offset.
  (C) INDEPENDENT FREEDOMS: applying the image split leaves the object split's pinned leg (and
      total) untouched, and the object split leaves the image total untouched -- the two legs
      are pinned in the same solve without fighting each other.
  (D) WIRED: the OBJECT popup builds both an object and an image split group, threads
      ``image_segment`` into the solve, and ``_apply_quick_estimation_fov_solve`` applies it via
      ``_apply_folded_image_split`` (gated on the object plane) and records it for replay. A
      refactor that drops the second group / the image_segment plumbing trips this guard.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_object_plus_image_split
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
import os
import types
from dataclasses import dataclass

import numpy as np

import KrakenOS.UI as _ui_pkg
from KrakenOS.UI.validate_open3d_two_fold_image_arm_follow import _two_fold_editor
from KrakenOS.UI.nonseq_output_ports import (
    build_optical_solid_output_port_pose_overrides,
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


def _along(ov, row_i, rhat):
    c = ov.get(row_i, {}).get("center")
    return float(np.dot(np.asarray(c, dtype=float).reshape(3), rhat)) if c is not None else float("nan")


def _method_src(full_src: str, name: str) -> str:
    """Slice out one ``    def name(...)`` method body (up to the next same-indent def)."""
    marker = f"    def {name}("
    start = full_src.find(marker)
    if start < 0:
        return ""
    nxt = full_src.find("\n    def ", start + len(marker))
    return full_src[start:nxt] if nxt > 0 else full_src[start:]


def validate_folded_object_plus_image_split() -> list[Check]:
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    checks: list[Check] = []

    editor = _quiet(_two_fold_editor)
    rows = editor.rows
    _first_fold, rhat = _reflected_leg(rows)
    promoted = _promoted_rows(rows)
    img_mirror = promoted[-1]
    last_lens = img_mirror - 1
    qe = QuickEstimationService(types.SimpleNamespace(editor=editor))

    # ---- the exact object-dialog sequence: FOV thickness solve, then BOTH leg pins ------------- #
    ok_fov, _msg = _quiet(qe.fov_solve, "object", "thickness", 30.0, 21.0, None)
    obj0 = editor._folded_object_conjugate_split()
    img0 = editor._folded_image_conjugate_split()
    obj_total0, img_total0 = float(obj0["total"]), float(img0["total"])

    obj_near_pin, img_near_pin = 60.0, 100.0
    ok_obj, _mo = editor._apply_folded_object_split("near", obj_near_pin)
    # snapshot the image total the object split leaves behind (independence, part 1)
    img_after_obj = editor._folded_image_conjugate_split()
    obj_near_after_obj = float(editor._folded_object_conjugate_split()["near"])
    ok_img, _mi = editor._apply_folded_image_split("near", img_near_pin)

    obj1 = editor._folded_object_conjugate_split()
    img1 = editor._folded_image_conjugate_split()

    checks.append(Check(
        "BOTH CONJUGATES HELD: one solve fills the sensor and pins one object leg and one image "
        "leg; each conjugate total (the focus) is preserved and each pinned leg is exact",
        (ok_fov and ok_obj and ok_img
         and abs(float(obj1["total"]) - obj_total0) < 1e-2
         and abs(float(img1["total"]) - img_total0) < 1e-2
         and abs(float(obj1["near"]) - obj_near_pin) < 1e-2
         and abs(float(img1["near"]) - img_near_pin) < 1e-2),
        f"obj total {obj_total0:.3f}->{float(obj1['total']):.3f} near->{float(obj1['near']):.3f} "
        f"(pin {obj_near_pin}); img total {img_total0:.3f}->{float(img1['total']):.3f} "
        f"near->{float(img1['near']):.3f} (pin {img_near_pin})",
    ))

    # ---- (B) the free-placed image mirror rides the beam at the pinned leg (bugs/0244 re-seat) -- #
    ov = build_optical_solid_output_port_pose_overrides(list(rows))
    last_lens_along = _along(ov, last_lens, rhat)
    img_mirror_along = _along(ov, img_mirror, rhat)
    target = last_lens_along + img_near_pin
    checks.append(Check(
        "IMAGE MIRROR RIDES THE BEAM: the free-placed image mirror re-seats at last-lens + the "
        "pinned image leg along the reflected arm (ordered after the lens, not the stale offset)",
        last_lens_along < img_mirror_along and abs(img_mirror_along - target) < 1e-2,
        f"last_lens_along={last_lens_along:.3f} img_mirror_along={img_mirror_along:.3f} "
        f"target(last_lens+near)={target:.3f}",
    ))

    # ---- (C) the two legs are independent -- neither pin disturbs the other's conjugate -------- #
    checks.append(Check(
        "INDEPENDENT FREEDOMS: the image split leaves the object leg + both totals untouched, and "
        "the object split leaves the image total untouched (object/image folds are separate DOF)",
        (abs(obj_near_after_obj - obj_near_pin) < 1e-2
         and abs(float(obj1["near"]) - obj_near_pin) < 1e-2
         and abs(float(img_after_obj["total"]) - img_total0) < 1e-2),
        f"obj near after obj-split={obj_near_after_obj:.3f} after img-split={float(obj1['near']):.3f} "
        f"(pin {obj_near_pin}); img total after obj-split={float(img_after_obj['total']):.3f} "
        f"(was {img_total0:.3f})",
    ))

    # ---- (D) wiring: the object popup builds both groups + threads image_segment through -------- #
    src_path = os.path.join(os.path.dirname(_ui_pkg.__file__), "open3d_inspector.py")
    with open(src_path, "r", encoding="utf-8") as fh:
        full_src = fh.read()
    popup = _method_src(full_src, "_open_quick_estimation_fov_popup")
    apply_src = _method_src(full_src, "_apply_quick_estimation_fov_solve")
    # the popup builds a reusable per-conjugate group and calls it for BOTH object and image
    w_obj_group = '_build_split_group(\n                    _obj_split, "object"' in popup
    w_img_group = '_build_split_group(\n                    _img_split, "image"' in popup
    w_thread = "image_segment_getter" in popup and "image_segment=image_segment" in popup
    # the solve applies the image leg via the image split, gated on the object plane, + records it
    w_gated = 'image_segment is not None and plane == "object"' in apply_src
    w_apply = "_apply_folded_image_split" in apply_src and w_gated
    w_record = '"image_segment"' in apply_src
    wired = w_obj_group and w_img_group and w_thread and w_apply and w_record
    checks.append(Check(
        "WIRED: the object popup builds both split groups and threads image_segment into the "
        "solve, which applies it via _apply_folded_image_split (object plane) and records it",
        wired,
        f"obj_group={w_obj_group} img_group={w_img_group} thread={w_thread} "
        f"apply_gated={w_apply} recorded={w_record}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_object_plus_image_split()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_object_plus_image_split()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded object+image combined-split validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
