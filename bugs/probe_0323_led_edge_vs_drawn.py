"""Characterise the LED hover-pick edge phantom (bugs/0323).

The user reports Alt-edge highlights "that do not match the drawn outline of the
part". The edge snap in step_feature_pick_for_display_xy snaps to
``face_outline_from_face_indices`` (a picked analytic-face-group boundary). This
probe MEASURES, on the real ILS0202 LED, whether those face-group boundary
segments actually coincide with the DRAWN feature edges (what the user sees):
``pose_invariant_feature_edges``. A high non-coincident fraction would confirm
the outline is the phantom source; ~0 would point at screen-space/occlusion
instead (and mean the #549 Alt gate is the real remedy for plain-hover phantoms).

Pure geometry once the display mesh is built; run under Xvfb because building the
editor needs a Tk root.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_face_index_edges import (
    face_outline_from_face_indices,
    line_segment_pairs,
    pose_invariant_feature_edges,
    triangle_array_and_face_index,
)

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def _segments(polydata) -> np.ndarray:
    """(M,2,3) world endpoints for every line segment of a line polydata."""
    if polydata is None:
        return np.empty((0, 2, 3), dtype=float)
    try:
        pts = np.asarray(polydata.points, dtype=float).reshape((-1, 3))
    except Exception:
        return np.empty((0, 2, 3), dtype=float)
    pairs = line_segment_pairs(polydata)
    if not pairs or pts.shape[0] == 0:
        return np.empty((0, 2, 3), dtype=float)
    out = []
    for i0, i1 in pairs:
        if 0 <= i0 < pts.shape[0] and 0 <= i1 < pts.shape[0]:
            out.append([pts[i0], pts[i1]])
    return np.asarray(out, dtype=float) if out else np.empty((0, 2, 3), dtype=float)


def _midpoint_keys(segs: np.ndarray, decimals: int = 4) -> set:
    if segs.shape[0] == 0:
        return set()
    mids = segs.mean(axis=1)
    return {tuple(np.round(m, decimals)) for m in mids}


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        app.open_3d_view()
        insp = app._three_d_inspector
        insp.update_idletasks()
        insp.refresh_from_editor()

        mesh = app._transformed_imported_step_mesh_for_label("led")
        if mesh is None:
            print("FAIL: no LED display mesh")
            return 0
        _tris, face_index = triangle_array_and_face_index(mesh)
        face_ids = sorted({int(v) for v in np.asarray(face_index).reshape(-1) if int(v) >= 0})
        print(f"LED display mesh: {int(getattr(mesh, 'n_cells', 0))} cells, "
              f"{len(face_ids)} analytic face indices")

        drawn = pose_invariant_feature_edges(mesh)
        drawn_segs = _segments(drawn)
        drawn_keys = _midpoint_keys(drawn_segs)
        print(f"drawn feature edges: {drawn_segs.shape[0]} segments")

        total_outline = 0
        total_phantom = 0
        sampled = 0
        worst = []
        for fid in face_ids:
            outline = face_outline_from_face_indices(mesh, (fid,))
            segs = _segments(outline)
            if segs.shape[0] == 0:
                continue
            sampled += 1
            keys = _midpoint_keys(segs)
            phantom = sum(1 for k in keys if k not in drawn_keys)
            total_outline += len(keys)
            total_phantom += phantom
            if phantom:
                worst.append((phantom, len(keys), fid))
        frac = (total_phantom / total_outline) if total_outline else 0.0
        print(f"\nsampled {sampled} face groups; outline segments={total_outline}, "
              f"NOT-on-a-drawn-edge={total_phantom} ({frac:.1%})")
        worst.sort(reverse=True)
        for phantom, n, fid in worst[:8]:
            print(f"  face {fid}: {phantom}/{n} outline segs are phantom")

        # Occlusion-phantom check: a single analytic face group whose outline
        # spans a large 3D extent (a wrap-around bore/cylinder) can have a
        # far-side boundary segment that projects near the cursor -- 2D-nearest
        # would then snap to an edge the user cannot see (behind the body). Report
        # how many groups have a wide outline diameter.
        wide = 0
        widest = []
        for fid in face_ids:
            segs = _segments(face_outline_from_face_indices(mesh, (fid,)))
            if segs.shape[0] < 2:
                continue
            mids = segs.mean(axis=1)
            diam = float(np.linalg.norm(mids.max(axis=0) - mids.min(axis=0)))
            if diam > 15.0:
                wide += 1
                widest.append((diam, segs.shape[0], fid))
        widest.sort(reverse=True)
        print(f"\nface groups with outline diameter > 15 mm (wrap-around, "
              f"occlusion-phantom risk): {wide}")
        for diam, n, fid in widest[:6]:
            print(f"  face {fid}: outline diameter {diam:.1f} mm across {n} segs")
        print(f"\nRESULT: phantom outline fraction = {frac:.1%} "
              f"({'OUTLINE IS THE PHANTOM' if frac > 0.05 else 'outline matches drawn edges'})")
    except Exception:
        traceback.print_exc()
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
