"""Diagnose flag_20260702_183320_903: "the ray not reaching the image plane or detector."

Folded AZ85 RA-mirror scene. Measure where the drawn folded on-axis rays terminate vs
every candidate "detector" position (last-row reference, image-plane row, camera step
overlay, detector-coverage sensor), both BEFORE and AFTER snap_detector_to_image_plane,
so we know the true gap and its cause."""
from __future__ import annotations

import contextlib
import io

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _onaxis(bundle):
    paths = getattr(bundle, "ray_paths", None) or []
    out = []
    for path in paths:
        pw = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pw.ndim != 2 or pw.shape[0] < 2 or pw.shape[1] < 3:
            continue
        if float(np.linalg.norm(pw[0][:3])) <= 1.0 and float(pw[:, 0].max()) > 250.0:
            out.append(pw)
    return out


def _all_paths(bundle):
    out = []
    for path in (getattr(bundle, "ray_paths", None) or []):
        pw = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and pw.shape[1] >= 3:
            out.append(pw)
    return out


def _dump(editor, tag):
    system, _rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
    oa = _onaxis(bundle)
    allp = _all_paths(bundle)
    print(f"\n===== {tag} =====")
    print(f"rows: {len(editor.rows)}")
    # per-row surface reference world X
    for i in range(len(editor.rows)):
        try:
            ref = np.asarray(editor._surface_reference_world_point(i, system=system), dtype=float).reshape(3)
            r = editor.rows[i]
            nm = getattr(r, "surface", getattr(r, "name", "?"))
            print(f"  row {i:2d} [{nm:>12}] ref=({ref[0]:8.3f},{ref[1]:7.3f},{ref[2]:8.3f}) thick={getattr(r,'thickness',None)}")
        except Exception as exc:
            print(f"  row {i:2d} ref FAILED: {exc!r}")
    drawn_x = float(np.asarray(editor._surface_reference_world_point(len(editor.rows) - 1, system=system), dtype=float).reshape(3)[0])
    print(f"  drawn detector (last row) X = {drawn_x:.3f}")
    if oa:
        ends = np.asarray([p[-1][:3] for p in oa])
        xm, zm = float(ends[:, 0].mean()), float(ends[:, 2].mean())
        trms = float(np.sqrt(((ends[:, 1:3] - ends[:, 1:3].mean(0)) ** 2).sum(1).mean()))
        print(f"  ON-AXIS rays: n={len(oa)} endpoint mean=({xm:.3f},{ends[:,1].mean():.3f},{zm:.3f}) transRMS={trms*1000:.2f}um")
        print(f"     gap on-axis-end -> drawn detector X: {drawn_x - xm:+.3f} mm")
    allmaxx = max((float(p[:, 0].max()) for p in allp), default=float("nan"))
    allendx = np.asarray([p[-1][0] for p in allp]) if allp else np.array([np.nan])
    print(f"  ALL rays: n={len(allp)} max-vertex-X={allmaxx:.3f}  endpoint-X min/mean/max=({allendx.min():.3f}/{allendx.mean():.3f}/{allendx.max():.3f})")
    return system, bundle


def main():
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)

    # As-loaded (what the user sees on flag) -- NO snap
    _dump(editor, "AS-LOADED (no snap)")

    # camera / detector overlay diagnostics
    print("\n--- overlay/step bounds ---")
    for attr in ("_scene_step_overlay_bounds", "_camera_step_overlay_bounds"):
        pass
    try:
        info = editor._scene_target_detector_info() if hasattr(editor, "_scene_target_detector_info") else None
        print("detector info:", info)
    except Exception as exc:
        print("detector info failed:", repr(exc))

    # After snap
    with contextlib.redirect_stderr(buf):
        editor.snap_detector_to_image_plane()
    _dump(editor, "AFTER snap_detector_to_image_plane")


if __name__ == "__main__":
    main()
