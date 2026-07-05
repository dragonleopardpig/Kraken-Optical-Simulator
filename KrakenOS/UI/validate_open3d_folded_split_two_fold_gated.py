"""Display-free guard for bugs/0234 -- the object-distance fold split is gated OFF on a two-fold
periscope, because the trailing (2nd) fold mirror cannot follow the object-mirror slide.

flag_20260706_070942_311 ("... click split button ... first RA mirror seems shifted, but 2nd RA
mirror wrong location. The rays even bend without touching the 2nd RA mirror."): the object-side
split (``_apply_folded_object_split``) slides the object mirror by trading the object gap against
the trailing air spacer. On a SINGLE fold every downstream element is a plain row that re-derives
from the folded-axis walk, so the slide is a clean mechanical repackaging. On a TWO-fold periscope
the trailing mirror is pinned to an absolute incoming-axis placement (bugs/0218) and does NOT
follow the object-gap walk: the slide moves mirror 1, the lenses, the rays and the detector, but
the drawn 2nd mirror stays FROZEN -- the beam then folds in empty space beside it.

Fix (bugs/0234): ``_folded_object_conjugate_split`` returns None when a fold mirror exists
downstream of the object mirror, so the split section is not offered (and the dialog explains the
absence). Single-fold scenes are unchanged.

  (A) TWO-FOLD GATED: on the promoted two-mirror AZ85 the split is None and Apply refuses.
  (B) ROOT CAUSE: forcing the object-mirror slide by hand (the operation the gate now forbids)
      moves mirror 1 (~+20 mm) and the beam's 2nd-fold vertex, but the trailing mirror stays put
      -- so the drawn 2nd mirror leaves the beam (the flagged desync).
  (C) SINGLE-FOLD UNAFFECTED: the one-mirror AZ85 split still reports its legs, applies, and keeps
      the total conjugate fixed.
  (D) WIRED: the bugs/0234 gate is in the split source and the two-fold note is in the dialog.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_split_two_fold_gated
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
from dataclasses import dataclass

import numpy as np

import KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover as carryover
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _placement_center(bundle, row_index):
    for p in getattr(bundle, "placements", []) or []:
        if int(getattr(p, "row_index", -1)) == int(row_index):
            c = getattr(p, "center_world", None)
            if c is not None:
                return np.asarray(c, dtype=float).reshape(3)
    return None


def _beam_second_fold_vertex(bundle):
    """Median second-turn vertex across the traced rays (the 2nd periscope fold)."""
    verts = []
    for r in getattr(bundle, "ray_paths", []) or []:
        pw = np.asarray(getattr(r, "points_world", []), dtype=float)
        if pw.ndim != 2 or pw.shape[0] < 4:
            continue
        turns = []
        for i in range(1, pw.shape[0] - 1):
            d0, d1 = pw[i] - pw[i - 1], pw[i + 1] - pw[i]
            n0, n1 = np.linalg.norm(d0), np.linalg.norm(d1)
            if n0 < 1e-6 or n1 < 1e-6:
                continue
            if float(np.dot(d0 / n0, d1 / n1)) < 0.9:
                turns.append(pw[i])
        if len(turns) >= 2:
            verts.append(turns[1])
    return None if not verts else np.median(np.asarray(verts), axis=0)


def _object_slide_gap_rows(editor, mirror_row):
    """Replicate the split's near/far gap rows (object gap vs the InPathTrailingSpacer) so the
    guard can force the slide the gate now forbids."""
    total, first_lens = _quiet(editor._paraxial_total_object_gap)
    spacer = None
    for j in range(int(mirror_row) + 1, int(first_lens)):
        adv = getattr(editor.rows[j], "advanced", None)
        if isinstance(adv, dict) and adv.get("InPathTrailingSpacer"):
            spacer = j
            break
    if spacer is None:
        spacer = min(int(mirror_row) + 1, int(first_lens) - 1)
    return 0, int(spacer)


def validate_folded_split_two_fold_gated() -> list[Check]:
    checks: list[Check] = []

    # ---- two-fold periscope: promote the trailing mirror -------------------------------------- #
    editor = _quiet(_build_editor, _AZ85)
    _quiet(carryover._promote_mirror2, editor)
    folds = [int(i) for i in editor._promoted_mirror_fold_row_indices()]

    # ---- (A) the split is gated off on a two-fold scene -------------------------------------- #
    split = _quiet(editor._folded_object_conjugate_split)
    ok_apply, msg_apply = _quiet(editor._apply_folded_object_split, "near", 80.0)
    checks.append(Check(
        "TWO-FOLD GATED: on a two-fold periscope the object split is not offered and Apply refuses",
        len(folds) >= 2 and split is None and (not ok_apply),
        f"folds={folds} split={split} apply_refused={not ok_apply} msg={msg_apply[:50]!r}",
    ))

    # ---- (B) root cause: forcing the slide leaves the trailing mirror behind ------------------ #
    _s, _r, b0 = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    m1_before = _placement_center(b0, folds[0])
    m2_before = _placement_center(b0, folds[-1])
    v_before = _beam_second_fold_vertex(b0)
    ng, fg = _object_slide_gap_rows(editor, folds[0])
    editor.rows[ng].thickness = float(editor.rows[ng].thickness) + 20.0   # the forbidden slide,
    editor.rows[fg].thickness = float(editor.rows[fg].thickness) - 20.0   # balanced (total fixed)
    _s, _r, b1 = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    m1_after = _placement_center(b1, folds[0])
    m2_after = _placement_center(b1, folds[-1])
    v_after = _beam_second_fold_vertex(b1)
    have = all(x is not None for x in (m1_before, m1_after, m2_before, m2_after, v_before, v_after))
    m1_moved = float(np.linalg.norm(m1_after - m1_before)) if have else 0.0
    m2_moved = float(np.linalg.norm(m2_after - m2_before)) if have else 9e9
    vertex_moved = float(np.linalg.norm(v_after - v_before)) if have else 0.0
    mirror2_off_beam = float(np.linalg.norm(v_after - m2_after)) if have else 0.0
    checks.append(Check(
        "ROOT CAUSE: the slide moves mirror 1 + the beam fold but the trailing mirror stays frozen",
        have and m1_moved > 15.0 and m2_moved < 1.0 and vertex_moved > 15.0,
        f"mirror1_moved={round(m1_moved, 2)} trailing_mirror_moved={round(m2_moved, 3)} "
        f"beam_vertex_moved={round(vertex_moved, 2)} beam_vs_frozen_mirror={round(mirror2_off_beam, 1)}",
    ))

    # ---- (C) single-fold scene is unaffected: the split still works -------------------------- #
    solo = _quiet(_build_editor, _AZ85)
    total0, _ = _quiet(solo._paraxial_total_object_gap)
    split_solo = _quiet(solo._folded_object_conjugate_split)
    ok_solo, _m = _quiet(solo._apply_folded_object_split, "near", float(split_solo["near"]) - 12.0) if split_solo else (False, "")
    total1, _ = _quiet(solo._paraxial_total_object_gap)
    checks.append(Check(
        "SINGLE-FOLD UNAFFECTED: the one-mirror AZ85 split still applies and keeps the total conjugate",
        (len(solo._promoted_mirror_fold_row_indices()) == 1)
        and split_solo is not None and ok_solo and abs(total1 - total0) < 1e-4,
        f"folds={solo._promoted_mirror_fold_row_indices()} split_ok={split_solo is not None} "
        f"applied={ok_solo} total {round(total0, 2)}->{round(total1, 2)}",
    ))

    # ---- (D) wiring ------------------------------------------------------------------------- #
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    split_src = inspect.getsource(type(editor)._folded_object_conjugate_split)
    dialog_src = inspect.getsource(Kraken3DInspector._add_folded_conjugate_split_section)
    wired = (
        "bugs/0234" in split_src
        and "any(int(f) > int(mirror_row) for f in folds)" in split_src
        and "two-fold periscope" in dialog_src
    )
    checks.append(Check(
        "WIRED: the bugs/0234 gate is in the split source and the two-fold note is in the dialog",
        wired,
        f"gate={'any(int(f) > int(mirror_row) for f in folds)' in split_src} note={'two-fold periscope' in dialog_src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_split_two_fold_gated()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_split_two_fold_gated()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded-split-two-fold-gated validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
