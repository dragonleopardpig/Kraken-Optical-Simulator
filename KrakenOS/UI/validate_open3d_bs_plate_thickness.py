"""Guard: the one-click BS PLATE default is a THIN substrate, not a fraction-of-aperture slab (bugs/0422).

Flag flag_20260723_115239: "Added a BS Plate ... the thickness is ridiculously thick." The plate default
thickness was ``side_mm * 0.12`` (12% of the LED opening) clamped to ``[2, side_mm*0.5]`` -- ~11 mm on a
90 mm opening. A plate beam splitter is a THIN substrate (~1-5 mm), independent of aperture. Fixed to
``min(max(side_mm*0.04, 1.0), 5.0)``.

Checks
------
* THIN-FORMULA -- ``add_beam_splitter_to_led`` sizes the plate thickness with the thin clamp (1-5 mm), not
  the old ``side_mm * 0.12`` slab.
* THIN-VALUES  -- across LED openings 8..90 mm the default thickness stays <= 5 mm (and <= ~6% of the
  face for a real aperture), so a plate never renders as a thick block.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_bs_plate_thickness

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def _plate_thickness(side_mm: float) -> float:
    """Reference reimplementation of the shipped default (bugs/0422)."""
    return min(max(side_mm * 0.04, 1.0), 5.0)


def _check_thin_formula(failures, notes):
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin as _Mixin
    src = inspect.getsource(_Mixin.add_beam_splitter_to_led)
    if "side_mm * 0.12" in src:
        failures.append("THIN-FORMULA: the plate thickness still uses the thick side_mm*0.12 slab")
    if "min(max(side_mm * 0.04, 1.0), 5.0)" not in src:
        failures.append("THIN-FORMULA: the plate thickness must use the thin 1-5 mm clamp (side_mm*0.04)")
    if not [f for f in failures if f.startswith("THIN-FORMULA")]:
        notes.append("thin-formula = plate thickness = min(max(side*0.04, 1), 5) mm (a thin substrate)")


def _check_thin_values(failures, notes):
    worst = 0.0
    for side in (8.0, 25.0, 50.0, 77.0, 90.0):
        t = _plate_thickness(side)
        worst = max(worst, t)
        if t > 5.0 + 1e-9:
            failures.append(f"THIN-VALUES: plate thickness {t:.2f} mm at aperture {side:.0f} mm exceeds 5 mm")
        # a plate must stay thinner than its face (beam_splitter_factory rejects thickness >= min(w,h))
        if t >= side:
            failures.append(f"THIN-VALUES: plate thickness {t:.2f} mm not thinner than the {side:.0f} mm face")
    if not [f for f in failures if f.startswith("THIN-VALUES")]:
        notes.append(f"thin-values = default thickness stays <= {worst:.1f} mm across 8-90 mm openings")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_thin_formula, _check_thin_values):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_bs_plate_thickness (bugs/0422) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll BS-plate-thickness checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
