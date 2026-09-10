# 0772 -- a hardware rail must not move when the lens moves

Flag `20260910_162743_697`: *"device size set to 23x23x1mm, image plane dislocate, only 2 rays,
worse than before."*

Reproduced on `om05a_folded_80mm` with a 23 x 23 x 1 device (offset -13.5, correctly centred):
the solve moved the lens -120.6 mm correctly and then **did not book the image side at all**,
leaving the image 77.2 mm off with a 1970 um spot and 216 rays landing instead of 644. The reason:

> the imaging group would have to travel to **192 mm**, outside its **192.7** to 292.7 mm stage

A **0.66 mm** miss. Those limits were mine -- guessed before the user said *"the A5+C1 is where
the motors can travel"*. The authored geometry gives seat 269.120, A5 130.889 in front, C1 17.510
behind, so the rail is **[138.231, 286.630]**, which contains 192.0 with 54 mm to spare.

**First, what this was NOT.** A/B'd against `d024bb64` (before bugs/0770 and 0771): byte-identical
numbers. The user's "worse than before" was not a regression from today's work -- it is a cliff in
device size. A 30 mm device lands (0.05 mm); a 23 mm device needs 0.66 mm more arm travel than the
stage claimed to have, and falls off.

## With the real rail

```
                  armx      rays   measured    spot
guessed limits  269.120      216   -77.222   1970.5 um
A5+C1 rail      191.979      644    -0.081      2.10 um   <- inside one pixel
```

## The code was worse than the guess

bugs/0766 added `_motor_rail_from_lens_block` precisely so limits would not be hand-typed. It was
wrong in a way the authored state hides: it read the **live** gaps. `a5` and `c1` track the LENS,
not the arm, so mid-solve -- with the lens moved to `a5 = 10.265` -- it produced an arm rail of
**[258.9, 407.3]**, further from the truth than the number it replaced.

The rail's LENGTH is invariant (`a5 + c1 = 148.400`, preserved by the lens's thickness pair) but
its ANCHOR is the authored lens position, which is not recoverable once a solve has moved things.
So the helper now reports only what it can measure -- the rail length and the three row indices --
and the travel limits are the scene's to state.

## Scene

`attachment/om05a_folded_80mm.py` (gitignored, backup `.pre-rail.bak`):

```
arm_min_mm / arm_max_mm   192.683 / 292.683  ->  138.231 / 286.630   (seat -+ A5, C1)
min_mm     / max_mm       -60.0   / 30.0     -> -121.219 / 27.180    (pad, same rail)
```

## Guard

`KrakenOS/UI/validate_open3d_0772_a_rail_that_moves_is_not_a_rail.py`, penta phase **556**: the
helper reports no travel limits it cannot anchor (A); it still reports the rail length and rows
(B); the rail length is invariant under the lens's thickness pair (C); a scene's own limits are
honoured untouched, and the corrected rail admits the 192.0 mm this flag needed (D).
