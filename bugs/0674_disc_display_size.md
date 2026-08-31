# 0674 — flag_20260901_072953: "the lens surrogate is oversized" (folded scene)

Measured (bugs/0674 disc-actor probe, archived in the guard): the folded scene's
lens datums (48.56) drew as 97.1 mm discs, the 50.8 filter as 101.5, and the
hidden-by-intent probe plates as an 80 mm cylinder stack. TWO display defects:

1. **EEE runtime caps render at 2x the row diameter.** Override-posed (folded)
   rows draw their surface cap from the core's `system.EEE` runtime mesh, which
   comes out at TWICE `row.diameter`. Straight scenes use the analytic path and
   never showed it. Fix (three_d_scene_tools): the runtime disc mesh (non
   file-backed rows only) is rescaled about its own centre to `row.diameter`.
2. **The row `Drawing` flag was 2D-only.** The om05a launch-probe plates
   (diameter 80 kept ONLY because the launch-measure probes need wide first
   apertures -- dia 46 collapsed the aim to 2% reach, bugs/0673) still rendered in
   3D. Fix: the 3D surface iterator now honors `drawing=0` like the 2D pane.
   The scene also hides the dia-80 AIR spacer rows the same way.

Verified: guard `validate_open3d_0674_disc_display_size` (penta phase 506,
standalone: real inspector, every round disc-like actor <= 60 mm; ribbons and 3D
bodies excluded), guard 0672 still green, render eyeballed (honest plate slabs,
mirrors, lens, camera; only the corner-field frontier fans remain visible).
