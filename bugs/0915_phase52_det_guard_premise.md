# 0915 -- phase 52 failed in every full run and passed alone: the guard never set its premise

Phase 52 ("Det toggle keeps Object/Image reference disks (no detector)", bug 0047) had been
recorded as `fail` in the gate baseline since at least 2026-08-30. In the 2026-09-27 full run it was
the last gated failure. Run alone, it passed.

## Root cause: inherited state, not the product

The bug 0047 scenario is an ON-AXIS field. There, the doublet's auto image plane is a 1 mm
"detector" with max real image height 0, so the coverage overlay draws no image circle, and the
Object/Image disks must stay. The live guard replaced the rows with the doublet but never set the
field. The phase docstring said it was "the last phase", which stopped being true long ago. In the
harness it runs after phases 0-51 and inherits an OFF-axis field.

Measured with the fresh editor:

| Field | max_rih | Coverage overlay | Det-ON disks |
|---|---|---|---|
| 0 (on-axis) | 0.0 | 3 actors, no replacement geometry | 2 |
| 5 deg (off-axis) | 8.74 mm | 11 actors, image circle drawn | 0 |

Off-axis, hiding the disks is the CORRECT bug 0033 behaviour. The guard's message, "the coverage
overlay drew nothing", misdiagnosed it.

## Fix: the guard only; no product change

- It sets its premise: an on-axis field.
- It checks the premise: `_detector_coverage_will_draw` is False on-axis. The service still
  draws a sensor outline (3 actors), so "drew nothing" was never the right test; "draws no
  replacement geometry" is.
- It adds the off-axis companion: the disks give way ONLY when the overlay draws its image circle
  (the decision is True, and it draws more than on-axis).
- It restores the field, so phases 53+ see exactly what they always did.

## Verification (A/B in the harness)

- Phases 0-52 with the OLD guard: 52 fails.
- Phases 0-60 with the new guard: 61/61 pass.
- The baseline records 52 as `pass`.
