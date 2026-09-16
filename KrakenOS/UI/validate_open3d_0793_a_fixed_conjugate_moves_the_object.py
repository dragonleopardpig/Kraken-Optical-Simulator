"""bugs/0793 -- a fixed-conjugate lens brings its object distance with it.

flag_20260916_105357, "rays seems like not focusing to sensor": a scene holding the SPO
TCL4.0X-65DI-5M reported the image forming 40.96 mm in front of the sensor. The optics were
ideal (spot 6.6e-12 um at best focus); the CONJUGATE was wrong -- a 110 mm object leg, the
OUTGOING 1x lens's working distance, on a 4x lens that works at 65 mm.

A swap preserves the object leg by design (bugs/0378) and refocuses the image (bugs/0388). For a
lens with a free object distance that is right. For a FIXED-CONJUGATE one it is not: at 110 mm
this lens forms a VIRTUAL image 16.4 mm before its rear group, so there is no best focus for the
refocus to find. bugs/0656 does place the object at the vendor working distance, but only via
``_lens_datasheet_wd_registration``, which needs a lens STEP mesh AND applies the
coincident-principal-plane law bugs/0792 showed is unreachable above about 1x -- and this lens
ships no STEP and is 4x.

Display-free and offline: closed-form optics plus the importer, no app.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from KrakenOS.UI.services import machine_vision_folder_import as mvi  # noqa: E402

SPO = PROJECT_ROOT / "attachment/Information/RD-80000/Drawings/SPO TCL4.0X-65DI-5M"
WWK = PROJECT_ROOT / "attachment/Information/RD-80000/Drawings/WWK10-110CP-111V3"
PYRITE = PROJECT_ROOT / "attachment/Lens/PYRITE_56_80_10x_V38_1097785"


def _trace(f1: float, f2: float, d: float, g: float, object_gap: float, rear_gap: float):
    """Paraxial trace of the emitted groups: (magnification, sensor-minus-image)."""
    a = object_gap + g
    v1 = a * f1 / (a - f1)
    m1 = -v1 / a
    s2 = v1 - d
    b = 1.0 / (1.0 / f2 + 1.0 / s2)
    return m1 * (b / s2), (rear_gap + g) - b


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # ---- A: the flag's arithmetic, from the numbers the saved scene held --------------------
    f1, f2, d, g = 47.112667, -23.882528, 132.5, 5.0
    m_bad, defocus_bad = _trace(f1, f2, d, g, 110.0, 19.526)
    ok(abs(defocus_bad - 40.96) < 0.01,
       f"A: a 110 mm object leg puts the image {defocus_bad:.2f} mm in front of the sensor "
       f"(the flag's banner said 40.96)")
    ok(abs(m_bad) < 1.0,
       f"A: and the magnification collapses to {m_bad:+.4f}, nowhere near the lens's 4x")
    m_ok, defocus_ok = _trace(f1, f2, d, g, 65.0, 17.526)
    ok(abs(defocus_ok) < 1e-3 and abs(abs(m_ok) - 4.0) < 1e-3,
       f"A: at its own 65 mm the same groups give m {m_ok:+.4f} and {defocus_ok:+.4f} mm defocus")

    # ---- B: the surrogate declares the contract, and only when it IS one --------------------
    if SPO.is_dir():
        model = mvi.import_lens_folder(SPO)
        ok(bool(getattr(model, "fixed_conjugate", False)),
           "B: the 4x telecentric declares fixed_conjugate")
        ok(abs(float(model.object_thickness) - 65.0) < 1e-9,
           f"B: and carries its own working distance ({model.object_thickness})")
    else:
        notes.append("SKIP: B: the SPO folder is not in this checkout")

    # the EFL route's object gap is DERIVED, not the vendor's WD -- claiming it would move the
    # object to a number no datasheet states, so those must NOT declare the contract
    for folder, label in ((WWK, "the 1x telecentric (EFL route)"), (PYRITE, "an ordinary lens")):
        if not folder.is_dir():
            notes.append(f"SKIP: B: {label} is not in this checkout")
            continue
        model = mvi.import_lens_folder(folder)
        ok(not bool(getattr(model, "fixed_conjugate", False)),
           f"B: {label} does NOT declare it (its object gap is derived, and bugs/0647 refits it)")

    # ---- C: the swap applies it ---------------------------------------------------------------
    import inspect as _inspect

    from KrakenOS.UI.services import layout_table_workbench as ltw

    source = _inspect.getsource(ltw.LayoutTableWorkbenchMixin.swap_imaging_lens_from_folder)
    ok("fixed_conjugate" in source,
       "C: the swap consults the contract rather than only the STEP-measured registration")
    ok("_lens_datasheet_wd_registration" in source,
       "C: the measured bugs/0656 route is still tried first")
    ok(source.index("_lens_datasheet_wd_registration") < source.index("fixed_conjugate"),
       "C: the model fallback runs AFTER it, so a measurable lens keeps the measured answer")
    ok("_swap_auto_refocus_to_best_focus" in source
       and source.index("fixed_conjugate") < source.index("_swap_auto_refocus_to_best_focus"),
       "C: the object moves BEFORE the refocus -- there is no best focus to find otherwise")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0793 fixed-conjugate object validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
