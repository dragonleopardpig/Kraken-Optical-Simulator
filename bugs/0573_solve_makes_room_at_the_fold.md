# 0573 — the solve makes room at the fold, so 35×35 and 55×55 solve

Follow-on to bugs/0572, which established the refusal *and the number*: on the user's
Apo75 + PYRITE 45‑85 machine a 35×35 field needs the lens **72.80 mm** further from the object
and only **45.73 mm** of the lens‑to‑fold leg is left; 55×55 needs **146.70 mm**. It also
established that the optics reach both fields — image distance **+25.36 mm** at 35×35 and
**+4.98 mm** at 55×55, with the ceiling at ~63.9 mm square. **The machine was too short, not the
lens.** The user asked for the obvious completion: make the room.

## What it does

`slide_fold_arm_along_leg(distance)` lengthens the machine at the fold — the fold mirror,
everything behind it, and the camera body glued to the sensor travel `distance` mm **along the
lens's own leg**. The bookkeeping is the bugs/0526 composite, one section further down:

* translate the arm's rows by `distance` along the leg — a fold leg's position lives in `desp`,
  not in a thickness (bugs/0499);
* grow the lens→fold gap row by the same amount, so the row frame records the leg that just
  opened up — **and that is exactly what gives the following lens slide its room**;
* cancel that station growth with `desp_z -= distance` for every row after it, so nothing else
  moves — notably the station‑neutral beam splitter sitting between them, which belongs to the
  illumination unit and not to the arm;
* carry the camera overlay by the same vector (it is placed absolutely, it does not ride a row).

The folded solve calls it when — and only when — the slide was refused for want of room, by the
shortfall bugs/0572 already computes (plus 1 mm of air), then retakes the slide it asked for. If
the arm cannot move, the bugs/0572 refusal stands: **there is still no dislocating fallback.**

## Measured, on the user's exact sequence

```
Apo75 -> swap PYRITE 45-85 -> Solve 35x35 -> Solve 55x55

35x35 -> SOLVED   "Made room first: the fold mirror and the camera moved +28.07 mm along the leg."
                  lens  x  82.039 -> 154.840   (+72.80)   z 54.283 unchanged
                  mirror x 179.788 -> 207.860   (+28.07)   z 54.321 unchanged
                  BS (-0.122, 0, 54.459) and the LED housing: 0.000000 mm
                  FOV readout 49.497 diag = 35x35, |m| 0.6583

55x55 -> SOLVED   "Made room first: the fold mirror and the camera moved +73.9 mm along the leg."
                  lens  x 154.840 -> 228.737   (+73.90)   z unchanged
                  mirror x 207.860 -> 281.757   (+73.90)   z unchanged
                  BS and LED housing: 0.000000 mm
                  FOV readout 77.782 diag = 55x55, |m| 0.4189
                  focus residual -42.88 -> -2.124 mm
```

Snapshots from the same run: `attachment/_0573_1_loaded.png`, `_2_swapped.png`, `_3_fov35.png`,
`_4_fov55.png`.

## Guard — phase 448 `validate_open3d_0573_solve_makes_room_at_the_fold`

* **A pure**: the composite on a stub — the arm translates along the leg, the gap row grows by the
  same amount, the rows after it have their station growth cancelled, the station‑neutral BS
  *between* the lens and the arm does not move, and the lens block is untouched by the
  room‑making itself.
* **B real scene**: the user's sequence. Both fields solve; the message says how far the arm moved;
  the FOV readout lands on the request; the lens and the mirror move **along** the leg (dz ≈ 0);
  the beam splitter and the LED body do not move at all.

bugs/0572's B section now runs with room‑making disabled — it owns the "no dislocating fallback"
contract, which is still exactly true when the arm cannot move.

## Still open

The image side. 55×55 lands at a −2.1 mm residual, but 35×35 reports −39 mm: the snap's adaptive
loop still cannot verify its own move on these scenes (its re‑measure returns None), so the focus
is not reliably landed even when the geometry is now right. That is the last piece of this chain.
