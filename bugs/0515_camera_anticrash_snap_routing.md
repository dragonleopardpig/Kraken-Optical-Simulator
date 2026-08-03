# 0515 — camera anti-crash: audit + the last unguarded writer (design of 2026-07-29)

The agreed design (bugs/0476 rejected warn-only twice): clearance for the camera
body comes out of the lens->mirror leg by REDISTRIBUTION — the optics pins
section 1 and the SUM of sections 3+4, never the split.

## Audit on the real scene (2026-08-03, real-mesh deficit via
## `_swap_camera_body_clearance_deficit`)

| gesture | result |
|---|---|
| FOV solve 30x30 (the flagged crash field) | solves, deficit **0.000** |
| FOV solve 35x35 (once buried the sensor IN the mirror) | solves, deficit **0.000** |
| defocus +20 -> snap_detector | restores focus, deficit **0.000** |

**Items 1 and 3 of the design were already delivered by the 0468-0486 arc**: the
0482 floor (sensor + body reach + margin) with the 0482/0484 leg rebalances
keeps the body clear at both crash fields — the Jul-29 "scalar floor measured
insufficient" result predates that rebalance stack — and every solve reports
"sensor re-seated in world terms, camera carried" (glued companions ride).

## What this change adds (item 2)

`snap_detector_to_image_plane` was the LAST image-distance writer with no floor
and no frozen awareness: a raw `rows[-2].thickness += delta` that could seat the
sensor (and the body reaching past it) inside the mirror, and on a 0433-frozen
fold moved the sensor the WRONG WAY (the 0478 inversion). It now routes through
the same machinery as the FOV solve: the body-aware collision resolver
(`_resolve_image_gap_collision`, frozen slide via `_apply_folded_image_split`)
plus the frozen-aware sensor write (`apply_image_distance_frozen_aware`, camera
carried), with the release flush promoted to a full rebuild.

Guard `validate_open3d_0515_snap_and_solve_keep_camera_clear` = penta phase 414:
source contract + the 35x35 solve clear-body assertions + the defocus/snap
round-trip (focus restored, body clear, camera rides out AND back).

## The frozen-snap accuracy saga (B2/B4), and the shipped design

Routing alone left snap INACCURATE on the frozen scene, through three layers all
rooted in the 0478 station/world split: (1) the paraxial-vs-station delta is off
by a constant (11.2 mm here) -> frozen scenes use the traced measures; (2) the
measured shift lives in the STATION-ALIGNED frame, inverted relative to the leg
length ``split["far"]`` -- applying it un-flipped DIVERGED (+86.8 mm runaway);
(3) the traced-bundle measure UNDER-measures an aberrated frozen bundle (8.8 mm
for a ~16 mm defocus). Shipped: an ADAPTIVE corrective loop -- apply with the
inverted-leg default sign, re-measure, flip direction if the residual grew,
stop inside 0.5 mm (max 5 iterations; every application rides the collision
floor + the frozen-aware writer). Converges to residual -0.0 on the real scene,
with the camera riding the sensor exactly.

DURABLE: NEVER combine a measured shift with a station-frame base on a frozen
chain -- and treat single-shot focus corrections from traced measures as
first-order steps of an iteration, not exact answers.

Ship-battery note: `validate_open3d_0453_bs_led_fov_solve` fails PRE-EXISTING
(clean-tree A/B): the real scene now loads glued=True (an in-app re-save) and a
NEG topology case fires on row 2 -- its own follow-up, unrelated to 0515.
