# 0709 — "changed device size to 20x20x1, blank the FOV. The ray go hay wire."

(flag_20260903_144408)

## Root cause

The 0708 slide treated every paired far-side solid as "the far tower". But
the CENTRE V is one routing assembly — two halves 0.1 mm apart astride the
gap midplane, belonging to NEITHER tower. Sliding its far half with the
tower (full delta) rammed it through the near half: overlapping glass, and
the trace scattered everywhere ("hay wire" — fat bundles reflecting straight
up out of the assembly).

## Fix

`_slide_far_tower_rows` now stamps TWO memberships on first classification:

- `far_tower` (the outer pairs: first mirror + BS + far half + LED) rides the
  FAR FACE (full delta);
- `centre_v` (the INNERMOST pair, both halves) rides the MIRROR PLANE (half
  delta), so the V stays intact and astride the new midplane at every size.

A large re-seat (>5 mm) appends a status CAUTION to verify clearances in 3D
— the vendor assembly was built for its original device depth, and extreme
shrinks still bring the BS cubes near the V.

## What remains physics, not bugs

- The A-arm's BS→centre-V leg shortens by delta/2, so the conjugates change
  — refocus/solve is the user's next step after any resize.
- The blank-FOV solve (face+5% = 21×21 on a 20 mm device) needs
  |m| = 23/21 ≈ 1.10 to FILL the sensor; the PYRITE 5.6/80 delivers 0.392.
  The solve refuses honestly — a small device needs a magnifying lens family
  (the System Selection Calculator + lens swap are the follow-on tools).

## End-to-end (om05a, 20x20x1, blank FOV)

Launches from both faces (z=0: 1416 rays, z=-20: 1083); the V halves land at
-4.03 / -15.97, astride the new midplane -10 with their 0.1 mm slot intact;
**reach 0 -> 491** -- light is coherent again instead of scattering. The
remaining shortfall is the documented conjugate shift + lens choice.

## Guard

`validate_open3d_0704_device_resize_follow` (phase 513): A3a far tower full
delta, NEW A3c centre-V halves ride the plane together, A4 second resize
consistent via both stamps — 9 checks green.
