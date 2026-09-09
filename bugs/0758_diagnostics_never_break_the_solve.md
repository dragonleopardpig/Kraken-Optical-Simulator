# 0758 -- an informational readout must never take the solve down with it

The chunked penta gate found one real regression from this session's work:

```
NEW FAILURES (PASS -> FAIL): 5  [39, 282, 412, 477, 492]
```

39, 282, 477 and 492 predate the session. **412** did not.

```
Phase 412: Quick Estimation holds the object-locked LED+BS unit through a conjugate solve

AttributeError: '_QE' object has no attribute '_in_focus_fields_at_current_track'
  quick_estimation.py:1565   in_focus_before = self._in_focus_fields_at_current_track()
```

bugs/0755 put a snapshot of the track's own focused field at the top of
`_apply_conjugate_pair`, so the banner could say what WOULD land. It called the helper
unconditionally. A consumer that composes only part of the service raised on the attribute --
and the **entire conjugate solve** went with it. A diagnostic that can break the thing it
describes is worse than no diagnostic.

## Fix

The snapshot is guarded; a missing or failing helper yields `[]` and the solve proceeds. It
still runs before the solve touches geometry, which is bugs/0755's whole point, and the field
list still reaches the stash when the helper works.

## Guard

`validate_open3d_0758_diagnostics_never_break_the_solve.py` (penta phase 547) does not only read
the source -- it composes two services, one with the helper ABSENT and one that RAISES, and
requires the conjugate solve to survive both.

---

# Also in this commit: the 77 mm disc (flag 20260908_231816_778)

> "50mm device size image focus at the sensor, but there exist unknown big circular disk."

The 50 mm device did focus (0.05351 / 0.05374 mm, both arms). The disc was mine: when I added
the `sensor standoff` row for bugs/0756 I cloned it from `RA mirror 2 (40 mm)` and cleared its
element label, desps and advanced dict -- but not its **77 mm diameter**. A bookkeeping air gap
for the camera's travel has no aperture of its own, so it was rendering as a 77 mm disc in front
of the camera.

Scene fix: `diameter 77.00 -> 32.58` (the sensor's own, so it can never clip) and `drawing
1.0 -> 0.0`. Verified by trace that this does NOT trip bugs/0738's phantom-spacer skip -- which
would have silently dropped 9.67 mm from the optical path:

```
before   residual [-0.0535, -0.0537]   field 54.09045 mm   322 rays
after    residual [-0.0535, -0.0537]   field 54.09045 mm   322 rays
```

---

# Also recorded: C1 cannot be freed by re-seating RA mirror 2

The user asked for C1 (lens rear -> filter) to become independent of A5, so the camera arm could
carry the track change instead of the sensor leg. Measured on the healthy scene, moving RA
mirror 2's seat DOES reach the trace but **cannot change the conjugate**:

```
dx =  0.0   fold vertex [279.299, 46.134, -23.982]   sensor [272.633, -2.609, -25.0]   residual [-0.0535, -0.0537]
dx = -5.0   fold vertex [273.854, 46.579, -23.451]   sensor [267.633, -7.609, -25.0]   residual [-0.0535, -0.0537]
```

The sensor is anchored in the mirror's own frame, so moving the mirror 5 mm toward the lens
shortens the lens->mirror leg by 5 mm and lengthens the mirror->sensor leg by exactly 5 mm. `s'`
is invariant to four decimals. Freeing C1 would need the sensor decoupled from that frame -- a
deeper change to how the camera arm is placed than re-seating one row. Not attempted.

This also explains five earlier failed attempts: they moved a knob that provably cannot change
the quantity they targeted.
