"""Diagnostic probe (#5 / bugs 0203): now that the folded straight-equivalent launch is a
real area-filling DISK (bugs/0203 #2 fix), does the folded display bend still converge the
whole cone on the drawn detector, or does it smear (the user's "focusing rays vary left to
right -- some before focus, some at, some after")?

Traces the straight-equivalent path and measures the beam waist at THREE bend stages:
  (1) rotation-fold only  (_fold_straight_equivalent_display_rays)
  (2) rotation + 0192 reflection correction  (the full _apply_folded_display_bend)
  (3) same as the app draws it
plus splits the cone into meridional vs sagittal rays to localise the smear.
"""
from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

from probe_0187_seq_mirror_focus import (  # type: ignore
    _onaxis_paths,
    _preview_2d_sampling_mode,
    _transverse_rms_at_x,
    _waist,
)


def _trace_bundle(editor):
    wavelength = float(editor._current_wavelength())
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
    system = editor.build_system(require_solids=True)
    folded_trace_rows = editor._folded_sequential_trace_rows(editor.rows)
    rays, fold_transform = editor._trace_preview_rays_folded_aware(
        system, wavelength, max_radius,
        sampling_mode=_preview_2d_sampling_mode(editor),
        folded_trace_rows=folded_trace_rows,
    )
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    return system, bundle, fold_transform


def _sensor_x(editor, system):
    n = len(editor.rows)
    drawn = np.asarray(
        editor._surface_reference_world_point(n - 1, system=system), dtype=float
    ).reshape(3)
    return float(drawn[0])


def _report_waist(tag, paths, drawn_x, lines):
    rms_sensor = _transverse_rms_at_x(paths, drawn_x)
    wx, wrms = _waist(paths, 40.0, drawn_x + 30.0)
    lines.append(f"  [{tag}] rays={len(paths)}")
    if rms_sensor is not None:
        lines.append(f"      RMS at sensor X={drawn_x:.2f}: {rms_sensor:.4f} mm")
    else:
        lines.append(f"      RMS at sensor X={drawn_x:.2f}: (n/a)")
    if wx is not None:
        lines.append(f"      waist X={wx:.2f} (RMS {wrms:.4f} mm), {drawn_x - wx:+.2f} mm from sensor")


def _split_meridional(paths, drawn_x):
    """Partition on-axis rays into near-meridional vs sagittal by their |Z| at the sensor."""
    mer, sag = [], []
    for pw in paths:
        xs = pw[:, 0]
        if xs.min() > drawn_x or xs.max() < drawn_x:
            continue
        idx = np.searchsorted(xs, drawn_x)
        if idx <= 0 or idx >= len(xs):
            continue
        x0, x1 = xs[idx - 1], xs[idx]
        if abs(x1 - x0) < 1e-9:
            continue
        t = (drawn_x - x0) / (x1 - x0)
        p = pw[idx - 1] + t * (pw[idx] - pw[idx - 1])
        (mer if abs(float(p[2])) <= abs(float(p[1])) else sag).append(pw)
    return mer, sag


def main() -> int:
    lines: list[str] = []
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()

        # Stage A: rotation-fold ONLY (skip the 0192 reflection correction).
        system, bundle, ft = _trace_bundle(editor)
        editor._fold_straight_equivalent_display_rays(bundle, ft)
        drawn_x = _sensor_x(editor, system)
        paths_rot = _onaxis_paths(bundle)

        # Stage B: full app bend (rotation + 0192 reflection correction).
        system2, bundle2, ft2 = _trace_bundle(editor)
        editor._apply_folded_display_bend(bundle2, ft2)
        paths_full = _onaxis_paths(bundle2)

    lines.append("=== #5 folded-cone focus (bugs/0203) ===")
    lines.append("Stage A -- rotation fold ONLY (no 0192 correction):")
    _report_waist("all", paths_rot, drawn_x, lines)
    mer, sag = _split_meridional(paths_rot, drawn_x)
    _report_waist("meridional", mer, drawn_x, lines)
    _report_waist("sagittal", sag, drawn_x, lines)

    lines.append("Stage B -- full bend (rotation + 0192 reflection correction):")
    _report_waist("all", paths_full, drawn_x, lines)
    mer2, sag2 = _split_meridional(paths_full, drawn_x)
    _report_waist("meridional", mer2, drawn_x, lines)
    _report_waist("sagittal", sag2, drawn_x, lines)

    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
