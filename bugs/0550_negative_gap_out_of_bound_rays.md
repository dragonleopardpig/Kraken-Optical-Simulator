# 0550 — "Extra rays out of bound"

**Flag:** `attachment/recorded_bug_repros/flag_20260805_072959_035` (build `bd3b86d1`, dirty)
**Scene:** `attachment/machine_vision_Apo75.py` (the AZ85 + RA-mirror + BS assembly after a swap
to `attachment/Lens/0703-005-000-40-EXC`)
**Reported:** *"replace lens surrogate, flip the LENS STEP, change FOV to 23x23, solve for
thickness. Extra rays out of bound."*

## What the flag shows

Rays spray past the RA prism and off-frame; `traced_ray_terminations` reads
`no_next_intersection: 375` of 558 paths, with drawn bounds blown out to x 375, z −366…+505.

The saved layout carries a **negative gap** on the re-seated promoted BS row, so the station
chain runs BACKWARDS across it:

| row | station | thickness | name |
|---|---:|---:|---|
| s5 | 168.974 | 83.381 | Rear Optical Vertex Datum |
| **s6** | **252.355** | **−13.595** | **Promoted OPTICAL STEP optical solid (BS)** |
| s7 | **238.760** | 72.519 | Promoted OPTICAL STEP optical solid (RA mirror) |

A gap is a *distance*. A negative one puts the next surface behind its predecessor, and the
trace loses it.

## Measurement

`bugs/diag_0550_negative_gap_strays.py` traces the scene as saved, then zeroes the negative gap
while compensating `desp_z` on every downstream row so **no pose moves by even a micron**
(verified drift 0.0 mm), and traces again. The un-swapped scene is the yardstick:

| | `no_next_intersection` | reaching | stop-vignetted |
|---|---:|---:|---:|
| original AZ85 (no swap) | **279** | 225 | 54 |
| Apo75 as saved | **375** | 93 | 87 |
| Apo75, gap zeroed | **287** | 160 | 105 |

287 against a normal 279 — the negative gap accounts for essentially every out-of-bound ray.
The residual (fewer reaching, more stop vignetting) is expected physics: a 75 mm lens at FOV
23×23 where an 85 mm lens ran 20×20.

## ROOT CAUSE (proven from the trap log)

The user reported the strays appear **as soon as the lens is swapped, before any FOV change**,
and ran a session with `KRAKEN_TRAP_NEGATIVE_GAP=1`. That log (609 trapped writes, every one the
already-persisted −13.5949 — i.e. the negative being *propagated* by row clones and paraxial
reference copies, not created) carried one signature that is a real write path:

```
quick_estimation.py:1504 _rebalance_image_leg_sections
  <- quick_estimation.py:1607 _rebalance_split_sections
  <- paraxial_tools.py:1859  _apply_folded_image_split
  <- paraxial_tools.py:1421  _apply_frozen_image_split
```

`_folded_image_conjugate_split` picks its near-leg write target **positionally**:

```python
"near_gap_row": int(mirror_row - 1),   # last leg INTO the mirror
```

* **Before bugs/0546** `mirror_row - 1` was the lens **Rear Optical Vertex Datum**, carrying
  80–100 mm — a −13.6 mm delta stayed comfortably positive.
* **After bugs/0546** it is the **re-seated promoted BS row, thickness 0.0** →
  `0.0 + (−13.595) = −13.595`.

And the write happens in `_apply_frozen_image_split` with **no negativity guard at all**, while
the unfrozen branch immediately below it explicitly refuses that case. The frozen branch is the
one a swap takes: `_swap_auto_refocus_to_best_focus()` runs at the end of every swap and is a
**headless no-op** (folded solve → live-only), which is exactly why the headless swap
reproduction left `rows[6] = 0.0` and the live one goes negative.

## Fix (root)

