# 0785 -- a datasheet the app cannot read is a vendor it cannot import

`attachment/error.png`, on `attachment/Information/RD-80000/Drawings/MV-CH120-60UM`:

> Could not extract a sensor size from this folder. Provide a vendor datasheet PDF whose spec
> table is text-based, or drop a camera .json sidecar ...

The folder has a datasheet PDF, and that PDF states the sensor plainly:

    Sensor type   CMOS, global shutter
    Pixel size    3.45 um x 3.45 um
    Sensor size   1.1"
    Resolution    4096 x 3000

User: *"why everytime a new brand of camera introduced, the camera swap failed? Can't it read
the PDF text?"* It can. `extract_pdf_text` -- shared by the camera folder importer AND the
machine-vision lens importer -- had three independent defects, each of which alone is enough to
turn a perfectly readable sheet into "unreadable datasheet". None is brand-specific; they are
PDF-TOOLCHAIN-specific, which is why each newly-added vendor looked like a fresh failure. The
same Hikrobot family proves it: `MV-CS050-60UMUC` imported fine while `MV-CH120-60UMUC` did not.

## Root cause 1 -- the raw-literal fallback harvested PDF plumbing as if it were text

`_harvest_literal_text` regexed **every** `(..)` literal in the content stream. An
accessibility-tagged sheet (any Word/InDesign export) writes one

    /P <</MCID 2/Lang (en-US)>> BDC

per text run, OUTSIDE any text object. Measured: **380** of them on the Hikrobot sheet, **2738**
on the Bopixel `BC-Gx25M12X4`. The harvested text therefore read

    Pixel sizeen-US en-USen-US en-USSensor sizeen-US en-US1.1"en-US en-USResolutionen-US en-US4096

and every scraper regex is `Label\s*:?\s*value`, so not one of them could match.

**Fix:** harvest only inside `BT .. ET`. PDF may only SHOW text in a text object, so this is the
definition, not a filter. Measured on the Bopixel sheet it removed 28538 "letters", of which
every single one was `en-US` (2734), `ja-JP` (34) or raw bytes of compressed image streams that
happened to look like Latin-1 -- no page text at all.

## Root cause 2 -- a show-string whose font had no ToUnicode was silently DROPPED

A datasheet routinely mixes fonts INSIDE one spec row: labels in a simple font with no
ToUnicode, values in a subset CID font that has one. The Hikrobot sheet's `F7` maps exactly
twelve glyphs -- `. 3 4 5 m o s t x u -` -- the set needed for "3.45 um x 3.45 um" and nothing
else. So each single-pass decode lost half of every row:

| pass | result |
|---|---|
| per-font CMap decode | **5** ASCII letters |
| raw-literal harvest | "Pixel size" with NO pitch after it |

**Fix:** fall back PER SHOW-STRING (`_show_text`) instead of per page -- document order is kept,
so a label and its value stay adjacent whichever font each is set in.

A trap inside the fix: the printability test must count Latin-1 **160..255**, not just ASCII.
The separator that decides a row is exactly there -- `\xd7` MULTIPLICATION SIGN between "4096"
and "3000". An ASCII-only test dropped it and left `Resolution 4096 3000`, which the
`[xX]`-requiring regex still could not read.

## Root cause 3 -- the stdlib decoder understands a slice of PDF, not the format

It parses `N 0 obj` bodies directly, so a sheet using cross-reference/object streams or a font
encoding it does not implement returns junk. The Bopixel `BC-Gx25M12X4` states
`Active Pixel 5120 (H) x 5120 (V)` and `Pixel Size 2.5 (H) x 2.5 (V) um` on page 4; the decoder
returned only dot-leaders for it.

**Fix:** run a real parser too and let the two compete. `pdfplumber` is ALREADY a declared
dependency (`pyproject.toml`, `devenv.nix`) -- the module docstring's "no third-party
dependency" note was stale -- and the import stays optional, returning `""` on any failure.

**The stdlib result wins ties**, so every sheet both read equally keeps the exact text its
scraper was written and regression-tested against.

