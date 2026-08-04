# 0530 — "Show clipped rays" drew escaped strays teleporting into the camera

## Flag

`flag_20260804_073933`: "enabled clipped overlay, rays not make sense." Dragged AZ85
scene; the overlay showed a wedge of chords running from the lens/BS region diagonally
through free space into the camera body, plus off-palette colors, plus the dense transmit
fan out of the housing bottom.

The user also asked "how can the reflected ray go 2 paths?" — the SPLIT itself is real
physics: the cube BS is non-sequential, every launch forks into a reflected branch
(toward the lens) and a transmitted branch (straight through, dumped out of the housing);
the overlay reveals the normally-hidden branches. The NONSENSE part was only the chords
into the camera.

## Root cause

`_replace_terminal_with_detector_miss` projects an escaped ray's last direction onto the
detector plane to classify near-misses (`missed_image`, with radial/local metadata). The
0018-era guard bounds the plane-crossing ANGLE (cos 80°) but not the TRAVEL. On the
folded scene the sensor plane sits up the fold leg inside the camera: every escaped
lens/BS stray had a legal forward crossing 155–220 mm away (the real prism→sensor arm is
44 mm), so ALL 225 "missed_image" rays on the dragged scene were teleports — their drawn
terminal segment was a chord the ray never flew. Measured: min travel 155 mm > 3× the
whole arm; zero genuine near-misses in the population.

## Fix

`_detector_plane_miss_intersection` gains an arm-gated travel bound: when the detector's
final-arm gap is known (`rows[detector-1].thickness`), a miss is only claimed within
`max(3 × arm, 6 × sensor-half)`. Beyond that the crossing is a coincidence of plane
geometry and the ray keeps its honest `no_next_intersection` terminal (drawn along its
real direction). Rows without thickness data (the 0018 mechanism harness, stubs) keep the
cos-guard-only behaviour, so the 0018 checks — grazing rejected, axial projects, runaway
documented — still hold.

AZ85 after: missed_image 225 → 0, no_next_intersection 279 → 504, reached 225 and
vignetted 108 unchanged; the render from the flag's own viewpoint shows the wedge gone
(remaining diagonals are launch-cone strays that miss the lens and honestly fly off-scene,
verified: zero non-target tails end near the sensor).

## Guard

`validate_open3d_0530_clipped_ray_teleport.py` (penta phase 425): no missed_image on the
dragged scene, no clipped tail ends beside the sensor, a genuine 30 mm-up-the-arm
near-miss STILL projects (POS), a ~200 mm free-space stray does not (NEG).
`validate_open3d_reflected_branch_detector_bounds` (0018) stays green.
