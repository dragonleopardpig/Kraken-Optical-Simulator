# 0838 -- the banner's place is computed from its text, so it sits beside the HUD

`flag_20260920_205738_022`: *"the banner position is not good, view blocking, please put it
back to beside the system resolution banner."*

bugs/0837's wrapping worked -- the 223-character STRAY LIGHT line wraps to three and nothing
is cut. But 0837 also made the placement decision read `GetSize`, the very measurement it had
just demonstrated to be untrustworthy. With a bad HUD width the "does the banner FIT" test
failed and chose the stacked fallback, putting the banner **on top of the scene** -- worse
than the overflow the test was added to prevent. A flaky input used to make a layout decision.

## The fix

Placement derives from the TEXT. Both actors are font size 13, and the per-character ratio is
MEASURED off the captures rather than assumed:

    system HUD      longest line  32 chars in ~223 px  ->  7.0 px/char  ->  0.54 x font
    wrapped banner  longest line 110 chars in ~719 px  ->  6.5 px/char  ->  0.50 x font

`BANNER_CHAR_WIDTH_RATIO = 0.55` is the conservative end: it errs HIGH, which moves the banner
away from the HUD rather than onto it. Estimates come out 241 px (drawn 223) and 799 px (drawn
719), and the anchor lands the banner beside the HUD at x = 289 px with its right edge at
1087 of 2478 -- a 48 px gap after the HUD's 241.

The estimate is an approximation and says so. A few percent of error moves the banner a few
pixels, which is the right failure mode for a layout offset. A wrong `GetSize` moved it 800 and
then hid it over the scene.

`renderer.GetSize()` stays: that is the VIEWPORT, which the banner genuinely needs. What is
gone is measuring the text actors.

## Guard

`KrakenOS/UI/validate_open3d_0838_banner_sits_beside_the_hud.py`, penta phase 617. It checks
the estimator against BOTH drawn widths, that it errs high, that the flagged HUD + banner
anchor beside rather than stacked, that the banner clears the HUD, and that the stacked
fallback still exists for a banner that genuinely cannot fit.

Three of its own checks were wrong first and are worth recording, because each is a way a
guard can lie:

* it forbade any `.GetSize(` and failed on the legitimate `renderer.GetSize()` viewport read;
* it matched on the word `GetSize` appearing in the explanatory COMMENT -- the third guard
  today to trip over its own prose;
* it hand-trimmed the test banner's lines to ~90 characters to keep the file tidy, then
  "measured" a banner 70 px narrower than the real one. It now wraps the real 223-character
  line itself rather than copying a wrapped form by hand.
