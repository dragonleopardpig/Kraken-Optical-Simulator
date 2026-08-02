"""Ground truth for the AZ85 RA-mirror scene: what does the REAL trace say?

The FOV readout (_current_finite_paraxial_magnification, whole-system first order) says |m|=1.0
as loaded; the folded FOV solver (lens-only first order) says |m|=1.26. One of them is wrong.
Trace the real folded scene and measure |m| + the focus directly.

Run: .devenv/state/venv/bin/python -m bugs.diag_az85_true_trace
"""
from __future__ import annotations

import numpy as np

from bugs.diag_az85_ra_fov_solve import _quiet, load_scene, qe_of


def _clean(pts: np.ndarray) -> np.ndarray:
    """Drop consecutive duplicate points (the trace pads the tail with repeats)."""
    keep = [0]
    for i in range(1, len(pts)):
        if np.linalg.norm(pts[i] - pts[keep[-1]]) > 1e-7:
            keep.append(i)
    return pts[keep]


def fields(editor):
    _s, _r, b = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    det = next((t for t in b.targets if getattr(t, "is_detector", False)), None)
    groups: dict[tuple, list] = {}
    for p in b.ray_paths:
        pts = _clean(np.asarray(p.points_world, dtype=float)[:, :3])
        if len(pts) < 2:
            continue
        groups.setdefault(tuple(np.round(pts[0], 3)), []).append(pts)
    return groups, det


def focus_of(paths):
    """Least-squares crossing point of the final (approach) legs = the real focus of this field."""
    A, bb = np.zeros((3, 3)), np.zeros(3)
    n = 0
    for pts in paths:
        d = pts[-1] - pts[-2]
        L = np.linalg.norm(d)
        if L < 1e-6:
            continue
        d = d / L
        P = np.eye(3) - np.outer(d, d)
        A += P
        bb += P @ pts[-2]
        n += 1
    if n < 2:
        return None
    return np.linalg.lstsq(A, bb, rcond=None)[0]


def report(editor, tag):
    print(f"\n{'='*100}\n### {tag}\n{'='*100}")
    groups, det = fields(editor)
    c = np.asarray(det.center_world, dtype=float).reshape(3)
    n = np.asarray(getattr(det, "normal_world", (0, 0, 1)), dtype=float).reshape(3)
    n = n / (np.linalg.norm(n) or 1.0)
    print(f"  detector centre={np.round(c,3)} normal={np.round(n,3)}  |  {len(groups)} fields")
    out = {}
    for key, paths in sorted(groups.items()):
        start = np.asarray(key, dtype=float)
        ends = np.asarray([p[-1] for p in paths])
        centroid = ends.mean(axis=0)
        spot = float(np.sqrt(np.mean(np.sum((ends - centroid) ** 2, axis=1))))
        f = focus_of(paths)
        out[key] = (start, f, centroid, spot)
        along = float(np.dot(f - centroid, n)) if f is not None else float("nan")
        print(
            f"    obj={np.round(start,2)} -> landing centroid={np.round(centroid,2)}  "
            f"spot RMS={spot:8.4f} mm   focus vs landing (along n)={along:+8.3f} mm"
        )
    return out, c, n


def mag_from(out):
    items = list(out.values())
    axial = min(items, key=lambda v: np.linalg.norm(v[0][:2]))
    off = [v for v in items if np.linalg.norm(v[0][:2] - axial[0][:2]) > 1e-6]
    if not off:
        return None
    best = max(off, key=lambda v: np.linalg.norm(v[0][:2] - axial[0][:2]))
    h_obj = float(np.linalg.norm(best[0][:2] - axial[0][:2]))
    h_land = float(np.linalg.norm(best[2] - axial[2]))
    h_foc = float(np.linalg.norm(best[1] - axial[1])) if best[1] is not None else float("nan")
    print(f"\n  TRACED |m| at the sensor (landing) = {h_land / h_obj:.5f}  (h_obj={h_obj:.3f} -> {h_land:.3f})")
    print(f"  TRACED |m| at the real focus       = {h_foc / h_obj:.5f}")
    return h_land / h_obj


def main() -> int:
    editor = load_scene()
    qe = qe_of(editor)
    ot = _quiet(editor._paraxial_total_object_gap)[0]
    f, ppa = 85.0, 10.5115  # lens-only first order (from the folded helper at 1X)
    print(f"READOUT |m|   = {_quiet(editor._current_finite_paraxial_magnification)}   "
          f"(FOV {_quiet(qe.object_fov_dimensions)})")
    print(f"LENS-ONLY |m| = {f/((ot + ppa) - f):.5f}  for object total {ot:.3f}")
    out, c, n = report(editor, "AS LOADED (flag 1)")
    mag_from(out)

    print("\n\n>>> replay the recorded solve: 54x54 + object near=50 + image far=30")
    sensor_wh = _quiet(qe.sensor_active_dimensions)
    _quiet(qe.fov_solve, "object", "thickness", 54.0, 54.0, tuple(sensor_wh))
    _quiet(editor._apply_folded_object_split, "near", 50.0)
    _quiet(editor._apply_folded_image_split, "far", 30.0)
    print(f"READOUT |m|   = {_quiet(editor._current_finite_paraxial_magnification)}   "
          f"(FOV {_quiet(qe.object_fov_dimensions)})")
    ot = _quiet(editor._paraxial_total_object_gap)[0]
    print(f"LENS-ONLY |m| = {f/((ot + ppa) - f):.5f}  for object total {ot:.3f}  "
          f"(requested 23.04/54 = {23.04/54:.5f})")
    out2, c2, n2 = report(editor, "AFTER THE SOLVE (flag 3)")
    mag_from(out2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
