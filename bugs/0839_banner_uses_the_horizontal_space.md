# 0839 -- the banner uses the horizontal space, and goes vertical only when out

`flag_20260920_211254_784`, after bugs/0838 put the banner back beside the HUD:

> *"banner at its original location. Actually, as you can see, the banner should make use of
> the horizontal space more, vertical comes later if run out of horizontal space."*

bugs/0835 and bugs/0837 wrapped to a FIXED 110 characters. On the flagged 2478 px window that
drew the banner about 725 px wide and stacked 8 lines while roughly 1400 px sat empty to its
right. A constant cannot know the window.

## The fix

The budget is the room that is actually there: the viewport, less where the banner starts
beside the HUD, less a margin, over the per-character advance measured in bugs/0838.

    view 2478 px -> budget 302 chars -> 6 lines, longest 223, right edge 1895
    view 1600 px -> budget 181 chars -> 7 lines, longest 179, right edge 1570
    view  900 px -> budget  84 chars -> 10 lines, longest  84, right edge  882

On the flagged window the 223-character STRAY LIGHT line stops wrapping **at all**. On a
narrow one it wraps more. Horizontal first; vertical when the horizontal runs out, which is
exactly what was asked for.

Floored at 48 characters so a cramped window degrades to a readable column rather than to
slivers.

## Guard

`KrakenOS/UI/validate_open3d_0839_banner_uses_the_horizontal_space.py`, penta phase 618. It
asserts the 223-char line does not wrap on the flagged window, that this is fewer lines than
the fixed-110 rule it replaces, that a 900 px window wraps MORE (so vertical does still
happen), that the right edge stays inside the viewport at six widths from 2478 down to 640,
and that a 320 px window floors rather than shredding the text.
