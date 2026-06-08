# 0034 — Open 3D should launch the rays as a cone, not a flat fan (keep the uniform 2D gap)

**Status:** Fixed (2026-06-08).
**Component:** preview ray sampling
(`KrakenOS/UI/services/trace_preview_sampling.py`,
`KrakenOS/UI/services/trace_preview.py`), 2D/3D sampling-mode split
(`KrakenOS/UI/services/three_d_scene_tools.py`), and the Open 3D cache-feed gate
(`KrakenOS/UI/services/open3d_trace_refresh.py`,
`KrakenOS/UI/services/plot_refresh.py`).
**Reported via:** the in-app recorder, machine-vision layout, follow-up to 0030.
In the user's words:
1. *"The ray fan gap is uniform now, but they are launch as a Fan in 3D, can't
   you make it launch as a Cone (but maintain the uniform gap in 2D)?"*
2. *"I open 150mm measured, the 3D still launch as Fan."*

## Diagnosis

0030 made the sequential pupil a uniformly spaced **meridional fan**
(`world_envelope`) so the 2D layout shows even gaps. That fan is flat (planar) by
construction — every sample lies on the display-slice meridian with a zero
sagittal offset. The Open 3D viewer then showed the same flat fan, because:

1. **One canonical sampling mode fed both views.** `_preview_2d_sampling_mode`
   and `_preview_3d_sampling_mode` both returned `world_envelope` for a
   sequential scene — a deliberate "2D and 3D use the same canonical sampling
   mode" parity contract. So 3D inherited the 2D flat fan verbatim.
2. **The 2D trace cache was fed straight into Open 3D.** The 2D plot commits the
   shared `last_system`/`last_rays`/`_last_scene_bundle` cache and pushes it into
   the open inspector (`_refresh_3d_inspector_if_open` →
   `current_or_rebuild_scene`). The feed gate `_active_trace_can_feed_open3d()`
   returned True for **any** open3d-scene sampling mode, so the flat 2D fan
   bundle was reused unchanged for 3D — there was no opportunity to revolve it.

The second report ("150mm measured still a Fan") is the same root cause seen on
load: the layout's load path seeds the `world_envelope` 2D trace, which the
open-inspector reuse gate then accepts as-is.

## Fix

A new `world_cone` sampling mode is the meridional fan **revolved about the
optical axis** into concentric rings of azimuthal spokes. The 2D view keeps its
flat fan; only Open 3D uses the cone.

`trace_preview_sampling.py`:
- `_sample_ray_count_cone_points`: center sample + `n_rings = count // 2` rings
  at radii `radius * j/n_rings`, each with `n_az = clamp(count, 3, 12)` azimuthal
  spokes. For an odd Ray Count the ring radii land exactly on the 2D fan's
  positive radii, so **every meridian still reads as the same uniform fan** — the
  radial gap is preserved, which is what the user asked for.
- `_build_world_cone_bundles` / `_trace_world_cone_rays`: build and trace the
  cone bundles (with the same through-going / sparse-discovery / clipped-launch
  fallbacks as the world envelope).

`trace_preview.py`: dispatch `mode == "world_cone"` to `_trace_world_cone_rays`.

`three_d_scene_tools.py`: split the previously-shared sampler. `_preview_2d_…`
stays `world_envelope` (flat fan); `_preview_3d_…` returns `world_cone` for a
sequential, non-folded scene (and still `full_pupil` / `world_envelope`
otherwise). Non-sequential / folded scenes keep the flat envelope so branched
(beam-splitter / mirror) 3D paths are unchanged.

Cache-feed gate (`open3d_trace_refresh.py` + commit-site tags): the committed 2D
trace is tagged with the mode that produced it
(`_last_scene_trace_sampling_mode`, set at the two `update_state=True` commit
sites in `three_d_scene_tools.py` and `plot_refresh.py`). The new
`_committed_scene_sampling_mode()` reads that tag (falling back to the transient
`_active_preview_sampling_mode`). `_active_trace_can_feed_open3d()` now requires
the committed mode to **equal** the Open 3D mode. So a `world_envelope` 2D fan no
longer feeds a `world_cone` 3D view: Open 3D rebuilds the cone (with
`update_state=False`, so it never clobbers the 2D cache). Non-sequential /
full-pupil scenes keep matching modes, so their bundle reuse is unchanged.

## Tests

`KrakenOS/UI/validate_open3d_launch_cone_geometry.py` (display-free): builds a
machine-vision editor at Field Samples = 1, Ray Count = 11 and asserts —
`_preview_2d_sampling_mode` is `world_envelope` and `_preview_3d_sampling_mode`
is `world_cone`; the 2D fan stays planar (zero sagittal offset); the cone has
azimuthal spread in both transverse axes with an on-axis centre and at least one
off-meridian spoke; the cone's ring radii equal the 2D fan's positive radii with
uniform ring gaps (the maintained-gap contract); the cone bundle's launch
directions span both transverse axes while the flat-fan bundle spans exactly one;
a traced cone produces one 3D ray record per bundle path, launched from the
object centre, and spreads in both transverse axes downstream; and a
monkeypatched non-sequential scene keeps `world_envelope` in 3D (the cone is
sequential-only). Folded into the comprehensive harness as **Phase 40**.

The pre-existing 2D/3D parity validators were updated to the cone contract:
`validate_infinity_field_launch` (2D `world_envelope` / 3D `world_cone`),
`validate_scene_sources` (the sequential 3D preview now revolves into an
azimuthal cone — this also *fixes* that validator's previously-failing
azimuthal-spread check), and
`validate_open3d_face_assignment_sampling_stability` (the machine-vision smoke
test now expects Open 3D to **rebuild** the launch cone rather than reuse the 2D
fan bundle).

## Verification note

The cone is a **visual** feature that cannot be pixel-verified headless (no GPU;
Xvfb/llvmpipe). The geometry is proven by the display-free guard above; the
on-screen cone appearance was confirmed on a real display.
