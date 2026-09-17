"""Unambiguous fan-vs-cone: scatter the (Y,Z) cross-section of the on-axis OUTGOING arm
(X in [140,160]) for the real production bundle. Fan -> a LINE; cone -> a filled DISK/RING."""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _cross(paths, xlo, xhi):
    pts = []
    for p in paths:
        m = (p[:, 0] >= xlo) & (p[:, 0] <= xhi)
        pts.extend(p[m, 1:3].tolist())
    return np.asarray(pts, float) if pts else np.empty((0, 2))


def _build(editor, mode):
    if mode is not None:
        editor._preview_scene_sampling_mode = lambda: mode
        editor._preview_3d_sampling_mode = lambda: mode
    editor._preview_scene_trace_dirty = True
    _s, _r, bundle = editor._build_preview_system_rays_bundle(update_state=True)
    paths = [np.asarray(getattr(p, "points_world", None), float)[:, :3] for p in bundle.ray_paths]
    return [p for p in paths if p.ndim == 2 and p.shape[0] >= 2 and p.shape[1] >= 3
            and float(np.linalg.norm(p[0, :3])) <= 1.0 and float(p[:, 0].max()) > 250.0]


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        env = _build(editor, None)
        cone = _build(editor, "world_cone")
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))
    for ax, (tag, paths) in zip(axes, (("world_envelope (current)", env), ("world_cone (proposed)", cone))):
        c = _cross(paths, 140.0, 160.0)
        ax.scatter(c[:, 0], c[:, 1], s=9, alpha=0.6, color="tab:blue")
        ax.set_title(f"{tag}\nX in [140,160]  n={len(c)}")
        ax.set_xlabel("Y (mm)"); ax.set_ylabel("Z (mm)")
        ax.set_aspect("equal"); ax.grid(True, alpha=0.3)
    fig.suptitle("On-axis outgoing-arm cross-section: fan=line, cone=disk")
    fig.tight_layout()
    fig.savefig("bugs/_0203_crossscatter.png", dpi=110)
    print(f"envelope n={len(env)} cone n={len(cone)} -> bugs/_0203_crossscatter.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
