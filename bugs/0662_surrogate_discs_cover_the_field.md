# 0662 — Surrogate discs drawn at the pupil, not the glass

**flag_20260830_180206:** "rays are passing beyond the diameter of the first and last
lens surrogate, is this correct behaviour?" — on the #67-319 1× telecentric library
layout (8.4 × 7.1 field, FOV rays visibly wider than the 3.5 mm surrogate rings).

## Answer

The RAYS were correct; the DISCS were not. The folder importer drew every datum and
group disc at 1.4 × the aperture stop (EFL/f# = 2.52 mm → 3.53 mm) — the on-axis pupil
footprint — while a finite-conjugate lens's front and rear elements must cover the
FIELD they image: a 1× lens with an 11 mm image circle needs ≥ 11 + pupil ≈ 13.5 mm of
glass. The trace refracted the field-edge rays anyway because bugs/0624 extends
blackbox-member trace apertures beyond their drawn discs — so the picture showed rays
"passing beyond" surrogates that were simply drawn too small. (Physically the real
#67-319 front element is ~25 mm.)

## Fix (general, both importer paths)

`lens_aperture = max(1.4 × stop, image_circle × max(1, 1/|m|) + stop)` when the
datasheet states an image circle (magnification-scaled to the object side; a
variable-focus lens uses the image circle as-is); the Black-Box path applies the same
rule when the dump states a paraxial image height. Measured after import:
1× telecentric 13.52 mm, 0.75× telecentric 19.96 mm, 35 mm f/1.8 30.44 mm. Datum discs
are the barrel walls (bugs/0623), so the trace apertures grow with them — fewer false
edge clips, never more.

Guard: 0656 section A6 (import invariants) pins "discs ≥ image circle/|m| + pupil".
Note: re-import a lens folder to regenerate its library surrogate with the new discs.
