# 0837 -- every banner line fits, and the banner fits the window

`flag_20260920_203630_905` *"Device 20x20x1mm. The banner seems shift to the right."* and
`flag_20260920_204200_878` *"loaded 80mm folded .py file, this time banner at the left."*
Both on the Phase D build (`547f58cc`).

## First, what those captures also show

The solve **succeeded** on both:

    SOLVE: delivering 21 x 21 mm (|m| 1.097); the lens moved -145.2 mm along its leg
    Landed: the blur on the sensor (3.06 um) is inside one pixel (4.5 um) -- nothing to move

That is the same 21 x 1.05 field refused at 18:20 for being "short by 1.983 mm". With the room
measured in the drawn frame (bugs/0836 + Phase D) the solve found the travel it always had.
The 80 mm file lands the same way at -133.4 mm.

## Two defects, both certain from the 20:36 capture

**1. The lines were never wrapped.** bugs/0835 wrapped the refusal's `reason` and stopped
there -- it fixed one line when the defect was in the formatter. The focus summary's lines
never passed through it:

    SOLVE                                                              80 chars
    FOCUS: the image forms 0.1155 mm ...                              103
    Landed: the blur on the sensor ...                                 88
    STRAY LIGHT: 8 ray(s) reach the sensor by another optical route ... 223   <-- 2x the budget

At roughly 1500 px the STRAY LIGHT line was cut by the WINDOW EDGE at *"...left out of the
focus measu"*, losing *"and drawn faint in the 3D scene"*. The same loss as bugs/0835 with no
character cap involved at all.

**2. Placement bounded only the START.**

    if x_norm > 0.72:          # where the banner BEGINS
        x_norm, y_norm = 0.012, 0.83

That says nothing about where it ends. Measured: a start of `0.445` passed its own check and
the banner still ran off a 2478 px window.

## On the left/right jump itself

The banner's x is `0.012 + (hud_width_px + 18) / view_w`. Solving back from the two captures:

    20:42 (left)   left edge ~335 px   ->  x 0.135  ->  hud_width ~285 px  == the visible HUD
    20:36 (right)  left edge ~1104 px  ->  x 0.445  ->  hud_width ~1055 px == 4x the visible HUD

So `hud.GetSize()` reported a width that does not match the HUD on screen, and
`_update_system_info_hud()` sets the HUD text WITHOUT rendering before `GetSize` is asked --
VTK can report the last rendered extent. That is a plausible mechanism, **not a proven one**,
and it is not what this bug fixes. What it does instead is make the position follow from
content: with every line inside the budget the banner cannot be wide enough to overflow, and
the anchor now refuses any placement that would not fit whatever width is measured. A wrong
width can no longer push the text off the screen, only sideways.

## The fix

* `wrap_banner_lines()` applied at `text = "\n".join(lines)` -- the ONE point where the
  refusal block, the focus summary and the placement-move lines converge, so every producer is
  covered including the next one added. The flagged banner wraps from 6 lines (longest 223) to
  8 (longest 110), and rejoining them reproduces the original exactly.
* `solve_banner_anchor(hud_width, banner_width, view_width)` -- pure arithmetic, so the half
  that was never testable now is. Beside the HUD when the WHOLE banner fits; stacked when it
  does not.

## The pattern

Fourth banner-text defect today, third where the end of a sentence was lost: bugs/0828's
derivation chain at 1246 px, bugs/0831's legend at 196 px in a 190 px canvas, bugs/0835's
reason cut at 107 characters, and now a 223-character line cut by the window. 0835 fixed the
line it was shown instead of the formatter behind it, which is why this one existed.

## Guard

`KrakenOS/UI/validate_open3d_0837_every_banner_line_fits_the_window.py`, penta phase 616. It
replays the real 20:36 banner, asserts the 223-char line reproduces before wrapping, that
rejoining loses nothing, and that the flagged geometry (start 0.445, which the old 0.72 check
passed) now stacks.

Its own first run failed on a case I had got wrong: a 1500 px banner beside a 285 px HUD does
fit in a 2478 px window (333 + 1500 + 12 = 1845). The code was right and my expectation was
not; the check now uses a width that genuinely cannot fit.
