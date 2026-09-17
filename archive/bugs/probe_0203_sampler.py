"""Does the pupil/cone sampler actually revolve under the AZ85 forced-fold condition?
Call the samplers directly on the editor + on the trace-preview service, with and without
the force flag, and report whether each is a 2D disk (X and Y vary) or meridional (X~0)."""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _desc(name, pts):
    a = np.asarray(pts, float)
    if a.ndim != 2 or a.shape[1] < 2:
        print(f"  {name}: shape {a.shape}?"); return
    xr = (a[:, 0].min(), a[:, 0].max()); yr = (a[:, 1].min(), a[:, 1].max())
    c = a[:, :2] - a[:, :2].mean(0)
    s = np.linalg.svd(c, compute_uv=False)
    s2 = float(s[1]) if s.size >= 2 else 0.0
    kind = "DISK" if s2 > 1e-6 else "meridional/fan"
    print(f"  {name}: n={a.shape[0]:4d} X[{xr[0]:+.3f},{xr[1]:+.3f}] Y[{yr[0]:+.3f},{yr[1]:+.3f}] s2={s2:.4f} -> {kind}")


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        svc = editor._trace_preview_service()

    print(f"editor id={id(editor)}  service id={id(svc)}  same={editor is svc}")
    print(f"editor _current_display_slice_axis = {editor._current_display_slice_axis()!r}")
    for label, obj in (("EDITOR", editor), ("SERVICE", svc)):
        print(f"[{label}]")
        obj.__dict__.pop("_force_folded_cone_preview_trace", None)
        print(f"  pref_fan (no flag) = {obj._launch_pupil_prefers_meridional_fan()}   "
              f"cone_flat = {obj._launch_cone_prefers_flat_fan()}")
        _desc("pupil no-flag", obj._sample_ray_count_pupil_points(10.0))
        _desc("cone  no-flag", obj._sample_ray_count_cone_points(10.0))
        obj.__dict__["_force_folded_cone_preview_trace"] = True
        print(f"  pref_fan (FLAG)   = {obj._launch_pupil_prefers_meridional_fan()}   "
              f"cone_flat = {obj._launch_cone_prefers_flat_fan()}")
        _desc("pupil  FLAG  ", obj._sample_ray_count_pupil_points(10.0))
        _desc("cone   FLAG  ", obj._sample_ray_count_cone_points(10.0))
        obj.__dict__.pop("_force_folded_cone_preview_trace", None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
