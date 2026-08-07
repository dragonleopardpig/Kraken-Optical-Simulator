# 0580/0581/0582 — a pinned solve poisoned the bookkeeping, and the next swap detonated it

The morning-of-2026-08-07 recording (`recording_20260807_073557.json`), flags
072907/073042/073242/073438, plus the repair-attempt flags 074450/075626/075933 — all on
`machine_vision_Apo75.py`, build `423052ec` (so the 0574–0577 fixes were already in).

The recorded sequence: load Apo75 → swap PYRITE ✔ → `fov_solve` 55×55 **with image pin
("far", 30.0)** ✔-looking → swap ELS-85 → `fov_solve` 23×23 (no pin) ✗ defocus → remove-defocus
✗ no-op, and the user spots the **lens and RA mirror off the optical axis**. Their three repair
attempts (rubber-band snap, manual snap, drag) each exposed the next inconsistency and ended with
a dead trace.

## The chain, each link measured

**0580 — the pin writes a negative frozen gap.** `_apply_frozen_image_split` spread the near-leg
delta through the guarded 0550 spreader but wrote the far row RAW:

```python
rows[fg].thickness = float(rows[fg].thickness) - float(delta)   # 47.5815 − 52.6084 = −5.0269
```

Reproduced bit-for-bit against flag 073042 (`row7 = −5.0269`). The world re-bake right after
seats mirror and sensor correctly — which is why the flag says "works" — while the prescription
carries the known off-axis poison (a negative frozen gap: it slides downstream rows off the
folded leg at the next raw redistribution, and persists into saves).

*Fix:* floor the far row at zero and conserve the pair sum through the near spreader. The world
targets are unchanged — only the bookkeeping had to stay legal.

**0581 — the bookkeeping had no durable home.** The near span's only row was the glued BS, whose
thickness bugs/0435 pins to zero at every normalise — so the pin's booking **evaporated at the
next swap**, and the bugs/0236 follower carry dragged the fold mirror back by exactly the
evaporated amount, into the lens block (measured: mirror x 334.4 → 281.8 with the lens rear datum
at 283.7; the split's `near_min` floor could not catch it because it measures from the
station-neutral BS 328 mm away).

*Fix,* three parts, all doctrine that already existed:
- the split's `gap_start` walk now steps back over **station-neutral** rows too, so the span's
  durable home is the lens Rear Datum's gap (bugs/0569: no conjugate write lands on a
  station-neutral row);
- `_apply_near_leg_delta` never books in a station-neutral row;
- `_apply_frozen_image_split` holds the glued illumination unit across its bookkeeping with the
  same writer-agnostic bracket `snap_detector_to_image_plane` uses (bugs/0571 — the first cut of
  this fix moved the BS +47.58 mm out of its housing and killed the trace; the hazard 0571's
  "Deliberately NOT changed" section documented);
- defense-in-depth: a Safe-gap check refuses any mirror slide that would land the mirror within
  its half-aperture of a genuinely-upstream row on its incoming leg, with the numbers
  (the bugs/0572 idiom).

**0582 — the composite tore the lens block.** With the mirror parked inside the block, row 4 fell
off `_lens_leg_slide_plan`'s arclength filter and the 23×23 composite slid `rows [1, 2, 3, 5]` —
desp for members only, station cancel for the whole span: the surrogate torn apart. A hole
between the datums is proof the scene is inconsistent, not a licence to move what remains.

*Fix:* the slide refuses non-contiguous members with the numbers.

## Replayed after (the full recorded sequence, `bugs/diag_0580_pinned_leg_negative_gap.py`)

| stage | gaps legal | prism on leg | rays |
|---|---|---|---|
| PYRITE swap | ✔ | z 54.32 | 205 |
| 55×55 + far=30 pin | ✔ (was −5.0269) | z 54.30 | **220** |
| ELS-85 swap | ✔ | z 54.30, **0.0000 mm moved** (was −52.6 into the lens) | **247** |
| 23×23 solve | ✔ | z 54.30 | 79 |
| remove defocus | ✔ | untouched | 79 |

The 23×23 end state is honestly defocused: with the sensor pinned at a 30 mm leg the optics want
85–118 mm, and every writer now says so with the numbers instead of thrashing. Giving that field
at this pin needs the image-side make-room (bugs/0578's design) or the user sliding the fold arm.

Phase 450 (`validate_open3d_0580_pinned_solve_survives_swap`) replays the whole sequence and
asserts legality, on-leg, alive and honest at every stage. Phases 446–449 still pass.

## Found en route, filed not fixed

- **Stale-table clobber (hardening):** `swap_imaging_lens_from_folder` begins with
  `_read_rows_from_table()`, which rebuilds the model from the DISPLAYED cells. Any row-writing
  path that skips `_sync_table()` is silently reverted by the next tool that reads the table
  (measured in the headless replay: it moved the fold mirror back to its pre-pin seat mid-swap).
  The inspector layer syncs after each command, so live solves are safe — but this is the table
  variant of the "2D is stale" class: the invariant wants a guard, not per-instance syncs.
- **Repair tools on a wrecked scene** (flags 074450 "rubberband snap did not center", 075626
  "drag detached the body", 075933 "camera body and sensor detached"): all three ran on the
  pre-fix wreck, whose states can no longer arise. Retest each on a clean scene post-fix; any
  that still misbehaves gets its own number. The rubber-band snap parking the lens front datum
  at exactly x=0 (jammed against the BS, distances collapsed) looks suspicious independent of
  the wreck and should be the first retest.
