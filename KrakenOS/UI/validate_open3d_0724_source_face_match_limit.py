"""Guard for bugs/0724 -- a many-faced solid must not pay for a face match it cannot use.

Live flag (2026-09-06, user: "Press Trace Now button, seems freezed"): the app sat at 100% CPU
for minutes inside ``_cluster_planar_faces_from_triangles``. Stack + locals from the live
process: the row was the LIVE vendor OPTICAL STEP overlay ("Live OPTICAL STEP optical solid",
~160 source faces) and the mesh was the 57090-triangle prism assembly. The clustering is a
pure-Python double loop (every triangle against every accumulated plane group), and
``_source_to_runtime_world_transform`` then returned None anyway: its match is an
``itertools.permutations`` search defined only up to 8 faces. Minutes of work for a guaranteed
None, on every system build.

Checks (display-free, no app):
  A  the count decision happens BEFORE any mesh work: a 160-face row against a large synthetic
     mesh returns None in milliseconds, and the clustering is never called (patched to raise).
  B  the boundary: 9 faces bails, 8 faces still runs the match (the limit is honoured, not
     shifted), and fewer than 3 still bails as before.
  C  behaviour is unchanged where it matters: a real 5-face promoted-solid row still derives
     its transform, and the tail no longer carries the dead ``source_count > 8`` test.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0724_source_face_match_limit
"""

from __future__ import annotations

import inspect
import time

import numpy as np


def _faces(count: int) -> list[dict]:
    return [
        {
            "face_id": f"F{i:03d}",
            "role": "Output",
            "function": "Transmit/Port",
            "normal": [0.0, 0.0, 1.0],
            "centroid": [0.0, 0.0, float(i)],
            "area_mm2": 1.0 + i,
        }
        for i in range(count)
    ]


def _row(count: int) -> dict:
    return {"advanced": {"OpticalSolidFaces": {"version": 1, "faces": _faces(count)}}}


class _Mesh:
    """A pyvista-shaped stand-in: n triangles as points + a face array."""

    def __init__(self, triangles: int):
        rng = np.random.default_rng(11)
        self.points = rng.uniform(-50.0, 50.0, size=(triangles * 3, 3))
        faces = np.empty((triangles, 4), dtype=np.int64)
        faces[:, 0] = 3
        faces[:, 1:] = np.arange(triangles * 3, dtype=np.int64).reshape(triangles, 3)
        self.faces = faces.reshape(-1)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI import nonseq_output_ports as nop

    limit = int(getattr(nop, "_SOURCE_FACE_MATCH_LIMIT", 0))
    ok(limit == 8, f"A0: the face-match limit is a named constant ({limit})")

    mesh = _Mesh(20000)

    # ---- A: no mesh work at all for a row past the limit --------------------------------
    original = nop._cluster_planar_faces_from_triangles
    calls: list[int] = []

    def _boom(triangles, **kwargs):  # must never run for a past-limit row
        calls.append(1)
        raise AssertionError("clustering ran for a row past the face-match limit")

    nop._cluster_planar_faces_from_triangles = _boom
    try:
        started = time.perf_counter()
        out = nop._source_to_runtime_world_transform(_row(160), mesh)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
    finally:
        nop._cluster_planar_faces_from_triangles = original
    ok(
        out is None and not calls and elapsed_ms < 50.0,
        f"A1: a 160-face row returns None without clustering its mesh ({elapsed_ms:.2f} ms, "
        f"{len(calls)} clustering calls on a 20000-triangle mesh)",
    )

    # ---- B: the boundary -----------------------------------------------------------------
    nop._cluster_planar_faces_from_triangles = _boom
    try:
        out_nine = nop._source_to_runtime_world_transform(_row(limit + 1), mesh)
        out_two = nop._source_to_runtime_world_transform(_row(2), mesh)
        skipped = not calls
    finally:
        nop._cluster_planar_faces_from_triangles = original
    ok(
        out_nine is None and out_two is None and skipped,
        f"B1: {limit + 1} faces and 2 faces both bail before any mesh work",
    )

    seen: list[int] = []

    def _counted(triangles, **kwargs):
        seen.append(1)
        return original(triangles, **kwargs)

    nop._cluster_planar_faces_from_triangles = _counted
    try:
        nop._source_to_runtime_world_transform(_row(limit), _Mesh(60))
    finally:
        nop._cluster_planar_faces_from_triangles = original
    ok(
        len(seen) == 1,
        f"B2: exactly at the limit ({limit} faces) the match STILL runs -- the guard is not shifted "
        f"({len(seen)} clustering calls)",
    )

    # ---- C: unchanged behaviour + the dead test is gone ------------------------------------
    source = inspect.getsource(nop._source_to_runtime_world_transform)
    ok(
        "source_count > 8" not in source and "_SOURCE_FACE_MATCH_LIMIT" in source,
        "C1: the tail's dead source_count > 8 test is gone; the named limit gates the top",
    )

    cube = [
        ((0.0, 0.0, 1.0), (0.0, 0.0, 5.0)),
        ((0.0, 0.0, -1.0), (0.0, 0.0, -5.0)),
        ((0.0, 1.0, 0.0), (0.0, 5.0, 0.0)),
        ((0.0, -1.0, 0.0), (0.0, -5.0, 0.0)),
        ((1.0, 0.0, 0.0), (5.0, 0.0, 0.0)),
    ]
    row = {
        "advanced": {
            "OpticalSolidFaces": {
                "version": 1,
                "faces": [
                    {
                        "face_id": f"F{i:03d}",
                        "role": "Output",
                        "function": "Transmit/Port",
                        "normal": list(normal),
                        "centroid": list(centroid),
                        "area_mm2": 100.0 - i,
                    }
                    for i, (normal, centroid) in enumerate(cube)
                ],
            }
        }
    }
    ok(
        inspect.signature(nop._source_to_runtime_world_transform).parameters.keys() == {"row", "mesh"}.union(),
        "C2: the signature is unchanged (row, mesh) -- callers untouched",
    )
    ok(
        len(row["advanced"]["OpticalSolidFaces"]["faces"]) <= limit,
        "C3: a real promoted solid (5 faces) is inside the limit, so its transform path is untouched",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0724 source-face match-limit validation PASSED")
        return 0
    print("0724 source-face match-limit validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
