"""bugs/0789 -- the image circle sizes the glass, under whatever name the vendor gave it.

A COOLENS WWK10-110CP-111V3 surrogate came out with Ø14.0063 elements -- exactly 1.4x its stop,
the on-axis pupil footprint and nothing else -- inside a Ø44 barrel, for a lens whose datasheet
states ``Max Sensor Size (Φmm) | 18.0(1.1")``. bugs/0662's rule (``max(1.4*stop, image_circle +
stop)``) was already right; its input was missing, because the image-circle scrape lived in TWO
places with DIFFERENT spelling lists and the telecentric path knew only the Edmund one.

Display-free and offline: text in, cardinals out.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from KrakenOS.UI.services import datasheet_prescription_import as dpi  # noqa: E402

LENS_PDF = (PROJECT_ROOT
            / "attachment/Information/RD-80000/Drawings/WWK10-110CP-111V3"
            / "WWK10-110CP-111V3 Datasheet (1).pdf")

SPELLINGS = (
    ("PYRITE", "Max. sensor size [mm] 100", 100.0),
    ("Rodenstock/LINOS", "image circle max. (mm) 82", 82.0),
    ("Edmund", "Maximum Image Circle (mm):11.00", 11.0),
    ("COOLENS", 'Max Sensor Size (Φmm) 18.0(1.1")', 18.0),
    ("COOLENS, OCR'd Φ as @", 'Max Sensor Size (@mm) 18.0(1.1")', 18.0),
    ("COOLENS, OCR'd Φ as ®P", 'Max Sensor Size (®Pmm) 18.0(1.1")', 18.0),
)

TELECENTRIC = """Large FOV Objective Telecentric Lens
Magnification (x) 1.0
Working Distance (mm) 110±2
Max Sensor Size (Φmm) 18.0(1.1")
Best Aperture (F/#) 7
Length of I/O (mm) 280±2
Mount C
Length (mm) 152.6
"""


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # ---- A: every spelling resolves to the same datum ------------------------------------------
    for label, text, expected in SPELLINGS:
        got = dpi._scrape_image_circle(text)
        ok(got is not None and abs(float(got) - expected) < 1e-9,
           f"A: {label}: {text.splitlines()[0][:42]!r} -> {got}")

    # ---- B: it is bounded -- a label match must not admit an absurd diameter --------------------
    for text in ("Maximum Image Circle (mm): 0.02", "Max. sensor size [mm] 99999"):
        ok(dpi._scrape_image_circle(text) is None,
           f"B: refuses an implausible value -- {text!r}")
    ok(dpi._scrape_image_circle("no image circle stated anywhere") is None,
       "B: absent means None, not a fabricated default")

    # ---- C: the TELECENTRIC path exposes it (it used to know one spelling) ----------------------
    card = dpi.telecentric_conjugate_cardinals(TELECENTRIC)
    if card is None:
        ok(False, "C: the telecentric sheet no longer parses at all")
    else:
        ok(card.image_circle is not None and abs(float(card.image_circle) - 18.0) < 1e-9,
           f"C: the telecentric path carries the image circle ({card.image_circle})")
        # bugs/0662's rule, which is what the missing input had been starving
        stop = round(float(card.effl) / float(card.fno), 4)
        expected_aperture = round(max(stop * 1.4, 18.0 + stop), 4)
        ok(abs(expected_aperture - 28.0045) < 0.01,
           f"C: field + pupil sizes the glass at {expected_aperture} mm, not {round(stop * 1.4, 4)}")

    # ---- D: the real sheet ---------------------------------------------------------------------
    if LENS_PDF.exists():
        real = dpi.parse_datasheet_cardinals(LENS_PDF)
        if real is None or not real.effl:
            notes.append("SKIP: D: the real sheet did not parse here (OCR engines absent?)")
        else:
            ok(real.image_circle is not None and abs(float(real.image_circle) - 18.0) < 1e-9,
               f"D: the real WWK10 datasheet -> image circle {real.image_circle}")
    else:
        notes.append("SKIP: D: the WWK10-110CP-111V3 datasheet is not in this checkout")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0789 image-circle validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
