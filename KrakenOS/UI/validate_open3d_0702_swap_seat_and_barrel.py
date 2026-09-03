"""Guard for bugs/0702 -- flag 094237 "swapped lens with 80mm, lens surrogate is
oversized. This is bug re-occurrence, multiple times."

Two general defects behind the recurrence:

1. SEAT LOSS: `swap_imaging_lens_from_folder` dropped the outgoing front datum's
   desp/tilt -- the om05a vendor-seat FRAME-DESP (the 0689 seat is ONE desp on
   the first follower row, a property of the LEG, not the lens). The 0547
   frozen-frame restore only engages when a block row is WORLD-placed; a lens
   block that walks sequentially from a frozen fold row got None and the fresh
   block landed with desp 0 (reproduced: (-6.08, 0, -0.3885) -> zeros on every
   swap). The swap now carries the old front datum's desp + tilt onto the
   replacement front datum.

2. WRONG HOUSING MEASURE: the 0668 clamp used the bbox MIDDLE extent as "the
   barrel". For x-authored / square-flanged vendor CAD (the PYRITE family:
   extents ~47 x 50 x 46) that number is the AXIAL LENGTH or the flange, not the
   glass housing -- the discs clamped to 47.03/48.56 and overhung the visible
   barrel. `_step_barrel_diameter` now measures the largest SUBSTANTIAL
   co-axial cylinder face (area-gated so a short flange BORE cannot pose as the
   barrel): 46.0 on the PYRITE family, CAD truth.

Checks:
  A  source-pin: the swap carries the old front datum's desp/tilt onto the new
     block's front datum.
  B  real STEP (skip-if-absent): the PYRITE 5.6/80 barrel measures 46.0 by
     cylinders, below the 47.03 bbox middle extent.
  C  real import (skip-if-absent): the PYRITE 5.6/80 Black-Box import clamps its
     datum discs to the cylinder barrel (46.0).
  D  wiring: BOTH importer clamp sites prefer `_step_barrel_diameter` with the
     bbox extent as fallback.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0702_swap_seat_and_barrel
"""

from __future__ import annotations

import inspect
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYRITE_80 = PROJECT_ROOT / "attachment/Lens/PYRITE_56_80_10x_V38_1097785"


def _check_swap_seat_carry(ok, notes) -> None:
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    src = inspect.getsource(LayoutTableWorkbenchMixin.swap_imaging_lens_from_folder)
    ok(
        "old_front_row = self.rows[front]" in src
        and '"desp_x", "desp_y", "desp_z", "tilt_x", "tilt_y", "tilt_z"' in src
        and "setattr(new_block[0], field" in src,
        "A: the swap carries the outgoing front datum's desp+tilt (the vendor-seat "
        "frame-desp) onto the replacement front datum",
    )


def _check_barrel_measure(ok, notes) -> None:
    from KrakenOS.UI.services.machine_vision_folder_import import (
        _step_barrel_diameter,
        _step_transverse_extent,
    )

    step = next(PYRITE_80.glob("*.stp"), None) if PYRITE_80.exists() else None
    if step is None:
        notes.append("SKIP: B: the PYRITE 5.6/80 folder is not in this checkout")
        return
    barrel = _step_barrel_diameter(step)
    extent = _step_transverse_extent(step)
    ok(
        barrel is not None
        and abs(float(barrel) - 46.0) < 0.2
        and extent is not None
        and float(barrel) < float(extent),
        f"B: PYRITE 5.6/80 cylinder barrel = {barrel} (bbox middle extent {extent} "
        f"was the axial length)",
    )


def _check_import_clamp(ok, notes) -> None:
    if not PYRITE_80.exists():
        notes.append("SKIP: C: the PYRITE 5.6/80 folder is not in this checkout")
        return
    from KrakenOS.UI.services.machine_vision_folder_import import import_lens_folder

    model = import_lens_folder(str(PYRITE_80))
    front = next(
        (
            surface
            for surface in model.surfaces
            if "Front" in str(surface.get("name", "")) and "Datum" in str(surface.get("name", ""))
        ),
        None,
    )
    diameter = float(front.get("diameter", 0.0)) if front else 0.0
    ok(
        front is not None and abs(diameter - 46.0) < 0.2,
        f"C: the Black-Box import clamps the datum discs to the cylinder barrel "
        f"({diameter} mm; was 47.0318 = the bbox axial length)",
    )


def _check_clamp_wiring(ok, notes) -> None:
    import KrakenOS.UI.services.machine_vision_folder_import as mvi

    src = inspect.getsource(mvi)
    count = src.count(
        "_step_barrel_diameter(assets.primary_step) or _step_transverse_extent(assets.primary_step)"
    )
    ok(
        count == 2,
        f"D: both importer clamp sites prefer the cylinder barrel with the bbox "
        f"extent as fallback ({count} of 2 wired)",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for check in (
        _check_swap_seat_carry,
        _check_barrel_measure,
        _check_import_clamp,
        _check_clamp_wiring,
    ):
        try:
            check(ok, notes)
        except Exception as exc:
            notes.append(f"FAIL: {check.__name__} raised {type(exc).__name__}: {exc}")
    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0702 swap-seat + barrel validation PASSED")
        return 0
    print("0702 swap-seat + barrel validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
