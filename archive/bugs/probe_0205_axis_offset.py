"""Probe: does the 0205 reflection fold land the folded outgoing arm on the DRAWN
detector's Z, or is it offset (the flag_20260702_152020_279 'obvious offset from optical
axis')? Measure the on-axis outgoing-arm Z-center vs the drawn detector/axis Z=71.897, for
(a) the NEW 0205 reflection fold and (b) the OLD 0197 bend + 0203 rigid flip.
"""
from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _onaxis_out(paths):
    out = []
    for p in paths:
        if p.ndim == 2 and p.shape[0] >= 3 and p.shape[1] >= 3 and float(np.linalg.norm(p[0, :3])) <= 1.0:
            if float(p[:, 0].max()) > 250.0:
                out.append(p)
    return out


def _arm_z(paths, x=260.0):
    zs = []
    for p in paths:
        xa = p[:, 0]
        for i in range(len(p) - 1):
            if (xa[i] - x) * (xa[i + 1] - x) <= 0 and abs(xa[i + 1] - xa[i]) > 1e-9:
                t = (x - xa[i]) / (xa[i + 1] - xa[i])
                zs.append(float((p[i] + t * (p[i + 1] - p[i]))[2]))
                break
    return np.asarray(zs, dtype=float)


def main() -> int:
    ft_holder = [None]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)  # do NOT snap -- match the user's live scene

        real_bend = editor._apply_folded_display_bend
        def _cap(scene_bundle, fold_transform):
            ft_holder[0] = fold_transform
            return real_bend(scene_bundle, fold_transform)
        editor._apply_folded_display_bend = _cap

        # (a) NEW production reflection fold
        editor._preview_scene_trace_dirty = True
        _s, _r, new_b = editor._build_preview_system_rays_bundle(update_state=True)
        new = [np.asarray(p.points_world, float) for p in (new_b.ray_paths or [])]

        # (b) OLD 0197 bend + 0203 rigid flip, reusing the captured fold_transform
        ft = ft_holder[0]
        editor._reflect_straight_equivalent_display_rays = lambda b: (
            editor._fold_straight_equivalent_display_rays(b, ft),
            editor._apply_folded_mirror_rigid_reflection(b, ft),
            None,
        )[-1]
        editor._preview_scene_trace_dirty = True
        _s, _r, old_b = editor._build_preview_system_rays_bundle(update_state=True)
        old = [np.asarray(p.points_world, float) for p in (old_b.ray_paths or [])]

    new_oa = _onaxis_out(new)
    old_oa = _onaxis_out(old)
    new_z = _arm_z(new_oa)
    old_z = _arm_z(old_oa)
    print("drawn folded axis / detector Z-center = 71.897 (front datum station_z = 59.397, desp_z = 12.5)")
    print(f"fold_transform captured: {'yes' if ft is not None else 'NONE'}")
    print(f"NEW 0205 reflection: on-axis {len(new_oa)} rays, arm Z@X=260 = "
          f"{new_z.mean() if len(new_z) else float('nan'):.3f} +/- {new_z.std() if len(new_z) else 0:.3f} "
          f"(offset {new_z.mean()-71.897 if len(new_z) else float('nan'):+.3f})")
    print(f"OLD 0197 bend+flip:  on-axis {len(old_oa)} rays, arm Z@X=260 = "
          f"{old_z.mean() if len(old_z) else float('nan'):.3f} +/- {old_z.std() if len(old_z) else 0:.3f} "
          f"(offset {old_z.mean()-71.897 if len(old_z) else float('nan'):+.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
