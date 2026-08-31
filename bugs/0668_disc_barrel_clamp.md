# 0668 — 320 mm discs on a 50 mm lens: the 0662 field rule fired on a non-telecentric

**6-sided.png (2026-08-31):** every station of the user's first solved six-station
cell wore a pair of giant teal discs, dwarfing the camera and barrel. "The lens
surrogate might have bug, previous fix (I think yesterday) introduce a big lens
surrogate." — correct on both counts.

## Root cause

bugs/0662 grew the surrogate discs to `image_circle × 1/|m| + stop` for ANY lens
whose datasheet states a magnification. That object-side scaling is the physics of
an **object-space telecentric** — its chief rays are parallel, so the front glass
really spans the object field. The cell solver picked the **PYRITE 4.5/90/0.3x V38**
(EFL 90.8, f/4.5): an ordinary large-format lens ("Max. angle 42°") with a 90 mm
line-scan image circle and "Rec. magnification −0.3" on the sheet. The rule computed
90/0.3 + 20.2 = **320.18 mm** of drawn glass — on a lens whose whole barrel is 50 mm.
An entocentric lens funnels its field through the pupil; its glass never spans the
object field.

## Fix (general, both importer paths)

1. **The 1/|m| object-side scaling now requires telecentricity.**
   `DatasheetCardinals.telecentric` — stamped `True` by the fixed-conjugate
   telecentric parser (0653) and by the word "telecentric" on the sheet in the
   generic parser (verified: no non-telecentric sheet in the library contains the
   word). Non-telecentric lenses keep `image_circle + stop` (the 0662 rear-field
   cover, unscaled).
2. **No disc exceeds the barrel.** `_step_transverse_extent`: the MIDDLE of the
   bundled STEP body's three bounding-box extents — a barrel is round, so two
   extents are its diameter and one its length; the middle one is the diameter
   whichever CAD axis is optical. `lens_aperture = max(1.4·stop, min(rule, barrel))`
   in the datasheet AND Black-Box paths (`_step_bounds_extents` shared with the span
   helper).

Library sweep after the fix: PYRITE 4.5/90/0.3x **320.18 → 50.06** (its barrel); all
other PYRITEs clamp to their 40–50 mm barrels; the three Edmund telecentrics keep
their exact 0662 field-sized discs (13.44 / 19.96 / 13.52); the 35 mm fixed-focal
keeps 30.44. The 0703 Excellitas (bugs/0417's wider-than-glass surrogate) clamps
82→52: 0417 was about the SPAN solve, and the housing bound on the DIAMETER is
physically right — glass lives inside the barrel.

The user's `attachment/cells/solved/` stations were repaired in place through the
editor (320.1778 rows → 50.0591; note `_write_layout_file` re-reads the table, so a
programmatic row edit needs `_sync_table()` first) and the cell re-composed.

## Verified

Guard `validate_open3d_0668_disc_barrel_clamp` (penta phase 501): rule branches on
the flag (A1/A2), middle-extent transverse logic both barrel aspect ratios (A3),
real PYRITE = barrel + telecentric unchanged (B), parser stamping on real sheets +
Black-Box clamp (C). Guard 0656 A6 (telecentric ≥ field) still green.
