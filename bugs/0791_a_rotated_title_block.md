# 0791 -- a CAD title block is typeset rotated, so read it that way

The user supplied an OCR'd copy of the SPO TCL4.0X-65DI-5M drawing, asking whether it helped.
It did not -- its text layer is the original's (315 characters against 314), and neither states a
focal length. But checking it turned up the real cause of a failure this repo has worked around
since bugs/0565.

## The failure was never a broken PDF

A drawing's title block is typeset at 90 degrees. A reading-order extractor walks it the wrong
way, emitting every label in one run and every value in another:

    Optical MgnificationResolution(um)W.D(mm)N.AF/#D.O.F (COC:20um)...
    4.0X 652.090.1612.5 31.3um< 0.03%< 0.02°

No `Label: value` regex can pair those, so a sheet that states its whole spec table reads as
though it states nothing. Measured: **all 284 characters on this page report `upright=False`**,
and they share just 20 distinct `x0` values -- the rotated lines.

This is the same shape as bugs/0565's ELS-85 ("its labels and its values live in separate text
runs"), which was worked around by recovering the focal length from the model designation instead.

## Fix -- assemble from character positions, in the rotated frame

`_extract_pdf_text_layout` reads `page.chars`, decides from `upright` whether the page is rotated,
and swaps the axes when it is (the row coordinate becomes `x0`, the advance becomes `top`). Rows
group with one tolerance per page taken from the median glyph size, and words are separated by
comparing each gap against that glyph's OWN set width -- which for a rotated glyph is
`bottom - top`, not `x1 - x0`.

Both of those were learned the hard way: a per-character row tolerance splits a label whose glyphs
differ in size, a nominal-size word gap glues "Optical" to "Mgnification", and the line's median
advance splits the wide ones ("OpticalM gnification").

The result, from the ORIGINAL PDF, with no OCR, no DWG and no external binary:

    F.O.V : 2.2mm X 1.65mm @ 2/3" ccd camera
    Optical Distortion(%) < 0.03% Telecentricity Angle < 0.02°
    F/# 12.5 D.O.F (COC:20um) 31.3um mm TCL4.0X-65DI-5M
    Resolution(um) 2.09 N.A 0.16
    Optical Mgnification 4.0X W.D(mm) 65

It is offered as a CANDIDATE (`text_candidates`) ahead of the OCR engines: it costs a fraction of
a second, needs nothing installed, and fixes the commonest reason a legible datasheet reads empty.
The ordinary text layer is still tried first, so nothing that already worked changes.

## Measured

Whole 29-datasheet corpus: **0 regressions, 0 value changes**. An upright sheet is unaffected --
PYRITE 56/80 still parses from its text layer at effl 82.39.

The SPO TCL4.0X-65DI-5M still does not import, for the reason bugs/0790 established: its spec is
now fully legible from its own PDF, and (m, WD, track) still pin the TRACK rather than the focal
length. What changed is that the drawing no longer needs its DWG, or an OCR pass, to be read.

## Guard

`python -m KrakenOS.UI.validate_open3d_0791_a_rotated_title_block` -- display-free; pins that the
reading-order text really does orphan the values (the bug), that the rotated assembly pairs them,
that the word spacing is right, that it is offered first, that an upright sheet is untouched, and
that a missing file degrades to "" rather than raising. Penta phase 574.
