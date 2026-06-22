# 0111 — Deselecting the camera STEP freezes ~18 s (bugs/0109 re-bake regression)

**Report (live, 2026-06-22):** "deselect the camera STEP takes long time."

The always-on timing log showed the culprit immediately:

```
step_overlay_face_metadata_done   18258 ms   (camera)
step_overlay_face_metadata_done   18029 ms   (camera)
```

Baking the **camera** STEP face metadata takes **~18 s** (the full
planar-clustering + affine-fit + snap-STL pipeline over the 228k-cell camera
body), and it was re-running on a deselect/refresh.

## Root cause — my own bugs/0109 fix

bugs/0109 ("ghost/offset highlight") folded the image-plane **alignment target**
into the face-metadata cache key for the display-only camera/led labels, so the
gold hover outline would track the body after an image-plane move:

```python
align_target = self._step_overlay_alignment_target_z(label)
if align_target is not None:
    cache_key = cache_key + (("align_z", align_target),)
```

The 0109 commit message claimed the recompute was "subsecond" — but the comment
*directly above* the cache block already said the same bake "took 35 s on the
first call", and the live log measured 18 s. So the assumption was wrong: folding
the alignment target made the **18–35 s** bake re-run whenever the image plane
moved (a solve / image-at-focus shift / thickness edit) **or on a deselect /
refresh that re-evaluated the alignment** — an 18 s UI freeze each time.

Before 0109 the display-only metadata was **pose-blind** — baked at most once per
session and cached forever — so this freeze did not exist.

## Fix — revert to pose-blind caching

The display-only camera/led labels keep the pose-blind cache key
`(label, stat_key)`, so the expensive bake runs at most once. The alignment
target accessor (`_step_overlay_alignment_target_z`) is kept for the proper
follow-up.

```python
cache_key = (label, self._step_overlay_stat_key(source_path_obj))
if label not in self._DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC:
    cache_key = cache_key + (self._step_overlay_pose_cache_signature(label),)
# bugs/0111: display-only labels stay POSE-BLIND (no align_z re-key) -> no re-bake.
```

## Trade-off / follow-up

This reintroduces the **cosmetic** 0109 symptom: after an image-plane move the
gold *hover outline* can sit offset from the camera body. That is far preferable
to an 18 s freeze on every deselect. The correct fix is to apply the **axial
alignment delta** to the cached metadata on read (the camera/led alignment is a
pure z-translation, so shifting the cached centroids/outline by Δz is O(faces) and
exact) — **without** re-baking. Tracked as a follow-up; not done here to keep the
live incident fix minimal and safe.

## Tests

- `python -m KrakenOS.UI.validate_open3d_camera_overlay_hover_alignment` — rewritten
  to assert the **freeze-free** contract: an image-plane move does NOT recompute the
  camera metadata (pose-blind cache hit), and the cache key does not fold the
  alignment target. Penta **phase 95** (re-titled; baseline unchanged at 100 phases).

In-app eyeball owed: confirm deselecting the camera STEP is now instant.
