# 0715 — "imported LENS-800M58B1-V01.stp, but it looks different to freecad.png"

(flag_20260904_072725)

## Root cause

The vendor lens STEP is a 21-solid assembly (149.1 x 71.6 x 71.6 mm; the
full barrel with mount flange + two knurled rings, as FreeCAD shows). The
plain "Import lens STEP" defaulted `largest_component_only=True`, which
keeps only the largest CONNECTED component — a 55.8 mm stub (one ring, no
flange). The folder importer already defaulted to False; the plain import
was the odd one out, and the 0653-era memory had already called this trap.

## Fix

The import default is now the WHOLE assembly (what the vendor CAD shows =
what the user expects): `import_lens_step` (service + mixin wrapper),
the editor init/reset defaults, and the swap-settings fallback all flip to
False. The largest-only toggle REMAINS for STEPs with stray junk bodies.
Persistence fallbacks in layout_settings stay True so legacy scenes saved
without the key keep their historical look.

Measured: largest-only 55.8 mm / 14612 points -> whole assembly 149.1 mm /
38660 points.

## Guard

`validate_step_overlay_import_service`: new defaults pin (service + wrapper
signatures) + the clear-reset pin flipped. While here, fixed pre-existing
stub drift (the fake editor lacked the 0210 `_clear_step_overlay_
independent_instance` — the validator failed at clean HEAD, stash-proven).
