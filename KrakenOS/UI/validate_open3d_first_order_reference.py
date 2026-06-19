#!/usr/bin/env python3
"""Display-free regression for bugs/0094 Phase 1: the transmissive FIRST-ORDER REFERENCE.

KrakenOS's sequential pupil/paraxial code (``Kos.PupilCalc``, the ABCD solve) cannot
trace a beam splitter or a promoted mesh solid -- it branches and throws, after which the
silent fallback aims the source at the wrong plane (the cube), so the beam "focuses at
the beam splitter". The fix: build a transmissive first-order reference of the layout --
beam splitters & mesh solids reduced to their straight-through (transmit) form, mirrors
folded out -- and have first-order code trace THAT.

Asserts:
  - ``_row_is_nonseq_optical_solid`` detects a Beam Splitter surface and a mesh solid,
    not a plain refractive surface;
  - ``_transmissive_reference_row`` KEEPS the mesh geometry + glass + thickness but STRIPS
    the branch (coating / per-face / tilt) -> a clean centered Standard surface;
  - ``_layout_needs_paraxial_reference`` is True for a non-seq layout, False for a plain
    lens stack;
  - the reference of a mesh-cube scene reproduces the direct mesh pupil (keeping the mesh
    matches PupilCalc; an analytic plate drifted ~8 mm);
  - a Beam Splitter surface that makes ``PupilCalc`` THROW no longer throws via the
    reference.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_first_order_reference

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
import os
import tempfile

import numpy as np


def _cube_stl(mm: float = 50.0) -> str:
    import pyvista as pv

    path = os.path.join(tempfile.gettempdir(), f"_first_order_ref_cube_{int(mm)}.stl")
    if not os.path.exists(path):
        pv.Box(bounds=(-mm / 2, mm / 2, -mm / 2, mm / 2, -mm / 2, mm / 2)).triangulate().save(path)
    return path


def _lens_rows():
    from KrakenOS.UI.surface_table_model import SurfaceRow

    return [
        SurfaceRow(surface="Standard", name="front datum", thickness=1.45390219, diameter=35.0, glass="AIR"),
        SurfaceRow(surface="Thin Lens", name="G1", rc=258.76640629, thickness=24.405, diameter=26.8, glass="AIR"),
        SurfaceRow(surface="Aperture", name="stop", thickness=21.64217312, diameter=19.35624, glass="AIR"),
        SurfaceRow(surface="Thin Lens", name="G2", rc=293.32901330, thickness=1.308924688, diameter=26.8, glass="AIR"),
        SurfaceRow(surface="Standard", name="rear datum", thickness=272.0, diameter=35.0, glass="AIR"),
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=33.0, glass="AIR"),
    ]


def _pupil_z(rows) -> float:
    import KrakenOS as Kos
    from KrakenOS.UI.layout_editor import _build_system_from_specs
    from KrakenOS.UI.surface_table_model import surface_rows_to_specs

    si = next(i for i, r in enumerate(rows) if r.surface == "Aperture")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        system = _build_system_from_specs(surface_rows_to_specs(rows))
        system.energy_probability = 0
        system.BUILD = 1
        system.build()
        pupil = Kos.PupilCalc(system, si, 0.546, "EPD", 26.8)
        return float(np.asarray(pupil.PosPupInp).ravel()[2])


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.surface_table_model import SurfaceRow
    from KrakenOS.UI.services.paraxial_tools import (
        ParaxialToolsMixin,
        _row_is_nonseq_optical_solid,
        _transmissive_reference_row,
    )
    from KrakenOS.common_optical_layouts.right_angle_beam_splitter_illumination import (
        BEAM_SPLITTER_SETTINGS,
        COMMON_SPLITTER,
    )

    failures: list[str] = []
    ref = lambda rows: ParaxialToolsMixin._paraxial_reference_rows_for_layout(None, rows)[0]
    needs = lambda rows: ParaxialToolsMixin._layout_needs_paraxial_reference(None, rows)

    obj = lambda: SurfaceRow(surface="Object", name="O", thickness=176.0, diameter=33.0, glass="AIR")
    spacer = lambda: SurfaceRow(surface="Standard", name="sp", thickness=49.0, diameter=35.0, glass="AIR")
    mesh_row = SurfaceRow(surface="Standard", name="cube", thickness=50.0, diameter=50.0, glass="BK7",
                          advanced={"Solid_3d_stl": _cube_stl(), "OpticalSolidFaces": {"faces": []}})
    bs_surface = SurfaceRow(surface="Beam Splitter", name="BS", thickness=99.0, diameter=50.0, tilt_x=-45.0,
                            glass="BK7", advanced={"BeamSplitter": BEAM_SPLITTER_SETTINGS, "Element": COMMON_SPLITTER})

    # 1) detection
    if not _row_is_nonseq_optical_solid(mesh_row):
        failures.append("FAIL: a mesh solid (Solid_3d_stl) was not detected as non-sequential")
    if not _row_is_nonseq_optical_solid(bs_surface):
        failures.append("FAIL: a Beam Splitter surface was not detected as non-sequential")
    if _row_is_nonseq_optical_solid(SurfaceRow(surface="Thin Lens", rc=150.0, glass="AIR")):
        failures.append("FAIL: a plain Thin Lens was wrongly detected as non-sequential")

    # 2) conversion keeps the mesh, strips the branch, centres it
    conv = _transmissive_reference_row(mesh_row)
    adv = conv.advanced or {}
    if conv.surface != "Standard" or str(adv.get("Solid_3d_stl", "None")) == "None":
        failures.append(f"FAIL: transmissive reference dropped the mesh / surface ({conv.surface}, adv={list(adv)})")
    if adv.get("OpticalSolidFaces") is not None or adv.get("BeamSplitter") is not None:
        failures.append("FAIL: transmissive reference kept a branch attribute (OpticalSolidFaces / BeamSplitter)")
    if any(abs(v) > 1e-9 for v in (conv.tilt_x, conv.tilt_y, conv.tilt_z, conv.desp_x, conv.desp_y, conv.desp_z, conv.axis_move)):
        failures.append("FAIL: transmissive reference kept a tilt/decenter")

    # 3) layout detection
    plain = [obj(), *(_lens_rows())]
    plain[0] = SurfaceRow(surface="Object", name="O", thickness=275.0, diameter=33.0, glass="AIR")
    cube_scene = [obj(), mesh_row, spacer(), *_lens_rows()]
    if needs(plain):
        failures.append("FAIL: a plain lens stack should NOT need a paraxial reference")
    if not needs(cube_scene):
        failures.append("FAIL: a mesh-cube layout should need a paraxial reference")

    # 4) reference reproduces the direct mesh pupil (keeping the mesh)
    try:
        direct = _pupil_z(cube_scene)
        via = _pupil_z(ref(cube_scene))
        if abs(direct - via) > 0.5:
            failures.append(f"FAIL: reference pupil {via:.2f} != direct mesh pupil {direct:.2f}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"FAIL: mesh-cube pupil correctness raised {type(exc).__name__}: {exc}")

    # 5) a Beam Splitter surface throws directly but not via the reference
    bs_scene = [obj(), bs_surface, *_lens_rows()]
    direct_threw = False
    try:
        _pupil_z(bs_scene)
    except Exception:  # noqa: BLE001
        direct_threw = True
    ref_threw = False
    try:
        _pupil_z(ref(bs_scene))
    except Exception:  # noqa: BLE001
        ref_threw = True
    if not direct_threw:
        failures.append("FAIL: the Beam Splitter test scene was expected to make PupilCalc throw directly")
    if ref_threw:
        failures.append("FAIL: PupilCalc still throws when traced through the first-order reference")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0094 first-order reference")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] transmissive first-order reference for beam splitters / mesh solids (bugs/0094)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
