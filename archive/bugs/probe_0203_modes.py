"""bugs/0203 #2: dump every trace-mode flag + sampling-mode decision for the folded AZ85
RA-mirror scene, and the REAL preview path count, so we know exactly which gate routes it
to the sparse world_envelope instead of the dense revolved world_cone."""
from __future__ import annotations
import contextlib, io, sys
import numpy as np
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _cross_count(paths, xlo, xhi):
    """Interpolate each on-axis path at the mid-plane X and report the 2D (Y,Z) spread."""
    xm = 0.5 * (xlo + xhi)
    yz = []
    for p in paths:
        K = np.asarray(getattr(p, "points_world", None), float)
        if K.ndim != 2 or K.shape[0] < 2 or K.shape[1] < 3:
            continue
        if float(np.linalg.norm(K[0, :3])) > 1.0:
            continue  # off-axis
        xa = K[:, 0]
        for i in range(len(xa) - 1):
            x0, x1 = xa[i], xa[i + 1]
            if (x0 - xm) * (x1 - xm) <= 0 and abs(x1 - x0) > 1e-9:
                t = (xm - x0) / (x1 - x0)
                yz.append(K[i, 1:3] + t * (K[i + 1, 1:3] - K[i, 1:3]))
                break
    a = np.asarray(yz, float) if yz else np.zeros((0, 2))
    if a.shape[0] == 0:
        return 0, 0.0, 0.0
    return a.shape[0], float(np.ptp(a[:, 0])), float(np.ptp(a[:, 1]))


def _onaxis(paths):
    out = []
    for p in paths:
        K = np.asarray(getattr(p, "points_world", None), float)
        if K.ndim == 2 and K.shape[0] >= 2 and K.shape[1] >= 3 \
           and float(np.linalg.norm(K[0, :3])) <= 1.0 and float(K[:, 0].max()) > 250.0:
            out.append(K)
    return out


def _endpoint_conv(paths):
    ends = np.asarray([p[-1][:3] for p in paths], float)
    ex = float(ends[:, 0].mean())
    erms = float(np.sqrt(((ends[:, 1:3] - ends[:, 1:3].mean(0)) ** 2).sum(1).mean()))
    return len(paths), ex, erms


def _interp_yz(K, x):
    xa = K[:, 0]
    for i in range(len(xa) - 1):
        x0, x1 = xa[i], xa[i + 1]
        if (x0 - x) * (x1 - x) <= 0 and abs(x1 - x0) > 1e-9:
            t = (x - x0) / (x1 - x0)
            return K[i, 1:3] + t * (K[i + 1, 1:3] - K[i, 1:3])
    return None


def _waist(paths, lo, hi):
    best = (None, 1e9)
    for x in np.linspace(lo, hi, 240):
        offs = [o for o in (_interp_yz(p, x) for p in paths) if o is not None]
        if len(offs) < 4:
            continue
        a = np.asarray(offs, float)
        r = float(np.sqrt(((a - a.mean(0)) ** 2).sum(1).mean()))
        if r < best[1]:
            best = (float(x), r)
    return best


def main() -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        ts = editor._resolved_trace_mode(system=editor.__dict__.get("last_system"))
        brk = editor._scene_breaks_rotational_symmetry()
        m_scene = editor._preview_scene_sampling_mode()
        m_3d = editor._preview_3d_sampling_mode()
        m_2d = editor._preview_2d_sampling_mode()
        fan = editor._launch_pupil_prefers_meridional_fan()
        flatfan = editor._launch_cone_prefers_flat_fan()
        has_fold = editor._scene_has_promoted_mirror_fold()
        prefers_cone = editor._folded_scene_prefers_launch_cone()
        # REAL preview
        _s, _r, bundle = editor._build_preview_system_rays_bundle(update_state=True)
        paths = list(getattr(bundle, "ray_paths", []))
        n, dy, dz = _cross_count(paths, 140.0, 160.0)
        oa = _onaxis(paths)
        noa, ex, erms = _endpoint_conv(oa) if oa else (0, 0.0, 0.0)
        drawn_x = float(np.asarray(
            editor._surface_reference_world_point(len(editor.rows) - 1, system=editor.last_system),
            float).reshape(3)[0])
        wx, wr = _waist(oa, 40.0, drawn_x + 40.0) if oa else (None, 0.0)
        # snap the detector to best focus, rebuild, re-measure the on-detector spot
        editor.snap_detector_to_image_plane()
        _s2, _r2, bundle2 = editor._build_preview_system_rays_bundle(update_state=True)
        oa2 = _onaxis(list(getattr(bundle2, "ray_paths", [])))
        noa2, ex2, erms2 = _endpoint_conv(oa2) if oa2 else (0, 0.0, 0.0)
        drawn_x2 = float(np.asarray(
            editor._surface_reference_world_point(len(editor.rows) - 1, system=editor.last_system),
            float).reshape(3)[0])

    keys = ("use_folded", "use_nonseq", "active", "has_beam_splitter", "has_diffuse_scatter",
            "has_probabilistic_nonseq", "has_optical_stl_solid", "has_nonseq_geometry")
    print("=== AZ85 folded RA-mirror trace-mode flags ===")
    for k in keys:
        print(f"  {k:26s}= {ts.get(k)}")
    print(f"  _scene_breaks_rotational_symmetry = {brk}")
    print("=== sampling-mode decisions ===")
    print(f"  _preview_scene_sampling_mode()          = {m_scene}   (shared bundle / 2D-when-3D-closed)")
    print(f"  _preview_3d_sampling_mode()             = {m_3d}   (Open 3D inspector)")
    print(f"  _preview_2d_sampling_mode()             = {m_2d}")
    print(f"  _launch_pupil_prefers_meridional_fan()  = {fan}")
    print(f"  _launch_cone_prefers_flat_fan()         = {flatfan}")
    print(f"  _scene_has_promoted_mirror_fold()       = {has_fold}")
    print(f"  _folded_scene_prefers_launch_cone()     = {prefers_cone}  <-- bugs/0203 fix")
    print("=== REAL preview bundle (what the app draws) ===")
    print(f"  total paths={len(paths)}  on-axis @X=150: n={n} Yspread={dy:.3f} Zspread={dz:.3f} mm")
    print(f"  -> {'CONE (2D disk)' if (n>40 and dy>1 and dz>1) else 'SPARSE/FAN'}")
    print("=== #5 focus convergence on the SAME production bundle (world_cone) ===")
    print(f"  before snap: on-axis rays={noa}  endpoint X={ex:.3f} (drawn X={drawn_x:.3f})  endRMS={erms*1000:.1f} um (defocus if detector not at focus)")
    if wx is not None:
        print(f"  cone WAIST: X={wx:.3f}  RMS={wr*1000:.2f} um  ({drawn_x-wx:+.3f} mm from drawn detector) -> {'TIGHT (cone converges)' if wr*1000 < 20 else 'BROAD'}")
    print(f"  after snap:  on-axis rays={noa2}  endpoint X={ex2:.3f} (drawn X={drawn_x2:.3f})  endRMS={erms2*1000:.2f} um")
    print(f"  -> {'CONVERGED on drawn detector' if erms2*1000 < 50 else 'NOT CONVERGED'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
