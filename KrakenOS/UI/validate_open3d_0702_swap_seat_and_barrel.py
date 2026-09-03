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
    # bugs/0703: the seat is desp + its ScenePlacement breadcrumb TOGETHER --
    # a carried desp WITHOUT the 0691 ``frame_seat`` marker reads as a hand-
    # tilted prescription, the paraxial reference refuses the layout, and the
    # imaging launch grid collapses to ONE field point per face (the user's
    # "only one point of ray launching ... instead of 3").
    ok(
        '"ScenePlacement"' in src and "deepcopy(old_placement)" in src,
        "A2: the swap carries the front datum's ScenePlacement breadcrumb with the "
        "desp (paraxial reference stays alive; launch grid keeps its 3x3 spread)",
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
    from KrakenOS.UI.services.machine_vision_folder_import import (
        _step_glass_aperture,
        import_lens_folder,
    )

    # bugs/0703 (third oversized flag): the GLASS aperture outranks the barrel --
    # the PYRITE 5.6/80 STEP shows ~23.8 mm glass inside its 46 mm collar, and
    # the drawn discs must hug the glass the user actually sees.
    glass = _step_glass_aperture(next(PYRITE_80.glob("*.stp")))
    ok(
        glass is not None and abs(float(glass) - 23.8169) < 0.05,
        f"C1: the PYRITE 5.6/80 measured glass aperture is 23.82 ({glass})",
    )
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
        front is not None and glass is not None and abs(diameter - float(glass)) < 0.01,
        f"C2: the Black-Box import clamps the datum discs to the measured glass "
        f"({diameter} mm; was 47.0318 bbox, then 46.0 collar)",
    )


def _check_clamp_wiring(ok, notes) -> None:
    import KrakenOS.UI.services.machine_vision_folder_import as mvi

    src = inspect.getsource(mvi)
    count = src.count("_step_glass_aperture(assets.primary_step)")
    fallback_ok = src.count(
        "or _step_barrel_diameter(assets.primary_step)"
    ) == count and src.count("or _step_transverse_extent(assets.primary_step)") == count
    ok(
        count == 2 and fallback_ok,
        f"D: both importer clamp sites prefer glass, then cylinder barrel, then "
        f"bbox extent ({count} of 2 wired, fallbacks {'ok' if fallback_ok else 'MISSING'})",
    )


def _check_display_only_flip(ok, notes) -> None:
    """bugs/0703 ("after clicking flip, not functioning ... any STEP manipulation
    should stop ray tracing"): the lens/camera flips route through the render-only
    cached-scene refresh -- refresh_from_editor on a promoted-STEP scene forces
    the full NS retrace and buried the flip under minutes of tracing."""
    from types import SimpleNamespace

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    for handler in ("_flip_lens_step_direction_from_context", "_flip_camera_step_direction_from_context"):
        src = inspect.getsource(getattr(Open3DFaceAssignmentService, handler))
        ok(
            "self.refresh_step_overlay_display_only(" in src
            and "self.refresh_from_editor()" not in src,
            f"E1: {handler} uses the render-only display refresh",
        )

    calls = []

    class _Stub:
        editor = SimpleNamespace(
            _open3d_trace_refresh_service=lambda: SimpleNamespace(
                can_reuse_current_scene_for_display_toggle=lambda _inspector: True
            )
        )
        _current_system = object()
        _current_rays = object()
        _current_row_names = ["r"]
        _current_scene_bundle = object()

        def _debug_trace(self, *a, **k):
            pass

        def refresh_scene(self, *a, **k):
            calls.append("refresh_scene")

        def refresh_from_editor(self, *a, **k):
            calls.append("refresh_from_editor")

    stub = _Stub()
    stub.editor = SimpleNamespace(
        _open3d_trace_refresh_service=lambda: SimpleNamespace(
            can_reuse_current_scene_for_display_toggle=lambda _inspector: True
        )
    )
    Kraken3DInspector.refresh_step_overlay_display_only(stub, "guard")
    ok(
        calls == ["refresh_scene"],
        f"E2: with a valid cached scene the helper re-renders WITHOUT a rebuild ({calls})",
    )
    calls.clear()
    stub.editor = SimpleNamespace(
        _open3d_trace_refresh_service=lambda: SimpleNamespace(
            can_reuse_current_scene_for_display_toggle=lambda _inspector: False
        )
    )
    Kraken3DInspector.refresh_step_overlay_display_only(stub, "guard")
    ok(
        calls == ["refresh_from_editor"],
        f"E3: with no cached scene the helper falls back to the full refresh ({calls})",
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
        _check_display_only_flip,
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
