"""probe_0217 POST-PASS prototype: after the folded display bend, the detector target AND the
ray endpoints both sit at fold(straight Image row) = the plate-back, ~28mm PAST where the cone
actually converges. Prototype the two-arm-style reconciliation: compute the folded on-axis ray
convergence W (least-squares closest point of the exit-ray lines), truncate every ray to the
plane through W, and reposition the detector target to W. Verify detector == W == ray-stop, and
that single-mirror is a NO-OP (already converges at its detector).

Run: .devenv/state/venv/bin/python bugs/probe_0217_postpass.py
"""
from __future__ import annotations

import contextlib
import io

import numpy as np

from KrakenOS.UI.validate_open3d_second_mirror_incoming_axis_placement import (
    _build_single_mirror,
    _build_two_mirror,
)


def _onaxis_paths(bundle):
    out = []
    for p in getattr(bundle, "ray_paths", None) or []:
        pw = np.asarray(getattr(p, "points_world", None), dtype=float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and pw.shape[1] >= 3 and np.linalg.norm(pw[0][:3]) <= 1.0:
            out.append((p, pw[:, :3]))
    return out


def _cross_plane(pw, ref, axis):
    """(transverse point, present) where polyline pw crosses the plane through ref ⊥ axis."""
    s = (pw - ref) @ axis
    for i in range(len(s) - 1):
        if (s[i]) * (s[i + 1]) <= 0 and abs(s[i + 1] - s[i]) > 1e-9:
            t = -s[i] / (s[i + 1] - s[i])
            p = pw[i] + t * (pw[i + 1] - pw[i])
            q = p - (float((p - ref) @ axis)) * axis  # foot on the plane
            return q, True
    return None, False


def _waist(paths, axis, ref, s_lo, s_hi, n=1400):
    """Slide a plane along `axis`; return (min transverse RMS, s_at_min, centroid)."""
    e = np.eye(3)
    u = np.cross(axis, e[np.argmin(np.abs(axis))]); u /= max(np.linalg.norm(u), 1e-12)
    v = np.cross(axis, u)
    best = (1e18, None, None)
    for s in np.linspace(s_lo, s_hi, n):
        c = ref + s * axis
        pts = [q for _p, pw in paths if (q := _cross_plane(pw, c, axis)[0]) is not None]
        if len(pts) >= 4:
            a = np.asarray(pts); ctr = a.mean(0)
            rms = float(np.sqrt((((a - ctr) @ u) ** 2 + ((a - ctr) @ v) ** 2).mean()))
            if rms < best[0]:
                best = (rms, float(s), ctr)
    return best


def _reconcile(bundle, tol_mm=1.0):
    paths = _onaxis_paths(bundle)
    if len(paths) < 4:
        return None
    # exit axis = mean final-segment direction; ref = mean endpoint
    dirs = [(pw[-1] - pw[-2]) / max(np.linalg.norm(pw[-1] - pw[-2]), 1e-12) for _p, pw in paths]
    axis = np.mean(dirs, axis=0); axis /= max(np.linalg.norm(axis), 1e-12)
    ends = np.asarray([pw[-1] for _p, pw in paths]); ref = ends.mean(0)
    endpoint_rms = float(np.sqrt((((ends - ref) - ((ends - ref) @ axis)[:, None] * axis) ** 2).sum(1).mean()))
    # search the waist BACKWARD from the endpoints (s<=0) up to the leg length
    starts = np.asarray([pw[0] for _p, pw in paths])
    leg = float(np.max(np.abs((ends - starts) @ axis)))
    waist_rms, waist_s, waist_ctr = _waist(paths, axis, ref, -leg, 0.5)
    if waist_s is None:
        return ("noop", axis, endpoint_rms, None, None)
    overshoot = -waist_s  # >0 when the waist is BEFORE the endpoints
    # GATE: only reconcile a real overshoot (waist clearly before endpoints AND much tighter)
    if overshoot <= tol_mm or waist_rms > 0.25 * max(endpoint_rms, 1e-9):
        return ("noop", axis, endpoint_rms, overshoot, waist_rms)
    W = np.asarray(waist_ctr, float)
    for p, pw3 in paths:
        a, b = pw3[-2], pw3[-1]
        d = b - a; dn = float(np.dot(d, axis))
        if abs(dn) < 1e-9:
            continue
        t = float(np.dot(W - a, axis)) / dn
        if t <= 0:
            continue
        newpw = np.asarray(p.points_world, float).copy()
        newpw[-1, :3] = a + t * d
        p.points_world = newpw
    moved = []
    for tg in getattr(bundle, "targets", []) or []:
        if getattr(tg, "is_detector", False):
            old = np.asarray(getattr(tg, "center_world"), float).reshape(3).copy()
            tg.center_world = W
            moved.append((old, W))
    return ("reconciled", axis, endpoint_rms, overshoot, waist_rms, W, moved)


def _report(builder, name):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor, _ = builder()
        _s, _r, bundle = editor._build_preview_system_rays_bundle(update_state=True)
    ends0 = np.asarray([pw[-1] for _p, pw in _onaxis_paths(bundle)])
    det0 = next((np.asarray(t.center_world, float).reshape(3) for t in bundle.targets if getattr(t, "is_detector", False)), None)
    print(f"\n=== {name} ===")
    print(f"  BEFORE: ray_end=({ends0[:,0].mean():.2f},{ends0[:,1].mean():.2f},{ends0[:,2].mean():.2f})  "
          f"detector={None if det0 is None else [round(float(x),2) for x in det0]}")
    res = _reconcile(bundle)
    if res is None:
        print("  reconcile: skipped (too few rays)")
        return
    status = res[0]
    print(f"  gate: {status}  endpoint_rms={res[2]*1000:.1f}um  overshoot={res[3]}  waist_rms={None if res[4] is None else round(res[4]*1000,1)}um")
    ends2 = np.asarray([pw[-1] for _p, pw in _onaxis_paths(bundle)])
    det2 = next((np.asarray(t.center_world, float).reshape(3) for t in bundle.targets if getattr(t, "is_detector", False)), None)
    trms = float(np.sqrt(((ends2 - ends2.mean(0)) ** 2).sum(1).mean()))
    print(f"  AFTER : ray_end=({ends2[:,0].mean():.2f},{ends2[:,1].mean():.2f},{ends2[:,2].mean():.2f})  "
          f"endpoint RMS={trms*1000:.1f}um  detector={None if det2 is None else [round(float(x),2) for x in det2]}")
    if status == "reconciled":
        moved = res[6]
        print(f"  moved detector by {np.linalg.norm(moved[0][1]-moved[0][0]):.2f}mm" if moved else "  (no detector target)")


def main() -> int:
    _report(_build_single_mirror, "SINGLE-MIRROR (must be ~no-op)")
    _report(_build_two_mirror, "TWO-MIRROR (0217)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
