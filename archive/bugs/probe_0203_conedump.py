"""Dump the ACTUAL 3D spread of the world_cone on-axis incoming leg: does X vary, or is it
still meridional? Rules out a probe artifact in the s2=0 reading."""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        editor._preview_scene_sampling_mode = lambda: "world_cone"
        editor._preview_3d_sampling_mode = lambda: "world_cone"
        editor._preview_scene_trace_dirty = True
        system, _r, bundle = editor._build_preview_system_rays_bundle(update_state=True)
        paths = [np.asarray(getattr(p, "points_world", None), float) for p in bundle.ray_paths]

    oa = [p for p in paths if p.ndim == 2 and p.shape[0] >= 2 and p.shape[1] >= 3
          and float(np.linalg.norm(p[0, :3])) <= 1.0 and float(p[:, 0].max()) > 250.0]
    print(f"world_cone on-axis rays: {len(oa)} of {len(paths)}")
    # Per-ray: max |X| over ALL vertices, and over the incoming leg (Z<60)
    maxx_all = []
    maxx_in = []
    for p in oa:
        maxx_all.append(float(np.abs(p[:, 0]).max()))
        inc = p[p[:, 2] < 60.0]
        maxx_in.append(float(np.abs(inc[:, 0]).max()) if inc.size else 0.0)
    maxx_all = np.array(maxx_all); maxx_in = np.array(maxx_in)
    print(f"per-ray max|X| ALL vertices:      min={maxx_all.min():.3f} max={maxx_all.max():.3f} mean={maxx_all.mean():.3f}")
    print(f"per-ray max|X| incoming (Z<60):   min={maxx_in.min():.3f} max={maxx_in.max():.3f} mean={maxx_in.mean():.3f}")
    # second vertex spread across rays (the launch direction sample)
    p1 = np.asarray([p[1, :3] for p in oa], float)
    print(f"2nd-vertex spread: X[{p1[:,0].min():.3f},{p1[:,0].max():.3f}] "
          f"Y[{p1[:,1].min():.3f},{p1[:,1].max():.3f}] Z[{p1[:,2].min():.3f},{p1[:,2].max():.3f}]")
    # endpoints spread (the focus)
    ends = np.asarray([p[-1, :3] for p in oa], float)
    print(f"endpoint spread:   X[{ends[:,0].min():.3f},{ends[:,0].max():.3f}] "
          f"Y[{ends[:,1].min():.3f},{ends[:,1].max():.3f}] Z[{ends[:,2].min():.3f},{ends[:,2].max():.3f}]")
    # sample 5 rays' first 3 vertices
    for p in oa[:5]:
        print("   ", np.array2string(p[:3, :3], precision=3, suppress_small=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
