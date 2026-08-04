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

## Diagnostic (the offender is not yet named)

Every other gap writer found already guards its negative case
(`scene_placement_commands` `gap_row`, the paraxial near/far gap writers, the bugs/0526
composite, the swap's own `_swap_downstream_gap`), the flagged session had **no recording
active**, and the solve bails headlessly ("No detector hit data for best-image solve target") —
so the writer in *this* flag is not proven. Per the bugs/0391-0395 lesson (*when headless repro
is impossible, ship the DIAGNOSTIC first*), two things now make the next occurrence name itself:

* **`negative_gap_rows` in the flag** — always captured; every negative-gap row with its name,
  thickness, station and next station.
* **`KRAKEN_TRAP_NEGATIVE_GAP=1`** — an opt-in tripwire (`install_negative_gap_trap` in
  `surface_table_model`) that appends the writer's stack to
  `attachment/negative_gap_trap.log`. Off by default, and the class is only patched when the
  variable is set, so it costs nothing normally.

Run one live session with the trap set, repeat the workflow, and the log names the writer.

## Guard

`KrakenOS/UI/validate_open3d_0550_no_negative_gap.py` (penta phase 435) drives the REAL
`Open3DSolveService.solve` with only the optimiser's answer stubbed: a negative solve lands at 0
and reports the clamp, a positive solve is written through untouched with no clamp reported, the
recorder snapshot carries `negative_gap_rows`, and the tripwire stays off without its
environment variable.

## Open

The root violation is still upstream of the clamp: on a **frozen** scene, element positions live
in `desp` (world terms), and moving the mirror by writing its preceding gap contradicts the
durable bugs/0448/0478 rule — *place image-side geometry in WORLD terms, never by assigning a
gap*. The clamp stops the damage; the world-aware fix waits on the tripwire naming the writer.
