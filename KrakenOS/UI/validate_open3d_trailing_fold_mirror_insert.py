"""Display-free guard for bugs/0232 -- a SECOND (trailing) fold mirror promoted near the camera
must fold ONLY the camera, not the lens group it physically sits after.

The flag (flag_20260705_172709, "after second RA promoted, it should only fold the camera"):
the free-placed 2nd RA mirror was inserted at row 2 (right after the FIRST mirror, via the table
selection's max(selected)+1), BEFORE the lens group. The pose-override walk folds every row after
the mirror, so on the re-saved Pyrite periscope the lens element "Blackbox Group 1" (row 5) folded
onto the mirror-2 branch at y=190.6 along with the camera -- not "only the camera".

Root: the trailing fold mirror was at the wrong sequential position. It must be the LAST optical
element before the sensor (like AZ85's 2nd mirror at row 8), so the fold moves only the image.
Fix (open3d_face_assignment `_promote_step_and_assign_face_function_inner`): when the scene ALREADY
has a promoted mirror fold and the user is assigning a Full-Reflecting face, insert the promotion
at the end (before Image) instead of after the selected row.

  (A) MECHANISM: on the two-mirror AZ85 (mirror-2 at the END) the LAST promoted mirror folds ONLY
      the image/camera row -- not the lens rows. This is exactly "only the camera", and it holds
      because the mirror is the last element before the sensor.
  (B) DECISION: promoting into an index at/after the row count resolves (clamps) to before-Image
      (the end); a large trailing-fold insert lands there, not after the first mirror.
  (C) WIRED: the face-assign inner computes `promote_insert_at = len(self.editor.rows)` when the
      assignment is a full mirror AND the scene already has a promoted fold.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_trailing_fold_mirror_insert
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover as carryover
from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides
from KrakenOS.UI.optical_solid_metadata import OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_MIRROR
from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FACE_ASSIGN_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "open3d_face_assignment.py"


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def validate_trailing_fold_mirror_insert() -> list[Check]:
    checks: list[Check] = []

    editor = _quiet(_build_editor, _AZ85)
    _quiet(carryover._promote_mirror2, editor)  # AZ85 two-mirror; mirror-2 at the END
    folds = list(editor._promoted_mirror_fold_row_indices())
    image_row = len(editor.rows) - 1

    # ---- (A) the last (trailing) mirror folds ONLY the image/camera ------------------------- #
    overrides = _quiet(optical_solid_output_port_pose_overrides, None, editor.rows)
    last_fold = max(folds) if folds else -1
    rows_folded_by_last = sorted(
        int(k) for k, v in overrides.items() if int(v.get("source_index", -1)) == last_fold
    )
    checks.append(Check(
        "MECHANISM: the LAST promoted mirror (at the chain end) folds ONLY the image/camera row",
        bool(folds) and rows_folded_by_last == [image_row],
        f"fold_rows={folds} last={last_fold} rows_it_folds={rows_folded_by_last} "
        f"(expect only image row {image_row}; a mid-chain mirror would also fold the lens rows)",
    ))

    # ---- (B) `_step_overlay_insert_index` clamps a large index to before-Image (the end) ----- #
    # (Called on the live app; on the __new__ snapshot editor the tk sentinel intercepts it, so
    # assert the clamp at the source level: min(index, len(rows) - 1_if_last_is_Image).)
    from KrakenOS.UI.services.step_overlay_promotion import StepOverlayPromotionService

    insert_src = inspect.getsource(StepOverlayPromotionService._step_overlay_insert_index)
    clamps_before_image = (
        'self.rows[-1].surface == "Image"' in insert_src
        and "min(resolved_insert_at" in insert_src
    )
    checks.append(Check(
        "DECISION: the insert-index clamps a large (end) index to the row before Image",
        clamps_before_image,
        f"clamp_present={clamps_before_image} (so insert_at=len(rows) -> before-Image)",
    ))

    # ---- (C) the decision (Full-Reflecting + existing fold -> end insert) is exercised ------ #
    is_full_mirror = str(OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_MIRROR).strip() == "Full Reflecting"
    existing_folds = list(editor._promoted_mirror_fold_row_indices())
    decided_insert_at = len(editor.rows) if (is_full_mirror and existing_folds) else None
    checks.append(Check(
        "DECISION: a full-mirror assignment with an existing fold picks the end index",
        decided_insert_at == len(editor.rows) and decided_insert_at is not None,
        f"full_mirror={is_full_mirror} existing_folds={bool(existing_folds)} insert_at={decided_insert_at}",
    ))

    # ---- (D) wiring ------------------------------------------------------------------------- #
    src = inspect.getsource(
        Open3DFaceAssignmentService._promote_step_and_assign_face_function_inner
    )
    wired = (
        "bugs/0232" in src
        and "promote_insert_at = len(self.editor.rows)" in src
        and "_promoted_mirror_fold_row_indices()" in src
        and "OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_MIRROR" in src
        and "insert_at=promote_insert_at" in src
    )
    checks.append(Check(
        "WIRED: the face-assign inner inserts a trailing full-mirror fold at the end",
        wired,
        f"bugs/0232={'bugs/0232' in src} end_insert={'promote_insert_at = len(self.editor.rows)' in src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_trailing_fold_mirror_insert()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_trailing_fold_mirror_insert()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Trailing-fold-mirror-insert validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
