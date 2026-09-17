"""probe_0217 DISSECT: pin the exact source of the two-mirror Image-row mis-placement.

For BOTH the single-mirror and two-mirror AZ85, dump:
  * the straight-equivalent rows (surface/thickness/cumulative-z),
  * where the UNFOLDED straight rays converge (focus) vs terminate (Image row) -> overshoot,
  * the folded display waist (true image) and ray hard-stop,
  * the drawn detector ref + which _surface_reference_world_point branch fired,
  * the ORIGINAL Image-row spec.

The contrast is the tell: if single-mirror has ~0 overshoot and two-mirror has ~28mm, then
inserting free-placed mirror-2 introduced it (its flat-plate thickness is counted past the
conjugate).

Run: .devenv/state/venv/bin/python bugs/probe_0217_dissect.py
"""
from __future__ import annotations

import contextlib
import io

import numpy as np

from KrakenOS.UI.validate_open3d_second_mirror_incoming_axis_placement import (
    _build_single_mirror,
    _build_two_mirror,
)


def _paths(bundle):
    out = []
    for p in getattr(bundle, "ray_paths", None) or []:
        pw = np.asarray(getattr(p, "points_world", None), dtype=float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and pw.shape[1] >= 3:
            out.append(pw[:, :3])
    return out


def _onaxis(paths):
    return [pw for pw in paths if float(np.linalg.norm(pw[0][:3])) <= 1.0]


def _waist_lines(segs, axis, lo, hi, n=2500):
    """segs: list of (P, D) ray line pieces along `axis` (a unit 3-vec). Slide along axis,
    measure transverse RMS. Return (rms, t_at_min, centroid)."""
    ax = np.asarray(axis, float)
    ax = ax / np.linalg.norm(ax)
    perp1 = np.cross(ax, [1.0, 0.0, 0.0])
    if np.linalg.norm(perp1) < 1e-6:
        perp1 = np.cross(ax, [0.0, 1.0, 0.0])
    perp1 /= np.linalg.norm(perp1)
    perp2 = np.cross(ax, perp1)
    best = (1e18, None, None)
    for tv in np.linspace(lo, hi, n):
        pts = []
        for P, D in segs:
            dn = float(np.dot(D, ax))
            if abs(dn) < 1e-9:
                continue
            s = (tv - float(np.dot(P, ax))) / dn
            pts.append(P + s * D)
        if len(pts) >= 4:
            a = np.asarray(pts)
            c = a.mean(0)
            rms = float(np.sqrt((((a - c) @ perp1) ** 2 + ((a - c) @ perp2) ** 2).mean()))
            if rms < best[0]:
                best = (rms, float(tv), c)
    return best


def _straight_overshoot(editor, label):
    """Trace the straight-equivalent (reflection disabled) and report focus-vs-Image-row."""
    editor._reflect_straight_equivalent_display_rays = lambda _b: None
    try:
        _s, _r, straight = editor._build_preview_system_rays_bundle(update_state=False)
    finally:
        del editor._reflect_straight_equivalent_display_rays
    soa = _onaxis(_paths(straight))
    if not soa:
        print(f"  [{label}] no on-axis straight rays")
        return
    ends = np.asarray([pw[-1] for pw in soa])
    img_z = float(ends[:, 2].mean())
    # straight rays travel +Z; build line pieces from the last two vertices
    segs = [(pw[-2], pw[-1] - pw[-2]) for pw in soa if pw.shape[0] >= 2]
    rms, zf, ctr = _waist_lines(segs, [0, 0, 1], img_z - 80, img_z + 20)
    print(
        f"  [{label}] STRAIGHT focus z={zf:.2f} (rms={rms*1000:.1f}um)  Image-row z={img_z:.2f}"
        f"  => overshoot {img_z-zf:+.2f} mm"
    )
    return zf, img_z


def _straight_rows(editor, label):
    rows = editor._folded_optical_solid_straight_equivalent_rows()
    if rows is None:
        print(f"  [{label}] straight-equivalent rows: None")
        return
    print(f"  [{label}] straight-equivalent rows (cumulative z):")
    z = 0.0
    for i, r in enumerate(rows):
        th = float(getattr(r, "thickness", 0.0) or 0.0)
        print(
            f"      [{i}] {str(getattr(r,'surface','')):<10} glass={str(getattr(r,'glass','')):<7} "
            f"th={th:8.3f}  cum_z(front)={z:8.3f}"
        )
        z += th


def _report(builder, name):
    print(f"\n===================== {name} =====================")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor, _ = builder()
    _straight_rows(editor, name)
    _straight_overshoot(editor, name)

    # folded display bundle
    system, _rays, folded = editor._build_preview_system_rays_bundle(update_state=True)
    oa = _onaxis(_paths(folded))
    # outgoing leg: trim from max-x corner
    segs = []
    for pw in oa:
        idx = int(np.argmax(pw[:, 0]))
        if float(pw[idx, 0]) > 150.0 and idx < len(pw) - 1:
            seg = pw[idx:]
            # line pieces along the outgoing leg
            for k in range(len(seg) - 1):
                segs.append((seg[k], seg[k + 1] - seg[k]))
    # detector ref
    try:
        ref = np.asarray(
            editor._surface_reference_world_point(len(editor.rows) - 1, system=system), float
        ).reshape(3)
    except Exception as exc:  # noqa: BLE001
        ref = None
        print(f"  detector ref unavailable: {exc!r}")
    # endpoints
    ends = np.asarray([pw[-1] for pw in oa])
    if name.startswith("TWO"):
        axis = [0, 0, -1]  # outgoing -Z
    else:
        axis = [1, 0, 0]  # single-mirror outgoing +X
    if segs:
        rms, tv, ctr = _waist_lines(segs, axis, -160, 90)
        print(
            f"  FOLDED display waist along {axis}: pt=({ctr[0]:.2f},{ctr[1]:.2f},{ctr[2]:.2f}) rms={rms*1000:.1f}um"
        )
    print(
        f"  FOLDED ray endpoints: centroid=({ends[:,0].mean():.2f},{ends[:,1].mean():.2f},{ends[:,2].mean():.2f})"
    )
    if ref is not None:
        print(f"  DRAWN detector ref: ({ref[0]:.2f},{ref[1]:.2f},{ref[2]:.2f})")

    # original Image row spec
    img = editor.rows[-1]
    print(
        f"  ORIGINAL Image row: surface={img.surface} th={float(img.thickness):.3f} "
        f"desp=({float(img.desp_x):.2f},{float(img.desp_y):.2f},{float(img.desp_z):.2f})"
    )


def main() -> int:
    _report(_build_single_mirror, "SINGLE-MIRROR")
    _report(_build_two_mirror, "TWO-MIRROR (0217)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
