"""Display-free guard for bugs/0214 -- re-importing the SAME right-angle-mirror part a
second time (the user's "add another mirror" workflow) must inherit that part's authored
Mirror face automatically, so the new mirror folds DOWN by its own orientation with NO
manual "Full Reflecting" right-click.

Background: bugs/0213 (Fix B) made a free-placed 2nd promoted mirror fold by physics off
its own world orientation -- but ONLY once it carries a ``function == "Mirror"`` face. The
user's real session promoted the 2nd mirror with ZERO right-clicks, so it had NO Mirror
face. A clean promote auto-roles every face Transmit/Port, and ``select_optical_solid_output_face``
then picks the +Z straight-through face (bugs/0084) as the output port -> the downstream
image/detector seats UP (+Z) at the wrong side (flag_20260703_122209_873: image z 83..123
above the mirror centre z=70.6), which the user flagged as "the image plane and detector
wrong direction".

Fix (``StepOverlayPromotionService._carry_over_same_part_mirror_face``, called at the end of
``promote_imported_step_to_optical_solid_row``): when the freshly-promoted solid is the SAME
imported part (matched by resolved source STEP path) as a mirror already in the scene, carry
that donor's Mirror face over by ``face_id`` (with an area cross-check) via the standard
``assign_optical_solid_face_function`` path -- so the fold + detector seating see exactly a
user-authored Mirror face. Strictly scoped: a promoted lens/prism (no mirror donor) is never
turned into a reflector, a row the user already marked keeps its own authoring, and a
coincidental face-id collision across DIFFERENT parts cannot mis-assign.

This guard is display-free. It (A) promotes the real RA mirror at the flagged pose on the
AZ85 scene and asserts the carry-over fires -> the fold normal, the detector/image seating
and the free-placed ray fold all go DOWN, with a causal strip-to-UP contrast proving the
carried Mirror face is what folds it; and (B) drives the scoping helper directly over crafted
same-part / different-part / lens / already-authored / id-collision rows to prove it only ever
carries a genuine same-part Mirror face.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
from KrakenOS.UI.nonseq_output_ports import build_optical_solid_output_port_pose_overrides
from KrakenOS.UI.services.folded_sequential_fold import (
    fold_promoted_mirror_specs_to_sequential,
    free_placed_mirror_world_planes,
    mirror_fold_face_normal,
)
from KrakenOS.UI.services.step_overlay_promotion import StepOverlayPromotionService
from KrakenOS.UI.optical_solid_metadata import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR as _FACES_ATTR,
    normalize_optical_solid_face_metadata,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROMOTION_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "step_overlay_promotion.py"
SRC = PROJECT_ROOT / "attachment" / "prisms" / "Right_Angle_Mirror" / "87931" / "step_87391.step"

# The pose the user dropped + oriented the 2nd RA mirror at (flag_20260703_122209_873).
_OFFSET = (188.9223, -1.5322, 64.3484)
_ROT = (90.0, 45.0, 0.0)
_MIRROR2_Z = 70.6  # the placed 2nd-mirror world centre z; the fold must land BELOW it.
_FOLD_DOWN = np.asarray([-0.707, 0.0, -0.707], dtype=float)  # the hypotenuse normal at _ROT.


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _fmt(v) -> str:
    if v is None:
        return "None"
    a = np.asarray(v, dtype=float).reshape(-1)
    return "(" + ",".join(f"{x:+.3f}" for x in a[:3]) + ")"


def _promote_mirror2(editor) -> int:
    """Promote the RA mirror at the flagged free-placed pose on the AZ85 scene, headless.
    Returns the new solid row index."""
    for attr, val in (
        ("_external_cad_mesh_cache", {}),
        ("_transformed_step_overlay_cache", {}),
        ("_step_overlay_face_metadata_cache", {}),
        ("_step_analytic_document_cache", {}),
    ):
        if not hasattr(editor, attr) or getattr(editor, attr) is None:
            with contextlib.suppress(Exception):
                setattr(editor, attr, val)
    editor.imported_optical_step_path = SRC
    editor.optical_step_placement_offset_xyz = _OFFSET
    (editor.optical_step_rotation_x_deg,
     editor.optical_step_rotation_y_deg,
     editor.optical_step_rotation_z_deg) = _ROT
    for stub in (
        "_begin_history_capture", "_commit_history_capture", "_refresh_open_3d_views",
        "_sync_table", "_commit_pending_table_edit", "_read_rows_from_table",
        "_normalize_special_rows", "_select_table_indices", "_mark_plot_update_pending",
        "append_debug",
    ):
        setattr(editor, stub, lambda *a, **k: None)
    editor._selected_table_indices = lambda *a, **k: []
    with contextlib.suppress(Exception):
        editor._invalidate_step_overlay_face_metadata_cache("optical")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        editor.select_step_component("optical")
        out = editor.promote_imported_step_to_optical_solid_row(
            "optical", open_face_editor=False, clear_overlay=True, refresh_open_3d=False,
        )
    return int(out.get("row_index"))


def _image_center_z(rows) -> float | None:
    """The seated Image-row world centre z from the pose-override builder, or None."""
    overrides = build_optical_solid_output_port_pose_overrides(list(rows))
    for fi in sorted(overrides):
        if getattr(rows[fi], "surface", "?") == "Image":
            return float(np.asarray(overrides[fi].get("center"), dtype=float).reshape(3)[2])
    return None


def _strip_mirror_faces(row) -> None:
    """Force every stored face on ``row`` to a transmit output (clears role AND function so
    the normaliser cannot re-derive Mirror from a legacy role) -- reproduces a no-Mirror
    clean promote for the causal contrast."""
    stored = getattr(row, "advanced", {}).get(_FACES_ATTR, {})
    for face in (stored.get("faces", []) or []):
        face["function"] = "Transmit"
        face["role"] = "Output"
        face["port_role"] = "Output"


# --------------------------------------------------------------------------- #
# Scoping harness: drive the real carry-over helper over crafted rows without a
# scene, so the gating (same part / lens / already-authored / id-collision) is
# proven directly. The helper only touches ``self.rows``, the static source-key
# reader, and ``self.assign_optical_solid_face_function`` -- all provided here.
# --------------------------------------------------------------------------- #
class _Row:
    def __init__(self, advanced):
        self.advanced = advanced


class _FakeEditor:
    _promoted_source_step_key = staticmethod(StepOverlayPromotionService._promoted_source_step_key)

    def __init__(self, rows):
        self.rows = rows
        self.assigned: list[tuple[int, str, str]] = []

    def assign_optical_solid_face_function(self, row_index, face_id, function_label):
        self.assigned.append((int(row_index), str(face_id), str(function_label)))
        stored = self.rows[int(row_index)].advanced.get(_FACES_ATTR, {})
        for face in (stored.get("faces", []) or []):
            if str(face.get("face_id", "")) == str(face_id):
                face["function"] = "Mirror"


def _face(face_id, function, area, normal=(-0.707, 0.0, -0.707)):
    return {"face_id": face_id, "function": function, "area_mm2": area, "normal": list(normal)}


def _adv(source_path, faces):
    return {
        "StepOverlayPromotion": {"source_step_path": source_path},
        _FACES_ATTR: {"faces": faces},
    }


def _carry(rows, new_index):
    """Run the real ``_carry_over_same_part_mirror_face`` over crafted rows; return
    ``(assigned_face_id_or_None, assign_calls)``."""
    fake = _FakeEditor(rows)
    result = StepOverlayPromotionService._carry_over_same_part_mirror_face(fake, new_index)
    return result, list(fake.assigned)


_PART_A = "/tmp/kraken_0214_part_a.step"
_PART_B = "/tmp/kraken_0214_part_b.step"


def validate_second_mirror_same_part_mirror_carryover() -> list[Check]:
    checks: list[Check] = []

    # ===================== (A) END-TO-END on the real AZ85 scene ==================== #
    editor = _build_editor(_AZ85)
    ri = _promote_mirror2(editor)
    adv = getattr(editor.rows[ri], "advanced", {}) or {}
    mfn = mirror_fold_face_normal(adv)

    carried_ok = (
        mfn is not None
        and float(np.dot(np.asarray(mfn, dtype=float).reshape(3), _FOLD_DOWN)) > 0.99
    )
    checks.append(Check(
        "clean promote of a same-part RA mirror auto-carries the Mirror face (fold normal folds +X DOWN)",
        carried_ok,
        f"mirror_fold_face_normal={_fmt(mfn)} (expect ~{_fmt(_FOLD_DOWN)}, dot>0.99)",
    ))

    img_z_down = _image_center_z(editor.rows)
    seat_down = img_z_down is not None and img_z_down < _MIRROR2_Z - 1.0
    checks.append(Check(
        "the detector/image seats DOWN (-Z) below the placed 2nd mirror (not the flagged +Z UP)",
        seat_down,
        f"image_center_z={None if img_z_down is None else round(img_z_down, 3)} "
        f"(expect < {_MIRROR2_Z - 1.0}; flagged bug was UP ~83..123)",
    ))

    specs = editor._serializable_specs_for_rows(list(editor.rows))
    _folded, records = fold_promoted_mirror_specs_to_sequential(specs)
    exclude = {int(r.get("row_index", -1)) for r in records}
    planes = free_placed_mirror_world_planes(specs, exclude_row_indices=exclude)
    ray_down = bool(planes)
    for _idx, _center, normal in planes:
        refl = np.asarray([1.0, 0.0, 0.0]) - 2 * float(np.dot([1.0, 0.0, 0.0], normal)) * np.asarray(normal)
        if float(refl[2]) >= -0.3:
            ray_down = False
    checks.append(Check(
        "the free-placed display-ray fold reflects the +X beam DOWN off the carried mirror plane",
        ray_down,
        f"free_placed_planes={len(planes)} (expect 1); "
        + "; ".join(
            f"row{idx} n={_fmt(n)} +X->"
            f"{_fmt(np.asarray([1.0,0,0]) - 2*float(np.dot([1.0,0,0], n))*np.asarray(n))}"
            for idx, _c, n in planes
        ),
    ))

    # CAUSAL contrast: strip the carried Mirror face and re-seat -> the detector flips back
    # UP (+Z), proving the carried Mirror face is exactly what makes the fold go DOWN (the
    # user's original no-Mirror bug).
    _strip_mirror_faces(editor.rows[ri])
    img_z_up = _image_center_z(editor.rows)
    flips_up = img_z_up is not None and img_z_up > _MIRROR2_Z + 1.0
    checks.append(Check(
        "CAUSAL: with the Mirror face stripped the detector seats UP (+Z) again (reproduces the flagged bug)",
        flips_up,
        f"stripped image_center_z={None if img_z_up is None else round(img_z_up, 3)} "
        f"(expect > {_MIRROR2_Z + 1.0}, i.e. the wrong side the carry-over fixes)",
    ))

    # ===================== (B) SCOPING of the carry-over helper ===================== #
    # positive control: same part, donor Mirror, target Transmit, matching id + area.
    res, calls = _carry(
        [_Row(_adv(_PART_A, [_face("S001/F002", "Mirror", 884.0)])),
         _Row(_adv(_PART_A, [_face("S001/F002", "Transmit", 884.0), _face("S001/F001", "Transmit", 500.0)]))],
        1,
    )
    checks.append(Check(
        "same-part re-import with a donor Mirror face carries that exact face id (one assign call)",
        res == "S001/F002" and calls == [(1, "S001/F002", "Full Reflecting")],
        f"assigned={res!r} calls={calls}",
    ))

    # different part -> inert (a coincidental id match across parts must not mis-assign).
    res, calls = _carry(
        [_Row(_adv(_PART_A, [_face("S001/F002", "Mirror", 884.0)])),
         _Row(_adv(_PART_B, [_face("S001/F002", "Transmit", 884.0)]))],
        1,
    )
    checks.append(Check(
        "a DIFFERENT part with a colliding face id is left inert (no auto-Mirror)",
        res is None and calls == [],
        f"assigned={res!r} calls={calls} (expect None / no assign)",
    ))

    # same part but donor is a lens (no Mirror face) -> a re-imported lens is never mirrored.
    res, calls = _carry(
        [_Row(_adv(_PART_A, [_face("S001/F002", "Transmit", 884.0)])),
         _Row(_adv(_PART_A, [_face("S001/F002", "Transmit", 884.0)]))],
        1,
    )
    checks.append(Check(
        "re-importing a same-part NON-mirror (lens/prism) is left inert -- never turned into a reflector",
        res is None and calls == [],
        f"assigned={res!r} calls={calls} (expect None / no assign)",
    ))

    # target already carries its own Mirror face -> idempotent, keep the user's authoring.
    res, calls = _carry(
        [_Row(_adv(_PART_A, [_face("S001/F002", "Mirror", 884.0)])),
         _Row(_adv(_PART_A, [_face("S001/F002", "Mirror", 884.0)]))],
        1,
    )
    checks.append(Check(
        "a target that already has a Mirror face is left untouched (idempotent, no re-assign)",
        res is None and calls == [],
        f"assigned={res!r} calls={calls} (expect None / no assign)",
    ))

    # same id, same part, but the area disagrees -> the cross-check rejects the carry.
    res, calls = _carry(
        [_Row(_adv(_PART_A, [_face("S001/F002", "Mirror", 884.0)])),
         _Row(_adv(_PART_A, [_face("S001/F002", "Transmit", 100.0)]))],
        1,
    )
    checks.append(Check(
        "a same-id face whose AREA disagrees with the donor is rejected (area cross-check)",
        res is None and calls == [],
        f"assigned={res!r} calls={calls} (expect None / no assign)",
    ))

    # ===================== (C) WIRED (guard not vestigial) ========================= #
    try:
        promo_src = _PROMOTION_SRC.read_text(encoding="utf-8")
    except Exception:
        promo_src = ""
    wired = (
        "def _carry_over_same_part_mirror_face" in promo_src
        and "self._carry_over_same_part_mirror_face(" in promo_src
    )
    checks.append(Check(
        "the carry-over is DEFINED and CALLED inside the promote path (not vestigial)",
        wired,
        f"defined={'def _carry_over_same_part_mirror_face' in promo_src}, "
        f"called={'self._carry_over_same_part_mirror_face(' in promo_src}",
    ))

    return checks


def run_checks() -> tuple[bool, list[str]]:
    """Penta-phase entry point: ``(passed, notes)`` where notes are the failures."""
    checks = validate_second_mirror_same_part_mirror_carryover()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_second_mirror_same_part_mirror_carryover()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Second-mirror same-part Mirror carry-over validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
