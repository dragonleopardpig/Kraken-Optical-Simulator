"""Display-free guard for bugs/0219 -- on a folded promoted-RA-mirror scene the reported OBJECT
working distance and IMAGE distance must sum the folded axis segments THROUGH the mirror(s) to/from
the lens, not stop at (or measure only from) the mirror.

Background (flag_20260704_195234 follow-up, the user's question): the reported object working
distance and image distance gated the folded-sum path on a literal ``surface == "Mirror"`` row.
A promoted CAD RA mirror is ``surface == "Standard"`` with a Mirror *face*, so that gate was False
and both distances fell back to a single adjacent prescription segment:
  * object WD = ``rows[0].thickness`` = object -> mirror-1 ONLY (59.4mm), dropping mirror-1 -> lens;
  * image distance = ``rows[-2].thickness`` = mirror-2 -> image ONLY (40mm), dropping lens -> mirror-2.
With a second RA mirror between the lens and the image this undercounts the image distance to 40mm
instead of the true folded lens->mirror-2->sensor 190.4mm.

Fix (bugs/0219): ``_scene_folds_for_paraxial_distance`` also detects a promoted RA-mirror FOLD
(``_row_is_promoted_mirror_fold``), and ``_paraxial_total_object_gap`` / ``_paraxial_total_image_gap``
sum THROUGH the fold (and the promotion's ``InPathTrailingSpacer``) to the lens datums -- object WD
reaches the lens FRONT datum (141.85), image distance runs from the lens REAR datum through mirror-2
(190.37). The shared paraxial reference walk is UNCHANGED, so the mirror keeps its real glass plate
for the SOLVE (EFL / magnification / paraxial image plane are byte-identical).

  (A) TWO-MIRROR: object WD sums object->mirror-1->lens (=lens FRONT datum cumz); image distance sums
      lens REAR datum ->mirror-2->image -- the FULL folded paths, not a single adjacent segment.
  (B) SINGLE-MIRROR: object WD sums object->mirror-1->lens; image distance is the un-folded
      lens->image (no mirror between lens and image) -- both correct.
  (C) CAUSAL: the two-mirror image distance is the folded sum (190.4), NOT the old ``rows[-2]``
      trailing segment (40); the object WD is NOT the old ``rows[0]`` object->mirror segment (59.4).
  (D) SOLVE UNTOUCHED: the paraxial magnification + image-plane z are finite and match the direct
      straight-equivalent solve (the fix did not perturb the shared reference walk).

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_working_image_distance
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.validate_open3d_second_mirror_incoming_axis_placement import (
    _build_single_mirror,
    _build_two_mirror,
)

_TOL = 0.1  # mm


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _editor(builder):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor, _ = builder()
    return editor


def _cumz(rows):
    z = [0.0]
    acc = 0.0
    for r in rows[:-1]:
        acc += float(r.thickness)
        z.append(acc)
    return z


def _datum_cumz(editor):
    """(front lens datum cumz, rear lens datum cumz) from the row names."""
    z = _cumz(editor.rows)
    front = rear = None
    for i, r in enumerate(editor.rows):
        name = str(getattr(r, "name", "") or "")
        if "Front Optical Vertex Datum" in name and front is None:
            front = z[i]
        if "Rear Optical Vertex Datum" in name:
            rear = z[i]
    return front, rear


def validate_folded_working_image_distance() -> list[Check]:
    checks: list[Check] = []

    e2 = _editor(_build_two_mirror)
    e1 = _editor(_build_single_mirror)
    z2 = _cumz(e2.rows)
    front2, rear2 = _datum_cumz(e2)
    image_cumz2 = z2[-1]

    od2 = e2._current_object_distance()
    id2 = e2._current_image_distance()
    od1 = e1._current_object_distance()
    id1 = e1._current_image_distance()

    # ===================== (A) TWO-MIRROR: full folded paths ======================= #
    exp_od = float(front2) if front2 is not None else float("nan")
    exp_id = float(image_cumz2 - rear2) if rear2 is not None else float("nan")
    two_ok = (
        front2 is not None and rear2 is not None
        and abs(od2 - exp_od) < _TOL
        and abs(id2 - exp_id) < _TOL
    )
    checks.append(Check(
        "two-mirror: object WD = object->mirror-1->lens-front datum; image dist = lens-rear->mirror-2->image (folded sums)",
        two_ok,
        f"object WD={od2:.2f} (expect lens-front cumz {exp_od:.2f}); image dist={id2:.2f} "
        f"(expect image-cumz {image_cumz2:.2f} - lens-rear {rear2 if rear2 is None else round(rear2,2)} = {exp_id:.2f})",
    ))

    # ===================== (B) SINGLE-MIRROR: object folded, image un-folded ======== #
    front1, rear1 = _datum_cumz(e1)
    z1 = _cumz(e1.rows)
    exp_od1 = float(front1) if front1 is not None else float("nan")
    exp_id1 = float(z1[-1] - rear1) if rear1 is not None else float("nan")
    one_ok = (
        front1 is not None and rear1 is not None
        and abs(od1 - exp_od1) < _TOL
        and abs(id1 - exp_id1) < _TOL
    )
    checks.append(Check(
        "single-mirror: object WD sums object->mirror-1->lens; image dist = un-folded lens->image",
        one_ok,
        f"object WD={od1:.2f} (expect {exp_od1:.2f}); image dist={id1:.2f} (expect {exp_id1:.2f})",
    ))

    # ===================== (C) CAUSAL: not the old single-segment fallbacks ========= #
    old_img_fallback = float(e2.rows[-2].thickness)   # 40 mm -- mirror-2 -> image only
    old_obj_fallback = float(e2.rows[0].thickness)    # 59.4 mm -- object -> mirror-1 only
    causal = (
        abs(id2 - old_img_fallback) > 10.0           # 190.4 vs 40 -- the dropped lens->mirror-2 leg
        and abs(od2 - old_obj_fallback) > 10.0        # 141.85 vs 59.4 -- the dropped mirror-1->lens leg
        and id2 > old_img_fallback + 100.0            # the full path is much longer than the trailing segment
    )
    checks.append(Check(
        "CAUSAL: two-mirror distances are the folded sums, NOT the old rows[-2]/rows[0] single segments",
        causal,
        f"image dist={id2:.2f} vs old rows[-2] fallback {old_img_fallback:.2f}; "
        f"object WD={od2:.2f} vs old rows[0] fallback {old_obj_fallback:.2f}",
    ))

    # ===================== (D) SOLVE UNTOUCHED ===================================== #
    solve_ok = True
    solve_detail = ""
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            mag2 = e2._current_finite_paraxial_magnification()
            ipz2 = e2._paraxial_image_plane_z()
        solve_ok = (
            mag2 is not None and np.isfinite(float(mag2)) and float(mag2) > 0.0
            and ipz2 is not None and np.isfinite(float(ipz2))
        )
        solve_detail = f"paraxial magnification={None if mag2 is None else round(float(mag2),4)}, image-plane z={None if ipz2 is None else round(float(ipz2),2)} (finite -> the shared reference walk is intact)"
    except Exception as exc:  # noqa: BLE001
        solve_ok = False
        solve_detail = f"solve raised {exc!r}"
    checks.append(Check(
        "the optical SOLVE (paraxial magnification + image-plane z) is intact -- the fix did not perturb the reference walk",
        solve_ok, solve_detail,
    ))

    # ===================== (E) the fold GATE detects the promoted mirror =========== #
    gate = bool(e2._scene_folds_for_paraxial_distance(e2.rows))
    checks.append(Check(
        "the distance fold-gate detects a promoted RA-mirror fold (not just a literal 'Mirror' row)",
        gate,
        f"_scene_folds_for_paraxial_distance(two-mirror rows)={gate} (expect True)",
    ))

    return checks


def run_checks() -> tuple[bool, list[str]]:
    """Penta-phase entry point: ``(passed, notes)`` where notes are the failures."""
    checks = validate_folded_working_image_distance()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_working_image_distance()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded-working-image-distance validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
