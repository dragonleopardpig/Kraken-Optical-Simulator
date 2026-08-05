# 0566 — the detector snap's mirror-slide wrote a negative gap

User: *"Swap lens introduce lens and other element off axis, I think need to fix this."*

Earlier flags said the same thing twice: *"the RA mirror is not centered to optical axis after
lens swap!"* and *"Lens also off axis!"*

## Reproduction

Swapping `attachment/machine_vision_Apo75.py` to `attachment/Lens/ELS-85-4.5V16K` — reachable
only since bugs/0565 — leaves:

```
row 6  Promoted BS   thickness   0.0000 -> -51.2548      <-- a NEGATIVE gap
row 7  RA mirror     station   252.3548 -> 201.0999
       mirror world z          54.3214 ->    3.0666      <-- 51.2548 mm off the leg
row 8  Sensor  world z         -3.3490 ->  -25.9134
       lens block   stayed at z = 54.2827 throughout
```

The mirror was never *moved*. Every pose is `station + desp_z`, so a negative gap runs the
station chain BACKWARDS across that row and slides **every downstream row** off the folded leg by
exactly that amount. The displacement equals the negative gap to four decimals. This is the same
mechanism as the `-13.5949` that `machine_vision_Apo75.py` carried on disk (see
`reference_negative_gap_off_axis`), which is why the two symptoms always arrived together.

Not reproducible with the PYRITE lens — its geometry does not trigger the collision resolve — so
the first pass at this looked clean. It needed the user's own lens.

## The writer

Named by the `KRAKEN_TRAP_NEGATIVE_GAP` tripwire, which logs a stack at the moment of the write:

```
layout_table_workbench.py:1568:swap_imaging_lens_from_folder
layout_table_workbench.py:1311:_swap_auto_refocus_to_best_focus
scene_placement_commands.py:3604:snap_detector_to_image_plane
scene_placement_commands.py:3564:_apply_gap_with_floor        <-- raw += near_delta
```

Three plausible candidates were eliminated by reading before the trap answered:
`_swap_auto_refocus_to_best_focus` only touches `len(rows)-2` (row 7 — that is the legitimate
+28.69 mm camera-clearance bump); `_swap_downstream_gap` correctly wrote row 5 = 78.3848; and
`apply_image_distance_frozen_aware` already refuses `gap_new < 0.0`.

`_apply_gap_with_floor` resolves a camera-body collision by sliding the fold mirror up its
incoming leg:

```python
self.rows[near_row].thickness = float(self.rows[near_row].thickness) + float(near_delta)
```

Unclamped. That was safe only while `near_row` was the lens Rear Vertex Datum carrying 80–100 mm.
bugs/0546 re-seats a promoted solid — an absolutely placed ELEMENT whose gap is `0` — directly
ahead of the mirror, so `0 + (-51.2548)` went straight through. **A mirror already AT the gap
cannot slide further toward it**; the request was geometrically impossible and was recorded
anyway.

## Fix

Route it through `_apply_near_leg_delta`, the helper bugs/0550 built for this exact failure on
this exact row. This was simply a second call site that kept the raw write. It absorbs what the
row can take and spills the remainder back through the leg (the split's arithmetic reads only the
SUM, so the leg total — and therefore the conjugate — is preserved), stops at `gap_start` so the
object distance is never raided, and reports failure when the leg cannot absorb the slide. On
failure the caller now refuses with a message naming the shortfall, instead of writing a chain
that renders nothing.

Why an invariant did not already catch it: the 0564 repair runs at `_normalize_special_rows`, and
this write happens *after* it, in the refocus stage that closes the swap.

## Verification

* ELS-85 swap: mirror back at z = 54.3214 and sensor at −3.3490 — both exactly their pre-swap
  poses; no negative gap; only the lens block moves (worst 5.08 mm, the new lens's own geometry).
* PYRITE swap: byte-identical to before the fix — no behaviour change where there was no bug.

## Guard

`KrakenOS/UI/validate_open3d_0566_snap_near_leg_never_negative.py` (penta phase 441): a 0 mm gap
ahead of the mirror absorbs the −51.2548 slide with every gap ≥ 0 and the leg total preserved; a
slide larger than the leg is refused rather than written; the object gap is never raided; and the
call site is asserted to route through the helper with the raw `+= near_delta` gone.

Honest note on the checks: the behavioural half exercises the 0550 helper, which already existed
and already passed. The **call-site** assertions are what pin this fix — they are the checks that
fail against the old code.
