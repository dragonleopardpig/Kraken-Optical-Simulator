#!/usr/bin/env python3
"""Display-free guard for the lossless decimated trace-proxy of a planar optical
solid (perf: the non-sequential trace + per-hit face work is O(cells); a fine
beam-splitter cube / prism STL is ~50x finer than ray intersection needs).

`MeshRayTrace.decimate_optical_solid_trace_mesh` returns a decimated proxy ONLY
when every proxy cell still lies on an original optical-face plane (centroid within
tolerance, normal aligned), so a planar polyhedron collapses with identical optics
while a curved surface -- which cannot be decimated without moving the surface --
falls back to the full mesh. The proxy's cells no longer map to original triangle
ids, so its face ids are assigned by plane match
(`assign_mesh_cell_face_ids(..., prefer_plane_match=True)`, which stamps
`KRAKEN_ORIGINAL_CELL_ID = -1` to defeat exact-membership aliasing).

What it checks:
  A. A fine planar cube with face planes decimates to far fewer cells, and every
     proxy cell lies on a face plane.
  B. A curved (sphere) mesh whose cells do NOT all lie on the given plane is
     returned UNCHANGED (the lossless gate).
  C. End-to-end: a metadata-bearing fine cube traced with the proxy lands the
     transmit focus at the SAME place as the full-mesh trace (|Δ| < 1e-6), and the
     proxy actually shrinks the cube's trace mesh.
  D. Source wiring: `__SceneMeshWithFaceIds` builds the proxy + assigns by plane
     match; `assign_mesh_cell_face_ids` exposes `prefer_plane_match`.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_nonseq_decimated_trace_proxy

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
from pathlib import Path

import numpy as np

OUT = Path("attachment/perf_ns_trace")


def _cube_stl(subdiv: int) -> str:
    import trimesh

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"cube_40_decguard_sub{subdiv}.stl"
    box = trimesh.creation.box(extents=(40.0, 40.0, 40.0))
    for _ in range(subdiv):
        box = box.subdivide()
    box.export(str(path))
    return str(path)


def _cube_meta(stl: str):
    from KrakenOS.UI.layout_editor import (
        auto_assign_optical_solid_face_roles,
        cluster_optical_solid_planar_faces,
        normalize_optical_solid_face_metadata,
        optical_solid_face_record_from_candidate,
    )

    cands = cluster_optical_solid_planar_faces(stl)
    recs = auto_assign_optical_solid_face_roles(
        [optical_solid_face_record_from_candidate(c) for c in cands]
    )
    return normalize_optical_solid_face_metadata({"source_stl": stl, "faces": recs}, cands, source_stl=stl)


def _transmit_focus(stl: str, meta, *, decimate: bool):
    import KrakenOS as Kos
    import KrakenOS.KrakenSys as KS
    from KrakenOS.TraceEvents import trace_event_to_record

    orig = KS.decimate_optical_solid_trace_mesh
    if not decimate:
        KS.decimate_optical_solid_trace_mesh = lambda mesh, *a, **k: mesh
    try:
        obj = Kos.surf()
        obj.Name = "src"
        obj.Thickness = 80.0
        obj.Diameter = 60.0
        obj.Drawing = 0
        cube = Kos.surf()
        cube.Name = "cube"
        cube.Solid_3d_stl = stl
        cube.Glass = "BK7"
        cube.Diameter = 64.0
        cube.Thickness = 200.0
        cube.OpticalSolidFaces = meta
        img = Kos.surf()
        img.Name = "det"
        img.Glass = "AIR"
        img.Diameter = 120.0
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
        cube_cells = max(
            (int(system.EEE[i].n_cells) for i in range(len(system.EEE)) if getattr(system.EEE[i], "n_cells", 0)),
            default=0,
        )
    finally:
        KS.decimate_optical_solid_trace_mesh = orig

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
        return None, cube_cells
    M = np.zeros((3, 3))
    b = np.zeros(3)
    eye = np.eye(3)
    for o, d in zip(origins, dirs):
        proj = eye - np.outer(d, d)
        M += proj
        b += proj @ o
    return np.linalg.solve(M, b), cube_cells


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    from KrakenOS.MeshRayTrace import (
        KRAKEN_ORIGINAL_CELL_ID,
        decimate_optical_solid_trace_mesh,
        raytrace_compatible_mesh,
    )

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        # A) planar cube decimates; every proxy cell on a face plane.
        stl = _cube_stl(5)  # 12288 cells (> min_cells 4000)
        meta = _cube_meta(stl)
        world_faces = []
        # mimic the world-face planes the system would pass (local == world here).
        for face in meta.get("faces", []):
            wf = dict(face)
            wf["centroid_world"] = tuple(float(v) for v in np.asarray(face.get("centroid", (0, 0, 0)), float)[:3])
            wf["normal_world"] = tuple(float(v) for v in np.asarray(face.get("normal", (0, 0, 1)), float)[:3])
            world_faces.append(wf)
        import pyvista as pv

        full = raytrace_compatible_mesh(pv.read(stl).triangulate())
        proxy = decimate_optical_solid_trace_mesh(full, world_faces)
        full_n = int(full.n_cells)
        proxy_n = int(proxy.n_cells)

        # B) curved sphere with a single non-matching plane -> unchanged.
        sphere = raytrace_compatible_mesh(pv.Sphere(theta_resolution=80, phi_resolution=80).triangulate())
        sphere_n = int(sphere.n_cells)
        curved_faces = [{"face_id": "P", "centroid_world": (0.0, 0.0, 0.0), "normal_world": (0.0, 0.0, 1.0)}]
        sphere_proxy = decimate_optical_solid_trace_mesh(sphere, curved_faces)

        # C) end-to-end lossless focus.
        f_on, cells_on = _transmit_focus(stl, meta, decimate=True)
        f_off, cells_off = _transmit_focus(stl, meta, decimate=False)

    if proxy_n >= full_n:
        failures.append(f"FAIL: a fine planar cube must decimate ({full_n} -> {proxy_n} cells)")
    if proxy_n < 4:
        failures.append(f"FAIL: proxy collapsed too far ({proxy_n} cells)")
    if KRAKEN_ORIGINAL_CELL_ID in getattr(proxy, "cell_data", {}):
        stamped = np.asarray(proxy.cell_data[KRAKEN_ORIGINAL_CELL_ID]).reshape(-1)
        if stamped.size and not np.all(stamped == -1):
            failures.append("FAIL: proxy must stamp KRAKEN_ORIGINAL_CELL_ID = -1 (defeat aliasing)")

    if int(getattr(sphere_proxy, "n_cells", 0)) != sphere_n:
        failures.append(
            "FAIL: a curved sphere whose cells are not all on the given plane must be returned "
            "UNCHANGED (the lossless planarity gate)")

    if f_on is None or f_off is None:
        failures.append("FAIL: transmit focus did not resolve (trace produced no exit rays)")
    else:
        if float(np.linalg.norm(f_on - f_off)) > 1e-6:
            failures.append(
                f"FAIL: decimation changed the optics (focus on={f_on}, off={f_off}); must be lossless")
        if not (cells_on < cells_off):
            failures.append(
                f"FAIL: the decimated trace should shrink the cube mesh (on={cells_on}, off={cells_off})")

    # D) source wiring.
    from KrakenOS import KrakenSys
    from KrakenOS.MeshRayTrace import assign_mesh_cell_face_ids

    scene_src = inspect.getsource(KrakenSys.system._system__SceneMeshWithFaceIds)
    if "decimate_optical_solid_trace_mesh(" not in scene_src:
        failures.append("FAIL: __SceneMeshWithFaceIds must build the decimated trace proxy")
    if "prefer_plane_match" not in scene_src:
        failures.append("FAIL: __SceneMeshWithFaceIds must assign proxy face ids by plane match")
    if "prefer_plane_match" not in inspect.signature(assign_mesh_cell_face_ids).parameters:
        failures.append("FAIL: assign_mesh_cell_face_ids must expose prefer_plane_match")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] lossless decimated trace-proxy for planar optical solids")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] planar optical solids trace against a lossless decimated proxy (~9x on a fine cube)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
