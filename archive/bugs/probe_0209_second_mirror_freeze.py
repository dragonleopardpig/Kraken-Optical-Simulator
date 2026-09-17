"""Diagnose flag_20260702_210526: importing a 2nd RA mirror (promoted at row 2 at a floating
pose) makes the scene DISAPPEAR the overlay, spray the rays, and FREEZE the UI (39s press->release
in the recording). Fast, TRACE-FREE diagnosis: why does the scene drop off the folded-sequential
path onto the non-seq mesh trace? Check fold detection + per-mirror tilt solve + resolved trace
mode with the 2nd mirror at the flag's pose."""
from __future__ import annotations

import contextlib
import io
from dataclasses import asdict

import numpy as np

from KrakenOS.UI.layout_editor import SurfaceRow
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
from KrakenOS.UI.services.folded_sequential_fold import (
    fold_promoted_mirror_specs_to_sequential,
    _is_promoted_mirror_fold,
    _solve_mirror_tilt,
    mirror_fold_face_normal,
)

# 2nd promoted mirror from flag_20260702_210526 promoted_solid_rows[1]
FLAG_DESP = (55.857, 126.376, 66.1585)
FLAG_THICK = 78.6585
FLAG_DIAM = 35.3553


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        rows = list(editor.rows)
        m2 = SurfaceRow(**asdict(rows[1]))
        m2.name = "Promoted OPTICAL STEP optical solid (imported 2nd)"
        m2.desp_x, m2.desp_y, m2.desp_z = FLAG_DESP
        m2.thickness = FLAG_THICK
        m2.diameter = FLAG_DIAM
        # insert at row 2 (right after the 1st mirror), as the flag shows
        editor.rows = rows[:2] + [m2] + rows[2:]
        editor._normalize_special_rows()
        specs = editor._serializable_specs_for_rows(list(editor.rows))

    print(f"rows: {len(editor.rows)}  (2nd mirror inserted at row 2, floating desp={FLAG_DESP})")
    # fold detection
    has_fold = bool(editor._scene_has_promoted_mirror_fold())
    _out, recs = fold_promoted_mirror_specs_to_sequential(specs)
    print(f"_scene_has_promoted_mirror_fold(): {has_fold}")
    print(f"fold records: {len(recs)}  (a clean 2-fold scene -> 2)")
    # per-mirror: is it a promoted mirror fold, does the tilt solve?
    out_accum: list[dict] = []
    for i, s in enumerate(specs):
        if not _is_promoted_mirror_fold(s):
            out_accum.append(s)
            continue
        fn = mirror_fold_face_normal(s.get("advanced"))
        tilt = _solve_mirror_tilt(out_accum, s, fn) if fn is not None else None
        print(f"  row {i}: promoted_mirror_fold=True face_normal={None if fn is None else np.round(fn,3).tolist()} "
              f"tilt_solved={'OK '+str({k:round(v,2) for k,v in tilt.items()}) if tilt else 'FAILED (row kept as-is -> non-seq)'}")
        # mimic the accumulation the real fold does
        out_accum.append(s)
    # resolved trace intent
    try:
        editor._build_preview_system_rays_bundle.__wrapped__  # noqa
    except Exception:
        pass
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            ftr = editor._folded_sequential_trace_rows(list(editor.rows))
        print(f"_folded_sequential_trace_rows -> {'None (NOT foldable -> non-seq mesh trace = FREEZE)' if ftr is None else str(len(ftr))+' rows'}")
    except Exception as exc:
        print("folded_sequential_trace_rows raised:", repr(exc))


if __name__ == "__main__":
    main()
