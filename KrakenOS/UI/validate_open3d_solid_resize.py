"""Guard: geometry core for the Open 3D "drag a face to resize a solid" feature.

Covers the pure-geometry kernel in ``KrakenOS.UI.services.open3d_solid_resize``:

* Coupling detection -- the beam-splitter 45-deg coating signature picks the free
  (depth) axis and the coupled (cross-section) pair; a plain element yields no
  coupling (-> free per-axis resize).
* Coupled scale -- a 50x50x50 cube to 55x55x78 gives scale factors [1.1, 1.1,
  1.56], and the coating normal (1,1,0)/sqrt2 stays at 45 deg.
* NEGATIVE control -- a non-coupled scale (55x50x78) tilts the coating off 45
  deg, proving the coupling constraint is what keeps a beam-splitter valid.
* Anchored resize -- growing one axis keeps the opposite (fixed) face put.
* Real vendor part (SKIP if absent / no OCC) -- the genuine
  ``Beam_Splitter/32704/step_32704.step`` is 2 solids, 50x50x50, and its planar
  faces yield free=Z, coupled={X,Y}; an OCC GTransform of the same coupled scale
  lands at 55x55x78.

The synthetic checks are portable (numpy only); the vendor-file checks degrade to
SKIP so the suite passes for any user without that attachment.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_solid_resize

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

# The vendor coating signature: normal (1,1,0)/sqrt2 -> free axis Z, coupled X/Y.
_SQRT_HALF = 1.0 / np.sqrt(2.0)
_VENDOR_STEP = Path("attachment/prisms/Beam_Splitter/32704/step_32704.step")


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    def skip(label: str) -> None:
        notes.append("SKIP " + label)

    from KrakenOS.UI.services import open3d_solid_resize as R

    # --- A. detection: the beam-splitter coating signature --------------------
    # Two opposing 45-deg coating faces + the six axis-aligned box faces.
    splitter_faces = [
        ((_SQRT_HALF, _SQRT_HALF, 0.0), 3535.5),
        ((-_SQRT_HALF, -_SQRT_HALF, 0.0), 3535.5),
        ((1.0, 0.0, 0.0), 2500.0), ((-1.0, 0.0, 0.0), 2500.0),
        ((0.0, 1.0, 0.0), 2500.0), ((0.0, -1.0, 0.0), 2500.0),
        ((0.0, 0.0, 1.0), 1250.0), ((0.0, 0.0, -1.0), 1250.0),
    ]
    axes = R.detect_coupling_from_faces(splitter_faces)
    ok(axes is not None and axes.free_axis == 2 and axes.coupled_axes == (0, 1),
       "A1: coating signature -> free axis Z, coupled pair {X, Y}")
    ok(axes is not None and axes.free_label == "Z" and axes.coupled_labels == ("X", "Y"),
       "A2: axis labels read free=Z, coupled=(X, Y)")

    # --- B. a plain element has no coupling -> free per-axis resize ----------
    box_faces = [
        ((1.0, 0.0, 0.0), 100.0), ((-1.0, 0.0, 0.0), 100.0),
        ((0.0, 1.0, 0.0), 100.0), ((0.0, -1.0, 0.0), 100.0),
        ((0.0, 0.0, 1.0), 100.0), ((0.0, 0.0, -1.0), 100.0),
    ]
    ok(R.detect_coupling_from_faces(box_faces) is None,
       "B: axis-aligned-only element -> no coupling (free per-axis resize)")

    # --- C. coupled scale 50x50x50 -> 55x55x78 -------------------------------
    assert axes is not None
    scales = R.coupled_scales(axes, (50.0, 50.0, 50.0), cross_section=55.0, depth=78.0)
    ok(np.allclose(scales, [55 / 50, 55 / 50, 78 / 50]),
       "C1: coupled scale = [1.1, 1.1, 1.56] (square cross-section + free depth)")
    ok(abs(scales[axes.coupled_axes[0]] - scales[axes.coupled_axes[1]]) < 1e-12,
       "C2: the two coupled axes scale by the SAME factor (prisms grow together)")

    # --- D. coupled scale keeps the coating at 45 deg ------------------------
    coupled_normal = R.transform_normal((_SQRT_HALF, _SQRT_HALF, 0.0), scales)
    ok(np.allclose(np.abs(coupled_normal), [_SQRT_HALF, _SQRT_HALF, 0.0], atol=1e-6),
       "D1: coupled resize keeps the coating normal at (0.707, 0.707, 0)")
    ok(R.is_coating_preserved((_SQRT_HALF, _SQRT_HALF, 0.0), scales),
       "D2: is_coating_preserved() True for the coupled scale")

    # --- E. NEGATIVE: non-coupled scale tilts the coating off 45 deg ---------
    bad_scales = R.axis_scales_for_extents((50.0, 50.0, 50.0), (55.0, 50.0, 78.0))
    bad_normal = np.abs(R.transform_normal((_SQRT_HALF, _SQRT_HALF, 0.0), bad_scales))
    ok(np.allclose(bad_normal, [0.673, 0.740, 0.0], atol=2e-3),
       "E1: non-coupled scale tilts the coating to ~(0.673, 0.74, 0) (matches OCC)")
    ok(not R.is_coating_preserved((_SQRT_HALF, _SQRT_HALF, 0.0), bad_scales),
       "E2: is_coating_preserved() False for the non-coupled scale (coupling matters)")

    # --- F. anchored resize keeps the opposite face fixed --------------------
    # Unit box [0,1]^3; grow X x2 with the X=max (x=1) face fixed.
    cube = np.array(
        [[x, y, z] for x in (0.0, 1.0) for y in (0.0, 1.0) for z in (0.0, 1.0)],
        dtype=float,
    )
    anchor = R.anchor_point_for_fixed_face([0, 0, 0], [1, 1, 1], fixed_axis=0, fixed_at_max=True)
    grown = R.resize_points(cube, [2.0, 1.0, 1.0], anchor)
    ok(np.allclose(grown[cube[:, 0] == 1.0][:, 0], 1.0),
       "F1: the fixed (x=max) face stays put under an anchored grow")
    ok(np.isclose(R.extents_of(grown)[0], 2.0) and np.isclose(grown[:, 0].min(), -1.0),
       "F2: the opposite face moves so the X extent doubles (grows outward)")

    # --- G. extents helper ---------------------------------------------------
    ok(np.allclose(R.extents_of(cube), [1.0, 1.0, 1.0]),
       "G: extents_of() reports the axis-aligned size")

    # --- H. real vendor part (SKIP if absent / no OCC) -----------------------
    if not _VENDOR_STEP.exists():
        skip(f"H: vendor beam-splitter STEP not present ({_VENDOR_STEP})")
    else:
        try:
            from KrakenOS.UI.services.cad_step_export import _read_step_shape, _shape_with_affine
            from OCC.Core.Bnd import Bnd_Box
            from OCC.Core.BRepBndLib import brepbndlib

            shape = _read_step_shape(_VENDOR_STEP)
            vendor_axes = R.detect_coupling(shape)
            ok(vendor_axes is not None
               and vendor_axes.free_axis == 2 and vendor_axes.coupled_axes == (0, 1),
               "H1: vendor STEP detects free=Z, coupled={X, Y}")

            box = Bnd_Box()
            brepbndlib.Add(shape, box)
            xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
            extents = np.array([xmax - xmin, ymax - ymin, zmax - zmin])
            ok(np.allclose(extents, [50.0, 50.0, 50.0], atol=1e-3),
               "H2: vendor STEP bounding box is 50 x 50 x 50 mm")

            centre = np.array([(xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2])
            matrix = R.anchored_scale_matrix([55 / 50, 55 / 50, 78 / 50], centre)
            scaled = _shape_with_affine(shape, matrix)
            sbox = Bnd_Box()
            brepbndlib.Add(scaled, sbox)
            sxmin, symin, szmin, sxmax, symax, szmax = sbox.Get()
            sext = np.array([sxmax - sxmin, symax - symin, szmax - szmin])
            ok(np.allclose(sext, [55.0, 55.0, 78.0], atol=1e-2),
               "H3: an OCC coupled scale of the vendor part lands at 55 x 55 x 78 mm")
        except Exception as exc:  # pragma: no cover - environment dependent
            skip(f"H: vendor-file OCC checks unavailable ({type(exc).__name__}: {exc})")

    passed = not any(n.startswith("FAIL") for n in notes)
    if verbose:
        for n in notes:
            print(n)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Open 3D solid-resize geometry-core validation passed.")
        return 0
    print("Open 3D solid-resize geometry-core validation FAILED:")
    for n in notes:
        if n.startswith("FAIL"):
            print(f"- {n}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
