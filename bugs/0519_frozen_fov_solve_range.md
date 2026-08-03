# 0519 — the FOV solve refused large fields on a frozen fold (55×55)

## Flag

`flag_20260803_140636`: "I couldn't change FOV to 55x55, I can do this in actual
production" — the frozen AZ85 scene (machine_vision_AZ85_RA_Mirror_BS), FOV popup →
Solve for Thickness → "That field is beyond this lens's range … the image distance would go
negative … about 77% of the size you entered."

## Root cause

The 0433-frozen scene fails BOTH conjugate branches' assumptions:

- The folded-aware branch (`_folded_conjugate_gaps_for_magnification`) is gated on
  `_folded_optical_solid_straight_equivalent_rows`, which needs a live rotating fold
  transform — the 0433 freeze baked those poses away, so the gate returns None.
- The plain `_conjugate_pair` uses `image_distance = f(1+m) + ppp` from the straightened
  reference, whose LAST VERTEX is the prism placeholder sitting ON the image plane
  (zero-length gap row): `ppp = −(H2→image) = −131.42`. The formula therefore measures the
  new gap from a zero-length anchor and crosses zero at m=0.546 — refusing 55×55
  (m=0.419) for a physical sensor move of just **−10.8 mm**. The "77%" clamp is exactly
  the artifact's zero-crossing (16.29/0.546/38.89 = 0.77).

## Fix

In `_conjugate_pair`, when the plain value turns infeasible (≤0) AND the scene has a frozen
image-side fold (`_folded_image_conjugate_split()["frozen_world"]`): re-anchor on the WORLD
far leg — H2 and the fold stay put through a conjugate change, so the sensor's world move
is `Δs_i = f(1+m) − image_principal` (shared first order, 0297), and
`image_distance = split["far"] + Δs_i`. The downstream writers already speak far-leg world
terms (the 0482 collision resolver, the 0478 frozen writer, the 0490 traced-focus
finisher). The previously-working regime (old value positive) and every unfrozen scene are
byte-identical.

Verified: 55×55 now solves end-to-end on the flag scene — |m|=0.4189, FOV diag 77.78
(= 55×55), image change shared 50:50 with floors honored (far floor 28.98), LED glue held,
camera carried, traced-focus residual +39.57 → +0.0000095 mm.

## Guard

`validate_open3d_0519_frozen_fov_solve_range.py` (penta phase 418).

## Related

The same flag session produced the GENERAL principle (flag 140823 + follow-ups): dragging
any component should behave like **"Solve for FOV"** with the drag as that section's
thickness constraint — refocus at the sensor, FOV readout follows. That is the 0520 arc
(drag-commit → traced-focus snap + QE readout), on top of this repaired solve.
