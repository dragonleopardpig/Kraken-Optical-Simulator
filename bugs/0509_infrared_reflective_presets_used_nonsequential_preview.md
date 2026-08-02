# 0509 — infrared reflective presets used the non-sequential preview

Flag: `attachment/recorded_bug_repros/flag_20260802_132828_513`

The flagged `IDE B.2.2 — F/3 Schwarzschild (flat image)` scene showed a large
ray spray instead of the ordered two-mirror image-forming path.  Its recording
identified the backend as `NsTraceLoop`: 493 of 496 displayed paths were
classified as `missed_image`, while only three stopped at the final surface.

## Root cause

The prescriptions extracted from William L. Wolfe's *Infrared Design Examples*,
Appendix B, are ordered sequential prescriptions.  Their negative thicknesses
encode propagation after reflection.  The UI's Auto trace-mode classifier sees
any `Mirror` row as non-sequential geometry, so it selected `NsTraceLoop` for
all seven reflective presets.  That engine can encounter the world-space
mirrors out of prescription order; it is the wrong model for these tables.

An audit through the UI's saved-layout pupil/field ray builder measured:

| Preset | Auto image hits | Sequential image hits |
| --- | ---: | ---: |
| B.2.1 SEAL | 0/124 | 122/124 |
| B.2.2 Schwarzschild, flat | 0/124 | 122/124 |
| B.2.2 Schwarzschild, curved | 0/124 | 122/124 |
| B.2.3 Reflective Schmidt (Lloyd) | 58/124 | 124/124 |
| B.2.3 Reflective Schmidt (reoptimized) | 58/124 | 124/124 |
| B.2.4 Correctorless Schmidt, curved | 20/124 | 124/124 |
| B.2.4 Correctorless Schmidt, flat | 20/124 | 124/124 |

## Fix and guard

All 15 Appendix B presets now declare `trace_mode = "Sequential"`, matching the
source prescription model.  The infrared-layout validator also runs the real
multi-field preview builder for every reflective design and requires at least
95 percent of its rays to terminate on the intended Image surface.  This guard
would fail all seven presets under the previous Auto behavior.

A headless replay of the flag's exact Full 3D `world_envelope` pipeline after
the fix selected `Scalar TraceLoop` for every reflective preset.  Each of the
seven layouts produced 496/496 paths terminating at `image`.
