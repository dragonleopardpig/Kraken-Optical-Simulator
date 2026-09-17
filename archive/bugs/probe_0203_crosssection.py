"""Measure the CONE cross-section correctly: the fold rotates about Y, so the converging
bundle's cross-section perpendicular to the +X outgoing arm is the (Y,Z) plane. Collect each
on-axis ray's kink vertex (Y,Z) and its outgoing-arm midpoint (Y,Z); s2>0 => real cone,
s2~0 => flat fan. Compare world_envelope (current) vs world_cone (proposed)."""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _s2(a):
    a = np.asarray(a, float)
    if a.ndim != 2 or a.shape[0] < 3 or a.shape[1] != 2:
        return 0.0
    c = a - a.mean(0)
    s = np.linalg.svd(c, compute_uv=False)
    return float(s[1]) if s.size >= 2 else 0.0


def _kink_yz(p):
    seg = np.diff(p[:, :3], axis=0); ln = np.linalg.norm(seg, axis=1); g = ln > 1e-9
    if int(g.sum()) < 2:
        return None
    u = np.zeros_like(seg); u[g] = seg[g]/ln[g, None]
    cos = np.sum(u[:-1]*u[1:], axis=1); ki = int(np.argmin(cos))
    if cos[ki] > 0.5:
        return None
    return p[ki+1, 1:3]


def _outgoing_yz_at_x(p, x):
    xa = p[:, 0]
    for i in range(len(xa)-1):
        x0, x1 = xa[i], xa[i+1]
        if (x0-x)*(x1-x) <= 0 and abs(x1-x0) > 1e-9:
            t = (x-x0)/(x1-x0)
            return p[i, 1:3] + t*(p[i+1, 1:3]-p[i, 1:3])
    return None


def _run(editor, mode):
    if mode is not None:
        editor._preview_scene_sampling_mode = lambda: mode
        editor._preview_3d_sampling_mode = lambda: mode
    editor._preview_scene_trace_dirty = True
    system, _r, bundle = editor._build_preview_system_rays_bundle(update_state=True)
    paths = [np.asarray(getattr(p, "points_world", None), float) for p in bundle.ray_paths]
    oa = [p for p in paths if p.ndim == 2 and p.shape[0] >= 3 and p.shape[1] >= 3
          and float(np.linalg.norm(p[0, :3])) <= 1.0 and float(p[:, 0].max()) > 250.0]
    drawn_x = float(np.asarray(
        editor._surface_reference_world_point(len(editor.rows)-1, system=system), float).reshape(3)[0])
    return oa, drawn_x, len(paths)


def _report(tag, oa, drawn_x, npaths):
    kinks = np.asarray([q for q in (_kink_yz(p) for p in oa) if q is not None], float)
    mid = np.asarray([q for q in (_outgoing_yz_at_x(p, drawn_x*0.6) for p in oa) if q is not None], float)
    ends = np.asarray([p[-1, :3] for p in oa], float)
    etrms = float(np.sqrt(((ends[:, 1:3]-ends[:, 1:3].mean(0))**2).sum(1).mean())) if len(ends) else 0.0
    print(f"{tag}: paths={npaths} onaxis={len(oa)}")
    print(f"   kink (Y,Z) cross-section: n={len(kinks)} s2={_s2(kinks):.4f}")
    print(f"   outgoing (Y,Z)@X={drawn_x*0.6:.0f}: n={len(mid)} s2={_s2(mid):.4f}")
    print(f"   endpoint X mean={ends[:,0].mean():.3f} (drawn {drawn_x:.3f}) transverse RMS={etrms*1000:.2f}um")


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        oa_e, dx_e, n_e = _run(editor, None)   # default (world_envelope)
        oa_c, dx_c, n_c = _run(editor, "world_cone")
    _report("world_envelope (current)", oa_e, dx_e, n_e)
    _report("world_cone   (proposed)", oa_c, dx_c, n_c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
