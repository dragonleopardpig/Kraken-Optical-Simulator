# 0745 -- the first-order track must match the path the light actually walks

The solve banner's "focus residual" and the drawn image plane (bugs/0728) disagreed by a constant
**+19.55 mm** on `om05a_folded_80mm.py`, so two readouts in one scene told different stories and
neither said which to trust. Chasing the glass first was a red herring -- the gap was flat whether
the prism glass was absent, wrong (158 mm) or correct (50 mm).

## Root cause

The first order sums ROW THICKNESSES; the trace walks the real folded geometry.

| scene | station sum | traced path | difference |
|---|---|---|---|
| `om05a_folded.py` (production) | 413.760 mm | 413.962 mm | +0.202 |
| `om05a_folded_80mm.py` | 433.360 mm | 414.026 mm | **-19.334** |

Walking the traced polyline against the stations put the whole excess in one step -- every arm-B
row sits at station 413.76 with zero thickness except **`LED panel B`, which carries 19.6 mm**, and
it sits BEFORE the Image row. Production has 0.0 there, as do all the other arm-B rows.

So the prescription said the object-to-image track was 19.6 mm longer than the light's path. The
imaging light never traverses the LED panel; it is an illumination component positioned by pose,
not by station.

## Fix

`LED panel B` thickness 19.6 -> 0 (backup `om05a_folded_80mm.py.pre-ledpad.bak`). Verified as a
pure prescription fix: image station 433.360 -> 413.760 and **zero rows changed world pose** --
nothing physical moved. Folds still 90.0000 deg, the prism split intact.

| device | paraxial | traced | gap before | gap after |
|---|---|---|---|---|
| 30 mm | -54.848 | -54.898 | +19.551 | **-0.049** |
| 42 mm | -27.009 | -26.971 | +19.638 | **+0.038** |
| 50 mm | -3.858 | -3.826 | +19.633 | **+0.033** |

Matching the production scene's own agreement (-0.061 / -0.028 / -0.007 mm). The variant solves
20-56 mm with focus crossing ~51.3 mm, now consistent between both readouts.

## Guard -- never silent again

A scene-data error like this cannot be caught by a source-level check, so the tool now cross-checks
itself: `_measure_focused_image_plane` compares the traced waist with the first order's residual
and, when they differ by more than 1 mm, stashes

    MODEL MISMATCH: the first order says X mm and the traced rays say Y mm (Z mm apart) -- the
    drawn image plane is the measured one; check for a row carrying thickness that the imaging
    path never travels

which the solve banner renders beside the residual. The measured value is named as the trustworthy
one, and the likely cause is pointed at.

Guard: `KrakenOS/UI/validate_open3d_0745_first_order_matches_the_trace.py` (penta phase 540).
