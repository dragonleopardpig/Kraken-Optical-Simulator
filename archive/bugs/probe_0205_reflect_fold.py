"""bugs/0205 PROTOTYPE: replace the rotate-downstream + reflect-tail fold with a SINGLE
reflection of the straight-equivalent rays about the mirror hypotenuse plane.

Root cause (probe_0205_station): _fold_ray_downstream_of_station rotates every vertex at/after
station_z=59.4 (the mirror FRONT datum) about the fold anchor. That rotation maps the incoming
leg's meridional (X-pupil) spread into pure axial (Z) displacement -> incoming collapses to a
flat Y-only fan while the meridional spread migrates into the outgoing arm's Z-spread.

Correct fold = reflect the straight-equivalent ray about the real mirror plane (center,
face_normal): an ISOMETRY (focus preserved), points ON the plane are FIXED (clean per-ray kink),
incoming leg untouched (cone preserved). This probe applies that to the RAW straight-equivalent
rays and checks: incoming (X,Y) is a disk, outgoing (Y,Z) is a disk, focus stays tight and lands
where the CURRENT rigid fold puts it.

Run: .devenv/state/venv/bin/python -m bugs.probe_0205_reflect_fold
"""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
import KrakenOS.UI.services.three_d_scene_tools as tdt
from KrakenOS.UI.services.folded_sequential_fold import (
    fold_promoted_mirror_specs_to_sequential, promoted_mirror_world_center,
)

_CAP = {}
_real_bend = tdt.ThreeDSceneToolsMixin._apply_folded_display_bend


def _s2(a, cols):
    a = np.asarray(a, float)
    if a.ndim != 2 or a.shape[0] < 3:
        return 0.0
    c = a[:, cols] - a[:, cols].mean(0)
    s = np.linalg.svd(c, compute_uv=False)
    return float(s[1]) if s.size >= 2 else 0.0


def _kink_index(p):
    seg = np.diff(p[:, :3], axis=0); ln = np.linalg.norm(seg, axis=1); g = ln > 1e-9
    if int(g.sum()) < 2:
        return None
    u = np.zeros_like(seg); u[g] = seg[g] / ln[g, None]
    cos = np.sum(u[:-1] * u[1:], axis=1); ki = int(np.argmin(cos))
    return ki + 1 if cos[ki] <= 0.5 else None


def _reflect_fold(points, center, n):
    """Reflect the downstream (past-mirror) portion of a straight-equivalent ray about the
    plane (center, n). Insert the plane-crossing vertex so the kink is exact."""
    coords = np.asarray(points, float)[:, :3]
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    signed = (coords - np.asarray(center, float)) @ n
    if abs(signed[0]) < 1e-9:
        return None
    down = (signed * np.sign(signed[0])) < 0
    out = []
    for i in range(len(coords)):
        out.append(coords[i] - 2.0 * signed[i] * n if down[i] else coords[i])
        if i < len(coords) - 1 and down[i] != down[i + 1] and abs(signed[i] - signed[i + 1]) > 1e-12:
            t = signed[i] / (signed[i] - signed[i + 1])
            out.append(coords[i] + t * (coords[i + 1] - coords[i]))  # on plane -> reflection-fixed
    return np.asarray(out, float)


def _onaxis(paths, need_x=False):
    out = []
    for p in paths:
        if p.ndim == 2 and p.shape[0] >= 3 and p.shape[1] >= 3 and np.linalg.norm(p[0, :3]) <= 1.0:
            if need_x and p[:, 0].max() <= 250.0:
                continue
            out.append(p)
    return out


def _xsec_z(paths, z, cols):
    out = []
    for p in paths:
        za = p[:, 2]
        for i in range(len(p) - 1):
            if (za[i] - z) * (za[i + 1] - z) <= 0 and abs(za[i + 1] - za[i]) > 1e-9:
                t = (z - za[i]) / (za[i + 1] - za[i]); out.append((p[i] + t * (p[i + 1] - p[i]))[cols]); break
    return np.asarray(out, float)


def _xsec_x(paths, x, cols):
    out = []
    for p in paths:
        xa = p[:, 0]
        for i in range(len(p) - 1):
            if (xa[i] - x) * (xa[i + 1] - x) <= 0 and abs(xa[i + 1] - xa[i]) > 1e-9:
                t = (x - xa[i]) / (xa[i + 1] - xa[i]); out.append((p[i] + t * (p[i + 1] - p[i]))[cols]); break
    return np.asarray(out, float)


