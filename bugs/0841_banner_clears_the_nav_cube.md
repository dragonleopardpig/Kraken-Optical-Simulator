# 0841 -- the banner stays clear of the navigation cube

Found by MEASURING `flag_20260920_212949_800` ("I think it looks nice now"), not from a report.

I suspected the STRAY LIGHT row was being cut at the right. It was not -- 226 characters,
complete, ending at x = 2406 px. But 2406 is **inside the navigation cube**, which owns a
pixel-square corner viewport of 278 px at 2478 x 1264, starting at x = 2200. A 206 px overlap,
in the same vertical band as the banner's rows.

## Cause

bugs/0837's fit test asked whether the banner fits the VIEWPORT. The viewport is not all
usable: the cube has been in that corner the whole time, and nothing in the banner's layout
knew about it.

bugs/0840's DOF row is what made it visible -- it widened the HUD from 32 to 66 characters,
pushing the banner from x = 289 to x = 587. But the collision was already there at 1920 x 1080
and 1280 x 800 before today.

    2478 x 1264   cube starts 2200   banner ended 2406   ->  now 2182   clear
    1920 x 1080   cube starts 1682   banner ended 1872   ->  now 1664   clear
    1280 x  800   cube starts 1104   banner ended 1265   ->  now  539   clear

## The fix

`solve_banner_anchor` and `banner_wrap_chars` take a right-hand reserve, and the inspector
asks the cube's OWN placement function (`corner_square_viewport`) for its width rather than
hardcoding one -- 278 px at 2478 x 1264, 132 px at 900 x 600. The two cannot drift.

No cube means no reserve: the banner is not shrunk for a widget that is not there.

## Guard

`KrakenOS/UI/validate_open3d_0841_banner_clears_the_nav_cube.py`, penta phase 620. It checks
the reserve against the cube's placement at four window sizes, that the banner clears at all
four, that WITHOUT the reserve the flagged geometry overlaps, and that a zero reserve restores
the full budget.

Its REPRODUCES check was too strict first: it demanded all four sizes overlap, and at
900 x 600 the banner wraps narrow enough never to reach the corner. Demanding all four asserted
something untrue about the DEFECT rather than about the fix. It now pins the flagged size and
reports the others.
