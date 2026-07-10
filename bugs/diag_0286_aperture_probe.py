"""bugs/0286 -- does clipping the object-illumination to the OBJECT APERTURE give a clean map?

The marked-face object map is sparse (occ ~18%) because a few outlier rays land far off-axis and
stretch the data extent, leaving most bins empty.  Only illumination WITHIN the object aperture (the
imaged FOV) is relayed to the sensor, so clip to the aperture and bin there.  Report occupancy + the
fold/perp edge ratios so we can pick a marker budget + bin count that reads as a real dark-edge map.
"""
from __future__ import annotations

import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import _load_python_data
from KrakenOS.UI.render_layout_snapshot import (
    _build_runtime_system,
    _rows_from_layout_info,
    _snapshot_editor,
)


def _load_editor(path):
    info = _load_python_data(path)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    return editor


def _trace(editor, path):
    system = _build_runtime_system(path, editor.rows)
    wavelength = editor._current_wavelength()
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    return system, editor._build_scene_bundle(system, rays, max_radius)


def _iso(editor, system, wl):
    bundles, sources = editor._build_illumination_marker_bundles(wl)
    if not bundles:
        return []
    rk = Kos.raykeeper(system)
    editor.__dict__["_force_nonseq_preview_trace"] = True
    prior = getattr(system, "_suppress_illumination_face_absorption", False)
    try:
        system._suppress_illumination_face_absorption = True
        editor._trace_preview_bundles(system, rk, wl, bundles, bundle_sources=sources)
    finally:
        editor.__dict__["_force_nonseq_preview_trace"] = False
        system._suppress_illumination_face_absorption = prior
    return editor._isolated_ray_analysis_records(system, rk)


def _clip_map(editor, system, recs, r_obj, bins):
    s = editor._source_illumination_hit_samples(system, 0, ray_records=recs)
    x = np.asarray(s.get("x", []), dtype=float)
    y = np.asarray(s.get("y", []), dtype=float)
    if x.size == 0:
        return "no hits"
    keep = (np.abs(x) <= r_obj) & (np.abs(y) <= r_obj)
    x, y = x[keep], y[keep]
    if x.size == 0:
        return "no hits in aperture"
    hist, xe, ye = np.histogram2d(x, y, bins=bins, range=[[-r_obj, r_obj], [-r_obj, r_obj]])
    d = hist.T / max(hist.max(), 1e-9)
    # crude fold/perp: centre 3x3 vs the four edge strips
    n = bins
    c0 = n // 2 - 1
    centre = d[c0:c0 + 2, c0:c0 + 2].mean()
    left = d[:, :2].mean(); right = d[:, -2:].mean()
    top = d[:2, :].mean(); bot = d[-2:, :].mean()
    edge = np.mean([left, right, top, bot])
    return (f"kept={x.size:>5} occ={(d>0).mean():.0%} centre={centre:.2f} "
            f"edgeLR={0.5*(left+right)/max(centre,1e-9):.2f} edgeTB={0.5*(top+bot)/max(centre,1e-9):.2f}")


def main():
    path = Path("attachment/machine_vision_150mm_test.py")
    r_obj = 32.5834804774 / 2.0  # object aperture radius (image circle)
    print(f"object aperture radius = {r_obj:.1f} mm\n")

    print("== marked BS face (aperture-clipped object map) ==")
    for rc in (2000, 6000):
        editor = _load_editor(path)
        editor.create_illumination_source_at_face(1, face_id="S001/F001", aim="inward")
        for spec in editor.layout_scene_source_specs:
            if "face_anchor_row" in spec:
                spec["ray_count"] = rc
        system, _ = _trace(editor, path)
        iso = _iso(editor, system, editor._current_wavelength())
        for bins in (8, 10):
            print(f"  rc={rc:>5} bins={bins}: {_clip_map(editor, system, iso, r_obj, bins)}")

    print("\n== LED flood (aperture-clipped object map) ==")
    editor = _load_editor(path)
    editor.add_illumination_led_source()
    system, _ = _trace(editor, path)
    recs = editor._collect_ray_analysis_records()
    for bins in (10, 12):
        print(f"  LED bins={bins}: {_clip_map(editor, system, recs, r_obj, bins)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
