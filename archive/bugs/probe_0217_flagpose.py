"""probe_0217 FLAG POSE: reproduce the ACTUAL flag_20260703_145514_224 geometry (mirror-2 at
world x=199.52, detector row 9 at z=-23.90, camera front face z=-32.4) and measure where the
light really focuses vs the drawn detector vs the ray hard-stop.

The shared `_build_two_mirror` harness promotes mirror-2 at an EARLIER flag's pose (x=182.67);
this probe patches the promotion offset so mirror-2 lands at the 0217 flag pose, then measures.

Run: .devenv/state/venv/bin/python bugs/probe_0217_flagpose.py [offx] [offy]
"""
from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

import KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover as carry


def _paths(bundle):
    out = []
    for p in getattr(bundle, "ray_paths", None) or []:
        pw = np.asarray(getattr(p, "points_world", None), dtype=float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and pw.shape[1] >= 3:
            out.append(pw[:, :3])
    return out


def _onaxis(paths):
    return [pw for pw in paths if float(np.linalg.norm(pw[0][:3])) <= 1.0]


def _outgoing(pw):
    idx = int(np.argmax(pw[:, 0]))
    if float(pw[idx, 0]) < 150.0 or idx >= len(pw) - 1:
        return None
    return pw[idx:]


def _cross_z(seg, zc):
    z = seg[:, 2]
    for i in range(len(z) - 1):
        z0, z1 = z[i], z[i + 1]
        if (z0 - zc) * (z1 - zc) <= 0 and abs(z1 - z0) > 1e-9:
            t = (zc - z0) / (z1 - z0)
            return seg[i, :2] + t * (seg[i + 1, :2] - seg[i, :2])
    return None


def _waist(segs, z_hi=71.0, z_lo=-160.0, n=3000):
    best = (1e18, None, 0, None)
    for zc in np.linspace(z_hi, z_lo, n):
        xy = [c for s in segs if (c := _cross_z(s, zc)) is not None]
        if len(xy) >= 4:
            a = np.asarray(xy)
            c = a.mean(0)
            rms = float(np.sqrt(((a - c) ** 2).sum(1).mean()))
            if rms < best[0]:
                best = (rms, float(zc), len(xy), c)
    return best


def main() -> int:
    offx = float(sys.argv[1]) if len(sys.argv) > 1 else 205.79
    offy = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    carry._OFFSET = (offx, offy, 64.3484)  # patch mirror-2 promotion offset toward flag pose

    from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor, _trace

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        carry._promote_mirror2(editor)
        _trace(editor)
        system, _rays, folded = editor._build_preview_system_rays_bundle(update_state=True)

    # mirror-2 center from the promoted row
    r8 = editor.rows[8]
    from KrakenOS.UI.services.folded_sequential_fold import promoted_mirror_world_center
    specs = editor._serializable_specs_for_rows(list(editor.rows))
    c2 = promoted_mirror_world_center(specs, 8)
    print(f"mirror-2 world center: ({c2[0]:.2f},{c2[1]:.2f},{c2[2]:.2f})   (flag target x=199.52)")

    # detector ref
    ref = np.asarray(
        editor._surface_reference_world_point(len(editor.rows) - 1, system=system), float
    ).reshape(3)
    print(f"drawn detector (row 9): ({ref[0]:.2f},{ref[1]:.2f},{ref[2]:.2f})   (flag target z=-23.90)")

    # folded focus + ray-stop
    oa = _onaxis(_paths(folded))
    segs = [s for pw in oa if (s := _outgoing(pw)) is not None]
    ends = np.asarray([pw[-1] for pw in oa])
    rms, zf, k, ctr = _waist(segs)
    print(f"folded WAIST (true focus): z={zf:.2f}  rms={rms*1000:.1f}um  ctr=({ctr[0]:.2f},{ctr[1]:.2f})  (n={k})")
    print(f"folded ray HARD-STOP: z={ends[:,2].mean():.2f}  (x={ends[:,0].mean():.2f})")
    print("\n--- relationships ---")
    print(f"  detector z            = {ref[2]:.2f}")
    print(f"  true focus z          = {zf:.2f}   (focus - detector = {zf-ref[2]:+.2f})")
    print(f"  ray hard-stop z       = {ends[:,2].mean():.2f}   (hardstop - detector = {ends[:,2].mean()-ref[2]:+.2f})")
    print(f"  hardstop - focus      = {ends[:,2].mean()-zf:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
