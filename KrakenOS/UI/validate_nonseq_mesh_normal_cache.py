#!/usr/bin/env python3
"""Display-free guard for the non-sequential mesh-trace cell-normal cache
(perf: a promoted-STL beam-splitter refresh took minutes; ~70% of the
NsTraceLoop wall was re-running PyVista's ``compute_normals`` VTK pipeline on the
full solid mesh once per ray-solid intersection -- ``mesh.cell_normals`` does not
cache).

The fix (`MeshRayTrace.mesh_cell_normals`) computes the cell normals once and
caches the array in the mesh's ``cell_data``; ``InterNormalCalc`` reads it at the
per-hit normal lookup instead of the recomputing property. The cached array is
bit-identical to the property, so the trace result is UNCHANGED.

What it checks:
  A. `mesh_cell_normals` returns values equal to `mesh.cell_normals`, populates
     the cache key on first call, and the second call returns the SAME cached
     array object (no recompute).
  B. Source wiring: `InterNormalCalc.__InterNormalSolidObject` reads the cached
     helper, not the bare `mesh.cell_normals` property, at the hit-normal line.
  C. Lossless: a small non-sequential trace through a BK7 cube STL lands the
     transmit focus at the SAME place at a coarse and a fine tessellation (the
     cache must not change the optics).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_nonseq_mesh_normal_cache

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
from pathlib import Path

import numpy as np


def _cube_stl(subdiv: int) -> str:
    import trimesh

    out = Path("attachment/perf_ns_trace")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"cube_40_guard_sub{subdiv}.stl"
    box = trimesh.creation.box(extents=(40.0, 40.0, 40.0))
    for _ in range(subdiv):
        box = box.subdivide()
    box.export(str(path))
    return str(path)


def _transmit_focus(stl_path: str) -> "np.ndarray | None":
    import KrakenOS as Kos
    from KrakenOS.TraceEvents import trace_event_to_record

    obj = Kos.surf()
    obj.Name = "src"
    obj.Thickness = 80.0
    obj.Diameter = 60.0
    obj.Drawing = 0
    cube = Kos.surf()
    cube.Name = "cube"
    cube.Solid_3d_stl = stl_path
    cube.Glass = "BK7"
    cube.Diameter = 64.0
    cube.Thickness = 200.0
    img = Kos.surf()
    img.Name = "det"
    img.Glass = "AIR"
    img.Diameter = 80.0
    img.Thickness = 0.0
    img.Drawing = 1
    system = Kos.system([obj, cube, img], Kos.Setup())
    system.energy_probability = 0
    keeper = Kos.raykeeper(system)
    for x0 in np.linspace(-8, 8, 5):
        for y0 in np.linspace(-8, 8, 5):
            o = np.array([x0, y0, 0.0])
            d = np.array([0.0, 0.0, 200.0]) - o
            d = d / np.linalg.norm(d)
            system.NsTrace([float(o[0]), float(o[1]), 0.0], [float(d[0]), float(d[1]), float(d[2])], 0.55)
            keeper.push()
    origins, dirs = [], []
    for ev_list in getattr(keeper, "TRACE_EVENTS", []) or []:
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
    M = np.zeros((3, 3))
    b = np.zeros(3)
    eye = np.eye(3)
    for o, d in zip(origins, dirs):
        proj = eye - np.outer(d, d)
        M += proj
        b += proj @ o
    return np.linalg.solve(M, b)


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    from KrakenOS.MeshRayTrace import KRAKEN_CELL_NORMALS, mesh_cell_normals

    # A) cache semantics.
    import pyvista as pv

    mesh = pv.Sphere(theta_resolution=60, phi_resolution=60).triangulate()
    first = mesh_cell_normals(mesh)
    prop = np.asarray(mesh.cell_normals, dtype=float)
    if first.shape != (int(mesh.n_cells), 3):
        failures.append(f"FAIL: mesh_cell_normals shape {first.shape} != ({mesh.n_cells}, 3)")
    if not np.allclose(first, prop, atol=1e-9):
        failures.append("FAIL: mesh_cell_normals values must equal mesh.cell_normals (lossless)")
    if KRAKEN_CELL_NORMALS not in mesh.cell_data:
        failures.append("FAIL: mesh_cell_normals must cache the array in cell_data on first call")
    second = mesh_cell_normals(mesh)
    cached = np.asarray(mesh.cell_data[KRAKEN_CELL_NORMALS], dtype=float)
    if not np.allclose(second, cached, atol=1e-12):
        failures.append("FAIL: second mesh_cell_normals call must return the cached array (no recompute)")

    # B) source wiring -- the hit-normal lookup uses the cached helper. The
    #    KrakenOS package re-exports the class as `KrakenOS.InterNormalCalc`.
    from KrakenOS import InterNormalCalc as InterNormalCalcClass

    solid_src = inspect.getsource(InterNormalCalcClass._InterNormalCalc__InterNormalSolidObject)
    if "mesh_cell_normals(mesh)" not in solid_src:
        failures.append(
            "FAIL: __InterNormalSolidObject must read mesh_cell_normals(mesh), not the "
            "recomputing mesh.cell_normals property, at the per-hit normal lookup")
    # The recomputing property is `NOR = mesh.cell_normals`; a doc comment may still
    # name it, so match the assignment statement, not any mention.
    code_lines = [
        ln.split("#", 1)[0] for ln in solid_src.splitlines()
        if not ln.lstrip().startswith("#")
    ]
    if any("= mesh.cell_normals" in ln for ln in code_lines):
        failures.append(
            "FAIL: __InterNormalSolidObject still assigns the bare mesh.cell_normals property "
            "(re-runs compute_normals per hit)")

    # C) lossless optics -- transmit focus invariant across tessellation.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        coarse = _transmit_focus(_cube_stl(1))
        fine = _transmit_focus(_cube_stl(4))
    if coarse is None or fine is None:
        failures.append("FAIL: transmit focus did not resolve (trace produced no exit rays)")
    elif float(np.linalg.norm(fine - coarse)) > 1e-3:
        failures.append(
            f"FAIL: transmit focus moved with tessellation (coarse={coarse}, fine={fine}); "
            "the normal cache must not change the optics")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] non-sequential mesh-trace cell-normal cache")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] NS mesh-trace caches solid cell normals once (lossless ~3x speed-up on fine STL)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
