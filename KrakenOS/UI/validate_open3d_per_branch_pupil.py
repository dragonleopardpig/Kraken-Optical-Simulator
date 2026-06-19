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


def _leaf_pupil_z(leaf_rows, *, unfold: bool = False) -> float:
    """Entrance-pupil z of one beam-splitter arm, via its first-order reference."""
    import numpy as np

    import KrakenOS as Kos
    from KrakenOS.UI.layout_editor import _build_system_from_specs
    from KrakenOS.UI.surface_table_model import surface_rows_to_specs
    from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin

    reference, _last = ParaxialToolsMixin._paraxial_reference_rows_for_layout(
        None, leaf_rows, unfold_branch_tilts=unfold
    )
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
    lens = lambda rc, t, tilt=0.0: SurfaceRow(surface="Thin Lens", name="L", rc=rc, thickness=t, diameter=30.0, glass="AIR", tilt_x=tilt)
    stop = lambda d, t, tilt=0.0: SurfaceRow(surface="Aperture", name="stop", thickness=t, diameter=d, glass="AIR", tilt_x=tilt)
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
    # A FOLDED reflect arm (bent off-axis via tilt, like beam_splitter_two_arm_doublets)
    # must UNFOLD to the same entrance pupil as the equivalent straight arm.
    folded = {
        "straight": [obj(), bs(), lens(100.0, 80.0), stop(20.0, 50.0), image()],
        "folded": [obj(), bs(), lens(100.0, 80.0, -90.0), stop(20.0, 50.0, -90.0), image()],
    }
    return private, shared, folded


def _two_arm_scene():
    """A single tagged surface table for a beam splitter with a DIFFERENT lens+stop per
    arm and a FOLDED reflect arm -- the structure of beam_splitter_two_arm_doublets, the
    shape a per-branch launch must drive."""
    from KrakenOS.UI.surface_table_model import SurfaceRow

    mesh = lambda: {"Solid_3d_stl": _cube_stl(), "OpticalSolidFaces": {"faces": []}}
    arm = lambda sel: {"Element": {"branch_selector": sel}}
    return [
        SurfaceRow(surface="Object", name="O", thickness=200.0, diameter=30.0, glass="AIR"),
        SurfaceRow(surface="Standard", name="BS", thickness=50.0, diameter=50.0, glass="BK7", advanced=mesh()),
        # transmit arm (+Z, straight)
        SurfaceRow(surface="Thin Lens", name="TXL", rc=100.0, thickness=80.0, diameter=30.0, glass="AIR", advanced=arm("transmit")),
        SurfaceRow(surface="Aperture", name="TXS", thickness=50.0, diameter=20.0, glass="AIR", advanced=arm("transmit")),
        SurfaceRow(surface="Image", name="TXI", thickness=0.0, diameter=20.0, glass="AIR", advanced=arm("transmit")),
        # reflect arm (folded -90 about X), different lens + smaller stop
        SurfaceRow(surface="Thin Lens", name="RXL", rc=60.0, thickness=50.0, diameter=30.0, glass="AIR", tilt_x=-90.0, advanced=arm("reflect")),
        SurfaceRow(surface="Aperture", name="RXS", thickness=30.0, diameter=10.0, glass="AIR", tilt_x=-90.0, advanced=arm("reflect")),
        SurfaceRow(surface="Image", name="RXI", thickness=0.0, diameter=20.0, glass="AIR", tilt_x=-90.0, advanced=arm("reflect")),
        SurfaceRow(surface="Image", name="GLOBAL", thickness=0.0, diameter=40.0, glass="AIR"),
    ]


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    private, shared, folded = _rows()

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

    # A folded arm must unfold to the same entrance pupil as the straight equivalent.
    try:
        straight_z = _leaf_pupil_z(folded["straight"])
        folded_z = _leaf_pupil_z(folded["folded"], unfold=True)
    except Exception as exc:  # noqa: BLE001
        return False, [f"FAIL: folded-arm unfold raised {type(exc).__name__}: {exc}"]
    if abs(straight_z - folded_z) > 0.5:
        failures.append(
            f"FAIL: a folded arm should unfold to the SAME entrance pupil as the straight "
            f"arm, got straight z={straight_z:.2f} != folded z={folded_z:.2f}"
        )

    # Phase 2 extraction: pull each arm's optical path from ONE tagged two-arm table
    # (branch_selector) and confirm a per-branch launch could aim each at its own pupil.
    from KrakenOS.UI.services.paraxial_tools import _branch_leaf_rows, _scene_branch_selectors

    scene = _two_arm_scene()
    selectors = _scene_branch_selectors(scene)
    if selectors != ["transmit", "reflect"]:
        failures.append(f"FAIL: scene branch selectors {selectors}, expected ['transmit', 'reflect']")
    tx_leaf = _branch_leaf_rows(scene, "transmit")
    rx_leaf = _branch_leaf_rows(scene, "reflect")
    tx_names = [r.name for r in tx_leaf]
    rx_names = [r.name for r in rx_leaf]
    # Each leaf = common (Object + BS) + its OWN arm, never the other arm or the GLOBAL image.
    if tx_names != ["O", "BS", "TXL", "TXS", "TXI"]:
        failures.append(f"FAIL: transmit leaf extraction = {tx_names}")
    if rx_names != ["O", "BS", "RXL", "RXS", "RXI"]:
        failures.append(f"FAIL: reflect leaf extraction = {rx_names}")
    try:
        tx_z = _leaf_pupil_z(tx_leaf, unfold=True)
        rx_z = _leaf_pupil_z(rx_leaf, unfold=True)
    except Exception as exc:  # noqa: BLE001
        return False, [f"FAIL: extracted two-arm leaf pupil raised {type(exc).__name__}: {exc}"]
    if abs(tx_z - rx_z) <= 1.0:
        failures.append(
            f"FAIL: the two extracted arms (different lens+stop) should get DIFFERENT pupils, "
            f"got transmit z={tx_z:.2f} ~= reflect z={rx_z:.2f}"
        )

    # The real dual-lens scene: the FOLDED reflect arm's entry gap (splitter -> first
    # lens) is encoded in the decenter, not the linear thickness; the extraction recovers
    # it so each arm keeps its own object conjugate (MV150 1X: 275 mm; MV120 1X: 215 mm).
    from KrakenOS.common_optical_layouts.beam_splitter_dual_mv_150_120 import SURFACES as DUAL
    from KrakenOS.UI.surface_table_model import SurfaceRow

    dual = [SurfaceRow(**{k: v for k, v in s.items() if k in SurfaceRow.__dataclass_fields__}) for s in DUAL]
    dual_tx = _branch_leaf_rows(dual, "transmit")
    dual_rx = _branch_leaf_rows(dual, "reflect")
    # leaf = [Object, splitter, <lens...>]; object->lens = object.thickness + splitter.thickness.
    tx_conj = float(dual_tx[0].thickness) + float(dual_tx[1].thickness)
    rx_conj = float(dual_rx[0].thickness) + float(dual_rx[1].thickness)
    if abs(tx_conj - 275.0) > 1.0:
        failures.append(f"FAIL: dual-lens transmit object->lens = {tx_conj:.1f}, expected 275 (MV150 1X)")
    if abs(rx_conj - 215.0) > 1.0:
        failures.append(
            f"FAIL: dual-lens reflect object->lens = {rx_conj:.1f}, expected 215 (MV120 1X) -- the "
            f"folded entry gap was not recovered from the decenter"
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
