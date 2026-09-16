"""bugs/0791 -- a CAD title block is typeset ROTATED, so read it that way.

The failure bugs/0565 worked around was never a broken PDF. A drawing's title block is typeset at
90 degrees, and a reading-order extractor walks it the wrong way: every label comes out in one run
and every value in another --

    Optical MgnificationResolution(um)W.D(mm)N.AF/#... 4.0X 652.090.1612.5...

-- so no ``Label: value`` regex can pair them and the sheet looks like it states nothing. On the
SPO TCL4.0X-65DI-5M all 284 characters report ``upright=False``.

Assembling from character POSITIONS in the rotated frame recovers the table as drawn, with no OCR,
no DWG and no external binary.

Display-free; the real-file checks skip when the drawing is absent.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from KrakenOS.UI.services import datasheet_prescription_import as dpi  # noqa: E402

DRAWING = (PROJECT_ROOT / "attachment/Information/RD-80000/Drawings/SPO TCL4.0X-65DI-5M"
           / "TCL4.0X-65DI-5M-V2.pdf")
READABLE = (PROJECT_ROOT / "attachment/Lens/PYRITE_56_80_10x_V38_1097785"
            / "PYRITE_56_80_10x_V38_1097785_datasheet.pdf")


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    if not DRAWING.exists():
        notes.append("SKIP: the SPO TCL4.0X-65DI-5M drawing is not in this checkout")
    else:
        # ---- A: the ordinary reading order really does orphan the values -----------------------
        plain = dpi.extract_pdf_text(DRAWING)
        ok("Mgnification" in plain and "Mgnification 4.0X" not in plain,
           "A: the reading-order text has the label but not the pair (the bug being fixed)")

        # ---- B: the rotated assembly pairs them --------------------------------------------
        layout = dpi._extract_pdf_text_layout(DRAWING)
        for want in ("Optical Mgnification 4.0X", "W.D(mm) 65", "F/# 12.5", "N.A 0.16"):
            ok(want in layout, f"B: the rotated assembly yields {want!r}")
        ok("F.O.V : 2.2mm X 1.65mm" in layout,
           "B: word spacing is right -- gaps measured against each glyph's own set width")

        # ---- C: it is a CANDIDATE, offered before the slow engines ---------------------------
        cands = dpi.text_candidates(DRAWING)
        ok(bool(cands) and "Optical Mgnification 4.0X" in cands[0],
           "C: the layout reading is offered FIRST, ahead of any OCR")

    # ---- D: an ordinary upright datasheet is untouched ------------------------------------
    if READABLE.exists():
        upright = dpi._extract_pdf_text_layout(READABLE)
        ok(bool(upright.strip()), "D: an upright sheet still assembles")
        card = dpi.parse_datasheet_cardinals(READABLE)
        ok(card is not None and card.effl is not None and abs(float(card.effl) - 82.39) < 0.01,
           f"D: the upright sheet still parses from its text layer (effl {getattr(card, 'effl', None)})")
    else:
        notes.append("SKIP: D: the PYRITE reference datasheet is not in this checkout")

    # ---- E: it degrades, never raises ------------------------------------------------------
    ok(dpi._extract_pdf_text_layout(PROJECT_ROOT / "does-not-exist.pdf") == "",
       "E: a missing file yields empty text rather than an exception")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0791 rotated-title-block validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
