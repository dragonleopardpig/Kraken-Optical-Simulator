# 0702 — "swapped lens with 80mm, lens surrogate is oversized" (flag_20260903_094237)

The user saved om05a as `om05a_folded_80mm.py` and swapped the lens for the
PYRITE 5.6/80 1.0x V38; the surrogate discs read oversized. "This is bug
re-occurrence, multiple times. Please check the fix is general enough so that
swapping and importing lens WILL NOT happen again."

## What the investigation ruled OUT first

- The saved rows ARE clamped (47.0318 = exactly what the 0668 housing clamp
  produced) — the sizing pipeline ran.
- The 0627 display-clip (0624's 2× trace extension trimmed back for display) is
  wired on both draw paths — the discs draw at row diameter.
- Mirror2's mirrored pose in the saved file (desp_x +272.7, mutated tilts) is
  NOT swap corruption: the instrumented headless swap
  (`bugs/0702_swap_repro.py`) leaves mirror2 byte-identical through every
  stage. It is the user's own production rotation of the station (the 0693
  carry), legitimately on the +x leg.

## Defect 1 — the swap silently drops the vendor seat (reproduced)

The om05a vendor seat (0689) is ONE frame-desp on the lens block's FIRST row:
front datum desp (−6.08, ~0, −0.3885). The swap splices in a fresh block with
desp 0, and the 0547 frozen-frame restore — the mechanism meant to re-land the
block — only engages when a block row is `row_placement.WORLD`; on a scene
whose lens block walks SEQUENTIALLY from a frozen fold row it returns None.
The world-settle bracket skips replaced lens rows by design. Net: the seat
calibration vanishes on EVERY swap of a seated scene.

Fix (`swap_imaging_lens_from_folder`): the outgoing front datum's desp + tilt
are carried onto the replacement front datum right after the splice — the seat
is a property of the LEG, not of the particular lens. The 0547 path, when it
does engage, runs later and overwrites (complement, not competitor); straight
scenes carry zeros (no-op). Reproduced fixed: (−6.08, ~0, −0.3885) survives
every stage.

## Defect 2 — the 0668 clamp measured the wrong quantity

`_step_transverse_extent` = the MIDDLE of the three bbox extents. The PYRITE
family is authored along X with axial length ≈ its square flange (extents
~47.0 × 50.1 × 46.1) — the "middle extent" returned the AXIAL LENGTH (47.03),
not a barrel diameter, and the discs overhung the visible barrel rings.

Fix: `_step_barrel_diameter` measures the largest SUBSTANTIAL co-axial
cylinder face — cylinders clustered by collinear axis exactly like the 0372
axis derivation, each weighted by lateral AREA so a short flange BORE (wide
but thin) cannot pose as the barrel wall. PYRITE 80 and 85 both measure 46.0
(CAD truth). Both importer clamp sites prefer it, bbox extent as fallback.
New import numbers: PYRITE 80 discs 47.03 → 46.0, PYRITE 85 48.56 → 46.0.

Note: the ORIGINAL scene's 36.0 discs predate the 0662 field-grow rule —
today's rule sizes any telecentric's front glass at field+stop, clamped to the
barrel. Disc = barrel is the user-accepted 0668 contract (the PYRITE 4.5/90
case); this fix makes the barrel number honest.

## The user's saved scene

`attachment/om05a_folded_80mm.py` patched in place (backup
`bugs/om05a_folded_80mm_0702_patched.py`): front datum seat restored, lens-row
diameters 47.0318 → 46.0. The rotated station (mirror2 on +x) left untouched —
it is the user's production orientation.

## Guards

`validate_open3d_0702_swap_seat_and_barrel` (penta phase 511): A seat-carry
source-pin, B real-STEP barrel 46.0 < bbox 47.03, C real import clamps to
46.0, D both clamp sites wired. `validate_open3d_0668_disc_barrel_clamp` B1
re-pinned to the cylinder barrel (was pinned to the bbox middle extent);
A/B2/C unchanged, all green.
