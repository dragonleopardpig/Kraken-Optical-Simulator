#!/usr/bin/env python3
"""Display-free regression for Phase 2 (DESIGN_nonseq_first_order_reference.md §5b):
the PER-BRANCH first-order pupil.

A beam splitter sends one object into two arms. §5b's central claim is that **each
terminal arm images its own aperture stop to its own entrance pupil**, so:

  - if each arm has a PRIVATE stop (after the split), the two arms have DIFFERENT
    entrance pupils (location + diameter) -- a single source launch fills one arm's
    pupil and vignettes / non-uniformly fills the other; a *per-branch* launch is
    required;
  - if the stop sits BEFORE the split (shared objective), both arms share ONE
    entrance pupil -- a single launch serves both seamlessly.

A per-leaf first-order reference is just the Phase-1 reference builder
(`_paraxial_reference_rows_for_layout`, which turns the beam-splitter cube into its
transmissive flat plate and folds mirrors out) applied to that leaf's ordered row
sequence; ``PupilCalc`` on it yields the leaf's entrance pupil. This test builds two
leaf references for each configuration and checks the pupil locations.

Asserts:
  - private-stop arms -> the two leaf pupils are well separated (per-branch needed);
  - shared pre-split-stop arms -> the two leaf pupils coincide (one launch ok);
  - every per-leaf reference traces cleanly (no PupilCalc throw through the cube).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_per_branch_pupil

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
import os
import tempfile


def _cube_stl(mm: float = 50.0) -> str:
    import pyvista as pv

    path = os.path.join(tempfile.gettempdir(), f"_per_branch_cube_{int(mm)}.stl")
    if not os.path.exists(path):
        pv.Box(bounds=(-mm / 2, mm / 2, -mm / 2, mm / 2, -mm / 2, mm / 2)).triangulate().save(path)
    return path


def _leaf_pupil_z(leaf_rows) -> float:
    """Entrance-pupil z of one beam-splitter arm, via its first-order reference."""
    import numpy as np

    import KrakenOS as Kos
    from KrakenOS.UI.layout_editor import _build_system_from_specs
    from KrakenOS.UI.surface_table_model import surface_rows_to_specs
    from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin

    reference, _last = ParaxialToolsMixin._paraxial_reference_rows_for_layout(None, leaf_rows)
    stop_index = next(i for i, r in enumerate(reference) if r.surface == "Aperture")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        system = _build_system_from_specs(surface_rows_to_specs(reference))
        system.energy_probability = 0
        system.BUILD = 1
        system.build()
        pupil = Kos.PupilCalc(system, stop_index, 0.55, "EPD", 16.0)
        return float(np.asarray(pupil.PosPupInp).ravel()[2])


def _rows():
    from KrakenOS.UI.surface_table_model import SurfaceRow

    adv = lambda: {"Solid_3d_stl": _cube_stl(), "OpticalSolidFaces": {"faces": []}}
    obj = lambda t=200.0: SurfaceRow(surface="Object", name="O", thickness=t, diameter=30.0, glass="AIR")
    bs = lambda t=50.0: SurfaceRow(surface="Standard", name="BS", thickness=t, diameter=50.0, glass="BK7", advanced=adv())
    lens = lambda rc, t: SurfaceRow(surface="Thin Lens", name="L", rc=rc, thickness=t, diameter=30.0, glass="AIR")
    stop = lambda d, t: SurfaceRow(surface="Aperture", name="stop", thickness=t, diameter=d, glass="AIR")
    image = lambda: SurfaceRow(surface="Image", name="I", thickness=0.0, diameter=20.0, glass="AIR")

    # Private stop per arm (stop AFTER each arm's own lens) -> different pupils.
    private = {
        "transmit": [obj(), bs(), lens(100.0, 80.0), stop(20.0, 50.0), image()],
        "reflect": [obj(), bs(), lens(60.0, 50.0), stop(10.0, 30.0), image()],
    }
    # Shared stop BEFORE the split (common objective) -> one pupil for both arms.
    pre = lambda: [obj(), lens(120.0, 50.0), stop(20.0, 30.0), bs()]
    shared = {
        "transmit": pre() + [lens(80.0, 60.0), image()],
        "reflect": pre() + [lens(40.0, 60.0), image()],
    }
    return private, shared


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    private, shared = _rows()

    try:
        priv_t = _leaf_pupil_z(private["transmit"])
        priv_r = _leaf_pupil_z(private["reflect"])
    except Exception as exc:  # noqa: BLE001
        return False, [f"FAIL: private-stop per-leaf pupil raised {type(exc).__name__}: {exc}"]
    if abs(priv_t - priv_r) <= 1.0:
        failures.append(
            f"FAIL: private-stop arms should have DIFFERENT entrance pupils, got "
            f"transmit z={priv_t:.2f} ~= reflect z={priv_r:.2f} (a single launch would be wrong)"
        )

    try:
        shar_t = _leaf_pupil_z(shared["transmit"])
        shar_r = _leaf_pupil_z(shared["reflect"])
    except Exception as exc:  # noqa: BLE001
        return False, [f"FAIL: shared-stop per-leaf pupil raised {type(exc).__name__}: {exc}"]
    if abs(shar_t - shar_r) > 1.0:
        failures.append(
            f"FAIL: a stop BEFORE the split should give ONE shared entrance pupil, got "
            f"transmit z={shar_t:.2f} != reflect z={shar_r:.2f}"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] Phase 2 per-branch first-order pupil (DESIGN §5b)")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] per-branch entrance pupil: private stops differ, shared pre-split stop coincides (DESIGN §5b)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
