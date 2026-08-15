# 0625 — TRIAGE (OPEN): the delivered field is DECENTRED; 2 field spots land off-glass

User reports (2026-08-15/16): "image side still missing 2 sampled rays, only shows 7"
+ "the object side is missing 2 launched rays". After 0624 (blackbox extended
apertures) the pencils all launch and refract — but 7 of 9 spots arrive.

## Measured (solved Apo75, 55×55, c = 0.906, build 995134a7)

Per-launch-column census (grid columns x = −27.6 / 0 / +27.6, 186 rays each):

- **x = −27.6: ALL 38 missed_image; only 21 arrivals** — the missing spots are BOTH
  on the minus-fold-axis side.
- x = 0: 61 arrivals, 0 missed. x = +27.6: 52 arrivals, 0 missed.

Consistent with the long-standing landing asymmetry (arrival clusters at
u ∈ {−10.6, −0.2, +6.5} instead of ±10.4): the real folded machine images the field
OFF-CENTRE along the fold axis. The bugs/0591 correction c fixes the delivered
SCALE; nothing fixes the delivered CENTROID, so a launch grid centred on the axis
maps to a footprint shifted off the 23×23 glass on one side.

## Design (the 0591 pattern, for the centre)

1. During `_refine_folded_field_fill` (which already traces probe bundles), measure
   the ON-AXIS probe's landing CENTROID on the sensor; convert to an object-plane
   offset via the delivered magnification: `obj_shift = −centroid / m_delivered`.
2. Store as `_folded_field_center_state` (editor runtime state; cleared on
   load/lens-swap/camera-swap exactly like `_folded_m_correction_state`).
3. Consumers (the delivered-readers side of the 0602 doctrine):
   - `_sample_imaging_field_grid_pairs`: offset the linspace grid by the shift.
   - The drawn FOV square (coverage overlay object rect): shift its centre.
   - Verify: 9 spots, arrivals ≈ 160+, symmetric landing clusters.
4. Guards: extend phase 467 (grid centre = learned shift; neutrality when unset);
   re-derive any guard pinning the grid symmetric about zero.

## Status: OPEN — design ready, not yet implemented (session ended at user's
shutdown request). Resume here.
