# 0786 -- a spec table is a table, and the sheet checks its own arithmetic

User, correcting bugs/0785's write-up: *"WWK10-110CP-111V3: the magnification is on the first
row in the datasheet table."* Correct, and the earlier claim ("states no focal length and no
magnification at all") was wrong. Rendering the page shows a full **Optical Specifications**
table whose first row is `Magnification (x) | 1.0`, with `Working Distance (mm) | 110+-2`,
`Mount | C` and `Length (mm) | 152.6` beside it. The claim had been made from the flattened text
without looking at the page.

Two independent things stood between that table and an import.

## 1 -- the table is a picture, not text

Measured with `pdfplumber` on `WWK10-110CP-111V3 Datasheet (1).pdf`:

| | |
|---|---|
| character objects on the page | **212** |
| of those, in the top 62% (where the tables are) | **26** -- exactly `WWK10-110CP-111V3` + `Datasheet` |
| images on the page | 4 |

Every spec row is inside one of those images. No text extractor can read it; bugs/0785's work
does not apply, because there is no text layer to decode.

## 2 -- even with perfect text, the telecentric path refused

bugs/0653 derives the EFL of a fixed-conjugate telecentric sheet from `T = WD + L + FFD` and
`f = T / (2 + m + 1/m)`. Every input is on this sheet -- but the patterns were written for the
Edmund #67-304 title format, and this vendor's typography is a TABLE. Measured, on the sheet's
own words:

| gate | the sheet prints | the pattern wanted | |
|---|---|---|---|
| magnification | `Magnification (x) 1.0` | `1.0X` | MISS |
| mount | `Mount C` (label column + cell) | `Mount: C-Mount` | MISS |
| corroboration | `WD=110` | `110mm WD` | MISS |
| corroboration | `1.0` | `1X` | MISS |
| working distance | `Working Distance (mm) 110+-2` | -- | 110.0 |
| length | `Length (mm) 152.6` | -- | 152.6 |

Four of six gates failed on typography alone, so `telecentric_conjugate_cardinals` returned
`None` for a sheet that states its whole first order.

## Fix -- read the table, and corroborate with ARITHMETIC rather than typography

* magnification also as `Magnification (x) <n>` (unit in the label, bare number in the cell);
* mount also as a bare Mechanical-Specifications cell, `Mount | C`;
* and the corroboration bugs/0565 demands is now earned **either** the old way (the Edmund title
  repeating "0.75X, 110mm WD") **or** by the sheet's own stated total:

      Length of I/O (mm)  280+-2
      Note 2: Length of I/O = WD + Length + Back Focal Length

  which is exactly `wd + length + flange`. Checked: `110 + 152.6 + 17.526 = 280.126` against a
  printed `280` -- **0.126 mm**. Accepted within `max(3.0, 2% of the stated total)`.

Checking the vendor's own arithmetic is strictly stronger than matching their title typography,
and it is what makes OCR safe to feed in later: see below.

## Measured

Clean text of the table: **effl = 70.0315 mm**, m = -1.0, wd = 110.0, span = 152.6, flange
17.526 (hand-check `(110 + 152.6 + 17.526)/4 = 70.032`). Five mutants each refuse: an
inconsistent stated total, no stated total, the WD misread, no mount row, no magnification row.

Whole-corpus regression, all 29 camera+lens datasheets under `attachment/`: **0 regressions,
0 value changes**, and `validate_open3d_0653` (the Edmund #67-304 sheet, its four mutants, the
ELS-85 designation path and the ordinary Edmund fixed-focal page) still passes -- the new
corroboration is an ALTERNATIVE, never a replacement.

## On OCR, and on `pdf-prep`

The user asked whether `pdf-prep` could supply the missing text layer. **Not as written:**
`run_ocr` hardcodes `ocrmypdf --skip-text`, which skips any page that already carries text, and
this page carries 212 characters from the mechanical drawing. Measured: `pdf-prep --force-ocr`
left the file at 255 characters (its `--force-ocr` forces the DECISION to OCR, not the flag
ocrmypdf needs). One flag in that script would change this.

`ocrmypdf --force-ocr --oversample 400` does produce a text layer -- 255 -> **1428** characters,
every spec row readable. It also shows why OCR must never be trusted blind: it reads

    Working Distance (mm) 110+-2   ->   Working Distance (mm) 1102

The identity above refutes that by itself -- `1102 + 152.6 + 17.526 = 1272` against a printed
`280` -- so the sheet REFUSES rather than importing a lens with a 1102 mm working distance. That
refusal is the correct outcome and is pinned by the guard.

**No OCR digit-repair heuristic was added, and none should be.** bugs/0565's rule holds: a wrong
prescription is far worse than a clear refusal. To import this particular file today, supply the
datasheet with a real text layer (or an OCR pass that preserves the `+-` glyph); any vendor who
ships this table AS TEXT now imports with no further work.

## Guard

`python -m KrakenOS.UI.validate_open3d_0786_the_sheet_corroborates_itself` -- display-free, pure
text in / cardinals out. Penta phase 569.
