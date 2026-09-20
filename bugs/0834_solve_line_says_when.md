# 0834 -- a SOLVE line that no longer describes the scene says so

`flag_20260920_182008_023`: *"setting device size to 20x20x1, solver refused, everything
correct?"*

The refusal was correct and every number in it checks out:

| banner line | verified |
|---|---|
| requested FOV `21 x 1.05` | the front face of a 20x20x1 part is 20 x 1 mm, x1.05 margin |
| needs `\|m\| 1.097` | sensor 23.04 / 21 = 1.0971 |
| delivered now `\|m\| 0.407`, FOV `56.57` | 23.04 / 0.40728 = 56.57 |
| short by `1.983 mm` | 131.2 - 129.2 rounded to 1 dp; unrounded, 1.983 |
| `FOV 21.0x8.3` in the scene | the per-FACE strip, not the whole-sensor field (bugs/0828) |
| focus 2.699 mm, spot 113 um on a 4.5 um pixel | 25 pixels of blur -- real |

## What was wrong

Three lines apart the same panel carried:

    delivered now: |m| 0.407  FOV 56.57 x 56.57 mm          <- the refusal, current
    SOLVE: delivering 52.5 x 52.5 mm (|m| 0.4389); the lens moved -25.19 mm along its leg

Both correct. The second is the record of the PREVIOUS solve. `_solve_summary_info` is written
when a solve APPLIES (`quick_estimation.py`, three sites) and never revisited, so anything that
changes the conjugates afterwards leaves it standing as though it were now. Here that was the
device edit itself: resizing to 20x20x1 at axis offset -15 is exactly what moved the delivered
field from 52.5 to 56.57.

Nothing on screen said which was which. This is the bugs/0828 failure again -- a number shown
without its parent -- except the missing parent is WHEN.

## The fix

Re-MEASURE rather than track. `_delivered_field_now()` reads the same two quantities the solve
itself records -- paraxial magnification and the camera's active sensor -- every time the
banner is drawn, and `solve_summary_superseded` captions the line when they disagree by more
than 0.1% (the flagged case drifted 7%). Paraxial only: no trace, nothing cached.

Magnification is the test, not the field: the field follows from |m| and the sensor, so |m| is
the one quantity that cannot agree by coincidence.

Cost: `_current_finite_paraxial_magnification` is an ABCD solve over the straight-equivalent
rows -- no trace, no system rebuild. It is also the number the system HUD already prints every
refresh (`Magnification: 0.407x (sensor/FOV)` in the flagged capture, the same 0.40728), so
this adds one duplicate paraxial solve per banner draw to a cost the scene already pays. It is
not cached deliberately: a cached answer is exactly what produced the stale line.

The line is NOT deleted -- the user still wants to know the lens moved -25.19 mm:

    SOLVE (superseded): delivering 52.5 x 52.5 mm (|m| 0.4389); the lens moved -25.19 mm along its leg
      -- the scene now delivers 56.57 x 56.57 mm (|m| 0.4073)

An unmeasurable present never captions anything. No `delivered_now`, a stash with no `|m|`, a
magnification that reads zero: all leave the line exactly as it was. An unknown is not a reason
to call something stale.

## The caption went on its own line, measured

Inlined, it made a **155-character** line in a panel whose other lines cap at the 110 the
reason text is truncated to. Split, the longest is **98**. The guard measures every line it
emits against that cap, because this session has already put three layout defects on screen
that every headless check passed (bugs/0828's 1246 px chain, bugs/0830's missing picture,
bugs/0831's 196 px legend in a 190 px canvas).

## Also seen in that capture, not fixed here

The reason line is truncated at 110 characters mid-word -- *"...but only 129.2 mm of physical
room is left before its bo..."* -- so the one word naming what the lens would hit is the word
that gets cut.

## Guard

`KrakenOS/UI/validate_open3d_0834_solve_line_says_when.py`, penta phase 613. It replays the
flagged pair exactly, and asserts the history survives the caption, that an accurate line is
left alone, that an unknown present never captions, that 0.02% drift is noise while 7% is not,
and that every line fits the banner.
