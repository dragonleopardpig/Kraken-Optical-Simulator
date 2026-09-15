"""bugs/0788 -- two OCR engines with complementary weaknesses, tried in turn.

rapidocr keeps the glyph that decides the value (``110±2``) and returns a box per line so a label
pairs with its value by geometry; its detector misses isolated one-character cells, and on the
COOLENS sheet that loses ``Mount | C`` -- no mount, no flange, no derivation. tesseract finds
those cells but mangles the same ``110±2``. Neither can be declared the winner, so
``ocr_text_candidates`` offers each reading and the CALLER keeps the first that yields a usable,
corroborated result.

Display-free: the engines themselves are stubbed, so this runs offline and in milliseconds. The
real-folder outcome is pinned by bugs/0787's guard.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from KrakenOS.UI.services import datasheet_prescription_import as dpi  # noqa: E402

# a reading that states everything and corroborates (COOLENS wording, bugs/0786)
GOOD = """Large FOV Objective Telecentric Lens
Magnification (x) 1.0
Working Distance (mm) 110±2
Length of I/O (mm) 280±2
Mount C
Length (mm) 152.6
"""
# the same sheet as the weaker engine reads it: the one-character mount cell is missing, so no
# flange can be found and the derivation must not happen
NO_MOUNT = GOOD.replace("Mount C\n", "")
# a reading whose numbers do not agree with the sheet's own printed total
UNCORROBORATED = GOOD.replace("110±2", "1102")
EXPECTED = (110.0 + 152.6 + 17.526) / 4.0


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    saved_engines = dpi._OCR_ENGINES
    saved_probe = dpi._ocr_engine_available
    saved_cache = dpi._OCR_CACHE_DIR
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        dpi._OCR_CACHE_DIR = Path(tmp)
        probe = PROJECT_ROOT / "KrakenOS" / "UI" / "validate_open3d_0788_two_engines_one_reading.py"
        try:
            # ---- A: the master switch is consulted BEFORE the cache ----------------------------
            dpi._OCR_ENGINES = (("stub", lambda _p: GOOD),)
            dpi._ocr_engine_available = lambda: True
            first = dpi.ocr_text_candidates(probe)
            ok(first and GOOD.splitlines()[0] in first[0],
               "A: an available engine's reading is offered")
            ok(any(Path(tmp).glob("*.stub.txt")),
               "A: each engine is cached under its OWN key")
            dpi._ocr_engine_available = lambda: False
            ok(dpi.ocr_text_candidates(probe) == [],
               "A: with OCR switched off, NOTHING is returned -- not even the cached reading")

            # ---- B: every available engine is offered, best-first -------------------------------
            dpi._ocr_engine_available = lambda: True
            dpi._OCR_ENGINES = (("weak", lambda _p: NO_MOUNT), ("strong", lambda _p: GOOD))
            cands = dpi.ocr_text_candidates(probe)
            ok(len(cands) == 2, f"B: both engines are offered ({len(cands)} readings)")
            ok(cands and "Mount C" not in cands[0],
               "B: order is preserved -- the first engine's reading comes first")

            # ---- C: the caller keeps the first reading that actually WORKS ----------------------
            got = dpi._cardinals_from_text(cands[0])
            ok(got is None or not got.effl,
               "C: the weaker reading alone yields nothing (its mount cell is missing)")
            got = dpi._cardinals_from_text(cands[1])
            ok(got is not None and abs(float(got.effl) - EXPECTED) < 0.01,
               f"C: the other reading yields effl {getattr(got, 'effl', None)}")

            # ---- D: a reading that fails CORROBORATION must not win -----------------------------
            dpi._OCR_ENGINES = (("mangled", lambda _p: UNCORROBORATED), ("clean", lambda _p: GOOD))
            readings = dpi.ocr_text_candidates(probe)
            first_result = dpi._cardinals_from_text(readings[0])
            ok(first_result is None or not first_result.effl,
               "D: the mangled reading (110±2 -> 1102) refuses -- the sheet's own total refutes it")
            winner = None
            for text in readings:
                candidate = dpi._cardinals_from_text(text)
                if candidate is not None and candidate.effl:
                    winner = candidate
                    break
            ok(winner is not None and abs(float(winner.effl) - EXPECTED) < 0.01,
               f"D: trying in turn reaches the corroborated reading (effl {getattr(winner, 'effl', None)})")
        finally:
            dpi._OCR_ENGINES = saved_engines
            dpi._ocr_engine_available = saved_probe
            dpi._OCR_CACHE_DIR = saved_cache
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0788 two-engine validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
