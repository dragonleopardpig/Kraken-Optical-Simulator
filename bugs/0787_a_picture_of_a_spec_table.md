# 0787 -- when the spec table is a picture, read the picture

`attachment/error.png` (second report), on the lens folder:

> Could not build a surrogate from this folder:
> .../RD-80000/Drawings/WWK10-110CP-111V3
> No Zemax .zmx prescription, no System/Prescription Data dump, and the datasheet PDF did not
> yield an effective focal length; cannot derive the lens optics.

bugs/0786 taught the scraper this vendor's table typography, and bugs/0785 fixed three text
extraction defects -- but neither could reach this sheet, because **there is no text to read**.
Measured with pdfplumber: 212 character objects on the page, 26 of them in the top 62% where the
tables are, and those 26 are exactly `WWK10-110CP-111V3` and `Datasheet`. Every spec row lives
inside one of the page's 4 images.

## Fix -- OCR, but only on failure, and never trusted on its own

`_extract_pdf_text_ocr` rasterises the pages and recognises them. It is wired as a LAST resort:
`parse_datasheet_cardinals` and `parse_camera_datasheet` first read the text layer, and only when
that yields no focal length / no sensor size do they retry on OCR. A readable datasheet therefore
never pays for it.

Two choices in it were measured, not assumed:

* **`--psm 4`**, a single column of variable-size text. This sheet prints two spec tables side by
  side; `--psm 6` merges them and `Magnification (x)` loses its `1.0` to the neighbouring
  Field-of-View row. With `--psm 4` every label keeps the value in its own row.
* **`pdftoppm -r 300`** for the raster. The tolerance glyph decides this: at 300 dpi
  `110+-2` survives as `110+2`, so the value regex stops at `110`. `ocrmypdf --force-ocr`
  rasterises differently and reads the same cell as **`1102`** -- a 1102 mm working distance.

| render + recogniser | the WD cell reads |
|---|---|
| `ocrmypdf --force-ocr` (any page-seg mode) | `1102` |
| `ocrmypdf --force-ocr --tesseract-pagesegmode 4` | `1102` |
| **`pdftoppm -r 300` + `tesseract --psm 4`** | **`110+2`** |

Both engines are optional: without `pdftoppm` and `tesseract` on PATH the function returns `""`
and the importer refuses exactly as before. The result is cached under
`attachment/cad_cache/datasheet_ocr/<md5>.txt` (gitignored, like every other generated cache)
because OCR is slow and a datasheet does not change.

**OCR is never trusted on its own.** Its numbers still have to earn bugs/0786's corroboration --
the sheet's own `Length of I/O = WD + Length + Back Focal Length` -- before they are used. That
is what makes reading a picture safe: had the render produced `1102`, the total would be 1272 mm
against a printed 280 and the import would refuse rather than ship a wrong lens.

One label pattern was relaxed: tesseract reads the total's label as `Length of I/0O (mm)`
(letter O as a zero). Being lenient about a LABEL is safe -- it only decides where to look; the
VALUE it introduces is still checked by the arithmetic.

## Measured

`import_lens_folder(".../WWK10-110CP-111V3")` now succeeds in about 8 s (once; cached after):

| | |
|---|---|
| effl | **70.0315 mm** |
| magnification / WD | -1.0 / 110.0 mm |
| vertex span | 152.6 mm |
| F-number | 7 |
| STEP body | `WWK10-110CP-111V3 3D Model (STEP) (1).step` |

With OCR disabled the same folder refuses, on both the original datasheet and the user's
`-prep.pdf` -- so the OCR path is doing the work and is the thing the guard pins:

| file | text-layer chars | has the `Magnification` row | OCR off | OCR on |
|---|---|---|---|---|
| `... Datasheet (1).pdf` | 216 | no | None | **70.0315** |
| `... Datasheet (1)-prep.pdf` | 3018450 | **no** | None | **70.0315** |

Whole 29-datasheet corpus: **0 regressions, 0 value changes**. The four that still miss are a
mechanical drawing, a marketing leaflet, a camera drawing and a catalogue page -- none states a
prescription, and each has a working spec sheet in its own folder.

## On `pdf-prep`

The user asked whether `pdf-prep` could supply the missing text layer. It cannot as written: its
`run_ocr` hardcodes `ocrmypdf --skip-text`, which skips any page that already carries text, and
this page carries 212 characters from the mechanical drawing. Measured on the user's own
`-prep.pdf`: 3 MB of extracted "text" and still no `Magnification` row. `pdf-prep --force-ocr`
forces the DECISION to OCR, not the flag ocrmypdf needs. One flag in that script would change
it; it belongs to the user's NixOS configuration and is left alone here.

## A note on better OCR

tesseract is enough for this sheet, but it is line-based: pairing a label with its value across
two side-by-side tables works only because `--psm 4` happens to. Engines that recognise TABLE
STRUCTURE (PaddleOCR PP-StructureV2, Surya) would remove that dependence on luck, and an
in-process ONNX engine (`rapidocr-onnxruntime`, ~15 MB) would remove both external binaries --
which is what the project's tooling rule prefers. `_extract_pdf_text_ocr` is deliberately one
function with an availability probe, so a better engine drops in without touching the callers.

## Guard

`python -m KrakenOS.UI.validate_open3d_0787_a_picture_of_a_spec_table` -- display-free; it pins
that OCR is a FALLBACK (never called when the text layer suffices), that it degrades to `""`
without the binaries, that its output is cached, and that the real folder imports at 70.0315
(skipped when the folder or the OCR binaries are absent). Penta phase 570.
