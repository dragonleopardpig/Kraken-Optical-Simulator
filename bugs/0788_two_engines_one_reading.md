# 0788 -- two OCR engines, complementary weaknesses, tried in turn

bugs/0787 gave the importer an OCR last resort and it worked, on `pdftoppm` + `tesseract`. The
user asked for a better offline model -- "is there a better offline OCR model based on deep
learning that we can use or download?" -- and asked for `rapidocr-onnxruntime` to be added to
`devenv.nix`.

It is a real improvement, and it is NOT a replacement. Measured on the COOLENS
WWK10-110CP-111V3 spec table:

| | rapidocr (in process) | pdftoppm + tesseract |
|---|---|---|
| the cell that decides the value | **`110±2`** (the real glyph) | `110+2`, and `1102` through ocrmypdf's rasteriser |
| row pairing | **a BOX per line** -- label and value pair by geometry | depends on `--psm 4` keeping two side-by-side tables apart |
| `Best Aperture (F/#) │ 7 ... Mount │ C` | **both values MISSED** -- the detector skips isolated one-character cells | found |
| external binaries | **none** (pdfplumber rasterises in process) | two |

So rapidocr reads the hard glyph and loses the easy one, and tesseract the reverse. Declaring
either the winner loses a sheet: with rapidocr preferred outright, WWK10-110CP-111V3 went back to
refusing, because a missing `Mount │ C` means no flange and no derivation.

## Fix -- engines are CANDIDATES, and the caller judges

`ocr_text_candidates(path)` returns each available engine's reading, best-first, each cached
under its own key (`<md5>.rapidocr.txt`, `<md5>.tesseract.txt`). `parse_datasheet_cardinals` and
`parse_camera_datasheet` try them in turn and keep the first that yields a usable result -- which,
because of bugs/0786, means the first that also passes corroboration against the sheet's own
printed total.

Merging the two texts was considered and rejected: a regex would then take whichever number
appeared first and could silently mix two engines' readings of the same cell. Trying whole
readings in turn keeps each candidate internally consistent, so the arithmetic check still means
something.

`_ocr_engine_available()` is the MASTER switch and is consulted **before the cache**, so turning
OCR off gives the pre-0787 behaviour exactly -- an honest refusal -- rather than a stale reading
from a previous run.

## Measured

`import_lens_folder(".../WWK10-110CP-111V3")` -> effl **70.0315 mm**, span 152.6, in ~10 s from
cold (both engines run; rapidocr first, tesseract supplies the reading that passes), then cached.

Whole 29-datasheet corpus, against the pre-bugs/0785 baseline:

| | before | after |
|---|---|---|
| scrape successfully | 23 | **26** |
| regressions | -- | **0** |
| value changes on files OK before AND after | -- | **0** |

The third recovery is the Bopixel `Leaflet_BC-GM25M12X4-EN.pdf` (12.8 x 12.8), whose spec panel
is also a picture.

## devenv.nix

`rapidocr-onnxruntime` added to the pip set and `KRAKEN_REQ_HASH` bumped to
`krakenos-core-v23-rapidocr-libredwg` so the install re-runs. `poppler-utils` and `tesseract` are
now DECLARED too: bugs/0787's fallback happened to work only because they were already on this
machine from the user's NixOS configuration, which is not a dependency, it is luck. `libredwg` is
declared for the DWG route below.

Re-enter the devenv shell (`devenv shell`) to pick them up.

## Still open -- the DWG, which is better than any OCR

`SPO TCL4.0X-65DI-5M` ships `TCL4.0X-65DI-5M-V2.dwg` beside its PDF, and the user asked about it.
It is the right source: `dwgread -O JSON` (libredwg, now declared) reads 814 objects including 53
MTEXT entities with coordinates, and the spec table is all there as TEXT --

    Optical Mgnification | 4.0X      W.D(mm) | 65       F/# | 12.5     N.A | 0.16
    F.O.V : 2.2mm X 1.65mm @ 2/3" ccd camera            C-MOUNT   IRIS
    dimension row:  WD65 %%P2   142.5   17.526

-- so a label pairs with its value by GEOMETRY, exactly, with no recognition step at all. The
dimension row is the conjugate chain itself: 65 + 142.5 + 17.526 = 225.026, giving
f = 225.026 / (2 + 4 + 0.25) = **36.00 mm**.

Not implemented here, because it needs a corroboration rule this sheet does not hand over: it
prints no total to check the chain against (the way the COOLENS sheet prints "Length of I/O"), so
accepting it means trusting that a row of three dimensions IS the WD/housing/flange chain. That
is a modelling judgement, and bugs/0565's rule -- a wrong prescription is far worse than a clear
refusal -- says it should be made deliberately rather than inside this change.

## Guard

`python -m KrakenOS.UI.validate_open3d_0788_two_engines_one_reading` -- display-free; pins the
master switch (checked before the cache), per-engine caching, and that a candidate which fails
corroboration does not win over one that passes. Penta phase 571.
