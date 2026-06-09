# 0040 — Open 3D launch cone reads as an X-fan + Y-fan cross, not a cone

**Status:** Fixed (2026-06-09).
**Component:** Open 3D launch-cone sampling + ray-draw budget
(`KrakenOS/UI/services/trace_preview_sampling.py`,
`KrakenOS/UI/services/three_d_scene_tools.py`).
**Reported via:** the user on the *Zemax Double Gauss 28 Degree Field* layout
(sequential, Infinity object, ±14° angle, 3 field samples, 3 wavelengths, Ray
Count 21). In the user's words: *"the input rays for each colors are consists of
X-Fan + Y-Fan. Not a cone."* (`attachment/3D.png`, and the
`flag_20260608_211726_877` recording, "Rays are still fan, not cone.")

This is the follow-on to bug 0034 (which introduced the revolved `world_cone`)
and 0038 (which fixed Open 3D wrongly *reusing* the 2D fan). The sampling mode
was correct (`world_cone`) and the cone was being rebuilt — but it still *looked*
like fans.

## Diagnosis

Two compounding causes, both confirmed by headless renders of the actual drawn
ray polylines (real `KrakenLayoutEditor` + `_iter_3d_scene_ray_records`):

1. **The cone was only a 12-spoke revolved fan.** `_sample_ray_count_cone_points`
   lays the meridional fan on `n_rings × n_az` spokes, and `_cone_azimuth_count()`
   was hard-capped at 12 (`clamp(ray_count, 3, 12)`). Looking straight down the
   optical axis, even the *undecimated* 1089-ray bundle is a clean **12-spoke
   asterisk**, never a filled disk. Viewed edge-on (the user's camera) those 12
   flat fans read as a few crossing sheets — "X-fan + Y-fan."

2. **The 3D draw then decimated the cone into uneven spokes.** Each ray is its
   own pickable VTK actor, so `_iter_3d_scene_ray_records` thins large bundles to
   a ~300 budget (`step = max(total // 300, 1)`): 1089 → **363** (exactly the
   `ray_actor_count` in the flags). The flat global stride phase-rotates through
   azimuths and turns the clean 12-spoke star into an *uneven* asterisk — making
   the "fan" look worse.

An oblique render comparison settled the fix: az=12 decimated = sparse flat fans
(the bug); **az=36 undecimated = a solid converging cone**; az=36 decimated =
back to fans. So a true cone needs **both** denser azimuths *and* not decimating
the cone away — within the ~300 pickable-actor budget.

## Fix

Spend the draw budget on azimuthal density instead of rings, and let the cone
draw in full.

`trace_preview_sampling.py`:
- `_cone_azimuth_count()` now returns `clamp(ray_count, _CONE_AZIMUTH_MIN=8,
  _CONE_AZIMUTH_MAX=18)` — enough spokes to read as a continuous cone surface.
- `_sample_ray_count_cone_points` caps the rings at `_CONE_RING_CAP = 3`
  (`n_rings = min(3, max(1, count // 2))`), uniform-gap out to the pupil rim, so
  the denser spoke set still fits the draw budget. The cone is no longer tied to
  every 2D-fan radius; it stays a uniform-gap revolved fan.

For the reported case this makes the cone `1 + 3×18 = 55` samples per
field/wavelength → `55 × 3 × 3 = 495` rays (was 1089).

`three_d_scene_tools.py`:
- The decimation budget is now mode-aware: `world_cone` bundles use
  `_RAY_DRAW_BUDGET_CONE = 600` instead of `_RAY_DRAW_BUDGET_DEFAULT = 300`. The
  modestly-sized cone (495) is under 600, so it draws **in full** (step = 1)
  rather than being thinned back into the uneven spokes. Other scenes keep the
  300 budget unchanged.

Result: the same Double Gauss 28° layout now renders a solid converging cone of
light (oblique view) with full azimuthal fill (down-axis view), verified
headless.

## Tests

`KrakenOS/UI/validate_open3d_cone_density_reads_as_cone.py` (display-free, Agg):
on the Double Gauss 28° layout, asserts the 3D mode is `world_cone`; the cone
pupil has dense azimuths (≥ 16 distinct angles, not the old 12 cap) on capped
uniform rings reaching the rim and spanning both transverse axes (off-meridian
spokes); and — the key regression guard — the drawn (decimated) record count
equals the bundle path count, i.e. the cone is drawn in full and not thinned into
uneven spokes. SKIPs cleanly if the layout/cone mode is unavailable. Folded into
the comprehensive harness as **Phase 46**.

The existing cone-geometry guard (`validate_open3d_launch_cone_geometry`,
Phase 40) was updated: its old "cone ring radii == 2D fan positive radii"
assertion (the bug-0034 radial-gap coupling) now checks the new invariant —
`_CONE_RING_CAP` uniform rings reaching the pupil radius. The bug-0038 reuse
guard (Phase 44) still passes (cone 495 paths > fan 189).

## Verification note

Headless renders of the real drawn polylines (`/tmp/cone_prod.png`): oblique
(user-like) view shows a solid converging cone; down-axis view shows 18
azimuthal spokes dense enough to fill — versus the prior sparse crossing fans.
`validate_open3d_launch_cone_geometry`, `validate_open3d_cone_not_reused_as_fan`,
and `validate_infinity_field_launch` all pass.
