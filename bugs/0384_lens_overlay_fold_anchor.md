# 0384 — lens STEP overlay loses its leg fold after swap (fold-anchor robustness)

**Origin:** follow-up to the AZ85 swap flags (bugs/0383). A subagent traced the display-fold
placement pipeline for the lens overlay and found a latent robustness bug that can leave a swapped
lens rendered UNFOLDED (off the mirror/splitter leg, e.g. "vertical").

## The pipeline (verified)

The lens STEP overlay is folded onto a fold leg by **System A** — the promoted RA-mirror / beam-splitter
`optical_solid_output_port_pose_overrides`, read LIVE (no stale cache) via
`_optical_axis_fold_world_transform_for_row(_lens_front_datum_row_index())`
(`layout_polyline_display.py`). The overlay is seated on the straight +Z axis at the front-datum z, then
`_mesh_with_world_transform(aligned, fold_transform)` bends it onto the leg. **If `fold_transform` is
None, the overlay stays at the raw unfolded datum z.** (The two-arm display fold folds only rays /
detectors, not overlays — and its caches rebuild correctly on a swap.)

## Root cause (general)

`_lens_front_datum_row_index()` used a **narrower** name test (`front` + `datum`/`edge`) than the swap's
block detector `_imaging_lens_block_indices` (`front` + `datum`/`vertex`). When they disagree — a lens
whose front row is e.g. "Front Vertex" (no "datum"), which the swap will happily splice in — the overlay
finder fell through to its fallback: *the first non-Object/Image/Aperture row*, which in a folded scene
is **the promoted RA-mirror fold source itself**. The fold source is not a follower, so its override
lookup is None → `fold_transform` None → the lens renders unfolded.

## Fix (general, not scene-specific)

Unified the three narrow finders (`_lens_front_datum_z`, `_lens_front_datum_row_index`,
`_lens_rear_datum_z`) into one `_lens_datum_row_index(side)` that:
- matches the SAME names as the block detector — `side` + (`datum` | `vertex` | `edge`), so the overlay
  anchor and the swap can never disagree;
- in its fallback, **skips promoted solids / optical-step solids**, so it can never anchor the lens
  overlay to the fold source.

## Verification

- AZ85: front datum → row 3, rear → row 7 (unchanged; standard naming already matched).
- "Front Vertex" (no "datum") → the lens row, NOT the fold-source mirror.
- No datum-like name → fallback skips the promoted mirror and lands on the real lens row.
- Mirror + Object/Image only → None (never the mirror).
- bugs/0374 glass-recenter guard still green (it consumes `_lens_front_datum_z`/`_lens_rear_datum_z`).

Guard `validate_open3d_lens_overlay_datum_anchor`, penta **phase 324**.

**Note:** for AZ85's standard "Front Optical Vertex Datum" naming both finders already agreed, so the
bugs/0383 downstream-collapse fix is the dominant fix for that specific flag; this 0384 hardening covers
the general case (any lens front-row naming) so a swap can never silently unfold the lens overlay. An
in-app eyeball on a real swap is still owed.

## Files

- `KrakenOS/UI/services/layout_polyline_display.py` — `_lens_datum_row_index` + thin wrappers.
- `KrakenOS/UI/validate_open3d_lens_overlay_datum_anchor.py` — guard (phase 324).
