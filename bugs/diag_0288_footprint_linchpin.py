"""bugs/0288 linchpin probe -- everything mechanism B needs, measured on the REAL vendor scene.

Three questions, answered without reading anything off a screenshot:

  Q1  Does the object->sensor conjugate exist EMPIRICALLY in the traced records?  i.e. are there
      rays with BOTH an object-surface event and a detector-surface event, so we can least-squares
      fit sensor_xy = A @ object_xy + b (the magnification) instead of hardcoding one?

  Q2  What is the illumination footprint on the OBJECT plane, at TRUE extent, for
        (a) the default added LED (seats at the object plane, z=0), and
        (b) a coaxial LED parked beside the beam splitter (the flagged intent)?
      For (b) the trace-order wall (0287) means 0 rays land on the object, so we must GEOMETRICALLY
      relay: extend each illumination ray's terminal polyline segment to the object plane.

  Q3  Given the footprint + the conjugate, what SHOULD the sensor heatmap look like?  Specifically:
      does the footprint under-fill the imaged aperture (=> dark edges) or over-fill it (=> uniform)?

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -u bugs/diag_0288_footprint_linchpin.py
"""
from __future__ import annotations

import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

from collections import Counter
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


def _hits(record):
    h = record.get("hits")
    return h if isinstance(h, list) else []


def _surface_hist(records):
    hist = Counter()
    for r in records:
        for h in _hits(r):
            try:
                hist[int(h.get("surface", -1))] += 1
            except Exception:
                pass
    return dict(sorted(hist.items()))


def _pairs(editor, system, obj_idx, det_idx, records):
    """(object_local_xy, detector_local_xy) for every ray touching BOTH surfaces."""
    o_pts, d_pts = [], []
    for r in records:
        o = d = None
        for h in _hits(r):
            try:
                s = int(h.get("surface", -1))
            except Exception:
                continue
            if s == obj_idx and o is None:
                o = editor._hit_local_xy(system, obj_idx, h)[:2]
            elif s == det_idx and d is None:
                d = editor._hit_local_xy(system, det_idx, h)[:2]
        if o is not None and d is not None and all(np.isfinite(v) for v in (*o, *d)):
            o_pts.append(o)
            d_pts.append(d)
    return np.asarray(o_pts, dtype=float), np.asarray(d_pts, dtype=float)


def _fit_affine(o_pts, d_pts):
    """Least-squares sensor_xy = A @ object_xy + b.  Returns (A, b, rms)."""
    if o_pts.shape[0] < 6:
        return None, None, float("inf")
    design = np.hstack([o_pts, np.ones((o_pts.shape[0], 1))])  # [x, y, 1]
    sol, *_ = np.linalg.lstsq(design, d_pts, rcond=None)  # (3, 2)
    pred = design @ sol
    rms = float(np.sqrt(np.mean(np.sum((pred - d_pts) ** 2, axis=1))))
    return sol[:2, :].T, sol[2, :], rms


def _terminal_segment(record):
    """Last (point, direction) of a record's traced path -- engine-derived, no hardcode."""
    poly = record.get("traced_polyline_world")
    if isinstance(poly, (list, np.ndarray)):
        pts = np.asarray(poly, dtype=float)
        if pts.ndim == 2 and pts.shape[0] >= 2:
            d = pts[-1] - pts[-2]
            n = np.linalg.norm(d)
            if n > 1e-9:
                return pts[-1], d / n
    # fall back to source origin + launch direction
    try:
        p = np.array([float(record["source_x"]), float(record["source_y"]), float(record["source_z"])])
        d = np.array([float(record["source_l"]), float(record["source_m"]), float(record["source_n"])])
        n = np.linalg.norm(d)
        if n > 1e-9:
            return p, d / n
    except Exception:
        pass
    return None, None


def _relay_to_plane(records, plane_z):
    """Geometrically extend each ray's terminal segment to z=plane_z.  Returns the (x, y) hits."""
    out = []
    for r in records:
        p, d = _terminal_segment(r)
        if p is None or abs(d[2]) < 1e-9:
            continue
        t = (plane_z - p[2]) / d[2]
        if t <= 1e-9:  # plane is behind the ray
            continue
        q = p + t * d
        out.append((q[0], q[1]))
    return np.asarray(out, dtype=float)


def _describe(name, pts, aperture_r):
    print(f"\n  -- {name} --")
    if pts.size == 0:
        print("     no points")
        return
    r = np.hypot(pts[:, 0], pts[:, 1])
    inside = int(np.count_nonzero(r <= aperture_r))
    print(f"     n={len(pts)}  x=[{pts[:,0].min():.1f},{pts[:,0].max():.1f}]  "
          f"y=[{pts[:,1].min():.1f},{pts[:,1].max():.1f}]")
    print(f"     radial max={r.max():.1f} mm   inside aperture r<={aperture_r:.2f}: {inside}")
    if inside:
        print(f"     => footprint {'UNDER-fills' if r.max() < aperture_r else 'reaches/over-fills'} the aperture")


