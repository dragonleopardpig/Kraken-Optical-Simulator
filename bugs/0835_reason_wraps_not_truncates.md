# 0835 -- the refusal's reason wraps instead of losing its ending

`flag_20260920_182008_023`. The banner's reason line read:

    that field needs the lens -131.2 mm along its leg, but only 129.2 mm of physical
    room is left before its bo...

`reason[:107] + "..."` kept the panel narrow by throwing the rest of the sentence away. The
whole reason is **254 characters**; the user saw 107 of them, ending mid-word.

What the 147 discarded characters contained:

    ... before its body reaches RA mirror 1 (50 mm) (station gap 180.5 mm; short by
    1.983 mm) -- a different lens / working distance, or Force FOV to SEE the collision.

So the cut swallowed **which body the lens reaches** -- the single most useful word in a
collision refusal -- plus the station gap and the remedy. The one mercy was that it cut
mid-word, which is how the user could tell something was missing rather than ended.

## The fix

Wrap, do not cut. The panel is sized to its longest line, so wrapping keeps it exactly as wide
as the cap intended while keeping the whole sentence:

    109 | that field needs the lens -131.2 mm along its leg, but only 129.2 mm of physical room is left before its
    101 |   reaches RA mirror 1 (50 mm) (station gap 180.5 mm; short by 1.983 mm) -- a different lens / working
     46 |   distance, or Force FOV to SEE the collision.

Hyphens are never break points, so `ELS-85`, `45-85`, `48-926` and `-131.2` stay whole -- a
number broken across a line is worse than no number. A token longer than the entire width (no
real number is; a path would be) is broken rather than allowed to overflow the panel the cap
exists to protect. A reason that will not end is capped at four lines and says so, because at
that point it is a runaway rather than an explanation.

## Guard

`KrakenOS/UI/validate_open3d_0835_reason_wraps_not_truncates.py`, penta phase 614. It asserts
the old rule really did cut mid-word and lose the obstacle's name; that re-joining the wrapped
lines reproduces the sentence exactly, so nothing is dropped; that hyphenated tokens survive;
and it MEASURES every line against the cap -- including the lines the real formatter emits for
the flagged refusal -- because this session has shipped three layout defects that every logic
check passed (bugs/0828, 0830, 0831).

The guard's first run failed on the wrapper's own docstring, which quotes the old expression to
explain itself. The SOURCE check now matches the executable line rather than the phrase.
