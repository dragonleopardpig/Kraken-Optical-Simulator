#!/usr/bin/env python3
"""Headless profiler for the non-sequential (NsTraceLoop) mesh-trace cost that
makes a promoted-STL beam-splitter refresh take minutes (see
reference_open3d_perf_profiling). Display-free: traces a converging cone through
a BK7 cube STL with KrakenOS directly and reads the built-in mesh-trace stats
(MeshRayTrace.reset_mesh_trace_stats / mesh_trace_stats_snapshot).

Two studies:
  A. CELL-COUNT SWEEP -- how wall time, intersections/ray, the mesh-trace
     fraction of wall, and per-intersection ms grow with the STL tessellation.
  B. DECIMATION PROTOTYPE (lever #1) -- trace a FINE cube vs a DECIMATED proxy
     of the same cube; report the speed-up AND the transmit-focus error (the
     proxy must land the rays in the same place). A planar cube decimates
     losslessly, so this is the best case for the lever; the focus delta
     quantifies the fidelity cost on geometry that is genuinely flat.

Run: .devenv/state/venv/bin/python tools/perf_ns_mesh_trace.py
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import trimesh

import KrakenOS as Kos
from KrakenOS.MeshRayTrace import mesh_trace_stats_snapshot, reset_mesh_trace_stats
from KrakenOS.TraceEvents import trace_event_to_record

CUBE_MM = 40.0
CUBE_CENTER_Z = 100.0
BARE_FOCUS_Z = 200.0
WL = 0.55
OUT = Path("attachment/perf_ns_trace")


def _cube_stl(subdiv: int) -> tuple[str, int]:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"cube_{int(CUBE_MM)}_sub{subdiv}.stl"
    box = trimesh.creation.box(extents=(CUBE_MM, CUBE_MM, CUBE_MM))
    for _ in range(subdiv):
        box = box.subdivide()
    box.export(str(path))
    return str(path), len(box.faces)


def _decimated_stl(src_path: str, target_faces: int) -> tuple[str, int]:
    """Decimate an STL to ~target_faces (PyVista quadric decimation, in-process)
    and write a proxy next to it."""
    import pyvista as pv

    mesh = pv.read(src_path).triangulate()
    n = int(mesh.n_cells)
    if n > target_faces:
        reduction = max(0.0, min(0.999, 1.0 - target_faces / float(n)))
        mesh = mesh.decimate(reduction)
    out = OUT / (Path(src_path).stem + f"_dec{target_faces}.stl")
    mesh.extract_surface().triangulate().save(str(out))
    return str(out), int(pv.read(str(out)).n_cells)


def _converging_cone(radius: float, n: int):
    coords = np.linspace(-radius, radius, n)
    rays = []
    for x0 in coords:
        for y0 in coords:
            o = np.array([x0, y0, 0.0])
            d = np.array([0.0, 0.0, BARE_FOCUS_Z]) - o
            rays.append((o, d / np.linalg.norm(d)))
    return rays


def _build_system(stl_path: str):
    obj = Kos.surf()
    obj.Name = "src"
    obj.Thickness = CUBE_CENTER_Z - CUBE_MM / 2.0
    obj.Diameter = 60.0
    obj.Drawing = 0
    cube = Kos.surf()
    cube.Name = "cube"
    cube.Solid_3d_stl = stl_path
    cube.Glass = "BK7"
    cube.Diameter = CUBE_MM * 1.6
    cube.Thickness = 200.0  # long gap to the detector
    img = Kos.surf()
    img.Name = "det"
    img.Glass = "AIR"
    img.Diameter = 80.0
    img.Thickness = 0.0
    img.Drawing = 1
    system = Kos.system([obj, cube, img], Kos.Setup())
    system.energy_probability = 0
    return system


def _closest_approach(origins: np.ndarray, dirs: np.ndarray) -> np.ndarray:
    M = np.zeros((3, 3))
    b = np.zeros(3)
    eye = np.eye(3)
    for o, d in zip(origins, dirs):
        d = d / np.linalg.norm(d)
        proj = eye - np.outer(d, d)
        M += proj
        b += proj @ o
    return np.linalg.solve(M, b)


def _exit_focus(rays_keeper) -> np.ndarray | None:
    origins, dirs = [], []
    for ev_list in getattr(rays_keeper, "TRACE_EVENTS", []) or []:
        recs = [trace_event_to_record(e) for e in (ev_list or [])]
        pts = [
            np.asarray(r.get("point_world"), dtype=float)
            for r in recs
            if np.all(np.isfinite(np.asarray(r.get("point_world"), dtype=float)))
        ]
        if len(pts) < 2:
            continue
        o = pts[-2]
        d = pts[-1] - pts[-2]
        if np.linalg.norm(d) < 1e-9:
            continue
        origins.append(o)
        dirs.append(d / np.linalg.norm(d))
    if len(origins) < 2:
        return None
    return _closest_approach(np.asarray(origins), np.asarray(dirs))


def _trace_and_measure(stl_path: str, cone):
    system = _build_system(stl_path)
    keeper = Kos.raykeeper(system)
    reset_mesh_trace_stats(active=True)
    t = time.perf_counter()
    for o, d in cone:
        system.NsTrace([float(o[0]), float(o[1]), 0.0],
                       [float(d[0]), float(d[1]), float(d[2])], WL)
        keeper.push()
    wall_ms = (time.perf_counter() - t) * 1000.0
    snap = mesh_trace_stats_snapshot(reset=True)
    focus = _exit_focus(keeper)
    return wall_ms, snap, focus


def main() -> int:
    cone = _converging_cone(8.0, 11)  # 121 rays
    nrays = len(cone)
    print(f"converging cone: {nrays} rays, bare focus z={BARE_FOCUS_Z}\n")

    print("== A. CELL-COUNT SWEEP ==")
    print(f"{'cells':>8} {'wall ms':>9} {'ms/ray':>8} {'isect/ray':>10} "
          f"{'mesh%wall':>9} {'ms/isect':>9} {'focus z':>9}")
    fine_path = None
    for subdiv in (0, 2, 4, 5, 6):
        stl, ncells = _cube_stl(subdiv)
        wall, snap, focus = _trace_and_measure(stl, cone)
        calls = snap["mesh_ray_call_count"]
        mesh_ms = snap["mesh_ray_total_ms"]
        fz = f"{focus[2]:.2f}" if focus is not None else "n/a"
        print(f"{ncells:>8} {wall:>9.1f} {wall/nrays:>8.2f} {calls/nrays:>10.1f} "
              f"{100*mesh_ms/wall:>8.0f}% {mesh_ms/max(calls,1):>9.3f} {fz:>9}")
        if subdiv == 6:
            fine_path = stl

    print("\n== B. DECIMATION PROTOTYPE (lever #1) ==")
    wall_f, snap_f, focus_f = _trace_and_measure(fine_path, cone)
    nf = trimesh.load(fine_path, process=False)
    print(f"FINE   cells={len(nf.faces):>7}  wall={wall_f:8.1f} ms  "
          f"mesh={snap_f['mesh_ray_total_ms']:7.1f} ms  focus_z={focus_f[2]:.3f}")
    for target in (1200, 192, 24):
        dec_path, dcells = _decimated_stl(fine_path, target)
        wall_d, snap_d, focus_d = _trace_and_measure(dec_path, cone)
        derr = float(np.linalg.norm(focus_d - focus_f)) if (focus_d is not None and focus_f is not None) else float("nan")
        print(f"DECIM  cells={dcells:>7}  wall={wall_d:8.1f} ms  "
              f"mesh={snap_d['mesh_ray_total_ms']:7.1f} ms  focus_z={focus_d[2]:.3f}  "
              f"|Δfocus|={derr:.4f} mm  speedup={wall_f/max(wall_d,1e-6):.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
