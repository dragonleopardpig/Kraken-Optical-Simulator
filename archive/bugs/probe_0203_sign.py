"""bugs/0203: does the wired Path A (rotation + rigid flip) still put off-axis kinks on the
correct '/' side (the original 0192 anti-regression), vs rotation-only which mid-airs them?"""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
from KrakenOS.UI.services.folded_sequential_fold import (
    _unit, fold_promoted_mirror_specs_to_sequential, promoted_mirror_world_center)
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _badsign(paths, center):
    bad = tot = 0
    res = []
    N = _unit([0.7071067811865476, 0.0, -0.7071067811865476])
    for p in paths:
        K = np.asarray(getattr(p, "points_world", None), float)
        if K.ndim != 2 or K.shape[0] < 3 or K.shape[1] < 3:
            continue
        seg = np.diff(K[:, :3], axis=0); ln = np.linalg.norm(seg, axis=1); g = ln > 1e-9
        if int(g.sum()) < 2:
            continue
        u = np.zeros_like(seg); u[g] = seg[g]/ln[g, None]
        cos = np.sum(u[:-1]*u[1:], axis=1); ki = int(np.argmin(cos))
        if cos[ki] > 0.2:
            continue
        kk = ki + 1
        kx, kz = float(K[kk, 0]), float(K[kk, 2])
        res.append(abs(float(np.dot(K[kk, :3] - center, N))))
        if abs(kx) > 0.5:
            tot += 1
            if np.sign(kx) != np.sign(kz - center[2]):
                bad += 1
    res = np.array(res) if res else np.array([0.0])
    return bad, tot, res.max(), res.mean()


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        specs = editor._serializable_specs_for_rows(list(editor.rows))
        _f, recs = fold_promoted_mirror_specs_to_sequential(specs)
        center = np.asarray(promoted_mirror_world_center(specs, int(recs[0]["row_index"])), float).reshape(3)

        # rotation ONLY (shadow the rigid flip)
        editor._apply_folded_mirror_rigid_reflection = lambda b, ft: None
        _s0, _r0, rot_bundle = editor._build_preview_system_rays_bundle(update_state=True)
        rot_paths = list(getattr(rot_bundle, "ray_paths", []))
        rot_tags = {str(getattr(p, "display_geometry_source", "")) for p in rot_paths}

        # wired (rotation + rigid flip)
        del editor._apply_folded_mirror_rigid_reflection
        _s1, _r1, full_bundle = editor._build_preview_system_rays_bundle(update_state=True)
        full_paths = list(getattr(full_bundle, "ray_paths", []))
        full_tags = {str(getattr(p, "display_geometry_source", "")) for p in full_paths}
        tag_ct = sum(1 for p in full_paths
                     if str(getattr(p, "display_geometry_source", "")) == "folded_mirror_rigid_reflected")

    rb, rt, rmax, rmean = _badsign(rot_paths, center)
    fb, ft_, fmax, fmean = _badsign(full_paths, center)
    print(f"rotation ONLY : badsign {rb}/{rt}  kink-resid max {rmax:.3f} mean {rmean:.3f}  tags={rot_tags}")
    print(f"wired (rigid) : badsign {fb}/{ft_}  kink-resid max {fmax:.3f} mean {fmean:.3f}  tags={full_tags}")
    print(f"paths tagged folded_mirror_rigid_reflected: {tag_ct}/{len(full_paths)}")

    # per-ray max |delta| between rotation-only and wired: which rays does the flip move?
    n = min(len(rot_paths), len(full_paths))
    moved = same = 0
    max_move = 0.0
    onaxis_move = []
    for i in range(n):
        a = np.asarray(getattr(rot_paths[i], "points_world", None), float)
        b = np.asarray(getattr(full_paths[i], "points_world", None), float)
        if a.shape != b.shape or a.ndim != 2:
            continue
        d = float(np.abs(a[:, :3] - b[:, :3]).max())
        max_move = max(max_move, d)
        if d > 1e-6:
            moved += 1
        else:
            same += 1
        # classify on-axis: launch near origin
        if float(np.linalg.norm(a[0, :3])) <= 1.0:
            onaxis_move.append(d)
    oa = np.array(onaxis_move) if onaxis_move else np.array([0.0])
    print(f"flip moves {moved} paths, leaves {same} identical; max move {max_move:.3f} mm")
    print(f"on-axis paths: {len(onaxis_move)}, their max flip-move {oa.max():.4f} mm (should be ~0: symmetric cone)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
