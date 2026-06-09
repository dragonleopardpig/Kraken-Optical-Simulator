# 0041 — 2D layout was a separate trace, not a slice of the 3D launch cone

**Status:** Fixed (2026-06-09).
**Component:** launch sampling + 2D/3D trace unification
(`KrakenOS/UI/services/trace_preview_sampling.py`,
`KrakenOS/UI/services/three_d_scene_tools.py`,
`KrakenOS/UI/services/layout_scene_projection.py`).
**Reported via:** the user on the *Zemax Double Gauss 28 Degree Field* layout
(`attachment/3D-YZ.png` vs `attachment/2D-YZ.png`): the Open 3D edge-on (YZ) view
"no longer matches" the 2D YZ fan. Then the deeper question — *"regarding North
Star, shouldn't the 2D display be just a slice of 3D? Any ray tracing should be
done in 3D from the start? ... is there a separate trace for 2D?"*

This is the architectural resolution of the cone saga (bugs 0034 → 0038 → 0040).
Each of those treated a symptom; this fixes the root cause.

## Diagnosis

**There were two separate simulations.** A sequential scene traced two bundles:
a flat `world_envelope` meridional fan for the 2D pane and a *separate*
`world_cone` for Open 3D. That is exactly the dual-simulation North Star
invariant #2 forbids:

> Optical elements and ray tracing are represented in 3D behind the scene; 2D
> plots are slice/projection views of traced 3D data, not separate simulations.

Because the two were independent, every prior fix that nudged one (the bug-0040
ring cap of 3, to fit the 3D draw budget) silently desynchronised the other: the
3D edge-on cone became sparse/irregular (3 rings) while the 2D fan stayed dense
(21 uniform heights). They could not be kept in lock-step by patching numbers —
they had to become *one* trace.

Two concrete geometric requirements for the 2D fan to be a true slice of the
cone (both verified numerically and by headless render):

1. **Full radial rings.** With `n_rings = count // 2`, the meridional spokes land
   exactly on the 2D fan's `linspace(-r, r, count)` positive heights. The
   bug-0040 cap (3) broke this. For an odd ray count the cone ring radii then
   equal the 2D fan's positive radii again (the original bug-0034 invariant,
   restored).
2. **Azimuth count divisible by 4.** The meridional slice keeps the rays at
   azimuth 90°/270° (the YZ plane). `linspace(0, 2π, n_az, endpoint=False)`
   includes 90° iff `n_az / 4` is integer. The old odd counts (e.g. az=18)
   produced a cone with **zero** rays in the YZ plane, so the slice was empty
   and the 2D pane silently fell back to the whole projected cone.

## Fix

**One cone trace is the 3D truth; the 2D layout is its X=0 meridional slice.**

`trace_preview_sampling.py` (the single cone sampler):
- `_cone_azimuth_count()` returns `4 * round(clamp(ray_count, 16, 24) / 4)` — a
  multiple of 4 so the YZ-meridian spokes exist (and dense enough to read as a
  filled cone down-axis, keeping bug 0040 fixed).
- `_sample_ray_count_cone_points()` restores full rings: `n_rings = count // 2`
  (the `_CONE_RING_CAP` of bug 0040 is removed entirely), so the cone meridian
  IS the 2D fan.

`three_d_scene_tools.py`:
- **Lazy trace.** `_preview_2d_sampling_mode()` returns `world_cone` only while an
  Open 3D inspector is live (new `_open3d_inspector_is_live()`, which reads
  `self.__dict__` directly to avoid Tk's `__getattr__` recursing on stripped
  snapshot editors); otherwise it stays `world_envelope`. When 3D is closed the
  2D pane traces only the cheap fan (whose meridional heights still equal the
  cone spine); when 3D opens, the committed 2D bundle becomes `world_cone` and
  Open 3D reuses it — ONE trace feeds both.
- **Route A draw budget.** `_RAY_DRAW_BUDGET_CONE` raised 600 → 2000 so the full
  cone (e.g. 1809 rays for the Double Gauss 28° 3×3 field grid) draws in full
  (step = 1) instead of being decimated back into the uneven spokes that read as
  fans (bug 0040). The cone only exists while the inspector is live, so the extra
  pickable VTK actors are bounded to that window.

`layout_scene_projection.py`:
- `_should_filter_projection_slice()` now applies the X=0 / Y=0 section filter to
  `world_cone` as well as `world_sections`, so the 2D pane is sliced from the
  cone.

For the reported case the cone is `1 + (21 // 2) × 20 = 201` samples per
field/wavelength → `201 × 9 = 1809` rays. Its YZ slice keeps the 3 meridional
fields (zero X-launch) × 21 uniform heights = **63 paths**, a strict subset of
the 1809-ray cone the 3D draws. The 6 off-meridian fields (with an X-field
offset) are correctly excluded from the X=0 meridian.

## Tests

`KrakenOS/UI/validate_open3d_2d_is_cone_slice.py` (NEW, display-free, Agg) —
**Phase 47**. On the Double Gauss 28° layout it asserts the North Star
invariant directly: the lazy 2D mode flips `world_envelope` ↔ `world_cone` with
inspector liveness; the cone YZ slice is a **non-empty strict subset** of the
cone bundle (same ray indices — one trace, not two); every sliced ray stays in
X=0 through the whole system and spans ±Y (a clean meridional fan); and the
slice keeps more than one field with uniform per-field heights.

Updated guards:
- `validate_open3d_launch_cone_geometry.py` (Phase 40): dropped the removed
  `_CONE_RING_CAP`; now asserts the cone ring radii equal the 2D fan's positive
  radii (bug-0034 invariant restored), the azimuth count is divisible by 4, and
  the 2D mode flips to `world_cone` under a live inspector.
- `validate_open3d_cone_density_reads_as_cone.py` (Phase 46): full rings
  (`count // 2`), azimuth divisible by 4, draw budget 2000 (cone drawn in full).

Existing guards still pass unchanged: `validate_open3d_cone_not_reused_as_fan`
(Phase 44, cone 1809 paths > fan 189), `validate_infinity_field_launch`,
`validate_ray_launch_center_uniform_fan` (Phase 36).

## Verification note

Headless render of the real drawn polylines (`/tmp/cone_unified.png`): edge-on
YZ shows a solid converging band (matching the 2D fan); down-axis XY shows the
3×3 field grid each as a filled ring/spoke disk; and the 2D pane (the cone's YZ
slice) is the clean 3-field uniform fan — literally a subset of the 3D cone's
data. One trace, two views.
