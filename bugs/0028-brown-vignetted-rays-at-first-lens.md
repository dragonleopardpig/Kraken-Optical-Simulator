# 0028 — Brown rays "terminating" at the first lens (genuine vignetting, over-prominent)

**Status:** Fixed (2026-06-07) — display change (B); the sampling (A) was
already correct.
**Component:** Open 3D ray terminal styling
(`KrakenOS/UI/services/three_d_scene_tools.py`).
**Reported via:** the in-app bug recorder —
`attachment/recorded_bug_repros/flag_20260607_211535_721/` ("there are some
Brown colored ray unexpectedly terminated at the first lens element"), on
`machine_vision_150mm_measured`.

## Diagnosis

The brown rays carry terminal status **`"stopped"`** (a ray blocked by a
surface's clear aperture), which `_ray_terminal_3d_style` recolored as a
prominent dark-red full line `(0.50, 0.11, 0.11)`, opacity 0.88. On the measured
layout **115 of 279 rays (41%)** stop exactly at S2 (Blackbox Group 1, Ø26.8 /
semi 13.4 mm).

This is **genuine vignetting**, not over-sampling. Investigation of the sampler
showed the ray fan is already sized from the **entrance pupil**:
`_resolved_preview_pupil_radius` computes `min(entrance_radius, aperture_radius)`
and runs `Kos.PupilCalc` (so "A" — pupil-limited sampling — is already in
effect; an experiment forcing the fan to the EPD changed nothing, 115 → 115).
The vignetting is real because the layout's aperture is **EPD = 27.95 mm** while
the first lens group is only Ø26.8 — so the field corners at full aperture
physically clip at the first element.

## Fix (B)

Since the rays are genuinely vignetted, keep them but make them read as expected
vignetting instead of an error: `"stopped"` rays now draw as a **faint, thin
grey stub** — colour `(0.66, 0.66, 0.66)`, opacity `0.24`, line width `0.6`,
small endpoint — rather than a prominent dark-red full line. `absorbed` and the
other statuses are unchanged.

To *eliminate* the vignetting (rather than just de-emphasise it) is a layout
choice: set the aperture (EPD/f-number) so the entrance pupil fits the first
element, or enlarge the first lens group.

## Tests

Verified `_ray_terminal_3d_style(color, "stopped")` returns the subtle grey/faint
style and leaves `hit_detector` / `missed_detector` / `escaped` untouched; the
machine-vision render phases exercise the ray styling path in the comprehensive
harness.
