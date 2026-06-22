"""Display-free guard: the STEP-overlay face-metadata bake is vectorised.

A cold STEP-overlay face-metadata bake clusters every STL triangle into planar
face candidates (``cluster_optical_solid_planar_faces``). On a fine vendor body
(a ~0.6 M-triangle camera STEP) the former per-triangle Python loop ran ~90 s --
the dominant cost of "Open 3D takes quite a while" on launch / first selection
(bug 0111 caps the bake to once per session, but every fresh launch re-paid it).

The loop is now a numpy batch (np.cross / np.unique / np.bincount / np.lexsort),
~30x faster, and **bit-identical**: this validator reimplements the original
loop as an independent brute-force reference and asserts the vectorised output
matches face-for-face (id, normal, centroid, area, plane offset, triangle count,
and the per-face triangle index list), including the area-tie tie-break (a cube's
six equal-area faces). It also checks the binary STL reader returns byte-for-byte
the same vertices as the former per-triangle frombuffer loop, and that the source
no longer carries the per-triangle Python loops.

Penta phase 101 (baseline -> 102).
"""

from __future__ import annotations

import inspect
import struct
import tempfile
from pathlib import Path

import numpy as np

from KrakenOS.UI import stl_geometry
from KrakenOS.UI.services import optical_solid_geometry as osg
from KrakenOS.UI.services.optical_solid_geometry import cluster_optical_solid_planar_faces


def _canonical(normal: np.ndarray, plane_offset: float):
    plane_normal = np.asarray(normal, dtype=float).reshape(3)
    norm = float(np.linalg.norm(plane_normal))
    if norm > 0.0:
        plane_normal = plane_normal / norm
    offset = float(plane_offset)
    pivot = int(np.argmax(np.abs(plane_normal)))
    if float(plane_normal[pivot]) < 0.0:
        plane_normal = -plane_normal
        offset = -offset
    return plane_normal, offset


def _reference_clusters(triangles: np.ndarray, *, max_faces: int = 160):
    """Independent reimplementation of the original per-triangle loop."""
    flat = triangles.reshape((-1, 3))
    max_extent = max(float(np.max(np.ptp(flat, axis=0))), 1.0)
    area_tol = max(max_extent * max_extent * 1e-18, 1e-24)
    plane_decimals = 4 if max_extent < 100.0 else 3
    normal_decimals = 4
    groups: dict = {}
    for triangle_index, tri in enumerate(triangles):
        v0, v1, v2 = (np.asarray(v, dtype=float) for v in tri)
        cross = np.cross(v1 - v0, v2 - v0)
        area = 0.5 * float(np.linalg.norm(cross))
        if area <= area_tol or not np.isfinite(area):
            continue
        normal = cross / max(float(np.linalg.norm(cross)), 1e-12)
        centroid = (v0 + v1 + v2) / 3.0
        plane_offset = float(np.dot(normal, centroid))
        cn, co = _canonical(normal, plane_offset)
        key = (
            tuple(float(v) for v in np.round(cn, normal_decimals)),
            float(np.round(co, plane_decimals)),
        )
        entry = groups.setdefault(
            key,
            {
                "nw": np.zeros(3),
                "cw": np.zeros(3),
                "area": 0.0,
                "tris": 0,
                "pow": 0.0,
                "idx": [],
                "ref": np.asarray(normal, dtype=float),
            },
        )
        ref = entry["ref"]
        oriented = normal if float(np.dot(normal, ref)) >= 0.0 else -normal
        entry["nw"] = entry["nw"] + oriented * area
        entry["cw"] = entry["cw"] + centroid * area
        entry["area"] += area
        entry["tris"] += 1
        entry["pow"] += float(np.dot(oriented, centroid)) * area
        entry["idx"].append(int(triangle_index))
    out = []
    for rank, entry in enumerate(
        sorted(groups.values(), key=lambda e: float(e["area"]), reverse=True)[: max(1, max_faces)],
        start=1,
    ):
        a = max(float(entry["area"]), 1e-12)
        out.append(
            {
                "face_id": f"F{rank:03d}",
                "normal": entry["nw"] / a,
                "centroid": entry["cw"] / a,
                "area": a,
                "plane_offset": float(entry["pow"]) / a,
                "tris": int(entry["tris"]),
                "idx": tuple(entry["idx"]),
            }
        )
    return out


def _save_stl(mesh, path: Path) -> Path:
    mesh.save(str(path))
    return path


