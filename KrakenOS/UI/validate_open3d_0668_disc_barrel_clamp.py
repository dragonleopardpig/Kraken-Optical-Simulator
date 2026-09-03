"""Guard for bugs/0668 -- surrogate discs: the object-field rule is TELECENTRIC-only,
and no disc exceeds the lens's own barrel.

6-sided.png (2026-08-31): every station of the user's first solved cell wore a pair of
320 mm teal discs -- the PYRITE 4.5/90/0.3x, whose real barrel is 50 mm. bugs/0662
grew discs to ``image_circle x 1/|m| + stop`` for ANY lens stating a magnification;
that object-side scaling is the physics of an object-space TELECENTRIC (chief rays
parallel -- the front glass really spans the object field). An ordinary lens funnels
its whole field through the pupil: the PYRITE's "Rec. magnification -0.3" turned its
90 mm line-scan image circle into 300 mm of drawn glass. Two-part fix: the 1/|m|
scaling now requires ``cardinals.telecentric`` (set by the telecentric-conjugate
parser and by the word on the sheet), and every disc is clamped to the bundled STEP
body's transverse extent -- the barrel -- since no lens's glass exceeds its housing.

Checks:
  A  RULE (pure): identical cardinals sized both ways -- non-telecentric keeps
     ``image_circle + stop``; telecentric scales by 1/|m|; the transverse extent is
     the MIDDLE bounding-box extent (the barrel diameter whether the lens is longer
     or shorter than it is wide).
  B  REAL FOLDERS (skip-if-absent): the PYRITE 4.5/90/0.3x disc equals its barrel
     (~50 mm, was 320.18) and still covers its pupil; the 67304 0.75x telecentric
     keeps its 0662 field-sized disc (~19.96).
  C  WIRING: the datasheet parser stamps ``telecentric`` from the sheet text; the
     telecentric-conjugate parser always stamps it; the Black-Box path carries the
     same barrel clamp.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0668_disc_barrel_clamp
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYRITE = PROJECT_ROOT / "attachment/Lens/PYRITE_45_90_03x_V38_1097784"
TELE_075 = PROJECT_ROOT / "attachment/Lens/67304_0.75X_Telecentric"


def _check_rule(ok, notes) -> None:
    import KrakenOS.UI.services.machine_vision_folder_import as mvi
    from KrakenOS.UI.services.datasheet_prescription_import import DatasheetCardinals

    with tempfile.TemporaryDirectory() as tmp:
        bare = mvi.scan_lens_folder(tmp)  # no STEP, no PDF -> no housing clamp
        base = dict(effl=90.8, fno=4.5, image_circle=90.0, magnification=-0.3, span=43.47)
        plain = mvi._core_from_datasheet_cardinals(DatasheetCardinals(**base), bare)
        tele = mvi._core_from_datasheet_cardinals(
            DatasheetCardinals(**base, telecentric=True), bare
        )
    stop = plain.stop_diameter
    ok(
        abs(plain.front_aperture - (90.0 + stop)) < 0.01,
        f"A1: a NON-telecentric's disc is image_circle + stop ({plain.front_aperture:.2f}), no 1/|m|",
    )
    ok(
        abs(tele.front_aperture - (300.0 + stop)) < 0.01,
        f"A2: the SAME cardinals marked telecentric scale to the object field ({tele.front_aperture:.2f})",
    )
    real_bounds = mvi._step_bounds_extents
    try:
        for extents, want, label in (
            ([46.08, 50.06, 51.98], 50.06, "squat barrel"),
            ([30.0, 80.0, 30.0], 30.0, "long barrel, CAD axis = Y"),
        ):
            mvi._step_bounds_extents = lambda _p, _e=extents: list(_e)
            got = mvi._step_transverse_extent("ignored.step")
            ok(abs(got - want) < 1e-9, f"A3: transverse = MIDDLE extent ({label}: {got})")
    finally:
        mvi._step_bounds_extents = real_bounds


def _check_real_folders(ok, notes) -> None:
    from KrakenOS.UI.services.machine_vision_folder_import import (
        _step_barrel_diameter,
        _step_transverse_extent,
        build_surrogate_from_assets,
        scan_lens_folder,
    )

    if PYRITE.exists():
        model = build_surrogate_from_assets(scan_lens_folder(PYRITE))
        # bugs/0702: the clamp now measures the REAL barrel (largest substantial
        # co-axial cylinder face -- 46.0 on the PYRITE family) instead of the bbox
        # middle extent (50.06 -- for x-authored / square-flanged CAD that number
        # is the axial length or the flange, not the glass housing).
        step = next(PYRITE.glob("*.stp"))
        barrel = _step_barrel_diameter(step) or _step_transverse_extent(step)
        ok(
            barrel is not None
            and abs(model.front_aperture - barrel) < 0.01
            and model.front_aperture >= 1.4 * model.stop_diameter
            and model.front_aperture < 60.0,
            f"B1: the PYRITE 4.5/90/0.3x disc is its cylinder barrel ({model.front_aperture:.2f} mm "
            f"vs barrel {barrel}; was 320.18, then bbox 50.06)",
        )
    else:
        notes.append("SKIP: B1: the PYRITE folder is not in this checkout")
    if TELE_075.exists():
        model = build_surrogate_from_assets(scan_lens_folder(TELE_075))
        ok(
            model.front_aperture >= 11.0 / 0.75 + 0.9 * model.stop_diameter,
            f"B2: the 0.75x telecentric KEEPS its 0662 field-sized disc ({model.front_aperture:.2f} mm)",
        )
    else:
        notes.append("SKIP: B2: the 67304 folder is not in this checkout")


def _check_wiring(ok, notes) -> None:
    import KrakenOS.UI.services.machine_vision_folder_import as mvi
    from KrakenOS.UI.services.datasheet_prescription_import import (
        parse_datasheet_cardinals,
        telecentric_conjugate_cardinals,
    )

    pyrite_pdf = next(PYRITE.glob("*.pdf"), None)
    tele_pdf = next(
        (PROJECT_ROOT / "attachment/Lens/63745_1X_Telecentric").glob("*.pdf"), None
    )
    if pyrite_pdf is None or tele_pdf is None:
        notes.append("SKIP: C1: the real datasheet PDFs are not in this checkout")
    else:
        pyrite = parse_datasheet_cardinals(pyrite_pdf)
        tele = parse_datasheet_cardinals(tele_pdf)
        ok(
            pyrite is not None and not pyrite.telecentric and pyrite.magnification is not None
            and tele is not None and tele.telecentric,
            f"C1: the parser stamps `telecentric` from the sheet -- PYRITE False despite "
            f"m={None if pyrite is None else pyrite.magnification}, 63745 sheet True",
        )
    ok(
        "telecentric = True" in inspect.getsource(telecentric_conjugate_cardinals),
        "C2: the telecentric-conjugate parser always stamps it",
    )
    src = inspect.getsource(mvi._core_from_prescription_data)
    ok(
        "_step_transverse_extent" in src,
        "C3: the Black-Box path carries the same barrel clamp",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_rule), ("B", _check_real_folders), ("C", _check_wiring)):
        try:
            fn(ok, notes)
        except Exception as exc:  # pragma: no cover - environment
            notes.append(f"FAIL: section {section} raised ({type(exc).__name__}: {exc})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Disc-barrel-clamp validation passed.")
        return 0
    print("Disc-barrel-clamp validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
