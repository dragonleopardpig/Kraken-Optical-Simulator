# 0030 — Field Samples = 1 should launch a centred, uniformly spaced fan, with clipped rays visible in 3D

**Status:** Fixed (2026-06-08).
**Component:** preview ray sampling
(`KrakenOS/UI/services/trace_preview_sampling.py`) + Open 3D ray terminal
styling (`KrakenOS/UI/services/three_d_scene_tools.py`).
**Reported via:** user comparison of `attachment/2D.png` (the 2D layout) against
the Open 3D viewer, machine-vision layout. Three requests, in the user's words:
1. *"Field Samples = 1 should launch rays from the Center of the object"* (the
   user first wrote "Ray Count" then corrected to **Field Samples**).
2. *"Please add show clipped rays in 3D as well."*
3. *"the rays are not launched in uniform gap between the rays"* — a single
   object point should emit a **uniformly spaced fan** (Zemax-like), not a
   golden-spiral disk whose meridional projection looks unevenly spaced.

## Diagnosis

The 2D layout and the Open 3D viewer share one `SceneBundle`
(`_last_scene_bundle`), so both are driven by the same field/pupil samplers.

1. **Off-centre launch.** With Field Samples = 1, the display field samplers
   `_sample_field_grid_pairs` and `_field_cross_pairs_for_world_sections`
   returned the lone `_sample_field_values` entry, which for count == 1 is the
   field **edge/max** (the convention analysis code relies on). So the single
   bundle launched from the field corner, not the on-axis object centre the 2D
   reference shows.
2. **Uneven fan.** `_sample_ray_count_pupil_points` used a golden-angle
   Fibonacci spiral. That area-fills a disk nicely for a 3D envelope, but its
   projection onto the display meridian has visibly non-uniform gaps — the
   opposite of the even fan in the 2D layout.
3. **Clipped rays too faint in 3D.** 0028 set `"stopped"` (aperture-vignetted)
   rays to a faint grey stub (opacity 0.24) so they read as expected vignetting
   rather than a dark-red error. That was *too* faint to see against the busy 3D
   scene; the 2D layout shows these clipped stubs plainly, so 3D must match. The
   rays were already present in the 3D records (2D/3D parity holds) — only the
   opacity was the problem; this was never a missing-ray bug.

## Fix

`trace_preview_sampling.py`:
- `_sample_field_grid_pairs` / `_field_cross_pairs_for_world_sections`: when
  `field_count <= 1`, return `[(0.0, 0.0)]` (the on-axis object centre). This is
  **display-only**; `_sample_field_values` (used pervasively by analysis) is
  unchanged, so analysis keeps its edge-sample convention.
- New `_launch_pupil_prefers_meridional_fan()`: True for a plain sequential
  scene, False when the resolved trace mode is non-sequential or folded.
- `_sample_ray_count_pupil_points`: for a sequential scene, emit a uniform
  meridional fan — `np.linspace(-radius, radius, count)` on the display-slice
  axis, zero sagittal offset — so 2D shows an even fan and 3D shows a clean
  planar fan. Non-sequential / folded scenes keep the golden-spiral disk so a
  branched 3D envelope (e.g. the penta cascade, beam splitters) is preserved.

`three_d_scene_tools.py`:
- `_ray_terminal_3d_style(..., "stopped")`: opacity `0.24 → 0.55`, line width
  `0.6 → 0.9`. Still grey (not the old dark-red) and still less prominent than a
  detector hit (0.88) — just visible enough to read, matching 2D. This refines
  0028's de-emphasis rather than reverting it.

## Tests

`KrakenOS/UI/validate_ray_launch_center_uniform_fan.py` (display-free): builds a
machine-vision editor at Field Samples = 1, Ray Count = 15 and asserts —
field grid/cross pairs are `[(0,0)]`; the sequential pupil is shape `(count, 2)`
with zero sagittal offset, uniform meridional gaps, spanning `[-radius, radius]`;
a monkeypatched non-sequential trace keeps the disk (not collapsed to a line);
`"stopped"` 3D opacity ≥ 0.5 and ≤ the detector-hit opacity; the 3D records
count equals the bundle path count (no clipped rays dropped) and `"stopped"`
survives into the records; and the single-field launch origins are centred at
`(0, 0)`. Folded into the comprehensive harness as **Phase 36**.