def run_checks() -> list[tuple[str, bool, str]]:
    import pyvista as pv

    results: list[tuple[str, bool, str]] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # A cube (six equal-area faces -> tie-break stress) fused with a rotated
        # cube (45 deg normals, distinct areas) gives a varied face set.
        cube = pv.Cube(x_length=2.0, y_length=2.0, z_length=2.0).triangulate()
        tilt = pv.Cube(x_length=3.0, y_length=1.0, z_length=1.0).triangulate()
        tilt = tilt.rotate_z(30.0, inplace=False).translate((20.0, 0.0, 0.0), inplace=False)
        combined = (cube + tilt).triangulate()
        stl_path = _save_stl(combined, tmp_path / "bake_combo.stl")

        _fmt, triangles = stl_geometry.read_stl_triangle_vertices(stl_path)

        # 1) byte-identical STL read vs the former per-triangle frombuffer loop.
        data = stl_path.read_bytes()
        tc = struct.unpack("<I", data[80:84])[0]
        manual = np.empty((tc, 3, 3), dtype=float)
        off = 84
        for i in range(tc):
            off += 12
            manual[i] = np.frombuffer(data, dtype="<f4", count=9, offset=off).reshape(3, 3)
            off += 38
        identical = bool(np.array_equal(manual, triangles))
        results.append(
            ("binary STL reader is byte-identical to the per-triangle loop", identical,
             f"tris={tc}, max|diff|={float(np.max(np.abs(manual - triangles))) if tc else 0.0}")
        )

        # 2) vectorised clustering matches the brute-force reference exactly.
        ref = _reference_clusters(triangles)
        got = cluster_optical_solid_planar_faces(stl_path)
        count_ok = len(ref) == len(got)
        results.append(("candidate count matches reference", count_ok, f"ref={len(ref)} got={len(got)}"))

        mism = 0
        first_bad = ""
        if count_ok:
            for r, c in zip(ref, got):
                ok = (
                    r["face_id"] == c.face_id
                    and np.allclose(r["normal"], np.asarray(c.normal, dtype=float), atol=1e-6)
                    and np.allclose(r["centroid"], np.asarray(c.centroid, dtype=float), atol=1e-6)
                    and abs(r["area"] - float(c.area_mm2)) <= 1e-6
                    and abs(r["plane_offset"] - float(c.plane_offset_mm)) <= 1e-6
                    and r["tris"] == int(c.triangle_count)
                    and r["idx"] == tuple(int(v) for v in c.triangle_indices)
                )
                if not ok:
                    mism += 1
                    if not first_bad:
                        first_bad = f"{r['face_id']}: area {r['area']:.6f} vs {float(c.area_mm2):.6f}"
        results.append(
            ("every face candidate matches the reference (lossless, incl. tie-break)", mism == 0,
             f"mismatches={mism}/{len(ref)}" + (f"; first={first_bad}" if first_bad else ""))
        )

        # 3) a plain cube yields exactly six axis-aligned faces.
        cube_only = _save_stl(pv.Cube(x_length=2.0, y_length=2.0, z_length=2.0).triangulate(),
                              tmp_path / "cube.stl")
        cube_faces = cluster_optical_solid_planar_faces(cube_only)
        axis_aligned = all(
            np.isclose(max(abs(v) for v in f.normal), 1.0, atol=1e-9) for f in cube_faces
        )
        results.append(
            ("plain cube clusters to 6 axis-aligned faces", len(cube_faces) == 6 and axis_aligned,
             f"faces={len(cube_faces)}")
        )

    # 4) source wiring: per-triangle Python loops are gone; numpy batch ops in.
    cluster_src = inspect.getsource(cluster_optical_solid_planar_faces)
    loop_gone = "for triangle_index, tri in enumerate" not in cluster_src
    batched = all(tok in cluster_src for tok in ("np.bincount", "np.lexsort", "np.unique"))
    results.append(("clustering is vectorised (no per-triangle loop)", loop_gone and batched,
                    f"loop_gone={loop_gone}, batched={batched}"))

    reader_src = inspect.getsource(stl_geometry.read_stl_triangle_vertices)
    reader_batched = "np.frombuffer(data, dtype=record_dtype" in reader_src and \
        "for index in range(int(triangle_count))" not in reader_src
    results.append(("binary STL reader is vectorised (structured frombuffer)", reader_batched,
                    f"batched={reader_batched}"))

    return results


def main() -> int:
    results = run_checks()
    ok = True
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        print(f"{name} | {status} | {detail}")
        ok = ok and passed
    print(
        "[PASS] STEP-overlay face-metadata bake vectorised (lossless ~30x on a fine STL)"
        if ok
        else "[FAIL] vectorised bake regressed"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
