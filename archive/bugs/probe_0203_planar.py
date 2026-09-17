"""Definitive fan-vs-cone: is the on-axis bundle COPLANAR (fan) or 3D (cone)? Gather all
on-axis ray vertices into one 3D cloud, center, SVD; s3/s1 ~ 0 => planar fan, >0 => 3D cone."""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _planarity(oa):
    pts = np.vstack([p[:, :3] for p in oa])
    c = pts - pts.mean(0)
    s = np.linalg.svd(c, compute_uv=False)
    return s[0], s[1], s[2], (s[2]/s[0] if s[0] > 0 else 0.0)


def _run(editor, mode):
    if mode is not None:
        editor._preview_scene_sampling_mode = lambda: mode
        editor._preview_3d_sampling_mode = lambda: mode
    editor._preview_scene_trace_dirty = True
    system, _r, bundle = editor._build_preview_system_rays_bundle(update_state=True)
    paths = [np.asarray(getattr(p, "points_world", None), float) for p in bundle.ray_paths]
    oa = [p for p in paths if p.ndim == 2 and p.shape[0] >= 3 and p.shape[1] >= 3
          and float(np.linalg.norm(p[0, :3])) <= 1.0 and float(p[:, 0].max()) > 250.0]
    return oa, len(paths)


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        oa_e, n_e = _run(editor, None)
        oa_c, n_c = _run(editor, "world_cone")
    for tag, oa, n in (("world_envelope (current)", oa_e, n_e), ("world_cone   (proposed)", oa_c, n_c)):
        s1, s2, s3, ratio = _planarity(oa)
        verdict = "3D CONE" if ratio > 0.02 else "PLANAR FAN"
        print(f"{tag}: onaxis={len(oa)}/{n}  s1={s1:.2f} s2={s2:.2f} s3={s3:.4f}  s3/s1={ratio:.4f} -> {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
