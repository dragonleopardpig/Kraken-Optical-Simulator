#!/usr/bin/env python3
"""Display-free guard for bugs/0319 -- the parametric beam-splitter generator.

The one-click "Add Beam Splitter to LED" builds its BS solid in-process with
pythonocc-core (no vendor STEP download; the gitignored ``attachment/prisms/*`` are
absent on a fresh clone) and caches it under ``attachment/cad_cache/`` so it can be
regenerated whenever the cache is missing.

The load-bearing requirement this guards: a beam-splitter **cube** must carry a
*real* 45-degree diagonal hypotenuse face -- a plain ``BRepPrimAPI_MakeBox`` has no
diagonal, and the resize/coupling detector + the auto-flag-the-coating promote step
both expect that face. So the cube is two cemented right-angle prisms sharing the
X = Z diagonal, and this guard re-reads the written STEP and asserts a genuine planar
face sits at 45 degrees to the optical axis (+Z).

What it checks
--------------
  A. Metadata math (OCC-free, always runs): cube coating normal is 45 deg to +Z;
     plate coating normal is 45 deg to +Z; the canonical solids are origin-centered;
     bad parameters (non-positive side, plate thicker than its face, tilt out of
     range) raise ValueError.
  B. Cube build (needs OCC; SKIP without it): writes a STEP with >= 2 solids, and
     re-reading it finds a genuine planar face ~45 deg to +Z (the coating diagonal).
  C. Plate build (needs OCC): writes a STEP whose large face is ~45 deg to +Z.
  D. Cache reuse + regen-if-missing: a second call reuses the file (regenerated is
     False); deleting the cache and calling again regenerates it (regenerated True).
  E. Returned coating_normal matches a real face in the written STEP.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_beam_splitter_factory

Exit: 0 = pass (incl. an OCC-absent environment skip), 1 = regression.
"""
from __future__ import annotations

import math
import tempfile
from pathlib import Path


def _occ_available() -> bool:
    try:
        import OCC.Core.BRepPrimAPI  # noqa: F401
        import OCC.Core.STEPControl  # noqa: F401
    except Exception:
        return False
    return True


def _angle_to_z_deg(normal) -> float:
    x, y, z = (float(v) for v in normal)
    norm = math.sqrt(x * x + y * y + z * z)
    if norm <= 1e-12:
        return float("nan")
    return math.degrees(math.acos(min(1.0, abs(z) / norm)))


def _step_planar_face_normals(path: Path) -> list:
    """Every planar-face unit normal in a STEP file (world frame)."""
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.GeomAbs import GeomAbs_Plane
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopoDS import topods

    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != 1:
        raise RuntimeError(f"could not read STEP: {path}")
    if reader.TransferRoots() <= 0:
        raise RuntimeError(f"could not transfer STEP roots: {path}")
    shape = reader.OneShape()
    normals: list = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        surface = BRepAdaptor_Surface(face)
        if surface.GetType() == GeomAbs_Plane:
            direction = surface.Plane().Axis().Direction()
            normals.append((direction.X(), direction.Y(), direction.Z()))
        explorer.Next()
    return normals


