#!/usr/bin/env python3
"""Headless repro for bugs/0093 — does a promoted BK7 beam-splitter cube
over-converge the transmitted beam? Numeric (ray convergence via least-squares
closest-approach), no VTK, so it checks the TRACE physics directly.

Three experiments, all tracing a converging cone (bare focus z=200):
  1. FLAT BK7 cube (no BS face, no branching) -> plane-parallel-plate baseline.
  2. hand-built BK7 BS cube (45deg diagonal 'Beam Splitter' face -> branching).
  3. the REAL promoted STEP cube (step_32704) from the cache.

RESULT (2026-06-18): all three are CORRECT — the transmit focus lands FURTHER
than the bare focus by the plate shift t*(1-1/n), never closer; the reflect arm
converges at the matching folded distance; the 45deg face is classified
`internal` (no refraction). 0093 (focus before the bare focus) does NOT
reproduce on current code => suspect a stale app at record time. See
bugs/0093-open3d-beam-splitter-cube-overfocuses-transmit.md.

Run: .devenv/state/venv/bin/python bugs/repro_0093.py
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import trimesh

import KrakenOS as Kos
from KrakenOS.TraceEvents import trace_event_to_record

CUBE_MM = 40.0
CUBE_CENTER_Z = 100.0
BARE_FOCUS_Z = 200.0   # where the launched cone converges with NO cube
WL = 0.55
N_BK7 = 1.5168         # ~d-line


def _cube_stl() -> str:
    out = Path("attachment/repro_0093")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"cube_{int(CUBE_MM)}mm.stl"
    if not path.exists():
        box = trimesh.creation.box(extents=(CUBE_MM, CUBE_MM, CUBE_MM))
        box.export(str(path))
    return str(path)


def _closest_approach(origins: np.ndarray, dirs: np.ndarray):
    M = np.zeros((3, 3)); b = np.zeros(3); eye = np.eye(3)
    for o, d in zip(origins, dirs):
        d = d / np.linalg.norm(d)
        proj = eye - np.outer(d, d)
        M += proj; b += proj @ o
    return np.linalg.solve(M, b)


def _converging_dirs(radius: float, n: int, focus_z: float):
    rays = []
    coords = np.linspace(-radius, radius, n)
    for x0 in coords:
        for y0 in coords:
            o = np.array([x0, y0, 0.0])
            d = np.array([0.0, 0.0, focus_z]) - o
            rays.append((o, d / np.linalg.norm(d)))
    return rays


def _build_system(with_cube: bool):
    obj = Kos.surf()
    obj.Name = "Source ref"
    obj.Thickness = CUBE_CENTER_Z - CUBE_MM / 2.0  # object -> cube front
    obj.Diameter = 60.0
    obj.Drawing = 0

    surfaces = [obj]
    if with_cube:
        cube = Kos.surf()
        cube.Name = "BK7 cube"
        cube.Solid_3d_stl = _cube_stl()
        cube.Glass = "BK7"
        cube.Diameter = CUBE_MM * 1.6
        cube.Thickness = CUBE_MM      # cube front -> ... (pose calibration below)
        surfaces.append(cube)

    img = Kos.surf()
    img.Name = "Detector"
    img.Glass = "AIR"
    img.Diameter = 80.0
    img.Thickness = 0.0
    img.Drawing = 1
    surfaces.append(img)
    # leave a long gap before the image so exit rays travel far enough to read
    surfaces[-2].Thickness = 200.0
    return Kos.system(surfaces, Kos.Setup())


def _trace(with_cube: bool, radius=8.0, n=5):
    system = _build_system(with_cube)
    system.energy_probability = 0
    rays = Kos.raykeeper(system)
    bundle = _converging_dirs(radius, n, BARE_FOCUS_Z)
    for o, d in bundle:
        system.NsTrace([float(o[0]), float(o[1]), 0.0],
                       [float(d[0]), float(d[1]), float(d[2])], WL)
        rays.push()
    return system, rays


def _exit_rays(rays):
    """Last polyline segment (exit ray) of each traced primary path."""
    origins, dirs = [], []
    events_all = getattr(rays, "TRACE_EVENTS", [])
    for ev_list in events_all:
        recs = [trace_event_to_record(e) for e in (ev_list or [])]
        pts = [np.asarray(r.get("point_world"), dtype=float) for r in recs
               if np.all(np.isfinite(np.asarray(r.get("point_world"), dtype=float)))]
        if len(pts) < 2:
            continue
        o = pts[-2]; d = pts[-1] - pts[-2]
        if np.linalg.norm(d) < 1e-9:
            continue
        origins.append(o); dirs.append(d / np.linalg.norm(d))
    return np.asarray(origins), np.asarray(dirs)


def _dump_chief(rays, label):
    events_all = getattr(rays, "TRACE_EVENTS", [])
    if not events_all:
        print(f"  [{label}] no TRACE_EVENTS"); return
    # pick a near-marginal ray (last) to see cube faces
    recs = [trace_event_to_record(e) for e in (events_all[0] or [])]
    print(f"  [{label}] hit records (ray 0):")
    for r in recs:
        p = np.asarray(r.get("point_world"), dtype=float)
        print(f"    surf={r.get('surface_id')} z={p[2]:.3f} "
              f"type={r.get('event_type','')!s:12} trans={r.get('media_transition','')!s:8} "
              f"in[{r.get('inside_volumes_before','')}|{r.get('inside_volumes_after','')}]")


def _bs_cube_stl() -> str:
    """A BK7 cube WITH a real 45deg diagonal face (normal in the y-z plane),
    so the ray hits it and the 'Beam Splitter' face fires the split. Built by
    slicing a box on y+z=0 and capping (gives the diagonal cap face)."""
    out = Path("attachment/repro_0093")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"bs_cube_{int(CUBE_MM)}mm.stl"
    if not path.exists():
        h = CUBE_MM / 2.0
        # two right-triangular prisms cemented on the 45deg plane y+z=0.
        V = np.array([
            [-h, -h, -h], [h, -h, -h],   # 0 a0, 1 a1
            [-h, -h,  h], [h, -h,  h],   # 2 d0, 3 d1  (y=-h,z=+h, on plane)
            [-h,  h, -h], [h,  h, -h],   # 4 e0, 5 e1  (y=+h,z=-h, on plane)
            [-h,  h,  h], [h,  h,  h],   # 6 b0, 7 b1
        ], dtype=float)
        F = [
            (0, 2, 4), (1, 3, 5),                       # A caps x=-+h
            (0, 2, 3), (0, 3, 1),                       # A y=-h
            (0, 4, 5), (0, 5, 1),                       # A z=-h
            (2, 4, 5), (2, 5, 3),                       # A diagonal (y+z=0)
            (6, 2, 4), (7, 3, 5),                       # B caps x=-+h
            (6, 2, 3), (6, 3, 7),                       # B z=+h
            (6, 4, 5), (6, 5, 7),                       # B y=+h
            (2, 5, 4), (2, 3, 5),                       # B diagonal (doubled, cemented)
        ]
        mesh = trimesh.Trimesh(vertices=V, faces=np.asarray(F), process=False)
        mesh.export(str(path))
    return str(path)


def _bs_cube_row(stl_override=None):
    from KrakenOS.UI.layout_editor import (
        OPTICAL_SOLID_FACES_ADVANCED_ATTR, SurfaceRow,
        auto_assign_optical_solid_face_roles, cluster_optical_solid_planar_faces,
        normalize_optical_solid_face_metadata, optical_solid_face_record_from_candidate,
    )
    from KrakenOS.UI.optical_solid_metadata import OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_SPLITTER

    stl = stl_override or _bs_cube_stl()
    candidates = cluster_optical_solid_planar_faces(stl)
    records = [optical_solid_face_record_from_candidate(c) for c in candidates]
    records = auto_assign_optical_solid_face_roles(records)
    # Tag the 45deg diagonal cluster (normal ~ (0,+-1,+-1)/sqrt2) as Beam Splitter.
    print(f"  bs cube: {len(records)} face clusters")
    for rec in records:
        nrm = np.asarray(rec.get("normal", (0, 0, 0)), dtype=float)
        nrm = nrm / max(np.linalg.norm(nrm), 1e-9)
        is_diag = abs(nrm[0]) < 0.2 and abs(abs(nrm[1]) - 0.707) < 0.2 and abs(abs(nrm[2]) - 0.707) < 0.2
        rec["function"] = OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_SPLITTER if is_diag else "Transmit/Port"
        if is_diag:
            rec["split_ratio"] = 0.5
        print(f"    face {rec.get('face_id','?')} n=({nrm[0]:.2f},{nrm[1]:.2f},{nrm[2]:.2f}) -> {rec['function']}")
    metadata = normalize_optical_solid_face_metadata(
        {"source_stl": stl, "faces": records}, candidates, source_stl=stl)
    return SurfaceRow(
        surface="Solid 3D STL", name="BS cube", glass="BK7",
        diameter=CUBE_MM * 1.6, thickness=CUBE_MM,
        advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata, "Solid_3d_stl": stl},
    ), stl, metadata


def _experiment2_bs_cube(stl_override=None, label="synthetic"):
    from KrakenOS.UI.nonseq_output_ports import (
        attach_scene_boundary_face_index, attach_scene_optical_volume_index)
    from KrakenOS.UI.layout_editor import SurfaceRow

    print(f"\n=== EXPERIMENT: BK7 BEAM-SPLITTER cube (branching) [{label}] ===")
    bs_row, stl, metadata = _bs_cube_row(stl_override)

    obj = Kos.surf(); obj.Name = "Source ref"; obj.Diameter = 60.0; obj.Drawing = 0
    obj.Thickness = CUBE_CENTER_Z - CUBE_MM / 2.0
    cube = Kos.surf(); cube.Name = "BS cube"; cube.Solid_3d_stl = stl
    cube.Glass = "BK7"; cube.Diameter = CUBE_MM * 1.6; cube.Thickness = 200.0
    cube.OpticalSolidFaces = metadata   # enables the branching gate (SDT[j].OpticalSolidFaces)
    img = Kos.surf(); img.Name = "Detector"; img.Glass = "AIR"; img.Diameter = 120.0; img.Drawing = 1
    system = Kos.system([obj, cube, img], Kos.Setup())

    rows = [SurfaceRow(surface="Object", name="Source ref", diameter=60.0,
                       thickness=CUBE_CENTER_Z - CUBE_MM / 2.0),
            bs_row,
            SurfaceRow(surface="Image", name="Detector", glass="AIR", diameter=120.0)]
    attach_scene_boundary_face_index(system, rows)
    attach_scene_optical_volume_index(system, rows)
    system.energy_probability = 0
    system.NsLimit = 200

    rays = Kos.raykeeper(system)
    for o, d in _converging_dirs(8.0, 5, BARE_FOCUS_Z):
        system.NsTrace([float(o[0]), float(o[1]), 0.0],
                       [float(d[0]), float(d[1]), float(d[2])], WL)
        rays.push()

    def _dedup(pts):
        out = []
        for p in pts:
            if not out or np.linalg.norm(p - out[-1]) > 1e-6:
                out.append(p)
        return out

    # group branch entries by exit direction
    groups = {}
    events_all = getattr(rays, "TRACE_EVENTS", [])
    print(f"  pushed {len(events_all)} branch entries from 25 rays")
    first_poly = {}
    for ev_list in events_all:
        recs = [trace_event_to_record(e) for e in (ev_list or [])]
        pts = _dedup([np.asarray(r.get("point_world"), dtype=float) for r in recs
                      if np.all(np.isfinite(np.asarray(r.get("point_world"), dtype=float)))])
        if len(pts) < 2:
            continue
        exitd = pts[-1] - pts[-2]; exitd = exitd / max(np.linalg.norm(exitd), 1e-9)
        if abs(exitd[2]) > 0.8:
            key = "transmit(+z)"
        elif abs(exitd[1]) > 0.5:
            key = "reflect(+-y)"
        else:
            key = f"other({exitd.round(2)})"
        g = groups.setdefault(key, {"o": [], "d": [], "trans": None})
        g["o"].append(pts[-2]); g["d"].append(exitd)
        if g["trans"] is None:
            g["trans"] = [(int(r.get("surface_id", -1)), str(r.get("media_transition", "")),
                           str(r.get("event_type", ""))) for r in recs]
            first_poly[key] = [p.round(2).tolist() for p in pts]
    for key, g in groups.items():
        print(f"  polyline[{key}]: {first_poly.get(key)}")
    for key, g in groups.items():
        o = np.asarray(g["o"]); d = np.asarray(g["d"])
        foc = _closest_approach(o, d) if len(o) >= 2 else np.full(3, np.nan)
        dist = float(np.linalg.norm(foc - np.array([0, 0, CUBE_CENTER_Z])))
        print(f"  {key}: {len(o)} rays, focus={foc.round(2)}  (|from cube center|={dist:.1f} mm)")
        print(f"    media seq: {g['trans']}")
    print(f"  [ref] bare focus z={BARE_FOCUS_Z}; flat-cube focus ~z=213.7; "
          f"transmit SHOULD be ~z>=214 (further). Closer => 0093 reproduced.")


def main():
    print(f"Cube {CUBE_MM}mm BK7 centered z={CUBE_CENTER_Z}; bare cone focus z={BARE_FOCUS_Z}")
    expected_shift = CUBE_MM * (1.0 - 1.0 / N_BK7)
    print(f"Expected plane-parallel-plate focus shift = +{expected_shift:.2f} mm "
          f"-> with-cube focus ~z={BARE_FOCUS_Z + expected_shift:.2f}\n")

    sys0, rays0 = _trace(with_cube=False)
    o0, d0 = _exit_rays(rays0)
    f0 = _closest_approach(o0, d0) if len(o0) >= 2 else np.full(3, np.nan)
    print(f"NO cube : {len(o0)} exit rays, converge z={f0[2]:.3f}")
    _dump_chief(rays0, "no-cube")

    sysC, raysC = _trace(with_cube=True)
    oC, dC = _exit_rays(raysC)
    fC = _closest_approach(oC, dC) if len(oC) >= 2 else np.full(3, np.nan)
    print(f"\nWITH cube: {len(oC)} exit rays, converge z={fC[2]:.3f}")
    _dump_chief(raysC, "with-cube")

    print(f"\n=> flat cube shifted focus to z={fC[2]:.3f} vs bare z={BARE_FOCUS_Z} "
          f"= {fC[2]-BARE_FOCUS_Z:+.3f} mm (expected ~+{expected_shift:.2f}); "
          f"{'FURTHER (correct)' if fC[2] > BARE_FOCUS_Z else 'CLOSER (bug)'}")

    _experiment2_bs_cube()
    # EXPERIMENT 3: the REAL promoted STEP beam-splitter cube (32704), y-z diagonal
    real = "attachment/cad_cache/promoted_step_overlays/optical_d647708c38ec4cd3.stl"
    if Path(real).exists():
        _experiment2_bs_cube(stl_override=real, label="REAL step_32704 cube")


if __name__ == "__main__":
    raise SystemExit(main())
