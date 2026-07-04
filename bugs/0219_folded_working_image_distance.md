# 0219 — folded working/image distance didn't sum through the RA mirror

**Status: FIXED. On a folded promoted-RA-mirror scene the reported OBJECT working distance and
IMAGE distance now sum the folded axis segments THROUGH the mirror(s) to/from the lens, instead of
stopping at (object) or measuring only from (image) the mirror. With a second RA mirror between the
lens and the image the reported image distance was 40 mm (mirror-2→image only) instead of the true
folded lens→mirror-2→sensor 190.4 mm. The optical SOLVE (EFL / magnification / paraxial image
plane) is untouched — only the reported distances changed. Answers the user's question on
`flag_20260704_195234`: "the working distance of the Object, is it measured from the first optical
axis segment (to the RA-mirror centre) + second segment (from the RA-mirror centre)? … Same for
Image Distance." — it wasn't; now it is.**

## The bug — the folded-sum path was gated on a literal `surface == "Mirror"` row

`_current_object_distance` (`services/layout_analysis_display.py`) and `_current_image_distance`
(`services/layout_scene_bundle_display.py`) chose the folded-sum path only when
`any(row.surface == "Mirror" …)`. A **promoted CAD RA mirror is `surface == "Standard"`** (a
`Solid_3d_stl` optical solid whose *face* S001/F002 has `function == "Mirror"`) — it has NO literal
`"Mirror"` row. So the gate was False and both distances fell back to a single adjacent prescription
segment:

- object WD = `rows[0].thickness` = object → mirror-1 ONLY (59.4 mm), dropping mirror-1 → lens;
- image distance = `rows[-2].thickness` = mirror-2 → image ONLY (40 mm), dropping lens → mirror-2.

For the current single-mirror AZ85 this happened to be right (the fold is entirely before the lens,
so the un-folded lens→image leg is the whole distance). But the user's planned layout puts a SECOND
RA mirror between the lens and the image, and there the image distance dropped the 150 mm lens→
mirror-2 leg → reported 40 mm instead of 190.4 mm.

Even the folded-sum helper mis-measured the image side: `_paraxial_reference_rows_for_layout`
treats a promoted solid as a `_transmissive_reference_row` (a powered plate) and sets
`last_source_index` ON it, so `_paraxial_total_image_gap` summed mirror-2 → image (40 mm), not
lens → mirror-2 → image.

## The fix

- **`_row_is_promoted_mirror_fold(row)`** (`services/paraxial_tools.py`): a promoted CAD solid whose
  `OpticalSolidFaces` carries a Mirror face — a fold with no paraxial power (distinct from a
  refractive/beam-splitter mesh solid).
- **`_scene_folds_for_paraxial_distance`**: the distance gate now fires for a literal `"Mirror"` row
  OR a promoted RA-mirror fold, so the folded-sum path runs for the promoted mirror.
- **`_paraxial_total_object_gap`**: sums THROUGH a promoted mirror fold AND its promotion-inserted
  `InPathTrailingSpacer` (the space the mirror solid occupies past its optical station), so the
  object WD reaches the lens FRONT datum (141.85), not the mirror.
- **`_paraxial_total_image_gap`**: backs `gap_start` up past a TRAILING promoted mirror fold, so the
  image distance runs from the lens REAR datum through mirror-2 to the image (190.37). The returned
  `last_source_index` + `reference_rows` are UNCHANGED.

**Critically, the shared `_paraxial_reference_rows_for_layout` walk is NOT changed.** An earlier
attempt merged the mirror away as an air gap there — but that walk feeds the optical SOLVE, where
the mirror's BK7 plate is a REAL glass focus-shift; merging it would corrupt EFL / magnification /
`_paraxial_image_plane_z`. Verified byte-identical to clean: two-mirror magnification 1.3977,
paraxial image plane z 354.97, before AND after.

## Results

```
                object WD              image distance
SINGLE mirror   59.4 → 141.85 (lens)   150.37 (un-folded lens→image, unchanged/correct)
TWO   mirror    59.4 → 141.85 (lens)   40.0  → 190.37 (lens-rear→mirror-2→sensor)
```

Object WD = object → mirror-1 → lens-front-datum (141.85 = its cumulative-z). Image distance =
lens-rear-datum → mirror-2 → image (190.37 = image-cumz 387.22 − rear-datum-cumz 196.85). Both are
the full folded paths, symmetric about the lens. Unfolded scenes are untouched (the gate is False →
`rows[0].thickness` / `rows[-2].thickness` as before).

## Verification

Display-free guard `validate_open3d_folded_working_image_distance` (5/5): the two-mirror folded
sums, the single-mirror (object folded, image un-folded), a CAUSAL contrast vs the old
`rows[-2]` (40) / `rows[0]` (59.4) single-segment fallbacks, the SOLVE intact (finite mag +
image-plane z), and the fold gate detecting the promoted mirror. Penta **phase 195**, baseline
`pass`. Regression sweep green: `validate_open3d_first_order_reference`,
`validate_open3d_ra_mirror_quick_estimation`, `validate_open3d_decoration_does_not_carve_thickness`.
(`validate_open3d_object_to_led_dimension` fails on clean `main` too — a pre-existing drag-registration
issue, unrelated.)

## Not in scope (separate items the user also raised)

- **Detector/camera STEP detached** + residual defocus: the camera follows `_current_image_plane_z`
  (prescription, 387) which overshoots the true focus (`_paraxial_image_plane_z`, 355); the 0217
  post-pass moved only the detector. Root-fix tracked separately.
- **Snap-to-RA-mirror-center** for the manual measurement overlay (+ that tool measures only the
  global-Z component, dropping a folded leg). Tracked separately.
- **FOV ≠ 1X** (magnification 1.40, not 1.0) — a pre-existing magnification bug, untouched here.
