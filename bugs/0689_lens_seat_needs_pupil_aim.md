# 0689 — flag_20260901_211438 + live: "side-B rays none reach the sensor"

## What the app really shows (state census)
Both arms fully trace (2,166 paths); face-B DOES reach — but only 20 rays (2%):
934 of its 1,083 die at the aperture stop because the chain-posed lens rides
arm A's beam (z=-15.8) and arm B crosses the stop ~19 mm off-axis. "None reach"
is what 2% looks like among 959 bright arm-A rays.

## The vendor geometry (derived, load-bearing for the next arc)
The two centre-flank windows tile the column and MEET at z=-25 (the part
symmetry plane): the vendor lens axis IS the split line, and EACH arm rides
~9.4 mm off-axis as a FIELD offset. Each arm's chief must arrive TILTED,
converging on the pupil at the lens axis.

## Two seat attempts, both reverted (scene restored byte-identical + leak bound)
1. 0433-style absolute bake (breadcrumb + desp = world - station): un-overridden
   STANDARD rows do not pose cleanly inside a folded non-seq scene -- rays looped
   forever at the filter (identical-point polylines), and a glass element's exit
   is the NEXT station, so partial baking twists the sandwich.
2. Frame-desp decenter (`_downstream_pose_from_frame` poses followers at
   frame_origin + R @ desp -- the standard folded decenter): geometry moved
   perfectly (lens + filter + sensor all on z=-25)... and reach went to ZERO for
   BOTH arms: the folded world-order launcher aims every field cone at a pupil
   ON the walk axis. With the lens 9.5 mm off that axis, every cone misses the
   19-mm stop. The vendor seat therefore REQUIRES a launcher feature:
   an authored transverse PUPIL OFFSET (walk-frame) that tilts each field
   cone's aim onto the true pupil -- for BOTH the chain and the mirrored face-B
   launch (which would then aim at the same pupil from the other side and
   deliver ~symmetric reach). That is the 0690 arc, fresh-context work.

## Also in this flag
- "rays leaks" (red + cyan fans): the vignetted portion of TRUE launches (both
  arms, symmetric behavior) flying through the DECORATION housing, which is
  display-only and does not stop rays. Honest but noisy; the clean future fix
  is 0379 clear-aperture ray stops on the housing decoration. A tightened
  mirror_bound_y (8 -> 5.2) is kept but measured ineffective for the fan (the
  fan rays are inside the legitimate y=0-row bundles).
- "LED arrow placement still wrong": verified the glyph descriptor draws at
  origin (0,0,-50) dir (0,0,-1) -- ON face B aiming into the lower BS. It is
  the face-B imaging-launch emitter marker, not an LED; the LED barrels (the
  two side assemblies) are not modelled as sources yet.
- "red ray still defocus": +26.8-field core rms 530 um vs 76 um elsewhere,
  0 outliers -- a real one-sided aberration/vignetting signature that the 0690
  pupil-aim + seat will re-deal; re-measure then.
- "no colors for side-B rays": all face-B bundles draw in the single source
  colour; per-field colours for additive imaging sources queued with 0690.
