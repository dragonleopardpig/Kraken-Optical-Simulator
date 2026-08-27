"""Guard for bugs/0653 -- a fixed-conjugate TELECENTRIC datasheet that states NO focal
length imports anyway: the conjugates derive the EFL.

The user's error.png (2026-08-27): "Could not build a surrogate from this folder:
.../67304_0.75X_Telecentric ... the datasheet PDF did not yield an effective focal
length". The Edmund CompactTL sheet has no focal-length row at all -- it pins the first
order mechanically instead: magnification 0.75X, Working Distance 110 mm, housing
Length 160.01 mm, C-Mount. With coincident principals (the bugs/0565-style nominal)
the fixed conjugate T = WD + L + FFD gives

    f = (WD + L + FFD) / (2 + m + 1/m)  =  287.536 / 4.08333  =  70.417 mm.

Two lessons pinned here beyond the parse:
  * every value must be CORROBORATED (this format's title repeats "0.75X, 110mm WD");
    anything missing or ambiguous refuses -- the honest "cannot derive" error stays.
  * the housing length is the VERTEX SPAN: a telecentric barrel is far longer than its
    EFL, and both the STEP-extent span (the CAD Z can be the DIAMETER when the model's
    axis is not Z -- measured 29.5 on this STEP) and the 0.7*EFL cap produce a block
    too short to hold the principal f(1+1/m)-WD = 54.3 mm behind the rim, so the
    bugs/0647 refit has no room and falls back to the advisory (measured: mismatch
    -37.65 with the short block; +0.00 with span = length).

Checks:
  A  REAL PDF (skip-if-absent): the #67-304 sheet parses to EFL 70.417, m -0.75,
     WD 110 @ 0.75x, span 160.01, f/13.3, image circle 11, id 67-304.
  B  DERIVATION on embedded text: the formula, the C-mount flange, and the refusals
     (no mount / no telecentric marker / uncorroborated WD / absurd magnification).
  C  REGRESSION: the ELS-85 sheet (skip-if-absent) still parses by its designation
     path (85 / f4.5 / WD 142 @ 1.0x); a non-telecentric text never enters this path.
  D  WIRING: parse_datasheet_cardinals falls through to the telecentric derivation,
     and the folder importer honors the datasheet vertex span.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0653_telecentric_datasheet_import
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TELE_PDF = PROJECT_ROOT / "attachment/Lens/67304_0.75X_Telecentric/spec_67304.pdf"
ELS_PDF = PROJECT_ROOT / "attachment/Lens/ELS-85-4.5V16K/ELS-85 4.5V16K_specification.pdf"

# The Edmund flattened-extraction shape, minimally: label:value runs with no spaces.
_TELE_TEXT = (
    "0.75X, 110mm WD, In-Line CompactTL Telecentric Lens#67-304"
    "Length (mm):160.01Length excluding Threads (mm):160.01Maximum Diameter (mm):29.5"
    "Numerical Aperture NA, Object Side:0.028Working Distance Tolerance (mm):±1"
    "Primary Magnification PMAG:0.75XTelecentric Lens Magnification:0.75"
    "Working Distance (mm):110Aperture (f/#):f/13.3Maximum Image Circle (mm):11.00"
    "Filter Thread:M25.5 x 0.50 (Female)Mount:C-Mount"
)


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.datasheet_prescription_import import (
        parse_datasheet_cardinals,
        telecentric_conjugate_cardinals,
    )

    # ---------------------------------------------------------------- A: real PDF
    if TELE_PDF.exists():
        a_problems = []
        c = parse_datasheet_cardinals(TELE_PDF)
        if c is None:
            a_problems.append("the #67-304 sheet yields no cardinals (error.png returns)")
        else:
            for field, want, tol in (
                ("effl", 70.417, 0.01),
                ("magnification", -0.75, 1e-9),
                ("optimum_wd", 110.0, 1e-9),
                ("optimum_wd_mag", 0.75, 1e-9),
                ("span", 160.01, 1e-6),
                ("fno", 13.3, 1e-9),
                ("image_circle", 11.0, 1e-9),
            ):
                value = getattr(c, field)
                if value is None or abs(float(value) - want) > tol:
                    a_problems.append(f"{field}={value}, want {want}")
            if c.lens_id != "67-304":
                a_problems.append(f"lens_id={c.lens_id!r}")
        if a_problems:
            ok = False
            notes.append(f"FAIL: A (bugs/0653): {a_problems}")
        else:
            notes.append("PASS: A: the real #67-304 sheet parses (EFL 70.417 derived)")
    else:
        notes.append("SKIP: A: the 67304 folder is not in this checkout")

    # ---------------------------------------------------------------- B: derivation
    b_problems = []
    c = telecentric_conjugate_cardinals(_TELE_TEXT)
    if c is None:
        b_problems.append("the embedded telecentric text refuses")
    else:
        want = (110.0 + 160.01 + 17.526) / (2.0 + 0.75 + 1.0 / 0.75)
        if abs(c.effl - want) > 0.01:
            b_problems.append(f"derived EFL {c.effl}, formula says {want:.4f}")
        if c.span is None or abs(c.span - 160.01) > 1e-6:
            b_problems.append(
                f"span={c.span}, want the housing length (the bugs/0647 refit needs the "
                f"room -- principal 54.3 mm behind the rim)"
            )
    for label, mutant in (
        ("no mount row", _TELE_TEXT.replace("Mount:C-Mount", "")),
        ("no telecentric marker", _TELE_TEXT.replace("Telecentric", "Macro").replace("telecentric", "macro")),
        ("uncorroborated WD", _TELE_TEXT.replace("110mm WD", "999mm WD")),
        ("absurd magnification", _TELE_TEXT.replace("PMAG:0.75X", "PMAG:55X").replace("0.75X,", "55X,").replace("Magnification:0.75", "Magnification:55")),
    ):
        if telecentric_conjugate_cardinals(mutant) is not None:
            b_problems.append(f"{label} did NOT refuse")
    if b_problems:
        ok = False
        notes.append(f"FAIL: B (bugs/0653): {b_problems}")
    else:
        notes.append("PASS: B: conjugate formula + C-mount flange; all four mutants refuse")

    # ---------------------------------------------------------------- C: regression
    c_problems = []
    if ELS_PDF.exists():
        e = parse_datasheet_cardinals(ELS_PDF)
        if e is None or e.effl != 85.0 or e.fno != 4.5 or e.optimum_wd != 142.0:
            c_problems.append(f"ELS-85 regression broke: {e}")
    else:
        notes.append("SKIP: C(ELS): the ELS-85 folder is not in this checkout")
    if telecentric_conjugate_cardinals("Focal length [mm] 85 ordinary lens text") is not None:
        c_problems.append("a non-telecentric text entered the telecentric path")
    if c_problems:
        ok = False
        notes.append(f"FAIL: C (bugs/0653): {c_problems}")
    else:
        notes.append("PASS: C: ELS-85 designation path untouched; non-telecentric text stays out")

    # ---------------------------------------------------------------- D: wiring
    import inspect as _inspect

    d_problems = []
    from KrakenOS.UI.services import datasheet_prescription_import as dpi
    from KrakenOS.UI.services import machine_vision_folder_import as mvi

    parse_src = _inspect.getsource(dpi.parse_datasheet_cardinals)
    if "telecentric_conjugate_cardinals(" not in parse_src:
        d_problems.append("parse_datasheet_cardinals never tries the telecentric path")
    mvi_src = _inspect.getsource(mvi)
    if "datasheet vertex span" not in mvi_src:
        d_problems.append("the folder importer no longer honors the datasheet vertex span")
    if d_problems:
        ok = False
        notes.append(f"FAIL: D (bugs/0653): {d_problems}")
    else:
        notes.append("PASS: D: parser fallthrough + importer span wiring intact")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Telecentric-datasheet-import validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
