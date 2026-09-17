"""Render the folded AZ85 on-axis ray bundle for world_envelope (current) vs world_cone
(proposed), drawing polylines directly (no Tk-var scene populator). Two views each: iso and
looking down the +X outgoing arm (a flat fan reads as a LINE, a real cone as a filled DISK)."""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
import pyvista as pv
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

OUT = "bugs/_0203_render"


def _onaxis(bundle):
    out = []
    for p in bundle.ray_paths:
        pw = np.asarray(getattr(p, "points_world", None), float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and pw.shape[1] >= 3 \
           and float(np.linalg.norm(pw[0, :3])) <= 1.0 and float(pw[:, 0].max()) > 250.0:
            out.append(pw[:, :3])
    return out


def _polyline(pts):
    pts = np.asarray(pts, float)
    n = len(pts)
    cells = np.hstack([[n], np.arange(n)])
    pd = pv.PolyData(pts, lines=cells)
    return pd


def _draw(paths, out_png, cam):
    pl = pv.Plotter(off_screen=True, window_size=(1100, 900))
    pl.set_background("white")
    for pts in paths:
        pl.add_mesh(_polyline(pts), color=(0.15, 0.35, 0.85), line_width=1.5)
    pl.add_axes(line_width=3)
    pl.show_grid(color="black", fmt="%.0f")
    pl.camera_position = cam
    pl.screenshot(str(out_png))
    try:
        pl.render_window.Finalize(); pl.close()
    except Exception:
        pass


def _build(editor, mode):
    if mode is not None:
        editor._preview_scene_sampling_mode = lambda: mode
        editor._preview_3d_sampling_mode = lambda: mode
    editor._preview_scene_trace_dirty = True
    _s, _r, bundle = editor._build_preview_system_rays_bundle(update_state=True)
    return _onaxis(bundle)


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        env = _build(editor, "world_envelope")  # OLD behaviour (forced)
        cone = _build(editor, "world_cone")     # NEW production default (bugs/0203)
    iso = [(-350.0, -350.0, 480.0), (150.0, 0.0, 60.0), (0.0, 0.0, 1.0)]
    downx = [(600.0, 0.0, 71.9), (150.0, 0.0, 71.9), (0.0, 0.0, 1.0)]
    _draw(env, f"{OUT}_envelope_iso.png", iso)
    _draw(env, f"{OUT}_envelope_downx.png", downx)
    _draw(cone, f"{OUT}_cone_iso.png", iso)
    _draw(cone, f"{OUT}_cone_downx.png", downx)
    print(f"envelope on-axis paths={len(env)}  cone on-axis paths={len(cone)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
