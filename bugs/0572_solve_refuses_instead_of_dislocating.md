# 0572 — the "recurrence" that broke 55×55: a spent leg and a dislocating fallback

**The user's own experiment (2026-08-06):** open `attachment/machine_vision_Apo75.py`, swap the
imaging lens to the **PYRITE 45-85**, then Solve for Thickness at **35×35** and **55×55** —
*"I think there is another recurrence bug that prevent solving for 55x55."*

There is, and it is mechanical. Run headless (`bugs/diag_0572_apo75_swap_then_35_and_55.py`):

```
35x35 -> True    lens leg slide +72.8008 mm along [1,0,0] | rows [1..5] | gaps 0:191.77  5:21.06
                 lens rear datum now x 194.36   (the fold mirror is at x 179.79)
55x55 -> True    lens leg slide +73.8976 mm REFUSED: the section gaps would become 266 / -52.8 mm
                 ... falls back to the raw object write ...
                 lens block z 54.283 -> 128.18       <- the bugs/0571 dislocation, straight back
```

Two faults, one after the other:

1. **The slide was unbounded by the geometry.** bugs/0571 moves the object-side delta by sliding
   the lens block along its fold leg. Nothing stopped it at the fold: 35×35 slid the block 72.8 mm
   and left its rear datum at x 194.36 — **past the fold mirror at x 179.79**. The room was never
   there: block end → fold centre is 58.23 mm, less the mirror's 12.5 mm half-aperture = **45.73 mm**.
2. **A refused slide fell back to the raw object write.** That write is exactly what bugs/0571
   replaced, so the second solve re-created the original dislocation — hence "recurrence": the
   first solve spends the leg, the second finds it empty and dislocates.

## Fix

* `_lens_leg_room_to_fold` — how far the block may still slide before it reaches the fold that
  terminates its leg (block end → fold centre, minus the mirror's own half-aperture).
* `slide_lens_block_along_its_leg` refuses beyond that, and stashes a reason with the numbers.
* the folded conjugate solve **refuses the whole solve** when the slide is refused, quoting it —
  **there is no safe fallback on a fold leg**, and a solve that silently dislocates the machine is
  worse than one that does not run.

Measured after, on the user's exact sequence:

```
35x35 -> False  FOV out of range on this fold: that field needs the lens 72.8 mm further from the
                object, but only 45.73 mm of the lens-to-fold leg is left -- slide the fold mirror
                (and the camera behind it) 27.07 mm along the leg first, or pin a segment.
55x55 -> False  ... needs 146.7 mm ... slide the fold mirror ... 101 mm along the leg first ...
NOTHING MOVES: max row drift 0.000000000 mm in both cases.
```

Snapshots from the same run: `attachment/_0572_1_loaded.png`, `_2_swapped.png`, `_3_fov35.png`,
`_4_fov55.png`.

## Why 55×55 cannot be solved on this scene (the honest answer)

It is not an arithmetic failure — it is a machine that is too short. With the PYRITE 45-85
(f = 85.13 mm) on a 23.04 mm sensor:

| field | \|m\| | object→lens needed | lens must move | room on the leg |
|---|---|---|---|---|
| 35×35 | 0.658 | 191.77 mm | +72.80 mm | 45.73 mm (short by 27.07) |
| 55×55 | 0.419 | 265.67 mm | +146.70 mm | 45.73 mm (short by 100.97) |

The fold mirror (and the camera behind it) has to travel that far along the leg first. The refusal
now says exactly that, with the number, so the user can do it — by dragging the mirror, or by
pinning a segment.

## Guard — phase 447 `validate_open3d_0572_solve_never_dislocates_when_the_leg_is_full`

* **A pure**: the room measure is block-end → fold-centre minus half-aperture (45.729 on the real
  numbers); a leg with no fold ahead of it stays unbounded.
* **B real scene**: the user's exact sequence — both fields refuse, the refusal names the shortfall
  and what to move, and every row's world pose is unchanged to 1e-9. Non-vacuity: a field that
  DOES fit (24×24) still solves and still slides the lens along its leg (dx +32.157, dz −0.000).

## Knock-on

bugs/0569's C5 lever moved from 40×40 (which no longer fits on that scene and is now correctly
refused) to 24×24, which does.

**Still open** (unchanged by this bug): the image side does not converge on these scenes — the
snap's adaptive loop cannot verify its own move — so a solve that DOES fit still reports a
residual. And the natural completion of this fix is to *make* the room automatically: slide the
fold mirror and the camera along the leg by the shortfall, then run the solve. The refusal already
names the exact distance, which is the input that feature needs.
