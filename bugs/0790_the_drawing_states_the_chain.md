# 0790 -- read the vendor DWG, and refuse for the right reason

User: *"About the SPO TCL4.0X-65DI-5M, isn't there a DWG file?"* -- and later, *"is the 4X lens
settled already?"*

There is, and it is the right source. It does not settle the lens, and the reason it does not is
worth more than the refusal that came before.

## The DWG states everything the PDF lost

`TCL4.0X-65DI-5M-V2.dwg` carries 814 objects including 53 MTEXT entities WITH COORDINATES, so a
label pairs with the value in its own row by GEOMETRY -- no recognition step, nothing to misread.
Rebuilt into reading order:

    Optical Mgnification 4.0X  W.D(mm) 65
    F/# 12.5  D.O.F (COC:20um) 31.3um  TCL4.0X-65DI-5M
    Resolution(um) 2.09  N.A 0.16
    F.O.V : 2.2mm X 1.65mm @ 2/3" ccd camera
    IRIS  C-MOUNT
    WD65 ±2  142.5  17.526

Neither earlier route could reach this. The PDF's text layer flattens the title block so every
label is orphaned from its value (bugs/0565's failure mode: 314 characters, labels only), and OCR
recovers the labels but not the small isolated value cells (bugs/0788's: rapidocr returns
`Optical Mgnification` with no `4.0X`, tesseract returns 14 characters for the whole drawing).

## Every number is corroborated before use

bugs/0565's rule applied to a source that states more than it needs to:

| datum | value | the second, independent statement |
|---|---|---|
| magnification | 4.0X | `F.O.V 2.2mm X 1.65mm @ 2/3"` -> 2.2 x 4.0 = **8.8** = the 2/3" format width |
| F-number | 12.5 | `N.A 0.16` -> an object-space telecentric images at m/(2 NA) = 4.0/0.32 = **12.5** |
| working distance | 65 | stated twice: the table's `W.D(mm) 65` and the dimension `WD65 ±2` |
| flange | 17.526 | equals the **C-mount standard FFD exactly**, and the drawing says `C-MOUNT` |

The housing length, 142.5, is then the only single-sourced value -- and it is the remainder of a
dimension run whose two ends are both verified. That is how the run is IDENTIFIED rather than
guessed: its first entry is labelled with the working distance and its last equals a standard
mount's flange focal distance. A run ending in anything else is not a chain, and is ignored.

(The same drawing carries a second, metric-comma view of the identical dimensions -- `142,5`,
`17,526`. Those parse to None rather than to 142 and 17, so the duplicate view is skipped.)

## Why the lens still does not import

    total track object -> image        65 + 142.5 + 17.526 = 225.026 mm
    f with HH' = 0                     225.026 / (2 + 4 + 1/4) = 36.0042 mm
    object -> front principal H        f (1 + 1/m) = 45.005 mm
    but the working distance is        65 mm
    => H would sit 19.99 mm IN FRONT OF THE HOUSING

bugs/0647's registration law (`0 < f(1+1/m) - WD < f`) refuses that, and it is right to. For H to
sit inside the housing the focal length must be at least `WD/(1+1/m)` = 52 mm, which forces
`HH' = 225.026 - 6.25 x 52 = -100 mm`. **With HH' unstated, (m, WD, track) leaves one free
parameter: this sheet pins the TRACK, not the focal length.** No amount of better reading fixes
that -- it is a modelling gap, not an extraction one.

So the EFL is not derived. bugs/0565 again: a wrong prescription is far worse than a clear refusal.

## What changed for the user

The refusal now says what was read and what is missing, instead of blaming a PDF that was never
the problem:

> TCL4.0X-65DI-5M-V2.dwg states the conjugate chain -- working distance 65 mm, housing 142.5 mm,
> C-mount flange 17.526 mm, so an object-to-image track of 225.026 mm -- but no focal length and
> no HH'. Those pin the TRACK, not the focal length: with coincident principal planes they give
> f = 36.00 mm, which would put the front principal plane outside the housing. Supply the EFL or
> HH' (or a .zmx) and this folder imports.

`.dwg` is now classified by `scan_lens_folder`, and a DWG is tried as a source whenever the PDF
route yields no focal length -- so any vendor whose drawing IS consistent with coincident
principal planes imports from it with no further work.

## Optional, like every other engine here

`libredwg`'s `dwgread` (declared in `devenv.nix` since bugs/0788) is the only requirement, and it
is probed, not assumed: without it every entry point returns None and the importer refuses exactly
as before.

Whole 29-datasheet corpus and every folder-import guard: unchanged. `PYRITE_56_80_10x` still
imports at effl 82.39, `WWK10-110CP-111V3` at 70.0315.

## Guard

`python -m KrakenOS.UI.validate_open3d_0790_the_drawing_states_the_chain` -- display-free; pins the
AutoCAD text codes, that the chain is identified by its standard-flange end, that the rebuilt rows
pair label with value, and -- the important half -- that **no focal length is invented** and the
refusal names the chain it read. Penta phase 573.
