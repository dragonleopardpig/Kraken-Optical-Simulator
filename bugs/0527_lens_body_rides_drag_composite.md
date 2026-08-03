# 0527 — the lens STEP body rides the 0526 drag composite

## Flag

`flag_20260803_170758`: "dragged lens to the right, FOV changed, everything looks correct
except the Lens STEP body detached" — the surrogate optics stayed on the beam, the barrel
hung below it by the drag amount.

## Root cause

The lens overlay aligner pins to the datum STATIONS (`_lens_front/rear_datum_z` →
`_row_z_positions()`), the ONE consumer inside the 0526-compensated span that reads
stations rather than poses. The composite grows those stations by the slide (trading
thickness against desp_z to hold poses), so the body's straight-frame anchor slid +z per
drag while the optics held.

## Fix

Compensate the persisted glue offset — the calibrated free parameter against that anchor —
by the same slide, mutated on `next_offset` (the value `translate_step_overlay` itself
writes at the end; a direct setter write mid-call is clobbered by it). Changing the
ANCHOR's semantics instead (pose-z rather than station-z) would break every saved scene's
persisted offset.

Verified: +8 mm drag → body delta = datum delta = (+8, 0, 0), attachment error 0.0000 mm,
gaps still ±8, FOV still follows.

## Guard

The phase-421 guard (`validate_open3d_0524_lens_drag_writes_sections`) gained the
body-attachment check: the STEP body's motion must equal the front datum's motion.
