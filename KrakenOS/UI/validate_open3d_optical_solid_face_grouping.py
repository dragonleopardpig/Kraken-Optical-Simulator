"""Regression (bug 0003, Issue 3): curved-lens face candidates group into a few
logical surfaces for the face editor.

`cluster_optical_solid_planar_faces` fragments a curved (aspheric/spherical)
surface into one planar micro-cluster per triangle, so an aspheric achromat lists
~160 face candidates -- impractical to role-assign. `group_optical_solid_face_candidates`
region-grows by mesh connectivity + normal continuity to collapse each smooth
surface into one group (front / back / edge), while leaving flat-faced solids
(prisms) one group per face. This is display-only; the candidates are unchanged.

Display-free: builds an STL from each STEP fixture's analytic tessellation and
checks the group counts. Skips a fixture that is not checked out.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_optical_solid_face_grouping
Exit: 0 = pass, 1 = regression, 2 = no fixtures available.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pyvista as pv

from KrakenOS.UI.services.step_analytic_geometry import load_step_analytic_document
from KrakenOS.UI.services.optical_solid_geometry import (
    cluster_optical_solid_planar_faces,
    group_optical_solid_face_candidates,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _stl_from_step(step: Path, out_dir: Path) -> Path | None:
    try:
        doc = load_step_analytic_document(step)
        tris = np.asarray(doc.triangles)
        if tris.size == 0:
            return None
        n = int(tris.shape[0])
        pts = tris.reshape(-1, 3)
        faces = np.hstack([np.full((n, 1), 3, np.int64), np.arange(n * 3, dtype=np.int64).reshape(n, 3)]).ravel()
        stl = out_dir / (step.stem + ".stl")
        pv.PolyData(pts, faces).save(str(stl))
        return stl
    except Exception:
        return None


def _group_count(stl: Path) -> tuple[int, int]:
    cands = cluster_optical_solid_planar_faces(stl)
    gids = group_optical_solid_face_candidates(stl, cands, angle_deg=35.0)
    n_groups = len({g for g in gids if g >= 0})
    return len(cands), n_groups


def main() -> int:
    out_dir = Path(tempfile.mkdtemp())
    failures: list[str] = []
    ran_any = False

    # Aspheric achromat: a curved lens -> many planar candidates collapse to a
    # handful of logical surfaces (front / back / edge).
    aspheric = PROJECT_ROOT / "attachment" / "Lens" / "Aspherized_Achromatic_Lenses" / "step_49665.step"
    if aspheric.exists():
        stl = _stl_from_step(aspheric, out_dir)
        if stl is not None:
            ran_any = True
            n_cands, n_groups = _group_count(stl)
            print(f"aspheric achromat: {n_cands} planar candidates -> {n_groups} group(s)")
            if n_cands < 20:
                failures.append(f"expected the aspheric lens to fragment into many candidates, got {n_cands}")
            if not (1 <= n_groups <= 8):
                failures.append(f"aspheric lens should collapse to a few groups (1..8), got {n_groups}")
            if n_groups >= n_cands:
                failures.append(f"grouping did not consolidate ({n_groups} groups for {n_cands} candidates)")

    # A penta prism: flat faces -> grouping must NOT over-merge (one per face).
    prism = next(iter((PROJECT_ROOT / "attachment" / "prisms").glob("*/step_*.step")), None)
    if prism is not None and prism.exists():
        stl = _stl_from_step(prism, out_dir)
        if stl is not None:
            ran_any = True
            n_cands, n_groups = _group_count(stl)
            print(f"prism {prism.parent.name}: {n_cands} planar candidates -> {n_groups} group(s)")
            if n_groups != n_cands:
                failures.append(f"prism flat faces should be one group each ({n_cands}), got {n_groups}")

    if not ran_any:
        print("SKIP: no STEP fixtures available.", file=sys.stderr)
        return 2
    if failures:
        for msg in failures:
            print(f"FAIL: {msg}", file=sys.stderr)
        return 1
    print("PASS: curved lens faces consolidate into a few groups; flat prism faces stay one group each.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
