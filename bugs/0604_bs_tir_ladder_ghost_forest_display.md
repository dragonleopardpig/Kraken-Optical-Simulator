# 0604 — BS TIR-ladder ghost forest: power-weighted display (defensive invariant)

Found while investigating flag `flag_20260810_164247_396` ("still have some stray rays
at detector") on `machine_vision_Apo75.py`. **NOT the flag's root cause** — that is
bugs/0605 (missed rays clipped in the 0601 pad ring). The LIVE display bundle traces
558 paths with ZERO re-split lineages, so the forest below never reaches the drawn
scene today; this change is the invariant that keeps it harmless if a drawn bundle
ever does carry re-splits (the analysis bundle already does).

## The forest (measured on the sampling_mode=None analysis bundle)

Classification of every drawn-style ray tail ending on the sensor plane (265 of 573):

- **257 land at the EXACT sensor centre** — all 2^8 = 256 reflect/transmit
  combinations of 8-deep `S6:S6` chains (plus the parent). Zero land outside the
  active rectangle (the 0601 clip works).
- 9 land spread to radius 15–18 mm: the single-bounce splitter arms, one per field.

A chain dump shows the mechanism: the ray refracts into the S6 beam-splitter solid
(row 6, Ø77 BK7) and then **ping-pongs down the plate in a real TIR ladder** — 60+
bounces ~2 mm apart, walking across the aperture (event stream: `refraction`, then
alternating `split_transmit`/`reflect_tir`, then pure `reflect_tir` after the
8-split engine cap). 45° internal incidence in BK7 is beyond the 41.8° critical
angle, so the TIR is physically correct, and every pass of the splitter-flagged
plane legitimately splits again. Each 8-deep leaf carries ~0.3% power
(`branch_power` 0.0031 measured).

So the pencils are REAL stray light — but drawn at the same full brightness as the
100% image-forming paths: a ~250× visual exaggeration. Real hardware kills this
ladder with absorbing edges/baffles; the sim shows it honestly, just unweighted.

## Fix — display weight follows the physics

`_ray_branch_power_display_weight(branch_path, branch_power)` (three_d_scene_tools):
ray line opacity is multiplied by a power-derived weight in both scene draw loops.

- **Scope guard**: only RE-SPLIT branches (2+ split events in the lineage) are ever
  faded. The root path and the two first-generation splitter arms keep full strength
  regardless of absolute power — a deliberately dim source (source_weight semantics)
  is never dimmed further.
- Below 5% of the source ray: weight = sqrt(power/5%), floored at 0.15 — deep ghosts
  stay faintly traceable (the bugs/0530 doctrine: true light is never hidden).
- Quantized to buckets {1.0, 0.55, 0.3, 0.15} so the bugs/0223 merged-ray-actor
  grouping (keyed by exact opacity) stays a few actors.

The physics is untouched: trace, QE readouts, detector census and the 0601 clip see
the same branches as before.

Guard: phase 457 (`validate_open3d_0604_ghost_power_weighted_display`) — weight
function contract (root/first-arm immunity, monotone fade, buckets) + both draw
loops apply it.

## Process note — measure the LIVE bundle

Three probes were spent believing the analysis bundle
(`_build_preview_system_rays_bundle(sampling_mode=None)`, 573 paths WITH the forest)
represented the display. It does not: the live refresh's
`build_inspector_refresh` bundle has 558 paths, no re-splits, and its termination
census matches the user's recorded flag state exactly. A display bug must be censused
on the bundle the display actually draws — A/B pixel-diffing the render caught the
mismatch (zero changed pixels with the weight forced off was the tell).