def _spy(self, scene_bundle, fold_transform):
    _CAP["raw"] = [np.array(getattr(p, "points_world", None), float) for p in (scene_bundle.ray_paths or [])]
    _CAP["ft"] = None if fold_transform is None else np.asarray(fold_transform, float).reshape(4, 4)
    _real_bend(self, scene_bundle, fold_transform)
    _CAP["final"] = [np.array(getattr(p, "points_world", None), float) for p in (scene_bundle.ray_paths or [])]


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor.snap_detector_to_image_plane()
        editor._preview_scene_trace_dirty = True
        tdt.ThreeDSceneToolsMixin._apply_folded_display_bend = _spy
        try:
            editor._build_preview_system_rays_bundle(update_state=True)
        finally:
            tdt.ThreeDSceneToolsMixin._apply_folded_display_bend = _real_bend
        specs = editor._serializable_specs_for_rows(list(editor.rows))
        _folded, records = fold_promoted_mirror_specs_to_sequential(specs)
        rec = records[0]
        row_index = int(rec["row_index"])
        center = promoted_mirror_world_center(specs, row_index)
        face_normal = np.asarray(rec["face_normal"], float).reshape(-1)[:3]
        station_z = float(sum(float(getattr(editor.rows[i], "thickness", 0.0) or 0.0) for i in range(row_index)))
        front = np.array([center[0], center[1], station_z], float)
        sys_full, _r, _b = editor._build_preview_system_rays_bundle(update_state=False)
        drawn_x = float(np.asarray(editor._surface_reference_world_point(len(editor.rows) - 1, system=sys_full), float).reshape(3)[0])

    raw = _CAP["raw"]; final = _CAP["final"]
    # my reflection fold on the raw straight-equivalent, about center (71.9) vs front face (59.4)
    reflected = [r for r in (_reflect_fold(p, center, face_normal) for p in raw) if r is not None]
    reflected_front = [r for r in (_reflect_fold(p, front, face_normal) for p in raw) if r is not None]

    raw_oa = _onaxis(raw)
    fin_oa = _onaxis(final, need_x=True)
    ref_oa = _onaxis(reflected, need_x=True)
    reff_oa = _onaxis(reflected_front, need_x=True)

    print(f"mirror center={np.round(center,3)}  front={np.round(front,3)}  face_normal={np.round(face_normal,4)}")
    print(f"DRAWN detector X = {drawn_x:.3f}")
    print(f"on-axis: raw={len(raw_oa)}  final(current)={len(fin_oa)}  refl-center={len(ref_oa)}  refl-front={len(reff_oa)}")

    def _focus(paths):
        ep = np.asarray([p[-1, :3] for p in paths], float)
        if len(ep) < 2:
            return None
        m = ep.mean(0)
        rms = float(np.sqrt(np.mean(np.sum((ep[:, 1:3] - m[1:3]) ** 2, axis=1))))
        return m, rms

    dx = float(fin_oa[0][:, 0].max()) if fin_oa else 296.0
    for tag, oa in (("current(rotate)", fin_oa), ("FIX refl-center", ref_oa), ("FIX refl-front", reff_oa)):
        inc = _xsec_z(oa, 35.0, [0, 1])
        out = _xsec_x(oa, dx * 0.6, [1, 2])
        foc = _focus(oa)
        s2i = _s2(inc, [0, 1]); s2o = _s2(out, [0, 1])
        fx = foc[0][0] if foc else float("nan"); rms = foc[1] if foc else float("nan")
        onfocus = abs(fx - drawn_x) < 0.05
        print(f"\n{tag}:")
        print(f"  incoming (X,Y)@Z=35: s2={s2i:.3f} X={np.ptp(inc[:,0]) if len(inc) else 0:.3f} Y={np.ptp(inc[:,1]) if len(inc) else 0:.3f}  {'DISK' if s2i>0.5 else 'FLAT FAN'}")
        print(f"  outgoing (Y,Z)@X={dx*0.6:.0f}: s2={s2o:.3f}  {'DISK' if s2o>0.5 else 'FLAT FAN'}")
        print(f"  focus X={fx:.3f} (drawn={drawn_x:.3f}, on-detector={onfocus})  transverse RMS={rms:.4f} mm")

    # decision: refl-front should give incoming DISK + focus ON the drawn detector
    inc_reff = _xsec_z(reff_oa, 35.0, [0, 1]); out_reff = _xsec_x(reff_oa, dx * 0.6, [1, 2]); foc_reff = _focus(reff_oa)
    ok = (foc_reff and _s2(inc_reff, [0, 1]) > 0.5 and _s2(out_reff, [0, 1]) > 0.5
          and foc_reff[1] < 0.05 and abs(foc_reff[0][0] - drawn_x) < 0.05)
    print("\nRESULT:", "PASS (refl-front: incoming cone + outgoing cone + focus on drawn detector)" if ok else "needs work")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
