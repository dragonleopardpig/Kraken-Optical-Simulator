# 0577 — the refocus loop diverged, and nothing stopped it

Flag `flag_20260806_210424_793`, "solve for FOV 23x23", recorded after
`flag_20260806_210207_730` ("swapped again with ELS85 lens, everything go heywire again, is your
fix general enough?"). Scene `machine_vision_Pyrite85_BS.py`, lens `ELS-85-4.5V16K` — a different
scene and a different lens from the 0574/0575/0576 flags.

The solve left **row 7's thickness at 2571 mm and the sensor at world z = 2595**, on a machine
whose entire image-leg budget was 90 mm. The camera body went with it, to z ≈ 2533–2607.

## It is not a regression — control first

Before diagnosing, the same script was run on a detached worktree at `f51b44ed` (pre-0574/5/6):

| after the 23×23 solve | pre-fix `f51b44ed` | with 0574/0575/0576 |
|---|---|---|
| surrogate rows 1–5 slid | −129.4 mm | −129.4 mm |
| lens body bounds X | [228.395, 287.587] — **detached by 129.4 mm** | [98.98, 158.17] — **tracks** |
| row 7 thickness | **2177.63** | **2624.32** |
| sensor world z | **2170.24** | **2648.62** |

The runaway reproduces identically pre-fix. It is pre-existing; 0574/0575/0576 neither caused it
nor caught it, because the Apo75 scene never entered this path. The table also settles the
question the flag asked: **the 0574 body carry is general** — on this second scene and second lens
the barrel detached by 129.4 mm before the fix and rides the surrogate after it.

## Root cause — two, and the first is the engine

**(a) `_apply_gap_with_floor` fell through to the raw write.** It ended:

```python
if not self.apply_image_distance_frozen_aware(target_gap):
    self.rows[-2].thickness = float(target_gap)
```

This is the same ambiguity 0575 fixed one call site up, and here it is not latent — it is what
powers the divergence. On a frozen fold the raw write moves the sensor the wrong way (bugs/0478)
**and grows the leg budget** `const = gap + far`, so each pass's target is larger than the last.
Measured across the five passes: the leg went 17 → 2178 mm and `const` went 90 → 5219 mm.

**(b) No divergence guard, because two guards cancel.** From the loop's own log:

```
iter 0: base=16.99   residual=-129.40  dir=-1 -> far 146.39
iter 1: base=84.70   residual=-197.10  dir=-1 -> far 281.80
iter 2: base=220.11  residual=-332.52  dir=-1 -> far 552.63
iter 3: base=490.94  residual=-603.36  dir=-1 -> far 1094.30
iter 4: base=1032.60 residual=-1145.03 dir=-1 -> far 2177.63
```

The residual grows every pass, so the adaptive flip (`|residual| > previous_magnitude → flip`)
fires correctly — and bugs/0570's pre-emptive flip (`a leg that would go negative proves the
sign`) immediately flips it *back*, because moving toward the mirror would take the leg negative.
`direction` is pinned at −1 and the error roughly doubles each iteration. Note `dir=-1` on every
line: that is the two guards cancelling, not the adaptive one failing to fire.

## Fix

1. `_apply_gap_with_floor` returns the frozen writer's refusal instead of writing it raw. Unfolded
   scenes have no inversion and keep the raw write (their refusal string is empty).
2. The loop keeps the **best state seen** — all row thicknesses and desp, so the collision
   resolver's mirror slide is covered too — and restores it the instant a pass fails to improve.
   Improvement is the only licence to keep a pass.
3. When it reverts without ever improving, `_snap_detector_refusal` says so, so the caller cannot
   report a focus that did not happen.

## Measured after

| | before | after |
|---|---|---|
| sensor world z | 2648.62 | **24.296** (unchanged from load) |
| row 7 thickness | 2624.32 | **0.0** (unchanged from load) |

And the message now names the real limit instead of thrashing:

> that field wants a mirror→sensor leg of 117.6 mm, but this fold's leg budget is 30 mm — slide the
> fold mirror (and the camera behind it) along the leg first, or pin a segment.

## What this exposes — see 0578

The honest refusal is the right behaviour, but it is not the user's goal. Their objective is to
change the imaging lens and the camera **at will**. On this scene the camera row's thickness is 0,
so `const = 30 mm`, while the ELS-85 wants ~117 mm of back focus. bugs/0573 solved exactly this
shape on the OBJECT side by making room at the fold; the image side has no counterpart, and
`slide_fold_arm_along_leg` cannot serve — it moves mirror and camera together, leaving
mirror→sensor unchanged. What is missing is a camera-side slide that moves the camera assembly
away from the mirror and grows the budget. That is 0578.
