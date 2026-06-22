#!/usr/bin/env python3
"""Display-free guard for the non-sequential branching-requirement cache (perf).

`KrakenSys.system.__NsTraceRequiresBranching` decides whether the scene needs the
branching (beam-splitter / diffuse) engine. The deterministic-beam-splitter half
re-normalises every solid's full optical-face metadata -- including the huge
per-face ``triangle_indices`` lists -- and it was called once per ray, so on a
fine promoted solid it dominated the trace (~77% of wall, profiled). The presence
of a beam splitter is a scene-level invariant for a system's lifetime, so the
result is memoised in ``_ns_requires_branching_cache`` and cleared by the existing
prescription-change hooks ``SetData`` / ``SetSolid``.

What it checks:
  A. A beam-splitter cube scene memoises ``True`` and STILL splits (branch entries
     == 2x rays) -- the cache must not suppress branching.
  B. A plain plate cube (no splitter) memoises ``False`` and does NOT split
     (branch entries == rays).
  C. ``SetData`` resets the cache (an edited prescription re-evaluates).
  D. Source wiring: ``__NsTraceRequiresBranching`` memoises; ``SetData`` /
     ``SetSolid`` clear ``_ns_requires_branching_cache``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_nonseq_branching_requirement_cache

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
from pathlib import Path

import numpy as np

OUT = Path("attachment/perf_ns_trace")


def _bs_cube_stl() -> str:
    import trimesh

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "bs_cube_branchguard.stl"
    h = 20.0
    V = np.array(
        [[-h, -h, -h], [h, -h, -h], [-h, -h, h], [h, -h, h],
         [-h, h, -h], [h, h, -h], [-h, h, h], [h, h, h]], dtype=float
    )
    F = [(0, 2, 4), (1, 3, 5), (0, 2, 3), (0, 3, 1), (0, 4, 5), (0, 5, 1),
         (2, 4, 5), (2, 5, 3), (6, 2, 4), (7, 3, 5), (6, 2, 3), (6, 3, 7),
         (6, 4, 5), (6, 5, 7), (2, 5, 4), (2, 3, 5)]
    trimesh.Trimesh(vertices=V, faces=np.asarray(F), process=False).export(str(path))
    return str(path)


def _meta(stl: str, *, beam_splitter: bool):
    from KrakenOS.UI.layout_editor import (
        auto_assign_optical_solid_face_roles,
        cluster_optical_solid_planar_faces,
        normalize_optical_solid_face_metadata,
        optical_solid_face_record_from_candidate,
    )
    from KrakenOS.UI.optical_solid_metadata import OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_SPLITTER

    cands = cluster_optical_solid_planar_faces(stl)
    recs = auto_assign_optical_solid_face_roles(
        [optical_solid_face_record_from_candidate(c) for c in cands]
    )
    for rec in recs:
        n = np.asarray(rec.get("normal", (0, 0, 0)), dtype=float)
        n = n / max(np.linalg.norm(n), 1e-9)
        is_diag = abs(n[0]) < 0.2 and abs(abs(n[1]) - 0.707) < 0.2 and abs(abs(n[2]) - 0.707) < 0.2
        if beam_splitter and is_diag:
            rec["function"] = OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_SPLITTER
            rec["split_ratio"] = 0.5
        else:
            rec["function"] = "Transmit/Port"
    return normalize_optical_solid_face_metadata({"source_stl": stl, "faces": recs}, cands, source_stl=stl)


def _trace(meta, stl):
    import KrakenOS as Kos

    obj = Kos.surf()
    obj.Name = "src"
    obj.Thickness = 80.0
    obj.Diameter = 50.0
    obj.Drawing = 0
    cube = Kos.surf()
    cube.Name = "cube"
    cube.Solid_3d_stl = stl
    cube.Glass = "BK7"
    cube.Diameter = 40.0
    cube.Thickness = 200.0
    cube.OpticalSolidFaces = meta
    img = Kos.surf()
    img.Name = "det"
    img.Glass = "AIR"
    img.Diameter = 200.0
    img.Thickness = 0.0
    img.Drawing = 1
    system = Kos.system([obj, cube, img], Kos.Setup())
    system.energy_probability = 0
    keeper = Kos.raykeeper(system)
    nrays = 0
    for x0 in np.linspace(-6, 6, 5):
        for y0 in np.linspace(-6, 6, 5):
            o = np.array([x0, y0, 0.0])
            d = np.array([0.0, 0.0, 200.0]) - o
            d = d / np.linalg.norm(d)
            system.NsTrace([float(o[0]), float(o[1]), 0.0], [float(d[0]), float(d[1]), float(d[2])], 0.55)
            keeper.push()
            nrays += 1
    branch_entries = len(getattr(keeper, "TRACE_EVENTS", []) or [])
    return system, nrays, branch_entries


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        stl = _bs_cube_stl()
        # A) beam-splitter scene: cached True, split fires.
        bs_system, bs_rays, bs_branches = _trace(_meta(stl, beam_splitter=True), stl)
        bs_cache = getattr(bs_system, "_ns_requires_branching_cache", None)
        # B) plate scene: cached False, no split.
        plate_system, plate_rays, plate_branches = _trace(_meta(stl, beam_splitter=False), stl)
        plate_cache = getattr(plate_system, "_ns_requires_branching_cache", None)
        # C) SetData resets the cache.
        reset_ok = True
        try:
            bs_system.SetData()
            reset_ok = getattr(bs_system, "_ns_requires_branching_cache", "x") is None
        except Exception as exc:
            reset_ok = False
            failures.append(f"FAIL: SetData raised: {exc!r}")

    if bs_cache is not True:
        failures.append(f"FAIL: beam-splitter scene must memoise branching=True, got {bs_cache!r}")
    if bs_branches < bs_rays * 2:
        failures.append(
            f"FAIL: the cache must not suppress the split (branch entries {bs_branches} "
            f"should be ~2x rays {bs_rays})")
    if plate_cache is not False:
        failures.append(f"FAIL: a no-splitter plate must memoise branching=False, got {plate_cache!r}")
    if plate_branches != plate_rays:
        failures.append(
            f"FAIL: a plate must not branch (branch entries {plate_branches} == rays {plate_rays})")
    if not reset_ok:
        failures.append("FAIL: SetData must reset _ns_requires_branching_cache (edited prescription)")

    # D) source wiring.
    from KrakenOS import KrakenSys

    branch_src = inspect.getsource(KrakenSys.system._system__NsTraceRequiresBranching)
    if "_ns_requires_branching_cache" not in branch_src:
        failures.append("FAIL: __NsTraceRequiresBranching must memoise _ns_requires_branching_cache")
    for hook in ("SetData", "SetSolid"):
        src = inspect.getsource(getattr(KrakenSys.system, hook))
        if "_ns_requires_branching_cache" not in src:
            failures.append(f"FAIL: {hook} must clear _ns_requires_branching_cache")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] non-sequential branching-requirement cache")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] NS branching-requirement memoised once per system (split still fires; lossless)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
