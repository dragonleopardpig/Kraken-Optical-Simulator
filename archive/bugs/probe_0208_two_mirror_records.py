"""Explore a 2-promoted-mirror AZ85 variant: insert a second RA-mirror cube between the
last lens and the camera, then inspect what the (already-general) fold machinery produces
-- record count, per-mirror chief_in/face_normal/tilt -- and whether the display-ray
reflection path bails (len(records)!=1) to the sequential-Mirror fallback."""
from __future__ import annotations

import contextlib
import io

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
from KrakenOS.UI.services.folded_sequential_fold import (
    fold_promoted_mirror_specs_to_sequential,
    mirror_fold_face_normal,
)

SPEC_KEYS = None


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        specs = editor._serializable_specs_for_rows(list(editor.rows))

    print(f"AZ85 base: {len(specs)} rows")
    for i, s in enumerate(specs):
        fn = mirror_fold_face_normal(s.get("advanced"))
        tag = "  <-- MIRROR FOLD" if fn is not None else ""
        print(f"  row {i}: surface={s.get('surface'):>10} thick={float(s.get('thickness',0)):8.3f} "
              f"desp_z={float(s.get('desp_z',0)):6.2f} glass={s.get('glass')}{tag}")

    # mirror spec is row 1; duplicate it as a second fold on the +X leg
    mirror_spec = {k: (dict(v) if isinstance(v, dict) else v) for k, v in specs[1].items()}
    print(f"\nmirror row-1 face_normal = {mirror_fold_face_normal(specs[1].get('advanced'))}")

    # insert a copy just before the Image row (last), shortening the preceding gap so it
    # sits partway down the +X leg
    dup = {k: (dict(v) if isinstance(v, dict) else v) for k, v in mirror_spec.items()}
    dup["name"] = "Promoted OPTICAL STEP optical solid (2nd fold)"
    two = specs[:-1] + [dup] + [specs[-1]]
    # give the copy a modest thickness and pull some length out of the last lens gap
    print(f"\n=== 2-mirror spec list: {len(two)} rows (mirror at 1 and {len(two)-2}) ===")

    _out, records = fold_promoted_mirror_specs_to_sequential(two)
    print(f"\nfold records = {len(records)}")
    for r in records:
        print(f"  record row_index={r['row_index']} chief_in={np.round(r['chief_in'],4).tolist()} "
              f"face_normal={np.round(r['face_normal'],4).tolist()} tilt={ {k: round(v,3) for k,v in r['tilt'].items()} }")
    print(f"\ndisplay-ray reflection path: len(records)={len(records)} -> "
          f"{'REFLECTS (single-fold)' if len(records)==1 else 'BAILS -> sequential-Mirror fallback'}")

    # what do the sequential 'out' specs look like (the fallback trace rows)?
    print(f"\nsequential-equivalent 'out' rows = {len(_out)}:")
    for i, s in enumerate(_out):
        am = s.get("axis_move", s.get("AxisMove"))
        print(f"  {i}: surface={str(s.get('surface')):>10} thick={float(s.get('thickness',0)):8.3f} "
              f"tiltx={float(s.get('tilt_x',0)):7.2f} tilty={float(s.get('tilt_y',0)):7.2f} axis_move={am}")


if __name__ == "__main__":
    main()
