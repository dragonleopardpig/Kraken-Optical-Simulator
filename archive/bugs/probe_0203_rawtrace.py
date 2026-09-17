"""Where is the pupil X-spread lost -- in the TRACE or in the display FOLD? Trace world_cone
via _trace_preview_rays_folded_aware, build the scene bundle WITHOUT folding, and dump the
raw (unfolded) on-axis pupil spread. Then apply the fold and re-dump."""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _spread(paths_xyz, tag):
    # widest transverse extent per axis over all vertices of all on-axis rays
    allpts = np.vstack(paths_xyz)
    print(f"  {tag}: n_pts={len(allpts)}  X[{allpts[:,0].min():+.2f},{allpts[:,0].max():+.2f}] "
          f"Y[{allpts[:,1].min():+.2f},{allpts[:,1].max():+.2f}] Z[{allpts[:,2].min():+.2f},{allpts[:,2].max():+.2f}]")


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        editor._preview_scene_sampling_mode = lambda: "world_cone"
        editor._preview_3d_sampling_mode = lambda: "world_cone"

        wl = float(editor._current_wavelength())
        mr = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
        system = editor.build_system(require_solids=True)
        ftr = editor._folded_sequential_trace_rows(editor.rows)
        rays, ft = editor._trace_preview_rays_folded_aware(
            system, wl, mr, sampling_mode="world_cone", folded_trace_rows=ftr)
        bundle = editor._build_scene_bundle(system, rays, mr)
        # RAW (unfolded straight-equivalent) paths
        raw = [np.asarray(getattr(p, "points_world", None), float)[:, :3] for p in bundle.ray_paths]
        raw_oa = [p for p in raw if p.ndim == 2 and p.shape[0] >= 2
                  and float(np.linalg.norm(p[0, :3])) <= 1.0]
        # object mode
        obj_mode = editor._current_object_mode()
        # now fold
        editor._apply_folded_display_bend(bundle, ft)
        fold = [np.asarray(getattr(p, "points_world", None), float)[:, :3] for p in bundle.ray_paths]
        fold_oa = [p for p in fold if p.ndim == 2 and p.shape[0] >= 2 and float(p[:, 0].max()) > 250.0
                   and float(np.linalg.norm(p[0, :3])) <= 1.0]

    print(f"object_mode={obj_mode!r}  ft is None? {ft is None}  raw on-axis={len(raw_oa)} folded on-axis={len(fold_oa)}")
    if raw_oa:
        _spread(raw_oa, "RAW straight-equiv (unfolded)")
        # pupil-plane spread: at the max-Z end (focus region) and mid
        second = np.asarray([p[1, :3] for p in raw_oa], float)
        print(f"  RAW 2nd-vertex: X[{second[:,0].min():+.3f},{second[:,0].max():+.3f}] "
              f"Y[{second[:,1].min():+.3f},{second[:,1].max():+.3f}] Z[{second[:,2].min():+.2f},{second[:,2].max():+.2f}]")
    if fold_oa:
        _spread(fold_oa, "FOLDED display")
    return 0


if __name__ == "__main__":
    sys.exit(main())
