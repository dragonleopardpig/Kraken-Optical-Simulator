# 0699 — the "vertical golden straight line near the top of the prism"

Flag context: reported mid-0697 ("Also, I see a vertical golden straight line near
the top of the prism, it shouldn't be there") and re-asserted after the
placement-handle theory failed ("I doubt the vertical line is placement handle.
Nothing can clear it"). The user was right on both counts.

## Identification (actor census, `bugs/0699_gold_actor_census.py`)

Walking every renderer prop for slender vertical gold actors found exactly two:

```
GOLD VLINE: bounds x[-0.5,0.5] y[-25.0,25.0] z[-50.0,-50.0] col=(1.00,0.80,0.20) owner=_actor_by_key
```

That is the **faceB scene-source glyph** (aperture panel + its border loop) at the
face-B plane z = −50 — drawn as a 1 mm × 50 mm VERTICAL stripe. The spec says
`radius_x = 25.0, radius_y = 0.5` (the 50×1 mm emitting face lies along x). The
glyph's extents were TRANSPOSED. Nothing could clear it because it is not a
handle at all: it is the source glyph, cleared only by hiding the source.

## Root cause — two different aperture frames

- The **ray sampler** orients bundles with
  `SourceModelingMixin._source_frame_vectors_from_direction`: for a z-facing
  direction it picks reference ŷ, so `u = ±x̂` (radius_x horizontal) and
  `v = ŷ` (radius_y vertical). The physics launched from the correct
  horizontal 50×1 rectangle all along.
- The **glyph** (`_scene_source_glyph_basis` in `open3d_inspector.py`) had its
  own private helper-vector construction: for |d_z| ≥ 0.9 it picked helper x̂
  with the opposite cross order, giving `u = ±ŷ` — radius_x drawn VERTICAL.

Classic display-vs-physics frame divergence
([[feedback_display_follows_physics]]). On near-square LED panels the transpose
is invisible; the om05a faceB emitter's 50:1 aspect made it a stripe.

## Fix

`_scene_source_glyph_basis` now DELEGATES to
`SourceModelingMixin._source_frame_vectors_from_direction` and returns
`(w, u, v)` — one frame for sampler, glyph panel, and the illumination-volume
overlay (the other consumer at `open3d_inspector.py` ~16862, which passes u/v +
radius_x/radius_y into `build_illumination_volume_overlay`).

## Guard

`validate_open3d_scene_source_object._check_basis` now also pins:
- glyph frame ≡ sampler frame for four directions (incl. (0,0,−1));
- for a z-facing source, the radius_x axis has zero ŷ component (the 0699
  stripe signature).

`validate_open3d_illumination_volume_overlay` re-run: PASS.

## Verification on the scene

Census after the fix: both glyph actors read
`x[-25.00,25.00] y[-0.50,0.50] z[-50.00,-50.00]` — the panel hugs the 50×1
face. Render `bugs/0699_faceb_glyph_after.png` shows no vertical golden line.