`near` is `sum(thickness[gap_start:mirror_row])` — a SUM over a span — so the delta may be
placed on ANY row in that span without changing what the split reads. `_apply_near_leg_delta`
absorbs what `mirror_row - 1` can take and **spills the remainder back** through the span to
`gap_start`; the leg total is preserved exactly, no row goes negative, and a delta the whole
span genuinely cannot absorb is REFUSED (constraint out of range) rather than written as a chain
that cannot be traced. The split now publishes `gap_start` so the applier knows the span.

Deliberately NOT clamped: the mirror's OWN gap to the sensor (`far_gap_row == mirror_row`), which
bugs/0297 shows may legitimately go negative on a best-focus seat.

## Why the gap could go negative here

`bd3b86d1` (bugs/0546) re-seats a promoted solid that sat inside the lens block to just after
the rear datum — which makes it the **immediate predecessor of the downstream mount**, carrying
a *zero* gap. Any "move that element by adjusting its preceding gap" operation now writes into a
zero row, where a negative result is near-inevitable. The arithmetic in the saved file matches
exactly: `83.381 + (−13.595) = 69.786` = rear-datum station → mirror station. Before 0546 the
predecessor was the rear datum itself (83 mm), where the same −13.6 mm move stayed comfortably
positive and harmless.

## Fix

`Open3DSolveService.solve` wrote `rows[i].thickness = solved` with **no lower bound at all** —
confirmed by inspection; the paraxial solvers it calls bound their own search at 0, so a
negative arriving here means the objective wanted the element *ahead of its predecessor*. It now
clamps to 0 and **says so** in the status message ("CLAMPED to 0 mm at row N: best focus wants
that element AHEAD of its predecessor — move the element itself, or free a different gap")
rather than silently flooring or committing an untraceable chain.

## Diagnostic (this is what named the offender)

Every other gap writer found already guards its negative case
(`scene_placement_commands` `gap_row`, the paraxial near/far gap writers, the bugs/0526
composite, the swap's own `_swap_downstream_gap`), the flagged session had **no recording
active**, and the solve bails headlessly ("No detector hit data for best-image solve target") —
so the writer could not be named by inspection. Per the bugs/0391-0395 lesson (*when headless
repro is impossible, ship the DIAGNOSTIC first*), two things name it instead:

* **`negative_gap_rows` in the flag** — always captured; every negative-gap row with its name,
  thickness, station and next station.
* **`KRAKEN_TRAP_NEGATIVE_GAP=1`** — an opt-in tripwire (`install_negative_gap_trap` in
  `surface_table_model`) that appends the writer's stack to
  `attachment/negative_gap_trap.log`. Off by default, and the class is only patched when the
  variable is set, so it costs nothing normally.

One live session with the trap set named the writer (see ROOT CAUSE above). Keep both: the flag
field costs nothing, and the tripwire is the fastest way to pin the next one.

## Guard

`KrakenOS/UI/validate_open3d_0550_no_negative_gap.py` (penta phase 435):

* **NEAR-LEG SPILL (the root cause)** — a −13.595 mm delta onto a zero-gap `mirror_row - 1`
  spills to the preceding gap row: no row negative, leg total moved by exactly the delta, the
  mirror's own gap untouched; a delta larger than the whole span is refused and leaves nothing
  negative behind; and the frozen split must route through the spill rather than writing raw.
  Non-vacuity checked by restoring the raw write — 3 assertions fire.
* **CLAMP** — the REAL `Open3DSolveService.solve` with only the optimiser's answer stubbed: a
  negative solve lands at 0 and reports the clamp, a positive one is written through untouched.
* **FLAG / TRIPWIRE** — the snapshot carries `negative_gap_rows`; the tripwire stays off without
  its environment variable.

## Open

`_apply_frozen_image_split` still does its bookkeeping through gap rows before re-baking world
centres. That is legitimate here (it re-bakes the mirror, sensor and camera in world terms right
after), but the prescription-vs-world split remains the standing hazard behind bugs/0448/0478 —
worth a pass that expresses the whole frozen image leg in world terms.
