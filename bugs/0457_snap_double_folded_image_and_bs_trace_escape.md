# 0457 — after add-BS + snap: the drawn Image is DOUBLE-FOLDED, and the trace stops half way

Recording `recording_20260728_075613.json` (3 flags) + `flag_20260728_080101_869` ("STEP hidden",
the clear view), all on build **`f1df9b58`** — i.e. WITH 0451 + 0456. Flags 1–2 are the user's
reference shots ("Original.", "1st RA mirror deleted."); flag 3 is the report:

> "After adding BS, rubberband select + snap to optical axis, sensor/image place relocate to wrong
> position, causing ray tracing stop half way. Layout save to `machine_vision_AZ85_RA_Mirror_BS.py`"

These are TWO independent defects. Neither is a 0451/0456 regression — those two fixes hold.

## Defect A — the drawn Image row is folded TWICE (the "wrong position")

The live scene and the saved prescription disagree about where the sensor is:

| | Image row (world z) | camera body (world z) |
|---|---|---|
| live app (both flags) | **−48.8** | +2.7 |
| the SAVED scene reloaded | **+2.73** | +2.73 |

Row 7 (the image-side promoted RA mirror) sits at z = 54.23 with thickness 51.5:

* correct single fold: 54.23 − 51.5 = **2.73** ← what the saved prescription and the camera say
* what the live view drew: 54.23 − 2×51.5 = **−48.77** ← the fold displacement applied a SECOND time

So the prescription is right and the DRAWING is wrong: on a frozen/snapped scene the row already
carries its absolute, already-folded world position, and the display fold then translates it by the
mirror thickness again. The camera body is drawn at the correct single-fold position, which is why
the sensor appears to "relocate" away from its camera. Same divergence FAMILY as 0456 but a
different mechanism and a different code path: 0456 was row-vs-body inside the solve; this is
prescription-vs-display inside the fold overlay. Compare 0448 (drawn-vs-traced tilt convention).

**Why the 0447/0456 probes never caught it:** they measure `station + desp` — the PRESCRIPTION. The
double fold happens in the DISPLAY layer, so a probe must assert on the DRAWN actor (what the
recorder captures in `row_actor_bounds`), not on the row arithmetic. Any guard for this must read
the drawn geometry.

## Defect B — the trace is already dead before the snap (the "stop half way")

Replaying the sequence headlessly (`/tmp/.../repro_snap.py`, ~2 min) on the pristine AZ85:

| step | ray terminal statuses | detectors |
|---|---|---|
| 1. original | **585 hit_detector** | Image at (235.9, 0, 1.5) |
| 2. 1st RA mirror deleted | **3249 stopped** (all vignetted) | + a suppressed dead-end arm (0451 working) |
| 3. BS added | **279 escaped, 0 hit** | both at the LED — (−0.12, −47.7, 38.7), (−0.12, 1.2, 88.1) |
| 4. rubber-band + snap | **279 escaped, 0 hit** | unchanged |

The beam stops imaging at **step 2** — deleting the object-side fold, long before the BS or the
snap. Nothing downstream can recover it: by step 3 every ray escapes and no detector sits at the far
end, which is exactly the flag's "ray tracing stop half way" (the STEP-hidden shot shows the bundle
dying just past the lens, with three stray "Sensor 23.0×23.0 / Image circle" labels — the three
branch arms — scattered at the BS, mid-lens and the mirror).

This is the known **non-sequential first-order seam** (`project_nonseq_first_order_seam`): the
sequential PupilCalc throws on a BS, the silent fallback aims the source down the OLD folded path,
and the launched fan misses the re-seated chain. It is now the dominant symptom, not a side effect.

**Note the asymmetry that proves it is a launch/aim problem, not a geometry problem:** loading the
user's SAVED `machine_vision_AZ85_RA_Mirror_BS.py` traces **healthy — 145 hit_detector, 7 escaped**,
with the Image at 2.73 coincident with the camera. The same geometry built INTERACTIVELY does not.
The save normalizes what the interactive path leaves inconsistent.

## What to do

Defect B is the real build — a universal first-order reference so the source aims at the actual
first surface of the actual chain (design note in `project_nonseq_first_order_seam`). It subsumes
the sparse-ray complaints from 0433/0448 as well.

Defect A is separately fixable: gate the display fold for rows whose placement is already absolute
(`stay_put_freeze` / `last_axis_to_axis_move` / snapped), the same predicate the 0447 appliers use.
Its guard MUST assert on drawn actor bounds.

Not started — documented with the evidence above so the fix can begin from measurements rather than
from a re-derivation.
