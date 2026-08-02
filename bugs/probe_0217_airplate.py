"""probe_0217 AIR-PLATE hypothesis: the straight-equivalent flattens each fold mirror to a
BK7 plate that REFRACTS the converging cone, shifting the focus by ~t(1-1/n)~12mm off the
geometrically-placed detector. A fold MIRROR reflects; it should not refract. Test: make the
flattened fold-mirror plates AIR and measure whether BOTH the single- and two-mirror folded
cones then converge ON their drawn detectors.

  * single-mirror MUST stay converged on its detector (it already does) -- a regression guard.
  * two-mirror focus should move from -33.84 onto the detector (-22.05) if this is the fix.

Run: .devenv/state/venv/bin/python bugs/probe_0217_airplate.py
"""
from __future__ import annotations

import contextlib
import io

import numpy as np

from KrakenOS.UI.validate_open3d_second_mirror_incoming_axis_placement import (
    _build_single_mirror,
    _build_two_mirror,
)


def _paths(b):
    out = []
    for p in getattr(b, "ray_paths", None) or []:
        pw = np.asarray(getattr(p, "points_world", None), dtype=float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and pw.shape[1] >= 3:
            out.append(pw[:, :3])
    return out


def _onaxis(paths):
    return [pw for pw in paths if float(np.linalg.norm(pw[0][:3])) <= 1.0]


def _cross_z(seg, zc):
    z = seg[:, 2]
    for i in range(len(z) - 1):
        z0, z1 = z[i], z[i + 1]
        if (z0 - zc) * (z1 - zc) <= 0 and abs(z1 - z0) > 1e-9:
            t = (zc - z0) / (z1 - z0)
            return seg[i, :2] + t * (seg[i + 1, :2] - seg[i, :2])
    return None


def _cross_x(seg, xc):
    x = seg[:, 0]
    for i in range(len(x) - 1):
        x0, x1 = x[i], x[i + 1]
        if (x0 - xc) * (x1 - xc) <= 0 and abs(x1 - x0) > 1e-9:
            t = (xc - x0) / (x1 - x0)
            p = seg[i] + t * (seg[i + 1] - seg[i])
            return np.array([p[1], p[2]])
    return None


def _waist(segs, coord, lo, hi, n=3000):
    fn = _cross_z if coord == "z" else _cross_x
    best = (1e18, None, 0)
    for c in np.linspace(hi, lo, n):
        xy = [v for s in segs if (v := fn(s, c)) is not None]
        if len(xy) >= 4:
            a = np.asarray(xy)
            rms = float(np.sqrt(((a - a.mean(0)) ** 2).sum(1).mean()))
            if rms < best[0]:
                best = (rms, float(c), len(xy))
    return best


def _measure(editor, name, coord):
    system, _r, folded = editor._build_preview_system_rays_bundle(update_state=True)
    ref = np.asarray(
        editor._surface_reference_world_point(len(editor.rows) - 1, system=system), float
    ).reshape(3)
    segs = _onaxis(_paths(folded))  # full on-axis polylines; scan range isolates the outgoing leg
    if coord == "z":
        rms, c, k = _waist(segs, "z", -160, 40)  # outgoing -Z leg only (z<40 excludes middle/incoming)
        det = ref[2]
    else:
        rms, c, k = _waist(segs, "x", 180, 340)   # outgoing +X leg only (x>180 excludes incoming)
        det = ref[0]
    if c is None:
        print(f"    {name}: detector={det:.2f}  waist=NONE (no crossings)")
        return
    print(
        f"    {name}: detector={det:.2f}  waist={c:.2f} (rms={rms*1000:.1f}um,n={k})  "
        f"waist-detector={c-det:+.2f}"
    )


def _run(builder, name, coord, air):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor, _ = builder()
    if air:
        orig = editor._folded_optical_solid_straight_equivalent_rows

        def patched():
            rows = orig()
            if rows is None:
                return None
            for r in rows:
                if str(getattr(r, "glass", "")).upper() not in ("AIR", ""):
                    # only the flattened fold-mirror plates carry BK7 here
                    r.glass = "AIR"
            return rows

        editor._folded_optical_solid_straight_equivalent_rows = patched
    _measure(editor, name, coord)


def main() -> int:
    print("=== BK7 plate (current) ===")
    _run(_build_single_mirror, "SINGLE", "x", air=False)
    _run(_build_two_mirror, "TWO", "z", air=False)
    print("=== AIR plate (hypothesis) ===")
    _run(_build_single_mirror, "SINGLE", "x", air=True)
    _run(_build_two_mirror, "TWO", "z", air=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
