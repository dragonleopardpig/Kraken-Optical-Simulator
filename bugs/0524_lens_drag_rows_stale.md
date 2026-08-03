# 0524 — OPEN: the FOV readout is blind to a lens drag (rows never learn the move)

## Flag

`flag_20260803_151917`: "dragged the lens to the right, the FOV is not changing" (frozen
AZ85 scene, after 0520 shipped the drag-commit refocus).

## Diagnosis (probe 2026-08-03, `probe_0524_lens_drag_fov.py`)

`translate_step_overlay("lens", (0,0,+8))` moves the lens BODY (world seats/glued
surrogate) and the TRACE sees it — the 0520 snap chases the moved focus and re-writes the
sensor gap (44.119 → 47.68). But **no other row gap changes**: the object-side and
lens→mirror section gaps stay byte-identical, so the shared first order
(s_o=158.78, s_i=131.42, |m|=1.152) — and therefore the FOV readout — never move. The
prescription and the world drift apart, the exact hazard the 0478 doc warns about
("re-baking moved the sensor correctly ONCE but let the prescription and the world drift").

## Fix direction (next arc)

Apply the user's own principle to the drag itself: an AXIAL lens-assembly drag is a
thickness edit on the lens's neighbouring sections — write through: object-side gap +d,
lens→mirror gap −d (frozen-aware on 0433 chains, the 0486 lesson: slide along the leg, not
the station axis). The per-label axial-redirect machinery (0508B/0513,
`_step_axial_redirect_latch`) is the natural home; today it serves the LED/BS labels. Once
the rows learn the move, the 0520 refocus + QE readout complete the user's loop:
drag lens → gaps update → FOV changes → image refocuses at the sensor.
