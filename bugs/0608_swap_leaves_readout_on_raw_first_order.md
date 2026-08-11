# 0608 — After a swap the FOV readout ran on the RAW folded first order (FIXED)

Flag `flag_20260811_133818_773`: *"swapped a lens, please verify rays."* Scene
`machine_vision_Apo75.py` with **PYRITE 4.5/85/0.5x-2.0x** (EFL 85.13) swapped in,
build f8c169c8.

## The rays are sound

Reproduced the swap headlessly and matched the user's recorded census exactly —
558 paths, `no_next_intersection` 280 / `target_termination` 205 /
`aperture_stop_vignette` 73:

- **205 arrivals, 205 of them inside the 23x23 active rect** — no strays, no misses,
  no fake arrivals.
- **9 clean field spots** on the 3x3 grid, each with RMS 0.0000 mm. Zero RMS is
  CORRECT here and not a red flag: the vendor lens is a SURROGATE built from two
  ideal `Thin Lens` rows, so every ray of a field converges exactly. Real aberration
  numbers need the vendor's own data — this model cannot produce them.
- 73 vignetted at the stop, 280 escaping down the beam splitter's other arm.

## The readout was not

Measured launch-vs-landing per arriving ray (object plane -> sensor plane):

| quantity | value |
|---|---|
| launched object field | 15.30 x 15.30 mm (exactly the drawn label — the launcher is honest) |
| landed image field | 18.78 x 17.74 mm on a 23 x 23 sensor |
| delivered \|m\| (ray-measured) | **1.160** |
| readout \|m\| | **1.506** |
| learned correction | 1.0000 (i.e. none) |

So the "FOV 15.3 x 15.3" label implied that field fills the sensor, while the traced
rays covered ~82% of its width — a **23% overstatement**, the bugs/0591 defect through
a new door.

**Root cause:** bugs/0591 invalidates `_folded_m_correction_state` on a swap (right —
the old glass's factor is meaningless on new glass) but nothing RE-MEASURED it, so every
readout between the swap and the user's next solve was the raw folded first order. A
solve does re-learn it (measured after one: readout vs delivered agree to −0.18%), but
the user should not have to run a solve to be told the truth.

## Fix

`QuickEstimationService.relearn_folded_m_correction()` re-measures delivered/promised
with the same real-ray probe the solve's refinement uses (and divides out any standing
factor so the result is absolute, never compounded). Called from
`_relearn_folded_m_correction_after_swap()` right after the swap's auto-refocus, on BOTH
the lens-swap and camera-swap paths, and reported in the swap message ("Re-measured the
delivered magnification by real rays (…%)"). Scenes whose first order is already
trustworthy (sequential, no world-placed chain) measure None and keep correction 1.0.

Guard: phase 460 (`validate_open3d_0608_swap_relearns_delivered_magnification`).
