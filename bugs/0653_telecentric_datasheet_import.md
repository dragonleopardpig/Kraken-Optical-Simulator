# 0653 — Telecentric datasheet with no focal length imports via its conjugates

**User (2026-08-27, error.png):** "Could not build a surrogate from this folder:
.../67304_0.75X_Telecentric ... the datasheet PDF did not yield an effective focal
length; cannot derive the lens optics." — "I think the PDF is multi-pages, the spec is
in the PDF."

## Root cause

Multi-page was NOT the issue — the hand-rolled extractor already walks every object
stream (7788 chars came out, spec included). The Edmund CompactTL sheet simply states
NO focal length anywhere. It pins the first order mechanically instead: Primary
Magnification PMAG 0.75X, Working Distance (mm) 110, Length (mm) 160.01, Mount
C-Mount, NA 0.028, f/13.3, image circle 11 mm.

## Fix (general): `telecentric_conjugate_cardinals`

A fixed-conjugate telecentric sheet derives its EFL: T = WD + L + FFD (flange focal
distance of the NAMED mount — C 17.526, CS 12.526, TFL 17.526, F 46.5) and, with the
coincident-principal nominal (same class as 0565's), T = f(2 + m + 1/m):

    f = (110 + 160.01 + 17.526) / (2 + 0.75 + 1/0.75) = 70.417 mm.

Every value is corroborated (this format's title repeats "0.75X, 110mm WD"); missing
mount / marker / corroboration / absurd m all refuse — the honest error stays. The
cardinals carry magnification −0.75 and Optimum WD 110 @ 0.75x, so the bugs/0647
housing law applies at import.

## Second finding: the housing length must be the vertex span

First import attempt built the surrogate but the 0647 refit fell back to the advisory
(mismatch −37.65): the block span came out 30 mm — the STEP's Z-extent is its DIAMETER
(29.5; this CAD's axis is not Z), and even the body-extent path caps span at 0.7·EFL
= 49.3 — while a telecentric principal must sit f(1+1/m) − WD = 54.3 mm behind the
rim. The barrel is 160 mm; the sheet says so. The telecentric cardinals now declare
`span = Length`, the importer's existing "datasheet vertex span" branch honors it, and
the refit has room. Measured after: registration mismatch **+0.00** (principal 54.3
behind rim = law), object leg exactly 110.0 mm — bench-true at import.

Guard: `validate_open3d_0653_telecentric_datasheet_import` (penta phase 489) — real-PDF
parse, derivation formula + four refusal mutants, ELS-85/PYRITE regression, wiring.