def _count_solids(path: Path) -> int:
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.TopAbs import TopAbs_SOLID
    from OCC.Core.TopExp import TopExp_Explorer

    reader = STEPControl_Reader()
    reader.ReadFile(str(path))
    reader.TransferRoots()
    shape = reader.OneShape()
    count = 0
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        count += 1
        explorer.Next()
    return count


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services import beam_splitter_factory as bsf
    from KrakenOS.UI.services import cad_cache_paths

    failures: list[str] = []

    # --- A) Pure metadata math (OCC-free) --------------------------------------
    cube = bsf._normalize_cube_params(20.0)
    cube_meta = bsf.beam_splitter_metadata("cube", cube)
    cube_tilt = _angle_to_z_deg(cube_meta["coating_normal"])
    if abs(cube_tilt - 45.0) > 1e-6:
        failures.append(f"FAIL(A): cube coating normal must be 45 deg to +Z, got {cube_tilt:.4f}")
    if cube_meta["coating_point"] != (0.0, 0.0, 0.0):
        failures.append(f"FAIL(A): cube coating plane must pass through the origin, got {cube_meta['coating_point']}")
    if cube_meta["bbox_min"] != (-10.0, -10.0, -10.0) or cube_meta["bbox_max"] != (10.0, 10.0, 10.0):
        failures.append(f"FAIL(A): 20mm cube bbox must be +/-10 on each axis, got {cube_meta['bbox_min']}..{cube_meta['bbox_max']}")

    plate = bsf._normalize_plate_params(30.0, 20.0, 2.0, 45.0)
    plate_meta = bsf.beam_splitter_metadata("plate", plate)
    plate_tilt = _angle_to_z_deg(plate_meta["coating_normal"])
    if abs(plate_tilt - 45.0) > 1e-6:
        failures.append(f"FAIL(A): plate coating normal must be 45 deg to +Z, got {plate_tilt:.4f}")

    for bad in (0.0, -5.0, float("nan")):
        try:
            bsf._normalize_cube_params(bad)
            failures.append(f"FAIL(A): cube side {bad!r} must raise ValueError")
        except ValueError:
            pass
    try:
        bsf._normalize_plate_params(10.0, 10.0, 10.0, 45.0)  # thickness == face -> not a plate
        failures.append("FAIL(A): a plate as thick as its face must raise ValueError")
    except ValueError:
        pass
    try:
        bsf._normalize_plate_params(30.0, 20.0, 2.0, 120.0)  # tilt out of range
        failures.append("FAIL(A): plate tilt 120 deg must raise ValueError")
    except ValueError:
        pass

    if not _occ_available():
        # Environment without pythonocc-core: the math is verified; the build is not
        # exercisable here. Treat as a pass with a note (like the other guards).
        return (not failures), failures + ["SKIP(B-E): pythonocc-core unavailable; metadata math only"]

    # Redirect the CAD cache at the source module so nothing lands in the real tree.
    saved_dir = cad_cache_paths.CAD_CACHE_DIR
    with tempfile.TemporaryDirectory() as tmp:
        cad_cache_paths.CAD_CACHE_DIR = Path(tmp)
        try:
            # --- B) Cube build -> real 45-deg diagonal face --------------------
            cube_solid = bsf.beam_splitter_cube_step(20.0)
            if not cube_solid.path.exists() or cube_solid.path.stat().st_size <= 0:
                failures.append("FAIL(B): cube STEP was not written")
            if not cube_solid.regenerated:
                failures.append("FAIL(B): first cube build should report regenerated=True")
            solids = _count_solids(cube_solid.path)
            if solids < 2:
                failures.append(f"FAIL(B): cube must be two cemented prisms (>=2 solids), got {solids}")
            cube_normals = _step_planar_face_normals(cube_solid.path)
            diagonal_faces = [n for n in cube_normals if abs(_angle_to_z_deg(n) - 45.0) < 1.0]
            if not diagonal_faces:
                angles = sorted({round(_angle_to_z_deg(n), 1) for n in cube_normals})
                failures.append(f"FAIL(B): cube STEP has NO real 45-deg diagonal face (plain box?); face angles to +Z: {angles}")

            # --- C) Plate build -> large face at 45 deg ------------------------
            plate_solid = bsf.beam_splitter_plate_step(30.0, 20.0, 2.0)
            if not plate_solid.path.exists() or plate_solid.path.stat().st_size <= 0:
                failures.append("FAIL(C): plate STEP was not written")
            plate_normals = _step_planar_face_normals(plate_solid.path)
            tilted_faces = [n for n in plate_normals if abs(_angle_to_z_deg(n) - 45.0) < 1.0]
            if not tilted_faces:
                angles = sorted({round(_angle_to_z_deg(n), 1) for n in plate_normals})
                failures.append(f"FAIL(C): plate STEP has NO face at 45 deg to +Z; face angles: {angles}")

            # --- D) Cache reuse + regenerate-if-missing ------------------------
            reused = bsf.beam_splitter_cube_step(20.0)
            if reused.regenerated:
                failures.append("FAIL(D): a present cache must be reused (regenerated=False)")
            if reused.path != cube_solid.path:
                failures.append("FAIL(D): identical params must map to one cache path")
            reused.path.unlink()
            regen = bsf.beam_splitter_cube_step(20.0)
            if not regen.regenerated:
                failures.append("FAIL(D): a missing cache must regenerate (regenerated=True)")
            if not regen.path.exists():
                failures.append("FAIL(D): regeneration must rewrite the STEP")

            # --- E) Returned coating_normal matches a real face ----------------
            returned_tilt = cube_solid.coating_tilt_deg
            if abs(returned_tilt - 45.0) > 1e-6:
                failures.append(f"FAIL(E): returned cube coating tilt must be 45 deg, got {returned_tilt:.4f}")
            match = any(
                abs(_angle_to_z_deg(n) - returned_tilt) < 1.0 for n in cube_normals
            )
            if not match:
                failures.append("FAIL(E): returned coating_normal has no matching face in the STEP")
        finally:
            cad_cache_paths.CAD_CACHE_DIR = saved_dir

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    hard = [f for f in failures if not f.startswith("SKIP")]
    skips = [f for f in failures if f.startswith("SKIP")]
    if hard:
        print("[FAIL] parametric beam-splitter generator (bugs/0319)")
        for item in hard:
            print(f"  - {item}")
        return 1
    print("[PASS] beam-splitter cube carries a real 45-deg diagonal face; plate tilts 45 deg; "
          "cache regenerates when missing")
    for item in skips:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
