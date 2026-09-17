"""bugs/0286 -- where does the marked BS-face illumination land on the object, per aim?

The marked face (aim=inward) lands its flood ENTIRELY outside the object aperture (+-16.3 mm) -> nothing
to image -> the sensor is (correctly) blank.  Probe both aims + report the object-hit centroid / spread
so we know whether the marked-face case can ever illuminate the imaged FOV, or whether only a source that
actually floods the FOV (the LED) drives the on-sensor overlay.
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


def _describe(editor, system, recs, r_obj):
    s = editor._source_illumination_hit_samples(system, 0, ray_records=recs)
    x = np.asarray(s.get("x", []), dtype=float)
    y = np.asarray(s.get("y", []), dtype=float)
    if x.size == 0:
        return "no object hits"
    r = np.hypot(x, y)
    in_ap = int(np.sum(r <= r_obj))
    return (f"n={x.size} centroid=({x.mean():+.1f},{y.mean():+.1f}) "
            f"x[{x.min():+.1f},{x.max():+.1f}] y[{y.min():+.1f},{y.max():+.1f}] "
            f"r[{r.min():.1f},{r.max():.1f}] in_aperture={in_ap}")


def main():
    path = Path("attachment/machine_vision_150mm_test.py")
    r_obj = 32.5834804774 / 2.0
    print(f"object aperture radius = {r_obj:.1f} mm; object at z=0\n")

    for aim in ("inward", "outward"):
        editor = _load_editor(path)
        editor.create_illumination_source_at_face(1, face_id="S001/F001", aim=aim)
        for spec in editor.layout_scene_source_specs:
            if "face_anchor_row" in spec:
                spec["ray_count"] = 6000
                # report the launch pose too
                print(f"aim={aim}: source origin=({spec.get('source_x'):+.1f},{spec.get('source_y'):+.1f},"
                      f"{spec.get('source_z'):+.1f}) dir=({spec.get('source_l'):+.2f},"
                      f"{spec.get('source_m'):+.2f},{spec.get('source_n'):+.2f})")
        system, _ = _trace(editor, path)
        iso = _iso(editor, system, editor._current_wavelength())
        print(f"  object landing: {_describe(editor, system, iso, r_obj)}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
