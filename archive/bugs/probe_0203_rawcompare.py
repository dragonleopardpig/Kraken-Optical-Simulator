"""Decisive: compare the RAW (pre-fold, unfolded straight-equivalent) on-axis trace for
world_envelope vs world_cone. Report the pupil-plane (X,Y) disk-ness at a mid station. If
envelope is a Y-only fan (X~0) and cone is a filled disk (X and Y equal), world_cone is the
real bug-#2 fix (the folded look-flat is just a slender double-cone + camera angle)."""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _raw_oa(editor, mode):
    editor._preview_scene_sampling_mode = lambda: mode
    editor._preview_3d_sampling_mode = lambda: mode
    wl = float(editor._current_wavelength())
    mr = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
    system = editor.build_system(require_solids=True)
    ftr = editor._folded_sequential_trace_rows(editor.rows)
    rays, ft = editor._trace_preview_rays_folded_aware(
        system, wl, mr, sampling_mode=mode, folded_trace_rows=ftr)
    bundle = editor._build_scene_bundle(system, rays, mr)
    raw = [np.asarray(getattr(p, "points_world", None), float)[:, :3] for p in bundle.ray_paths]
    return [p for p in raw if p.ndim == 2 and p.shape[0] >= 2 and float(np.linalg.norm(p[0, :3])) <= 1.0]


def _pupil_at_z(paths, z):
    rows = []
    for p in paths:
        za = p[:, 2]
        for i in range(len(za)-1):
            z0, z1 = za[i], za[i+1]
            if (z0-z)*(z1-z) <= 0 and abs(z1-z0) > 1e-9:
                t = (z-z0)/(z1-z0)
                rows.append(p[i, 0:2] + t*(p[i+1, 0:2]-p[i, 0:2]))
                break
    return np.asarray(rows, float) if rows else np.empty((0, 2))


def _report(tag, oa):
    pupil = _pupil_at_z(oa, 30.0)
    if pupil.shape[0] < 3:
        print(f"{tag}: only {pupil.shape[0]} rays cross Z=30"); return
    xr = pupil[:, 0].max()-pupil[:, 0].min()
    yr = pupil[:, 1].max()-pupil[:, 1].min()
    c = pupil - pupil.mean(0)
    s = np.linalg.svd(c, compute_uv=False)
    s2 = float(s[1]) if s.size >= 2 else 0.0
    print(f"{tag}: onaxis={len(oa)}  pupil@Z=30 Xrange={xr:.3f} Yrange={yr:.3f} s2={s2:.4f} "
          f"-> {'DISK/CONE' if s2 > 0.5 else 'Y-FAN (flat)'}")


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        oa_env = _raw_oa(editor, "world_envelope")
        oa_cone = _raw_oa(editor, "world_cone")
    _report("RAW world_envelope", oa_env)
    _report("RAW world_cone    ", oa_cone)
    return 0


if __name__ == "__main__":
    sys.exit(main())
