"""bugs/0286 -- decide the marked-face ray budget + whether a Mirror routes illum to the sensor.

Two questions the Approach-A design hinges on:
  Q1  The marked BS face emits 400 rays; only 18 reach the object -> a noisy 12x12 map.  Does boosting
      the marker ray budget give a DENSE, clean dark-edge object map?
  Q2  Does making the FOV object a MIRROR route illumination all the way to the SENSOR (so a
      physically-exact density-on-sensor heatmap becomes possible), or does it stay too sparse (so the
      projection is the only viable path)?

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python bugs/diag_0286_density_probe.py
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
from KrakenOS.UI.services.source_object_coupling import object_irradiance_map


def _load_editor(path: Path):
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
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    return system, bundle


def _isolated_emission_records(editor, system, wavelength):
    bundles, sources = editor._build_illumination_marker_bundles(wavelength)
    if not bundles:
        return []
    rays_illum = Kos.raykeeper(system)
    editor.__dict__["_force_nonseq_preview_trace"] = True
    prior = getattr(system, "_suppress_illumination_face_absorption", False)
    try:
        system._suppress_illumination_face_absorption = True
        editor._trace_preview_bundles(system, rays_illum, wavelength, bundles, bundle_sources=sources)
    finally:
        editor.__dict__["_force_nonseq_preview_trace"] = False
        system._suppress_illumination_face_absorption = prior
    return editor._isolated_ray_analysis_records(system, rays_illum)


def _sensor_surface_index(editor, bundle):
    target = editor._source_illumination_anchor_target(bundle)
    if target is None:
        return None
    for attr in ("trace_surface", "row_index"):
        try:
            return int(getattr(target, attr))
        except Exception:
            continue
    return None


def _map_quality(editor, system, obj_idx, recs, bins):
    m = object_irradiance_map(editor, system, int(obj_idx), ray_records=recs, bins=bins)
    if not m:
        return "None"
    d = np.asarray(m["density"], dtype=float)
    return f"hits={m['hit_count']} bins={d.shape} min={d[d>0].min():.2f} max={d.max():.2f} occ={(d>0).mean():.0%}"


def main() -> int:
    path = Path("attachment/machine_vision_150mm_test.py")

    # Q1: marked BS face, sweep the marker ray budget.
    print("== Q1: marked BS face -- object map vs marker ray budget ==")
    for rc in (400, 4000, 20000):
        editor = _load_editor(path)
        editor.create_illumination_source_at_face(1, face_id="S001/F001", aim="inward")
        # bump the stored marker ray_count so _illumination_marker_full_surface_source floods more
        for spec in editor.layout_scene_source_specs:
            if "face_anchor_row" in spec:
                spec["ray_count"] = rc
        system, bundle = _trace(editor, path)
        wl = editor._current_wavelength()
        iso = _isolated_emission_records(editor, system, wl)
        sidx = _sensor_surface_index(editor, bundle)
        s_obj = editor._source_illumination_hit_samples(system, 0, ray_records=iso)
        s_sen = editor._source_illumination_hit_samples(system, sidx, ray_records=iso) if sidx is not None else {"x": []}
        n_obj = np.asarray(s_obj.get("x", []), dtype=float).size
        n_sen = np.asarray(s_sen.get("x", []), dtype=float).size
        q = _map_quality(editor, system, 0, iso, bins=12)
        print(f"  rc={rc:>6}: emitted={len(iso):>6}  object_hits={n_obj:>5}  sensor_hits={n_sen:>4}  map[{q}]")

    # Q2: LED, plain Object vs Mirror -- how many illum rays reach the SENSOR?
    print("\n== Q2: LED flood -- illum rays reaching the SENSOR, plain Object vs Mirror ==")
    for label, mirror in (("plain Object", False), ("Mirror object", True)):
        editor = _load_editor(path)
        if mirror:
            editor.rows[0].surface = "Mirror"
        editor.add_illumination_led_source()
        system, bundle = _trace(editor, path)
        recs = editor._collect_ray_analysis_records()
        sidx = _sensor_surface_index(editor, bundle)
        s_obj = editor._source_illumination_hit_samples(system, 0, ray_records=recs)
        s_sen = editor._source_illumination_hit_samples(system, sidx, ray_records=recs) if sidx is not None else {"x": []}
        n_obj = np.asarray(s_obj.get("x", []), dtype=float).size
        n_sen = np.asarray(s_sen.get("x", []), dtype=float).size
        print(f"  {label:>13}: records={len(recs):>5}  sensor_idx={sidx}  object_hits={n_obj:>5}  sensor_hits={n_sen:>4}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
