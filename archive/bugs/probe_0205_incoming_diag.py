"""bugs/0205 diagnosis: WHERE does the incoming +Z leg lose its X-spread?

probe_0204_fan_vs_cone measured incoming (X,Y)@Z=35 s2=0 (flat) while outgoing (Y,Z) is a
disk. The display fold (_fold_ray_downstream_of_station) only rotates vertices at Z>=station,
so the incoming leg (Z<station) is IDENTICAL before/after the fold -> the flatness must be in
the TRACE, not the display. This probe checks that: it measures the incoming-leg X/Y/Z spread
on the RAW pre-fold bundle (bend monkeypatched to no-op) vs the FINAL folded bundle, and dumps
sample vertices so we can see the real geometry instead of theorising.

Run: .devenv/state/venv/bin/python -m bugs.probe_0205_incoming_diag
"""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
import KrakenOS.UI.services.three_d_scene_tools as tdt


def _kink_index(p):
    seg = np.diff(p[:, :3], axis=0); ln = np.linalg.norm(seg, axis=1); g = ln > 1e-9
    if int(g.sum()) < 2:
        return None
    u = np.zeros_like(seg); u[g] = seg[g] / ln[g, None]
    cos = np.sum(u[:-1] * u[1:], axis=1); ki = int(np.argmin(cos))
    if cos[ki] > 0.5:
        return None
    return ki + 1


def _onaxis(paths):
    return [p for p in paths if p.ndim == 2 and p.shape[0] >= 3 and p.shape[1] >= 3
            and float(np.linalg.norm(p[0, :3])) <= 1.0 and float(p[:, 0].max()) > 250.0]


def _onaxis_raw(paths):
    """RAW straight-equivalent rays go +Z (never fold to +X); filter by launch-at-origin + reaches past station."""
    return [p for p in paths if p.ndim == 2 and p.shape[0] >= 3 and p.shape[1] >= 3
            and float(np.linalg.norm(p[0, :3])) <= 1.0 and float(p[:, 2].max()) > 100.0]


def _incoming_pts_at_z(paths, z):
    """gather each on-axis ray's (X,Y,Z) where its pre-kink +Z leg crosses Z=z."""
    out = []
    for p in paths:
        ki = _kink_index(p); hi = ki if ki is not None else len(p) - 1
        za = p[:, 2]
        for i in range(hi):
            z0, z1 = za[i], za[i + 1]
            if (z0 - z) * (z1 - z) <= 0 and abs(z1 - z0) > 1e-9:
                t = (z - z0) / (z1 - z0)
                out.append(p[i, :3] + t * (p[i + 1, :3] - p[i, :3]))
                break
    return np.asarray(out, float)


def _xy_spread_at_z(paths, z):
    """(X,Y,Z) of each path where ANY segment crosses Z=z (raw straight-equiv has no kink)."""
    out = []
    for p in paths:
        za = p[:, 2]
        for i in range(len(p) - 1):
            z0, z1 = za[i], za[i + 1]
            if (z0 - z) * (z1 - z) <= 0 and abs(z1 - z0) > 1e-9:
                t = (z - z0) / (z1 - z0)
                out.append(p[i, :3] + t * (p[i + 1, :3] - p[i, :3]))
                break
    return np.asarray(out, float)


def _report(tag, paths, raw=False):
    print(f"\n=== {tag}: on-axis rays = {len(paths)} ===")
    if not paths:
        return
    kis = [_kink_index(p) for p in paths]
    kset = sorted({k for k in kis if k is not None})
    print(f"kink indices present: {kset}  (None: {sum(k is None for k in kis)})")
    for p in paths[:3]:
        ki = _kink_index(p)
        print(f"  path npts={len(p)} kink@{ki}  head={np.array2string(p[:min(4,len(p)),:3],precision=3)}")
    for z in (35.0, 60.0, 100.0, 150.0):
        pts = (_xy_spread_at_z if raw else _xy_spread_at_z)(paths, z)
        if len(pts) >= 2:
            print(f"  @Z={z:5.0f}: n={len(pts)}  X-spread={np.ptp(pts[:,0]):.4f}  "
                  f"Y-spread={np.ptp(pts[:,1]):.4f}")


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor.snap_detector_to_image_plane()
        editor._preview_scene_trace_dirty = True

        # RAW: monkeypatch the display bend to a no-op so we see the straight-equivalent trace.
        real_bend = tdt.ThreeDSceneToolsMixin._apply_folded_display_bend
        tdt.ThreeDSceneToolsMixin._apply_folded_display_bend = lambda self, b, ft: None
        try:
            _s, _r, raw_bundle = editor._build_preview_system_rays_bundle(update_state=True)
            raw = _onaxis_raw([np.asarray(p.points_world, float) for p in raw_bundle.ray_paths])
        finally:
            tdt.ThreeDSceneToolsMixin._apply_folded_display_bend = real_bend

        editor._preview_scene_trace_dirty = True
        _s, _r, fin_bundle = editor._build_preview_system_rays_bundle(update_state=True)
        fin = _onaxis([np.asarray(p.points_world, float) for p in fin_bundle.ray_paths])

    _report("RAW (straight-equivalent, no display fold)", raw, raw=True)
    _report("FINAL (folded display)", fin)
    return 0


if __name__ == "__main__":
    sys.exit(main())
