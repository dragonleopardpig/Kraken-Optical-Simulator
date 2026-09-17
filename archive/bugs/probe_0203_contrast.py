"""bugs/0203 #5 contrast: on the SAME rotation-folded AZ85 bundle, the RIGID flip keeps the
on-axis cone converged on the drawn detector while the OLD per-ray tau SHEARS it."""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
from KrakenOS.UI.services.folded_sequential_fold import (
    correct_folded_mirror_ray_points, fold_promoted_mirror_specs_to_sequential,
    mirror_reflection_flip_plane_normal, promoted_mirror_world_center,
    rigid_reflect_folded_mirror_ray_points)
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _onaxis(paths):
    out = []
    for pw in paths:
        pw = np.asarray(pw, float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and pw.shape[1] >= 3 \
           and float(np.linalg.norm(pw[0, :3])) <= 1.0 and float(pw[:, 0].max()) > 250.0:
            out.append(pw)
    return out


def _interp(pts, x):
    xa = pts[:, 0]
    for i in range(len(xa) - 1):
        x0, x1 = xa[i], xa[i + 1]
        if (x0 - x) * (x1 - x) <= 0 and abs(x1 - x0) > 1e-9:
            t = (x - x0) / (x1 - x0)
            return pts[i, 1:3] + t * (pts[i + 1, 1:3] - pts[i, 1:3])
    return None


def _rms_at(paths, x):
    offs = [o for o in (_interp(p, x) for p in paths) if o is not None]
    if len(offs) < 4:
        return None
    a = np.asarray(offs, float)
    return float(np.sqrt(((a - a.mean(0)) ** 2).sum(1).mean()))


def _waist(paths, lo, hi):
    best = (None, 1e9)
    for x in np.linspace(lo, hi, 240):
        r = _rms_at(paths, x)
        if r is not None and r < best[1]:
            best = (x, r)
    return best


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        specs = editor._serializable_specs_for_rows(list(editor.rows))
        _f, recs = fold_promoted_mirror_specs_to_sequential(specs)
        ri = int(recs[0]["row_index"])
        face_normal = np.asarray(recs[0]["face_normal"], float).reshape(3)
        chief_in = np.asarray(recs[0].get("chief_in") or [0, 0, 1.0], float).reshape(3)
        center = np.asarray(promoted_mirror_world_center(specs, ri), float).reshape(3)
        flip = mirror_reflection_flip_plane_normal(chief_in, face_normal)

        wl = float(editor._current_wavelength())
        mr = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
        system = editor.build_system(require_solids=True)
        ftr = editor._folded_sequential_trace_rows(editor.rows)
        rays, ft = editor._trace_preview_rays_folded_aware(
            system, wl, mr, sampling_mode=editor._preview_3d_sampling_mode(), folded_trace_rows=ftr)
        bundle = editor._build_scene_bundle(system, rays, mr)
        editor._fold_straight_equivalent_display_rays(bundle, ft)  # rotation fold only
        rot = [np.asarray(getattr(p, "points_world", None), float) for p in bundle.ray_paths]

        M = np.asarray(ft, float).reshape(4, 4)
        anchor = M[:3, :3] @ center + M[:3, 3]
        rigid = [rigid_reflect_folded_mirror_ray_points(p, anchor, flip) for p in rot]
        tau = [correct_folded_mirror_ray_points(p, center, face_normal, chief_in) for p in rot]
        rigid = [p for p in rigid if p is not None]
        tau = [p for p in tau if p is not None]
        drawn_x = float(np.asarray(
            editor._surface_reference_world_point(len(editor.rows) - 1, system=system), float).reshape(3)[0])

    for tag, paths in (("rotation-only", rot), ("RIGID flip", rigid), ("per-ray TAU", tau)):
        oa = _onaxis(paths)
        wx, wr = _waist(oa, 40.0, drawn_x + 30.0)
        ends = np.asarray([p[-1][:3] for p in oa], float)
        ex = float(ends[:, 0].mean())
        etrms = float(np.sqrt(((ends[:, 1:3] - ends[:, 1:3].mean(0)) ** 2).sum(1).mean()))
        print(f"{tag:14s}: rays={len(oa)}  waist X={wx:.2f} RMS={wr*1000:.1f}um ({drawn_x-wx:+.2f}mm)  "
              f"endpoint X={ex:.3f} ({ex-drawn_x:+.3f}) endRMS={etrms*1000:.2f}um")
    print(f"drawn sensor X={drawn_x:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
