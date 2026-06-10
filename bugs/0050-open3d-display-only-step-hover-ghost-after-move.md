# 0050 — Open 3D: hover highlight stranded at a display-only STEP's old location after a gizmo move

## Symptom (user's words)

> the residul highlight at old location bug surface again.

Flag `flag_20260610_192731_451` (2026-06-10T19:27:31), `machine_vision_150mm`
layout. The LED STEP was slid along an axis with its gizmo translate arrow, but
a gold face-hover edge outline stayed behind at the LED's **previous**
position (the yellow wireframe box to the left of the moved body in the
screenshot). This is bug **0010** ("ghost" stranded hover edges) resurfacing —
for the imported solids the 0010 fix did **not** cover.

## State evidence

`scene_state` in the flag bundle:

* `selected_step_label = "led"`, `rotation_handle_count = 6` (single gizmo, fine).
* `step_actor_bounds["led"]` X spans `[-33.4, 76.8]` — the LED was translated
  **+X ≈ 21.7 mm** from its earlier pose (`[-55.1, 55.1]` one flag before).
* `hover_outline_bounds` is a degenerate plane at **X = -55.117** — the LED's
  *former* left face — and `hover_step_cell_key = (None, 'passive', 'F010')`.
* `stray_props_above_body` non-empty — the standing 0010 tripwire is firing.

So a passive hover over the now-empty old region re-picked face F010 there and
redrew its outline: stale face geometry at the pre-move pose.

## Root cause

The hover outline / face pick read `_step_overlay_face_metadata(label)`
(`scene_placement_commands.py`), which memoises per-face records carrying
world-space `centroid_world` / outline geometry baked from the *currently
transformed* mesh. bug 0010 made that cache **pose-aware** — but only for
**analytic** labels. Display-only labels keep a deliberately **pose-blind**,
stat-only cache key:

```python
cache_key = (label, self._step_overlay_stat_key(source_path_obj))
if label not in self._DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC:   # {camera, led, lens}
    cache_key = cache_key + (self._step_overlay_pose_cache_signature(label),)
```

The pose signature is skipped for `camera`/`led`/`lens` to avoid recomputing
their planar-clustering metadata (a cold 51 MB camera body took ~35 s on the
first call). The cost of that shortcut: after a gizmo move the LED/camera/lens
keep handing back the body's **former** world coords, so the hover outline is
drawn at the old, now-empty location — exactly the 0010 ghost, for the labels
0010 left pose-blind. The original 0010 repro was the *aspheric lens*
(analytic, fixed); this repro is the *LED* (display-only, still broken).

## Fix

Invalidate the label's cached face metadata whenever its pose changes, inside
the three pose **setters** every move path routes through
(`_set_step_placement_offset_xyz`, `_set_step_axis_offset_xy`,
`_set_step_rotation_deg_tuple` — `translate_step_overlay` and
`rotate_step_world_axis` both go through these). New helper
`_invalidate_step_overlay_face_metadata_cache(label)` drops the label's entries
from `_step_overlay_face_metadata_cache`.

This is freeze-free: `_step_overlay_face_metadata` is called only on lazy paths
(hover / pick / promote / axis-snap), **never** during the scene refresh, and
the move's own refresh already rebuilt the transformed mesh — so the recompute
the next hover pays is just the planar-clustering pass, not a CAD reload.

Belt-and-suspenders on the inspector side: `_translate_step_overlay_actors`
(the live drag mover, which only `AddPosition`s the body + gizmo actors) now
drops the displayed hover-outline actor on the move, so the gold edge does not
linger during the drag either.

Files:

- `KrakenOS/UI/services/scene_placement_commands.py` — new
  `_invalidate_step_overlay_face_metadata_cache`; called from the three pose
  setters.
- `KrakenOS/UI/open3d_inspector.py` — `_translate_step_overlay_actors` clears
  the stranded hover outline when the body moves.

## Tests

- `KrakenOS/UI/validate_open3d_step_display_only_metadata_tracks_pose.py` —
  display-free, no X server. Imports the prism under the display-only `lens`
  label, reads the metadata (caching it), moves it +20 mm in z through the
  public `translate_step_overlay`, reads again with **no** manual cache clear,
  and asserts every face centroid is present at the moved pose (matched as an
  ID-independent cloud, since the planar clusterer may swap two symmetric
  faces' IDs). Negative control: with the invalidation stubbed to a no-op the
  guard fails 7/7 (the pose-blind cache returns the unmoved coords). Run:
  `.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_display_only_metadata_tracks_pose`.
- Phase 55 in `validate_open3d_penta_telescope_comprehensive.py` — end-to-end
  on the booted inspector: import a display-only body, move it, assert the
  metadata tracks and no hover-outline actor is stranded.

The existing analytic-label guards
(`validate_open3d_step_overlay_metadata_tracks_pose`, the 0010 snapshot) stay
green — the fix only *adds* invalidation for the display-only labels they don't
cover.