def scenario_default_led(path):
    print("=" * 78)
    print("SCENARIO A: default added LED (add_illumination_led_source) -- the FLAGGED scene")
    print("=" * 78)
    editor = _load_editor(path)
    editor.add_illumination_led_source(record_history=False)
    system, bundle = _trace(editor, path)

    obj_idx = int(editor._source_object_coupling_object_index())
    target = editor._source_illumination_anchor_target(bundle)
    aperture_r = float(editor.rows[obj_idx].diameter) / 2.0
    half_w, half_h = editor._detector_target_half_extent(target)
    print(f"\n  object idx={obj_idx} (aperture r={aperture_r:.3f} mm)")
    print(f"  anchor target: row_index={getattr(target, 'row_index', None)} "
          f"trace_surface={getattr(target, 'trace_surface', None)} "
          f"is_detector={getattr(target, 'is_detector', None)} "
          f"sensor half {half_w:.2f} x {half_h:.2f} mm")

    wl = float(editor._current_wavelength())
    records = editor._coupled_object_illumination_records(system, wl)
    hist = _surface_hist(records)
    print(f"  coupled illumination records = {len(records)}")
    print(f"  surface-hit histogram        = {hist}")
    print(f"  record keys                  = {sorted(records[0].keys()) if records else '-'}")

    ts = getattr(target, "trace_surface", None)
    det_idx = int(ts) if ts is not None else (max(hist) if hist else -1)
    print(f"  => detector surface index used for the conjugate fit = {det_idx}")

    # Q1: the empirical conjugate
    o_pts, d_pts = _pairs(editor, system, obj_idx, det_idx, records)
    print(f"\n  Q1 object<->detector paired rays = {len(o_pts)}")
    A, b, rms = _fit_affine(o_pts, d_pts)
    if A is None:
        print("     CANNOT FIT the conjugate from these records")
    else:
        print(f"     A = [[{A[0,0]:+.4f} {A[0,1]:+.4f}], [{A[1,0]:+.4f} {A[1,1]:+.4f}]]  b = "
              f"({b[0]:+.3f}, {b[1]:+.3f})   fit rms = {rms:.4f} mm")
        sx, sy = np.hypot(A[0, 0], A[1, 0]), np.hypot(A[0, 1], A[1, 1])
        print(f"     => magnification |m| = ({sx:.4f}, {sy:.4f})  "
              f"[object r{aperture_r:.2f} images to r{aperture_r*sx:.2f} on the sensor]")
        print(f"     => sensor half {half_w:.2f} corresponds to object half {half_w/max(sx,1e-9):.2f} mm")

    # Q2a: footprint on the object plane -- DIRECT hits (the launch, since the LED sits at z=0)
    samples = editor._source_illumination_hit_samples(system, obj_idx, ray_records=records)
    direct = np.column_stack([np.asarray(samples.get("x", []), dtype=float),
                              np.asarray(samples.get("y", []), dtype=float)])
    _describe("Q2a DIRECT object-surface illumination samples", direct, aperture_r)
    return editor, system, bundle, obj_idx, det_idx, aperture_r


def scenario_coaxial_led(path):
    print("\n" + "=" * 78)
    print("SCENARIO B: coaxial LED parked beside the beam splitter (the flagged INTENT)")
    print("=" * 78)
    editor = _load_editor(path)
    # Park a real emitter beside the BS aimed at its 45-deg face -- the coaxial illuminator.
    editor.layout_scene_source_specs = [{
        "source_id": "source:coax", "name": "Coaxial LED", "model": "Random rectangle source",
        "role": "illumination", "physical": True, "enabled": True,
        "source_x": 90.0, "source_y": 0.0, "source_z": 229.646,
        "source_l": -1.0, "source_m": 0.0, "source_n": 0.0,
        "radius_x": 27.5, "radius_y": 37.0, "radius": 37.0,
        "cone_deg": 30.0, "ray_count": 4000, "power": 1.0,
        "wavelength": float(editor._current_wavelength()), "seed": 7,
    }]
    system, bundle = _trace(editor, path)
    obj_idx = int(editor._source_object_coupling_object_index())
    aperture_r = float(editor.rows[obj_idx].diameter) / 2.0
    wl = float(editor._current_wavelength())
    records = editor._coupled_object_illumination_records(system, wl)
    print(f"\n  coupled illumination records = {len(records)}")
    print(f"  surface-hit histogram        = {_surface_hist(records)}")
    has_poly = sum(1 for r in records if isinstance(r.get("traced_polyline_world"), (list, np.ndarray)))
    print(f"  records carrying traced_polyline_world = {has_poly}")

    samples = editor._source_illumination_hit_samples(system, obj_idx, ray_records=records)
    direct = np.column_stack([np.asarray(samples.get("x", []), dtype=float),
                              np.asarray(samples.get("y", []), dtype=float)])
    _describe("DIRECT object-surface hits (expect ~0: the trace-order wall)", direct, aperture_r)

    relayed = _relay_to_plane(records, 0.0)
    _describe("GEOMETRIC RELAY: terminal segments extended to the object plane z=0", relayed, aperture_r)


def main() -> int:
    path = Path("attachment/machine_vision_150mm_test.py")
    if not path.exists():
        print("fixture missing:", path)
        return 1
    scenario_default_led(path)
    scenario_coaxial_led(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
