"""bugs/0288 -- the REAL relay measurement.

diag_0288_footprint_linchpin.py showed the earlier 0287 "flood sprays +-1000 mm" conclusion was an
ARTIFACT: launched-source records carry no ``traced_polyline_world``, so extending their LAUNCH
direction (which runs parallel to the object plane) exploded.  The marker path (bugs/0270/0272) traces
into an ISOLATED keeper and DOES attach the engine's true ``points_world``.  Do the same for a LAUNCHED
source, then relay the TRUE terminal segment to the object plane.

Also reads the paraxial conjugate (``_current_finite_paraxial_magnification``, fixed for BS-cube scenes
by bugs/0104) -- the object->sensor scale mechanism B needs, with no hardcode.

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -u bugs/diag_0288_relay_probe.py
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
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    editor.last_system = system
    editor.last_rays = rays
    editor._last_scene_bundle = bundle
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    return system, bundle


def isolated_source_records(editor, system, wavelength):
    """Trace the LAUNCHED scene sources into an isolated keeper -> records with traced_polyline_world.
    Mirrors _isolated_illumination_marker_records (bugs/0270/0272) but for non-marker sources."""
    bundles, sources = editor._build_scene_source_bundles(float(wavelength))
    if not bundles:
        print("   (no scene-source bundles)")
        return []
    rays_illum = Kos.raykeeper(system)
    prior = editor.__dict__.get("_force_nonseq_preview_trace", False)
    editor.__dict__["_force_nonseq_preview_trace"] = True
    try:
        editor._trace_preview_bundles(system, rays_illum, float(wavelength), bundles, bundle_sources=sources)
    finally:
        editor.__dict__["_force_nonseq_preview_trace"] = prior
    return editor._isolated_ray_analysis_records(system, rays_illum)


def relay_to_plane(records, plane_z):
    """Extend each record's TRUE terminal segment (from the engine polyline) to z=plane_z."""
    hits, no_poly, wrong_way = [], 0, 0
    for r in records:
        poly = r.get("traced_polyline_world")
        pts = np.asarray(poly, dtype=float) if poly is not None else None
        if pts is None or pts.ndim != 2 or pts.shape[0] < 2:
            no_poly += 1
            continue
        p, q = pts[-2], pts[-1]
        d = q - p
        n = np.linalg.norm(d)
        if n < 1e-9 or abs(d[2]) < 1e-9:
            wrong_way += 1
            continue
        d = d / n
        t = (plane_z - q[2]) / d[2]
        if t <= 1e-9:  # object plane is behind the terminal point
            wrong_way += 1
            continue
        h = q + t * d
        hits.append((h[0], h[1]))
    return np.asarray(hits, dtype=float), no_poly, wrong_way


def report(tag, pts, aperture_r):
    print(f"\n   {tag}")
    if pts.size == 0:
        print("      (no relayed points)")
        return
    r = np.hypot(pts[:, 0], pts[:, 1])
    inside = int(np.count_nonzero(r <= aperture_r))
    print(f"      n={len(pts)}  x=[{pts[:,0].min():+.2f},{pts[:,0].max():+.2f}]  "
          f"y=[{pts[:,1].min():+.2f},{pts[:,1].max():+.2f}]  r_max={r.max():.2f}")
    print(f"      inside object aperture (r<={aperture_r:.2f}): {inside}")
    if inside:
        fill = "OVER-fills (=> uniform, no dark edges)" if r.max() >= aperture_r else \
               "UNDER-fills (=> dark edges at the rim)"
        print(f"      => footprint {fill}")


def run(tag, path, spec_or_none):
    print("=" * 78)
    print(tag)
    print("=" * 78)
    editor = _load_editor(path)
    if spec_or_none is None:
        editor.add_illumination_led_source(record_history=False)
    else:
        editor.layout_scene_source_specs = [spec_or_none]
    system, bundle = _trace(editor, path)
    wl = float(editor._current_wavelength())
    obj_idx = int(editor._source_object_coupling_object_index())
    aperture_r = float(editor.rows[obj_idx].diameter) / 2.0

    mag = editor._current_finite_paraxial_magnification()
    print(f"\n   paraxial magnification m = {mag}")
    target = editor._source_illumination_anchor_target(bundle)
    hw, hh = editor._detector_target_half_extent(target)
    print(f"   sensor half = {hw:.3f} x {hh:.3f} mm   object aperture r = {aperture_r:.3f} mm")
    if mag:
        print(f"   sensor half {hw:.2f} mm  <->  object half {hw/abs(mag):.2f} mm  (via |m|={abs(mag):.4f})")

    recs = isolated_source_records(editor, system, wl)
    print(f"\n   isolated source records = {len(recs)}")
    with_poly = sum(1 for r in recs if r.get("traced_polyline_world") is not None)
    print(f"   carrying traced_polyline_world = {with_poly}")
    if recs and with_poly:
        sample = next(r for r in recs if r.get("traced_polyline_world") is not None)
        pts = np.asarray(sample["traced_polyline_world"], dtype=float)
        print(f"   sample polyline ({pts.shape[0]} pts): "
              f"{[tuple(round(float(v),1) for v in p) for p in pts[:4]]}"
              f"{' ...' if pts.shape[0] > 4 else ''}")

    relayed, no_poly, wrong_way = relay_to_plane(recs, 0.0)
    print(f"\n   relay: no_polyline={no_poly}  not-heading-to-plane={wrong_way}  intersecting={len(relayed)}")
    report("RELAYED footprint on the object plane (z=0):", relayed, aperture_r)


def main() -> int:
    path = Path("attachment/machine_vision_150mm_test.py")
    if not path.exists():
        print("fixture missing:", path)
        return 1

    run("SCENARIO A: default added LED (seats at the object plane) -- the FLAGGED scene", path, None)

    coax = {
        "source_id": "source:coax", "name": "Coaxial LED", "model": "Random rectangle source",
        "role": "illumination", "physical": True, "enabled": True,
        "source_x": 90.0, "source_y": 0.0, "source_z": 229.646,
        "source_l": -1.0, "source_m": 0.0, "source_n": 0.0,
        "radius_x": 27.5, "radius_y": 37.0, "radius": 37.0,
        "cone_deg": 30.0, "ray_count": 4000, "power": 1.0,
        "wavelength": 0.55, "seed": 7,
    }
    print()
    run("SCENARIO B: coaxial LED beside the BS (the flagged INTENT)", path, coax)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
