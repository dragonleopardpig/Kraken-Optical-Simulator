"""bugs/0287 -- test the USER's reformulation on the REAL MV-150 scene.

Instead of the factorized "bin illumination on the object, project to sensor" coupling (0286), model the
ACTUAL light path as a folded trace and let KrakenOS's native ray tracer carry the pattern:

    LED illuminator  --(-x)-->  BS +x face (Absorber flipped to Transmit)  --(reflect down -z)-->
    object plane at z=0 (now a DIFFUSE OBJECT: MIRROR base + Lambertian scatter guided at the sensor)
    --(scatter up +z)-->  imaging lens  -->  sensor (Image surface).

KrakenOS HAS real Lambertian scatter with target-importance-sampling (validate_open3d_source_object_coupling
_build_coupling_fixture proves ~950 scatter rays reach the detector on the TEACHING layout). The question:
does it work on the REAL vendor scene, and does the sensor show 2-sided dark edges (fold dark / perp uniform)
-- or, as the 202mm object<->BS air gap predicts, a ~uniform bright-center patch (no edges in the FOV)?

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -u bugs/diag_0287_diffuse_fold_probe.py
"""
from __future__ import annotations

import copy
import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import _build_system_from_specs, _load_python_data
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor

PATH = Path("attachment/machine_vision_150mm_test.py")
SENSOR_INDEX = 8  # Image surface (from the scene: 0 Object .. 8 Image)


def _flip_absorber(surfaces):
    flipped = []
    for s in surfaces:
        adv = s.get("advanced")
        if not isinstance(adv, dict):
            continue
        meta = adv.get("OpticalSolidFaces")
        if not isinstance(meta, dict):
            continue
        for face in meta.get("faces", []):
            if str(face.get("function", "")).strip() == "Absorber/Mechanical":
                face["function"] = "Transmit/Port"
                face["role"] = "Output"
                flipped.append(str(face.get("face_id")))
    return flipped


def _make_object_diffuse(surfaces, diameter, target_surface):
    s0 = surfaces[0]
    s0["surface"] = "Diffuse Object"
    s0["glass"] = "MIRROR"
    s0["diameter"] = float(diameter)
    s0["advanced"] = dict(s0.get("advanced", {}))
    s0["advanced"]["DiffuseScatter"] = {
        "model": "Lambertian", "backend": "Built-in", "reflectance": 0.8,
        "sample_count": 12, "max_scatter_angle_deg": 80.0, "min_branch_power": 1e-6,
        "max_branch_depth": 1, "target_surface": int(target_surface), "target_radius_scale": 0.95,
        "polarization": "Preserve projected Jones",
    }


def _profile(px, py, half):
    bins = 13
    edges = np.linspace(-half, half, bins + 1)
    centres = 0.5 * (edges[:-1] + edges[1:])
    H, _, _ = np.histogram2d(px, py, bins=[edges, edges])
    H = H.T  # [iy, ix]
    fold = H[np.abs(centres) <= half * 0.35, :].sum(0)   # sum over y-strip -> x/fold profile
    perp = H[:, np.abs(centres) <= half * 0.35].sum(1)   # sum over x-strip -> y/perp profile

    def ratio(prof):
        cen = prof[np.abs(centres) <= half * 0.35].mean()
        edg = prof[np.abs(centres) >= half * 0.72].mean()
        return (edg / cen) if cen > 0 else 0.0

    lx, ly = ratio(fold), ratio(perp)
    x_dark, y_dark = lx < 0.80, ly < 0.80
    shape = ("RADIAL (both dark)" if x_dark and y_dark
             else "2-SIDED (fold/x dark, perp/y uniform)" if x_dark and not y_dark
             else "2-SIDED (perp/y dark, fold/x uniform)" if y_dark and not x_dark
             else "UNIFORM (no dark edges)")
    return f"fold/x edge/centre={lx:.3f} perp/y edge/centre={ly:.3f} => {shape}"


def _run(diffuse_diam, radius_x, radius_y, tag):
    info = _load_python_data(PATH)
    surfaces = copy.deepcopy(info["surfaces"])
    settings = copy.deepcopy(info.get("settings", {})) if isinstance(info.get("settings", {}), dict) else {}

    flipped = _flip_absorber(surfaces)
    _make_object_diffuse(surfaces, diffuse_diam, SENSOR_INDEX)

    wavelength = float(settings.get("wavelength", 0.55))
    spec = {
        "source_id": "source:coax-probe", "name": "Coaxial probe LED",
        "model": "Random rectangle source", "role": "illumination",
        "physical": True, "enabled": True,
        "source_x": 60.0, "source_y": 0.0, "source_z": 229.646,
        "source_l": -1.0, "source_m": 0.0, "source_n": 0.0,
        "radius_x": float(radius_x), "radius_y": float(radius_y), "radius": float(max(radius_x, radius_y)),
        "cone_deg": 18.0, "ray_count": 8000, "power": 1.0,
        "wavelength": wavelength, "seed": 7,
    }
    settings["scene_sources"] = [spec]

    rows = _rows_from_layout_info({"surfaces": surfaces, "settings": settings})
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = PATH
    editor._normalize_special_rows()

    sources = editor._collect_scene_sources(wavelength=wavelength)
    system = _build_system_from_specs(surfaces)
    rays = Kos.raykeeper(system)
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    editor.last_system = system
    editor.last_rays = rays

    records = editor._ray_analysis_records_for_trace(system=system, rays=rays)
    n_rec = len(records)

    # DIAGNOSTIC: did the flood reach the diffuse object (surface 0), and did anything scatter?
    from collections import Counter
    surf_hist = Counter()
    ev_hist = Counter()
    min_z = np.inf
    for r in records:
        for h in (r.get("hits") or []):
            s = str(h.get("surface"))
            surf_hist[s] += 1
            ev_hist[str(h.get("event") or h.get("event_kind") or "")] += 1
            try:
                zf = float(h.get("z"))
                if np.isfinite(zf):
                    min_z = min(min_z, zf)
            except Exception:
                pass
    print(f"    surface-hit histogram = {dict(sorted(surf_hist.items(), key=lambda kv: kv[0]))}")
    print(f"    event histogram = {dict(ev_hist)}")
    print(f"    min z reached = {min_z:.1f}   (object diffuse surface is at z=0)")

    # Sensor hits (reuse the exact overlay machinery).
    samples = editor._source_illumination_hit_samples(system, SENSOR_INDEX, ray_records=records)
    sx = np.asarray(samples.get("x", []), dtype=float)
    sy = np.asarray(samples.get("y", []), dtype=float)
    n_sensor = int(sx.size)

    print(f"[{tag}] flipped={flipped} diffuse_diam={diffuse_diam} records={n_rec} "
          f"sensor_hits={n_sensor}")
    if n_sensor:
        print(f"    sensor x=[{sx.min():.2f},{sx.max():.2f}] y=[{sy.min():.2f},{sy.max():.2f}]")
        half = float(max(abs(sx).max(), abs(sy).max(), 1.0))
        if n_sensor >= 60:
            print(f"    SENSOR PROFILE (half={half:.1f}): {_profile(sx, sy, half)}")
        else:
            print(f"    (too few sensor hits for a stable profile)")
    print(flush=True)


def main() -> int:
    if not PATH.exists():
        print("fixture missing")
        return 1
    # One config with full diagnostics: is the flood even tested against the diffuse object at z=0?
    _run(diffuse_diam=200.0, radius_x=27.5, radius_y=39.0, tag="flood-size 200mm DIAG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
