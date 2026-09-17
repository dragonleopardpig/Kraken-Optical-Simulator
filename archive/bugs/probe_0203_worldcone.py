"""Bug #2: the folded AZ85 preview traces sampling_mode='world_envelope' (_preview_scene_
sampling_mode returns it for every folded scene) which launches a FLAT meridional fan.
Forcing 'world_cone' (the revolved cone) should make the on-axis 3D bundle a real cone AND
keep it converged on the drawn detector (bug #5 intact)."""
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


def _measure(tag, editor, system, bundle, drawn_x):
    paths = [np.asarray(getattr(p, "points_world", None), float) for p in bundle.ray_paths]
    oa = [p for p in paths if p.ndim == 2 and p.shape[0] >= 2 and p.shape[1] >= 3
          and float(np.linalg.norm(p[0, :3])) <= 1.0 and float(p[:, 0].max()) > 250.0]
    if not oa:
        print(f"{tag}: no on-axis paths (of {len(paths)})")
        return
    zmax = min(p[:, 2].max() for p in oa)
    z = zmax * 0.4
    pts = np.asarray([q for q in (_at_z(p, z) for p in oa) if q is not None], float)
    s1, s2 = _s2(pts)
    ends = np.asarray([p[-1][:3] for p in oa], float)
    ex = float(ends[:, 0].mean())
    etrms = float(np.sqrt(((ends[:, 1:3] - ends[:, 1:3].mean(0)) ** 2).sum(1).mean()))
    print(f"{tag}: paths={len(paths)} onaxis={len(oa)}  incoming@Z={z:.1f} s1={s1:.3f} s2={s2:.4f}  "
          f"endX={ex:.3f} (dX{ex-drawn_x:+.3f}) endRMS={etrms*1000:.2f}um")


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        mode0 = editor._preview_scene_sampling_mode()
        system, _r, b_env = editor._build_preview_system_rays_bundle(update_state=True)
        drawn_x = float(np.asarray(
            editor._surface_reference_world_point(len(editor.rows) - 1, system=system), float).reshape(3)[0])

        # Force world_cone on the SHARED scene mode + the 3D mode, rebuild.
        editor._preview_scene_sampling_mode = lambda: "world_cone"
        editor._preview_3d_sampling_mode = lambda: "world_cone"
        editor._preview_scene_trace_dirty = True
        _s2sys, _r2, b_cone = editor._build_preview_system_rays_bundle(update_state=True)

    print(f"drawn sensor X={drawn_x:.3f}  default scene mode={mode0!r}")
    _measure("world_envelope (current)", editor, system, b_env, drawn_x)
    _measure("world_cone   (proposed)", editor, system, b_cone, drawn_x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
