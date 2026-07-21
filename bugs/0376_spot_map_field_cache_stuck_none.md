# 0376 — 3D spot diagram blank after a fresh import (until save + restart + reload)

**Flags:** 20260721_071925 / 072755 / 074256 ("spot diagram / etc overlays not showing";
"Astigmatism and Distortion work, not sure why Spot Diagram not") + 075948 ("I saved the
layout to machine_vision_Apo75.py and restart, reload the file, it is working, it seems
weird"). User also confirmed it "works last night at M90aPro" and that it is nothing to do
with the camera STEP overlay/opacity. **Status:** SHIPPED 2026-07-21 (guard
`validate_open3d_spot_map_field_cache`, penta phase 317).

## Why it happened

The per-field spot map traces 25 hexapolar fields (2-D pupil) and returns **None when
fewer than 2 survive** (`_compute_spot_field_map_spec`, `len(chief_u) < 2`). Confirmed on
the real Apo75 surrogate:

| field (image height) | spot map |
|---|---|
| **41.0 mm** (datasheet-max, a FRESH import's initial size) | **None** — every off-axis field vignettes past the ~16 mm image circle |
| **16.29 mm** (BC-OM25M sensor, after camera coupling) | 13-field map |

Sequence on a fresh import:
1. Import the lens → the surrogate sizes the field to the datasheet **max image height
   (41 mm)** (`camera_precouple_stash.field_value = 41.0`).
2. Spot map is computed at 41 mm → **None**, and `spot_field_map_overlay_spec` **cached it**
   (`_spot_field_map_cache = (signature, None)`).
3. Import the camera → the coupling shrinks the field to the **sensor (16.29 mm)**, where the
   map is valid.
4. But the cache **signature did not include the field size**, so the shrink did not
   invalidate the cached None → the spot diagram stayed blank **for the whole session**.
5. Save → restart → reload started clean at 16.29 mm → a fresh compute → it works. ("weird".)

Distortion / astigmatism use a meridional-fan field-curvature scan that **survives** the
41 mm field, so they never cached a None and kept working — which is exactly the
"Distortion + Astigmatism work, Spot doesn't" signature. It also worked on the other host
"last night" because that session's field was already at the sensor size when spot was first
computed. Nothing to do with the camera body / occlusion (ruled out by the user: the other
image-plane overlays render at the same place).

## The fix

`spot_field_map_overlay_spec` (`three_d_scene_tools.py`):
- **Fold the field metric into the cache signature** via `_spot_map_field_signature_component()`
  (`("height"|"angle", round(field, 4))`), so the datasheet-max → sensor shrink invalidates a
  stale (including legitimately-None) spec.
- **Never persist a falsy spec** (`if signature is not None and spec:`) — belt-and-suspenders,
  so a transient oversized-field None can never stick even if a signature somehow matched.

Either mechanism alone recovers the map on the first refresh after the field settles; together
they are robust. The sibling overlays are untouched (they don't exhibit the None-at-oversized-
field behaviour). Verified: field 41 mm → None (not cached), field 16.29 mm → 13-field map; the
signature component differs across the two.

## Files

- `KrakenOS/UI/services/three_d_scene_tools.py` — field metric in the spot signature +
  truthy-gated cache + `_spot_map_field_signature_component`.
- `KrakenOS/UI/validate_open3d_spot_map_field_cache.py` — display-free guard (penta phase 317).
