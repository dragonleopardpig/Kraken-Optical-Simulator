# 0371 — Folder import failed on the Apo-Rodagon-D: datasheet patterns were PYRITE-only

**Report:** attachment/error.png — "Could not build a surrogate from this folder:
attachment/Lens/0703-005-000-40-EXC ... the datasheet PDF did not yield an effective focal length."
**Status:** FIXED 2026-07-20 (guard `validate_datasheet_lens_import` extended).

## Root cause

The folder holds a Rodenstock **Apo-Rodagon-D 1x 4/75** datasheet + vendor STEP. The PDF's text
layer extracts fine and CONTAINS everything Path C needs — but `parse_datasheet_cardinals`'s
patterns were written on the OPT/PYRITE sheet style (`f'eff [mm]`, `SF [mm]`, `Max. sensor size`)
while this vendor writes lower-case labels with PARENTHESISED units and `*)` in-air footnotes:
`focal length f' (mm) 74.9`, `SF (mm) -44.2`, `S'F' (mm) *) 44.2`, `image circle max. (mm) 82`,
`magnification W [range] -1 [ -1.2 ... -0.8]`.

## Fix (general — both unit styles, not per-vendor)

Fallback patterns accepting `[mm]` OR `(mm)`, case-insensitive labels, the `f'` token in the EFL
row, optional `*)` footnote markers, and the bracketed-range magnification row. Number tokens stay
tight (`-?\d+\.?\d*`) so column-glued runs ("`-44.2f-stop0`") still yield the clean leading value.
**HH'/span are deliberately NOT extended to the (mm) style**: those rows glue their columns
("`-14.355.6`" = −14.3 next to 55.6) and a misparse would silently corrupt the solve — SF + S'F' +
EFL suffice for the EXACT two-group solution, the honest subset (guarded: the glued HH' must stay
unparsed).

## Verified end-to-end

`parse_datasheet_cardinals` → EFL 74.9, SF −44.2, S'F' 44.2, mag −1, image circle 82;
`build_surrogate_from_assets` on the real folder → 7-row "Machine Vision 0703-005-000-40-EXC"
surrogate, "Both principal planes recovered from the datasheet (SF + S'F'); the two ideal groups
reproduce all four cardinals exactly", span sized to the STEP body. PYRITE-family guards untouched.

## Also repaired in passing

`validate_datasheet_lens_import`'s "3D importer delegates" needle was silently stale-failing since
the 0294 SIGSEGV fix (986fe41b rebound the call through a local `editor` variable) — masked by
last-line-only PASS/FAIL classification. Needle now matches the call itself. Plus a synthetic
Rodenstock-text regression case (mocked `extract_pdf_text`, no PDF dependency).
