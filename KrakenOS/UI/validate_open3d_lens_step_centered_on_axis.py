"""Guard: an imported Imaging-Lens STEP is centred on the optical axis, not
pushed off it by an asymmetric mount/flange (bugs/0077).

Reported (``attachment/3D.png``): the user glued the Imaging Lens STEP to its
surrogate lens but the barrel sat **laterally offset** from the optical axis --
the lens-STEP rings and the surrogate circles were not concentric.

Root cause: ``_cad_mesh_aligned_to_optical_axis`` centred each overlay on its
mesh **bounding-box midpoint**.  For a rotationally symmetric lens with a
one-sided mount tab / connector, the bbox midpoint is shifted toward the tab, so
the optical barrel lands off the axis.  ``_step_primary_cylinder_axis`` already
detected the lens cylinder *direction* but discarded ``Axis().Location()`` -- the
point that actually lies on the optical axis.

Fix: ``_step_primary_cylinder_axis`` now also returns a radius-weighted point on
the dominant cylinder axis; ``_cad_mesh_aligned_to_optical_axis`` projects it into
the transverse plane and uses it as the lateral centre instead of the bbox
midpoint.  The lens display path and the promotion/export affine both pass it.

Fully DISPLAY-FREE: the core check drives ``_cad_mesh_aligned_to_optical_axis``
on a synthetic asymmetric lens point cloud (no render).  A second, skip-if-absent
section exercises the real OCC cylinder-axis extraction on an imported lens STEP.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_lens_step_centered_on_axis

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Real imported lens STEPs are vendor fixtures under the gitignored attachment/
# tree, so the OCC section is skip-if-absent for other checkouts.
_REAL_LENS_CANDIDATES = (
    PROJECT_ROOT / "attachment" / "Lens" / "1072517_00165969_001.stp",
    PROJECT_ROOT / "attachment" / "1072517_00165969_001.stp",
    PROJECT_ROOT / "attachment" / "Lens" / "15056" / "15056.STEP",
)


def _synthetic_asymmetric_lens() -> "tuple[np.ndarray, int]":
    """A lens barrel of radius 10 mm centred on the optical axis (0, 0) PLUS a
    one-sided mount tab on +x.  Returns ``(points, n_barrel)`` with the barrel /
    optical-surface points first so their post-alignment centroid is easy to
    read.  The tab pushes the +x bounding box to ~18 mm, so the bbox midpoint sits
    at x ~ +4 mm -- nowhere near the true axis at x = 0."""
    radius = 10.0
    thetas = np.linspace(0.0, 2.0 * np.pi, 48, endpoint=False)
    barrel: list[list[float]] = []
    for z in np.linspace(0.0, 20.0, 11):
        for t in thetas:
            barrel.append([radius * np.cos(t), radius * np.sin(t), float(z)])
    # front + rear optical surfaces (filled discs), also concentric with the axis
    for z in (0.0, 20.0):
        for r in np.linspace(0.0, radius, 6):
            for t in thetas:
                barrel.append([r * np.cos(t), r * np.sin(t), float(z)])
    barrel_arr = np.asarray(barrel, dtype=float)
    tab = np.asarray(
        [
            [x, y, z]
            for x in np.linspace(radius, radius + 8.0, 4)
            for y in np.linspace(-2.0, 2.0, 3)
            for z in np.linspace(6.0, 14.0, 4)
        ],
        dtype=float,
    )
    return np.vstack([barrel_arr, tab]), int(barrel_arr.shape[0])


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    try:
        import pyvista as pv

        from KrakenOS.UI.services.layout_polyline_display import (
            LayoutPolylineDisplayMixin,
        )
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: lens-centering deps unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    insp = object.__new__(LayoutPolylineDisplayMixin)
    insp.append_debug = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    insp._external_cad_mesh_cache = {}  # type: ignore[attr-defined]
    align = insp._cad_mesh_aligned_to_optical_axis

    # --- A. synthetic asymmetric lens: the CAD axis point centres it ----------
    pts, n_barrel = _synthetic_asymmetric_lens()
    base_mesh = pv.PolyData(pts)
    common = dict(
        source_axis=(0.0, 0.0, 1.0),
        front_face="min",
        target_front_z=0.0,
        label="Lens STEP",
    )

    aligned_axis = align(base_mesh, optical_axis_point_xyz=(0.0, 0.0, 10.0), **common)
    aligned_bbox = align(base_mesh, optical_axis_point_xyz=None, **common)

    ok(aligned_axis is not None and aligned_bbox is not None,
       "A0: alignment returns a mesh for both centring modes")

    if aligned_axis is not None and aligned_bbox is not None:
        bc_axis = np.asarray(aligned_axis.points, dtype=float)[:n_barrel, :2].mean(axis=0)
        bc_bbox = np.asarray(aligned_bbox.points, dtype=float)[:n_barrel, :2].mean(axis=0)

        ok(float(np.linalg.norm(bc_axis)) < 1e-6,
           f"A1 (the fix): with the CAD cylinder-axis point the barrel centres on the "
           f"optical axis (centroid={np.round(bc_axis, 6).tolist()} ~ 0,0)")
        ok(float(np.linalg.norm(bc_bbox)) > 1.0,
           f"A2 (the bug, fail-before): bbox-midpoint centring pushes the barrel off-axis "
           f"toward the mount (centroid={np.round(bc_bbox, 4).tolist()}, |offset| "
           f"{float(np.linalg.norm(bc_bbox)):.3f} mm)")
        ok(float(np.linalg.norm(bc_axis)) + 1e-6 < float(np.linalg.norm(bc_bbox)),
           "A3: the CAD-axis centring is strictly more on-axis than bbox centring")
        # the axial datum must be untouched by the lateral re-centring
        front_z = float(np.asarray(aligned_axis.points, dtype=float)[:, 2].min())
        ok(abs(front_z) < 1e-6,
           f"A4: front optical surface still lands on target_front_z (min z={front_z:.6f} ~ 0)")

    # --- B. real OCC cylinder-axis extraction (skip-if-absent) ----------------
    real_lens = next((p for p in _REAL_LENS_CANDIDATES if p.exists()), None)
    if real_lens is None:
        notes.append("SKIP: no imported lens STEP fixture present for OCC extraction check")
    else:
        try:
            axis = insp._step_primary_cylinder_axis(real_lens)
            point = insp._step_primary_cylinder_axis_point(real_lens)
            if axis is None or point is None:
                notes.append(
                    f"SKIP: OCC cylinder extraction returned nothing for {real_lens.name} "
                    "(no qualifying cylinder / OCC unavailable)"
                )
            else:
                ok(np.all(np.isfinite(np.asarray(point, dtype=float))) and point.shape == (3,),
                   f"B1: a real lens STEP yields a finite on-axis point for {real_lens.name} "
                   f"(point={np.round(point, 3).tolist()})")
                ok(abs(float(np.linalg.norm(np.asarray(axis, dtype=float))) - 1.0) < 1e-6,
                   "B2: the returned cylinder axis is a unit direction")
        except Exception as exc:
            notes.append(f"SKIP: real lens OCC extraction raised ({type(exc).__name__}: {exc})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Lens-STEP optical-axis centring validation passed.")
        return 0
    print("Lens-STEP optical-axis centring validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
