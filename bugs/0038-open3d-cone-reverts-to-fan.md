# 0038 — Open 3D launch cone reverts to the flat 2D fan

**Status:** Fixed (2026-06-08).
**Component:** Open 3D trace/refresh sampling-mode feed
(`KrakenOS/UI/services/open3d_trace_refresh.py`).
**Reported via:** `attachment/3D.png` on the *Zemax Double Gauss 28 Degree Field*
layout (sequential, Infinity object, ±14° angle field, 3 field samples). In the
user's words: *"the 3D goes back to fan instead of Cone rays."* The 3D view showed
per-field flat meridional fans instead of the revolved launch cone introduced in
bug 0034.

## Diagnosis

Bug 0034 makes a sequential, non-folded scene draw a flat `world_envelope` fan in
2D and a revolved `world_cone` in Open 3D. The cached 2D scene bundle can only
feed Open 3D directly when its sampling mode equals the 3D mode; otherwise Open 3D
must rebuild the cone. That decision is `_active_trace_can_feed_open3d()`, which
compares `_committed_scene_sampling_mode()` to the 3D mode.

`_committed_scene_sampling_mode()` preferred the committed tag
`_last_scene_trace_sampling_mode`, and **fell back to the transient
`_active_preview_sampling_mode`** when the tag was unset. But the transient is set
on *every* trace (`trace_preview.py`), so an Open 3D cone rebuild leaves it
pointing at `world_cone` — even though that rebuild runs with `update_state=False`
and never replaces the cached 2D bundle (still the `world_envelope` fan). When the
committed tag was unset (e.g. before the first 2D refresh tagged it on a fresh
load) the fallback reported the cached *fan* as `world_cone`, so
`_active_trace_can_feed_open3d()` returned True and Open 3D **reused the flat 2D
fan** instead of rebuilding the cone.

A direct build confirmed the cone trace itself was healthy (1089 ray paths,
launch mode `world_cone`) — the bug was purely the feed/reuse decision wrongly
green-lighting the 189-ray envelope fan.

## Fix

`_committed_scene_sampling_mode()` now reads the **cached scene bundle's own
launch mode** first (`scene_bundle_launch_sampling_mode(_last_scene_bundle)`) as
the ground truth, only falling back to the committed tag and then the transient
for editors / test fakes that never tag a committed bundle. Because an Open 3D
cone rebuild never replaces `_last_scene_bundle`, the committed mode now correctly
reports `world_envelope`, `_active_trace_can_feed_open3d()` returns False, and
Open 3D rebuilds the `world_cone`. Sequential scenes get their cone back; nonseq /
folded scenes (where 2D and 3D are both `world_envelope`) still reuse correctly.

## Tests

`KrakenOS/UI/validate_open3d_cone_not_reused_as_fan.py` (display-free, Agg):
on the Double Gauss 28° layout it commits the 2D envelope trace, then builds a
cone trace (leaving the transient at `world_cone`) with the committed tag cleared
— recreating the reuse trigger — and asserts the committed mode still reads
`world_envelope` from the cached bundle, the cached fan is not cone-ready, and
`current_or_rebuild_scene` rebuilds a `world_cone` scene with the cone's larger
ray-path count (1089) rather than reusing the fan (189). SKIPs cleanly if the
layout/cone mode is unavailable. Folded into the comprehensive harness as a new
phase.

## Verification note

Headless simulation of the live feed decision: before the fix the untagged state
reused the 189-ray fan; after the fix it rebuilds the 1089-ray cone, while the
normal (tagged) state was unaffected. The existing `validate_open3d_launch_cone_geometry`
(Phase 40) and the cone-contract validators (`validate_scene_sources`,
`validate_infinity_field_launch`) still pass.
