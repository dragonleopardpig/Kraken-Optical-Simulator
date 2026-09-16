# 0789 -- the image circle sizes the glass, under whatever name the vendor gave it

Recording `flag_20260916_085939_919`, on a scene the user built from the two folders bugs/0785-0788
made importable (`MV-CH120-60UM_WWK10-110CP-111V3.py`):

> Please check is everything is correct? Can the lens surrogate size fit the lens barrel of the
> STEP file? It seems too small to be true.

It is too small, and the user is right. Measured on the saved scene:

| | |
|---|---|
| surrogate element diameters | **Ø14.0063** |
| aperture stop | Ø10.0045 |
| lens STEP barrel (transverse extent) | **Ø44.00** (156.47 mm long) |
| the datasheet's own row | `Max Sensor Size (Φmm)` \| **18.0(1.1")** |

Ø14.0063 is exactly `1.4 x stop` -- the on-axis pupil footprint, and nothing else. A lens cannot
pass an 18 mm image circle through 14 mm of glass.

## Root cause -- the rule was already right; its input was missing

bugs/0662 already says a finite-conjugate lens's front and rear elements must cover the FIELD
they image, not just the pupil, and bugs/0668 refined it:

    lens_aperture = max(1.4 * stop, image_circle + stop)

For this sheet that is `max(14.0063, 18.0 + 10.0045)` = **Ø28.0045** -- which sits sensibly inside
the Ø44 barrel and agrees with the DWG's internal Ø30 / Ø31 / Ø34 bores. It never fired, because
`cardinals.image_circle` was `None`.

It was `None` for a filing reason, not an optical one. The image-circle scrape lived in **two**
places with **different** lists of spellings, and the telecentric path (bugs/0653, which is the
path this sheet takes) knew only the Edmund one:

| path | spellings it knew |
|---|---|
| general (`_cardinals_from_text`) | `Max. sensor size [mm]`, `image circle max. (mm)`, `Maximum Image Circle (mm)` |
| **telecentric** | `Maximum Image Circle (mm)` only |

and neither knew `Max Sensor Size (Φmm)`.

## Fix

One helper, `_scrape_image_circle`, holding every spelling and used by both paths. The unit is
written `(mm)`, `[mm]` or `(Φmm)` -- and an OCR'd sheet renders that Φ as `@` or `®P` (both
observed on this very page), so a couple of characters before `mm` are tolerated. Being lenient
about a LABEL is safe for the same reason as bugs/0786: it only decides where to look. The value
is bounded to a plausible 1-400 mm, and an image circle sizes apertures -- unlike the EFL it
cannot move the first order.

## Measured

`import_lens_folder(".../WWK10-110CP-111V3")`:

| | before | after |
|---|---|---|
| image circle | -- | **18.0 mm** |
| front / rear aperture | Ø14.0063 | **Ø28.0045** |
| object / image diameter | 14.0063 | **18.0** |
| effl / span | 70.0315 / 152.6 | unchanged |

Whole 29-datasheet corpus: **0 regressions, 0 value changes** -- the unified helper keeps the
existing spellings in their existing order, so every sheet that already resolved an image circle
resolves the same one.

## The other half of the question -- "is everything correct?"

The scene's banner reads *"FIELD REACHES THE SENSOR EDGE: 1718 ray(s) land up to 1.891 mm outside
the active area (66.5% of the landing rays)"*. That one is arithmetic, not a fault:

    object/image field   Ø17.5157 mm   (the sensor DIAGONAL)
    sensor active area   14.1312 x 10.35 mm
    overflow             17.5157/2 - 14.1312/2 = 1.6924 mm

and the headless trace reports `overflow_mm 1.6924`, `fraction 0.6667` -- exact. A field defined
as a DISC of the sensor diagonal necessarily has two thirds of its area outside the rectangle it
circumscribes; that is what an image circle covering a sensor looks like. Nothing is mis-focused:
the same trace measures a focus offset of -1.6e-11 mm and an RMS of 3.4e-13 mm.

So the banner is true and benign. If it should stop reading as an alarm, the traced field for a
rectangular detector should be the RECTANGLE rather than its circumscribing circle -- a separate
decision, not made here.

## Note for the user's scene

`attachment/MV-CH120-60UM_WWK10-110CP-111V3.py` has the old Ø14.0063 baked into its rows. It was
written before this fix and is the user's file, so it is left untouched: re-import the lens folder
to pick up the Ø28.0045 surrogate.

## Guard

`python -m KrakenOS.UI.validate_open3d_0789_the_image_circle_sizes_the_glass` -- display-free,
text in / cardinals out: every spelling (including the OCR'd Φ) resolves, implausible values are
refused, and the telecentric path exposes it. Penta phase 572.
