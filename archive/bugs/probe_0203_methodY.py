"""bugs/0203 Method Y: fold the straight-equivalent display rays by a SINGLE physical
reflection across the tilted '/' mirror-face plane (per-ray crossing, no per-ray tau).

Each straight ray crosses the 45 deg face plane at a different Z (like a real mirror), so
the kink lands ON the drawn face by construction; the reflection is one rigid isometry, so
the converging cone keeps its tight waist and the focus maps to the drawn detector.

Compares three folds on the AZ85 on-axis cone:
  (A) rotation fold ONLY               (_fold_straight_equivalent_display_rays)
  (B) rotation + rigid flip (CURRENT)  (_apply_folded_display_bend)
  (Y) single reflection across '/' face (this probe)
reporting waist (X, RMS, dist from sensor) AND kink residual vs the drawn face plane.
"""
from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

from KrakenOS.UI.services.folded_sequential_fold import (
    fold_promoted_mirror_specs_to_sequential,
    promoted_mirror_world_center,
    _unit,
)
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

from probe_0187_seq_mirror_focus import (  # type: ignore
    _onaxis_paths,
    _waist,
)


def _reflect_tail_across_plane(points, plane_point, plane_normal):
    """Reflect the past-mirror tail across the tilted face plane. The straight-equivalent
    ray has NO kink yet (it is straight until folded), so split at the plane CROSSING: keep
    the incoming leg, insert the exact crossing point (on the face), reflect every vertex
    past the plane. One rigid reflection -> kink on face + focus preserved."""
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 3 or pts.shape[1] < 3:
        return None
    n = _unit(plane_normal)
    p0 = np.asarray(plane_point, dtype=float).reshape(3)
    coords = pts[:, :3]
    s = (coords - p0) @ n
    sign0 = np.sign(s[0]) if abs(s[0]) > 1e-9 else 1.0
    crossed = np.where(np.sign(s) == -sign0)[0]
    if crossed.size == 0:
        return None
    k = int(crossed[0])
    if k == 0:
        return None
    out = pts.copy()
    tail = coords[k:]
    out[k:, :3] = tail - 2.0 * s[k:, None] * n[None, :]
    # splice the exact crossing point (on the face) so the kink lands ON the plane
    x0, x1 = coords[k - 1], coords[k]
    d0, d1 = float(s[k - 1]), float(s[k])
    if abs(d1 - d0) > 1e-12:
        t = d0 / (d0 - d1)
        cross = x0 + t * (x1 - x0)
        row = np.zeros((1, pts.shape[1]))
        row[0, :3] = cross
        if pts.shape[1] > 3:
            row[0, 3:] = out[k, 3:]
        out = np.vstack([out[:k], row, out[k:]])
    return out


def _kink_resid(points, plane_point, plane_normal):
    coords = np.asarray(points, float)[:, :3]
    seg = np.diff(coords, axis=0)
    ln = np.linalg.norm(seg, axis=1)
    g = ln > 1e-9
    if int(g.sum()) < 2:
        return None
    u = np.zeros_like(seg)
    u[g] = seg[g] / ln[g, None]
    cos = np.sum(u[:-1] * u[1:], axis=1)
    ki = int(np.argmin(cos))
    if cos[ki] > 0.2:
        return None
    return abs(float(np.dot(coords[ki + 1] - plane_point, plane_normal)))


def _trace_straight_bundle(editor):
    wl = float(editor._current_wavelength())
    mr = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
    system = editor.build_system(require_solids=True)
    ftr = editor._folded_sequential_trace_rows(editor.rows)
    rays, ft = editor._trace_preview_rays_folded_aware(
        system, wl, mr, sampling_mode=editor._preview_3d_sampling_mode(), folded_trace_rows=ftr
    )
    bundle = editor._build_scene_bundle(system, rays, mr)
    return system, bundle, ft


def _sensor_x(editor, system):
    n = len(editor.rows)
    return float(
        np.asarray(editor._surface_reference_world_point(n - 1, system=system), dtype=float).reshape(3)[0]
    )


def _report(tag, paths, plane_pt, plane_n, drawn_x, lines):
    wx, wrms = _waist(paths, 40.0, drawn_x + 30.0)
    res = [r for r in (_kink_resid(p, plane_pt, plane_n) for p in paths) if r is not None]
    res = np.array(res) if res else None
    lines.append(f"  [{tag}] rays={len(paths)}")
    if wx is not None:
        lines.append(
            f"      waist X={wx:.2f} (RMS {wrms*1000:.2f} um), {drawn_x - wx:+.3f} mm from sensor"
        )
    if res is not None and res.size:
        lines.append(f"      kink residual vs '/' face: max={res.max():.3f} mean={res.mean():.3f} mm")


def main() -> int:
    lines: list[str] = []
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()

        specs = editor._serializable_specs_for_rows(list(editor.rows))
        _f, recs = fold_promoted_mirror_specs_to_sequential(specs)
        row_index = int(recs[0]["row_index"])
        face_center = np.asarray(promoted_mirror_world_center(specs, row_index), float).reshape(3)
        face_normal = _unit(recs[0]["face_normal"])

        # (A) rotation fold only
        system, bundleA, ftA = _trace_straight_bundle(editor)
        drawn_x = _sensor_x(editor, system)
        editor._fold_straight_equivalent_display_rays(bundleA, ftA)
        pathsA = _onaxis_paths(bundleA)

        # (B) current: rotation + rigid flip
        _s, bundleB, ftB = _trace_straight_bundle(editor)
        editor._apply_folded_display_bend(bundleB, ftB)
        pathsB = _onaxis_paths(bundleB)

        # (Y) single reflection across '/' face on the STRAIGHT-equivalent rays
        _s, bundleY, ftY = _trace_straight_bundle(editor)
        for path in getattr(bundleY, "ray_paths", []) or []:
            folded = _reflect_tail_across_plane(
                getattr(path, "points_world", None), face_center, face_normal
            )
            if folded is not None:
                path.points_world = folded
        pathsY = _onaxis_paths(bundleY)

    lines.append("=== bugs/0203 Method Y: single reflection across '/' face ===")
    lines.append(f"  '/' face center={face_center}  normal={face_normal}  sensor X={drawn_x:.3f}")
    lines.append("(A) rotation fold ONLY:")
    _report("onaxis", pathsA, face_center, face_normal, drawn_x, lines)
    lines.append("(B) CURRENT rotation + rigid flip:")
    _report("onaxis", pathsB, face_center, face_normal, drawn_x, lines)
    lines.append("(Y) single '/' reflection:")
    _report("onaxis", pathsY, face_center, face_normal, drawn_x, lines)

    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
