# 0602 — "Solving for 55x55 now forced to become 49.8x49.8" (FIXED)

Flag `flag_20260810_164247_396` (first complaint), scene `machine_vision_Apo75.py`, build
`e1b2958f`. After a 55×55 FOV solve, the green object-plane coverage label read
**FOV 49.8×49.8** — the user read it as the solve refusing/clamping their request.

## Root cause — the readout contract has TWO readers

bugs/0591 made the solve book a *corrected* conjugate: the learned measured/first-order
ratio `c` shifts the RAW paraxial magnification so the field the TRACED machine delivers
is the 55 the user typed (verified by real rays, ±1%). `QuickEstimationService.
current_state()` reports the measured-aware magnification (`m_raw × c`), so the panel
readout says 55.

But the detector-coverage overlay's object-FOV box computes `sensor / |m|` from
`_current_finite_paraxial_magnification()` — the **raw** paraxial value. After the solve
that back-computes `55 × c`; with this scene's learned `c ≈ 0.905`, exactly the flagged
49.8. The machine was delivering 55 the whole time; the LABEL was the lie — the
wrong-direction number, worse than the honest pre-0591 error because it looks like a
forced clamp.

## Fix

- `folded_m_correction(editor)` promoted to a module-level accessor in
  `quick_estimation.py` (the service method delegates), so display readouts outside the
  service share the delivered-truth view.
- `DetectorCoverageOverlayService._magnification()` multiplies the raw paraxial value by
  it. Every consumer of the metrics heals at once: the green FOV label, the drawn
  object-FOV rectangle, and the pickable Object-FOV square.
- The raw helper `_current_finite_paraxial_magnification` deliberately stays raw: the
  solve's own booking math and `current_state()` apply `c` themselves — correcting at
  the source would double it (and would perturb sampling/coupling physics paths).

Readout contract after the fix: **typed = delivered = panel readout = drawn label**.

Guard: phase 456 (`validate_open3d_0602_0603_readout_and_corners`) — sets a synthetic
correction on the editor and asserts the overlay magnification is `raw × c` while the
raw helper is unchanged.
