# 0588 — the folded gate bailed to the plain refusal (the FOURTH door)

Flag `flag_20260808_211659_040`: **"changing FOV to 55x55 is forbiden. It should be allowed."**
Scene `machine_vision_Apo75.py`, **as-loaded** lens (0703 Apo75), build `21f82684`. The user is
right twice over: it should be allowed, and — their own words — *"this bug recurred multiple
times already."*

## The recurrence, named honestly

The same user-visible refusal — *a large field is forbidden on a machine that could be
lengthened to image it* — has now arrived through four doors:

| # | door | fix that opened it |
|---|---|---|
| 1 | 0466 — AZ85, "No real-image conjugate" → "~80%" message | made the refusal *informative* |
| 2 | 0572/0573 — PYRITE, lens-to-fold leg too short | refuse-with-numbers → **make room at the fold** |
| 3 | 0578 — ELS-85, image leg beyond the fold's budget | image-side make-room (sensor + camera down the leg) |
| 4 | **0588 — as-loaded Apo75, 55×55** | this fix |

Each earlier fix opened one door and left this one shut, because each was validated on the
scene state that flagged it (post-swap), never on the as-loaded state. The project's own
doctrine — *guard the invariant, not the instance* (penta 262) — applied to bugs but not yet to
this refusal family.

## Root cause

`_folded_conjugate_gaps_for_magnification` carried a feasibility gate from the bugs/0297 era:

```python
if not (... and object_distance > 1e-6 and image_distance > 1e-6):
    return None
```

`image_distance` here is `image_total + image_delta` — a **station-frame row-sum**. Measured on
the as-loaded Apo75 at 55×55: `72.52 − 80.38 = −7.86` → `None` → the caller falls through to
the plain `_conjugate_pair`, whose failure path is 0466's "largest field ~80%" refusal — and the
**entire 0571–0583 machinery is bypassed**: the lens-leg slide, the 0572 refusal-with-numbers,
the 0573 fold-arm make-room, the 0575 re-measure/defer, the 0578 image-side make-room.

Why only the as-loaded lens? A swap rewrites the gaps (auto-refocus books a large row-7
thickness), which keeps the station sum positive — 23×23 and 35×35 pass the gate even as-loaded
(sums 35.7 and 10.0). The 55×55 sum is the first to go negative. So doors 2 and 3 never saw it.

On a **frozen** fold that sum is a station-frame quantity anyway (bugs/0576: the frame is not
the scene), and a negative value means *"the machine is currently ~8 mm too short"* — a
make-room request, not an infeasibility.

## Fix

The gate keeps `object_distance > 1e-6` unconditionally, and keeps the old bail on **unfrozen**
scenes (where the raw gap distribution really would book negative rows). When
`_folded_image_conjugate_split()` reports `frozen_world`, a non-positive station-frame image
distance **proceeds** — with a debug line naming the choice — and the image side is placed in
world by the existing machinery.

## Measured after (as-loaded Apo75, 55×55)

```
folded gate: station-frame image distance -7.8048 <= 0 on a frozen fold -- proceeding ...
lens leg slide +104.0278 mm refused: ... only 35.25 mm of the lens-to-fold leg is left
fold arm slide +69.7823 mm along [1.0, -0.0, -0.0]
lens leg slide +104.0278 mm along [1.0, -0.0, -0.0]
folded solve: image delta re-measured after the object move -80.3242 -> -46.0788 mm
snap detector iter 0: ... ok=True
```

> Object 55 x 55 mm fills the sensor. Solved (folded): object->lens 222.998 mm; the sensor
> moved −46.08 mm along its folded leg (the fold mirror stayed put) (|m|=0.4189). **Made room
> first: the fold mirror and the camera moved +69.78 mm along the leg.** Snapped the detector
> to the traced focus.

## Guarding the invariant this time

Phase 448's validator gains **B-1/B-2**: 55×55 must solve on the **as-loaded** lens, before any
swap, and must say it made room. That is the door-independent statement — *a physically
reachable field solves on ANY lens state; the machine makes room, it does not forbid* — so a
fifth door has a guard waiting for it.

The 0466 "~80%" refusal remains for scenes where it is true: unfrozen scenes, and object-side
infeasibility.
