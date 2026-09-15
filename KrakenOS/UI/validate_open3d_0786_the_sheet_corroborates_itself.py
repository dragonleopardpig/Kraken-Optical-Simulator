"""bugs/0786 -- a spec table is a table, and the sheet checks its own arithmetic.

The COOLENS WWK10-110CP-111V3 states its whole first order in an Optical Specifications TABLE
(``Magnification (x) | 1.0``, ``Working Distance (mm) | 110+-2``, ``Mount | C``,
``Length (mm) | 152.6``), yet bugs/0653's telecentric derivation refused it: four of its six
gates were written for the Edmund #67-304 TITLE format and missed on typography alone.

The fix reads the table wording AND earns bugs/0565's corroboration from the sheet's own printed
total -- ``Length of I/O = WD + Length + Back Focal Length`` -- instead of from a title. That
arithmetic is what keeps an OCR'd sheet safe: recognising ``110+-2`` as ``1102`` gives a total of
1272 mm against a printed 280, so the sheet refutes the misread itself and the import refuses.

Display-free and offline: text in, cardinals out. No Tk, no VTK, no PDF needed.
"""

from __future__ import annotations

from KrakenOS.UI.services.datasheet_prescription_import import telecentric_conjugate_cardinals

# The sheet's own words, as printed in its rasterised table (see bugs/0786 for the render).
COOLENS_TABLE = """WWK10-110CP-111V3
Large FOV Objective Telecentric Lens
Optical Specifications
Magnification (x) 1.0
Working Distance (mm) 110±2
Max Sensor Size (Φmm) 18.0(1.1")
Best Aperture (F/#) 7
Length of I/O (mm) 280±2
Mechanical Specifications
Mount C
Length (mm) 152.6
2. Length of I/O = WD + Length + Back Focal Length.
"""

# An Edmund-format sheet states NO total and earns corroboration from its title instead; it must
# keep working, so the arithmetic route is an ALTERNATIVE and never a replacement.
EDMUND_TITLE = """0.75X, 110mm WD, CompactTL Telecentric Lens
Primary Magnification PMAG: 0.75 X
Working Distance (mm): 110
Length (mm): 155
Mount: C-Mount
"""


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # ---- A: the table wording parses, and to the right number ----------------------------------
    card = telecentric_conjugate_cardinals(COOLENS_TABLE)
    expected = (110.0 + 152.6 + 17.526) / (2.0 + 1.0 + 1.0)
    if card is None:
        ok(False, "A: the table-typography sheet still refuses")
    else:
        ok(abs(float(card.effl) - expected) < 0.01,
           f"A: table sheet -> effl {card.effl} (T/4 = {expected:.4f})")
        ok(abs(float(card.magnification) + 1.0) < 1e-9,
           f"A: magnification read from 'Magnification (x) 1.0' -> {card.magnification}")
        ok(abs(float(card.optimum_wd) - 110.0) < 1e-9, f"A: WD -> {card.optimum_wd}")
        ok(abs(float(card.span) - 152.6) < 1e-9, f"A: housing length -> {card.span}")
        ok(abs(float(card.mount_flange_mm) - 17.526) < 1e-9,
           f"A: bare 'Mount C' cell -> flange {card.mount_flange_mm}")

    # ---- B: every way the arithmetic can fail must REFUSE ---------------------------------------
    mutants = (
        ("a stated total that does not match wd+L+flange",
         COOLENS_TABLE.replace("280±2", "999")),
        ("no stated total at all (nothing to corroborate with)",
         COOLENS_TABLE.replace("Length of I/O (mm) 280±2\n", "")),
        ("the OCR misread '110±2' -> '1102'",
         COOLENS_TABLE.replace("110±2", "1102")),
        ("no mount row (the flange is unknown)",
         COOLENS_TABLE.replace("Mount C\n", "")),
        ("no magnification row",
         COOLENS_TABLE.replace("Magnification (x) 1.0\n", "")),
        ("not a telecentric sheet at all",
         COOLENS_TABLE.replace("Telecentric", "Fixed Focal")),
    )
    for label, text in mutants:
        ok(telecentric_conjugate_cardinals(text) is None, f"B: refuses -- {label}")

    # ---- C: the Edmund title route is untouched -------------------------------------------------
    edmund = telecentric_conjugate_cardinals(EDMUND_TITLE)
    ok(edmund is not None and edmund.effl is not None,
       "C: a sheet with NO stated total still corroborates from its title (0653 route intact)")
    if edmund is not None:
        expected_e = (110.0 + 155.0 + 17.526) / (2.0 + 0.75 + 1.0 / 0.75)
        ok(abs(float(edmund.effl) - expected_e) < 0.01,
           f"C: Edmund-format effl {edmund.effl} (T/(2+m+1/m) = {expected_e:.4f})")

    # ---- D: the arithmetic route cannot be satisfied by a coincidence ---------------------------
    # a total that matches only because the mount was guessed must not pass: drop the mount and
    # the derivation has no flange, so there is nothing to check the total against.
    ok(telecentric_conjugate_cardinals(
        COOLENS_TABLE.replace("Mount C\n", "Mount Q\n")) is None,
       "D: an unrecognised mount refuses rather than assuming a flange")
    return (not problems), notes


def main() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("bugs/0786 sheet-corroboration validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