### The (cid:N) trap this uncovered -- caught by an existing guard, not by the corpus

pdfminer writes `(cid:1239)` for a glyph it cannot map. **"cid" is three ASCII letters**, so a
naive letter count reads a page of placeholders as a rich text layer. The AZURE ELS-85 sheet is
exactly that: **1101 "letters" of pure `(cid:N)`** where the stdlib decoder recovers the real
447 and the bugs/0565 designation path needs them. Preferring the parser on that count broke
`validate_open3d_0653` ("ELS-85 regression broke: None"). `_useful_letter_count` strips the
placeholders before counting, and the competition above then hands that sheet back to the
decoder.

## Also fixed -- `_field` over-capture on the mount

`_field(blob, "Lens mount", r"Weight")` captures up to the NEXT label, so a sheet without the
expected following row swallows the rest of the table. The record stored

    "lens_mount": "C-mount Dimension 29 mm x 29 mm x 30 mm (1.1\" x 1.1\" x 1.2\")"

A mount is a single token; whatever trails it is trimmed, so the flange lookup gets a clean key.

## Measured

The flagged folder, end to end (`import_camera_folder(..., persist=False)`):

| field | before | after |
|---|---|---|
| sensor | -- (ValueError) | **14.1312 x 10.3500 mm** |
| diagonal | -- | 17.5161 mm (the sheet's "1.1\"" format) |
| resolution / pixel | -- | 4096 x 3000 / 3.45 um |
| lens mount / flange | -- | `C-mount` / 17.526 mm |
| STEP body | -- | `MV-CH120-60UMUC.stp` |

14.1312 = 4096 x 3.45/1000 and 10.3500 = 3000 x 3.45/1000 exactly: the sheet states no sensor
size in mm at all (only the "1.1 inch" optical format), so bugs/0307's pitch x resolution
derivation supplies it -- it simply never got the chance before, because neither input parsed.

Whole-corpus regression, every camera and lens datasheet under `attachment/` (29 files):

| | before | after |
|---|---|---|
| scrape successfully | 23 | **25** |
| regressions | -- | **0** |
| value changes on files OK before AND after | -- | **0** |

Recovered: the Hikrobot `MV-CH120-60UMUC` (14.1312 x 10.35) and the Bopixel `BC-Gx25M12X4`
(12.8 x 12.8). The four that still miss are a mechanical drawing, a marketing leaflet, a
catalogue page and a drawing -- each with a working spec sheet in its own folder, so every
camera and lens FOLDER in the corpus imports.

**And this is the real shape of the user's question.** The Bopixel FOLDER already imported
before this fix -- but only because someone had hand-written `BC-GM25M12X4_camera.json`, the
very workaround the error dialog suggests. That is what "every new brand fails" looks like from
the inside: each vendor whose PDF toolchain tripped one of the three defects above needed a
human to transcribe the sensor size into a sidecar before the app would take it. The sheet now
parses on its own, so the sidecar is no longer required (it still wins when present -- a curated
value beats a scraped one by design).

## Not fixed, and why

`attachment/Information/RD-80000/Drawings` holds two lens folders that still refuse, both
honestly: `SPO TCL4.0X-65DI-5M` states magnification 4.0X and W.D 65 mm but no housing length
and no mount, and bugs/0653's telecentric derivation needs `T = WD + L + FFD` to close;
`WWK10-110CP-111V3` states no focal length and no magnification at all -- only `WD=110`, the
17.526 flange and `max 1.1" sensor`. Neither is an extraction failure: the text comes out
complete. A prescription cannot be invented from a dimensional drawing, and bugs/0565's lesson
stands -- a wrong prescription is far worse than a clear refusal.

## Guard

`python -m KrakenOS.UI.validate_open3d_0785_datasheet_text_is_the_import` -- display-free, and
it drives the REAL functions: synthetic streams pin each mechanism (plumbing outside `BT..ET`
ignored; a no-ToUnicode show-string falls back in ORDER; `\xd7` survives the printability test;
`(cid:N)` discounted; stdlib wins ties), and the real vendor folders pin the outcome
(skip-if-absent). Penta phase 568.
