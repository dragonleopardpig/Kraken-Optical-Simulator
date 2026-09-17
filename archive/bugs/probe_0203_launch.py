"""What does the WIRED AZ85 folded bundle's on-axis incoming leg actually look like:
disk or fan? And what sampling mode / launch decision produced it?"""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _s2(a):
    a = np.asarray(a, float)
    if a.ndim != 2 or a.shape[0] < 3 or a.shape[1] != 2:
        return (0.0, 0.0)
    c = a - a.mean(0)
    s = np.linalg.svd(c, compute_uv=False)
    return (float(s[0]), float(s[1]) if s.size >= 2 else 0.0)


def _at_z(p, z):
    za = p[:, 2]
    for i in range(len(za) - 1):
        z0, z1 = za[i], za[i + 1]
        if (z0 - z) * (z1 - z) <= 0 and abs(z1 - z0) > 1e-9:
            t = (z - z0) / (z1 - z0)
            return p[i, 0:2] + t * (p[i + 1, 0:2] - p[i, 0:2])
    return None


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        mode = editor._preview_3d_sampling_mode()
        rc = editor._current_ray_count()
        system, rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
        paths = [np.asarray(getattr(p, "points_world", None), float) for p in bundle.ray_paths]

    print(f"sampling_mode={mode!r}  ray_count={rc}  total paths={len(paths)}")
    # on-axis = launch near origin, reaches +X arm
    oa = [p for p in paths if p.ndim == 2 and p.shape[0] >= 2 and p.shape[1] >= 3
          and float(np.linalg.norm(p[0, :3])) <= 1.0 and float(p[:, 0].max()) > 250.0]
    print(f"on-axis paths (launch|.|<=1, maxX>250): {len(oa)}")
    # also try a looser on-axis: small |x0,y0| but allow larger launch (collimated disc)
    oa2 = [p for p in paths if p.ndim == 2 and p.shape[0] >= 2 and p.shape[1] >= 3
           and float(np.hypot(p[0, 1], p[0, 2])) <= 30.0 and float(p[:, 0].max()) > 250.0]
    if oa:
        zmax = min(p[:, 2].max() for p in oa)
        print(f"on-axis incoming Zmax(min over rays)={zmax:.2f}")
        for frac in (0.2, 0.4, 0.6, 0.8):
            z = zmax * frac
            pts = np.asarray([q for q in (_at_z(p, z) for p in oa) if q is not None], float)
            s1, s2 = _s2(pts)
            print(f"  Z={z:7.2f}: {pts.shape[0]:3d} rays  s1={s1:.4f} s2={s2:.4f}")
        # sample a few launch dirs
        print("first-3 on-axis launch pts & 2nd vertex:")
        for p in oa[:3]:
            print(f"    p0={p[0,:3]}  p1={p[1,:3]}")
    # global: do ALL paths' start points fill a disk? (collimated infinity launch)
    starts = np.asarray([p[0, 1:3] for p in paths if p.ndim == 2 and p.shape[1] >= 3], float)
    s1, s2 = _s2(starts)
    print(f"ALL launch (Y,Z) start spread: s1={s1:.3f} s2={s2:.3f}  n={starts.shape[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
