# 0098 — folded two-arm scene: redundant/mis-oriented detectors + broken reflect-arm thickness overlays

**Date:** 2026-06-19 (M90aPro)
**Branch:** nonseq-display-refactor
**Status:** issues 1 + 2 **FIXED** — `drop_superseded_image_display` now drops ALL
sequential detectors (per-arm detector rows + the global Image) when branch detectors
exist, so each arm shows ONE clean branch detector and the mis-oriented row-10 plane is
no longer drawn (`validate_open3d_detector_redundancy_drop` green). Issues 3 (missing
BS→lens reflect entry gap) + 4 (overlapping/skewed reflect thickness dims) still open.
In-app render confirm pending (cannot render off-screen here — editor validators hit the
pre-existing `_branch_detector_camera_sensors` RecursionError). Follows 0097.

**Scene:** `KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py` —
rows 0-2 common (Object + BS front/rear), 3-6 transmit doublet+detector (along +Z),
7-10 reflect doublet+detector (folded along +Y via `tilt_x=-90` + decenter), 11 global
Image. Two branch detectors (synthetic rows 100000=reflect, 100001=transmit).

**Recordings:** `flag_20260619_154528` → `_161049` → `_163723` (the last is the
clearest, with the user's itemised description).

## Symptoms (user, flag_163723)

1. "Two square detectors on each arm." — each arm draws the scene's *sequential*
   per-arm detector (rows 6/10) **and** the derived *branch* detector, plus the
   transmit arm also shows the 160×160 global Image.
2. "Reflecting arm shows Image Plane overlap with a perpendicular detector
   (detector wrong orientation)." — on the reflect arm the clean +Y branch detector
   and the mis-oriented sequential row-10 detector overlap at ~90°.
3. "Missing thickness measurement from beam splitter to the lens for reflecting arm."
4. "Thickness overlay of lens and thickness overlay of lens to image plane overlap
   and [are] not perpendicular to arrow segments." (reflect arm)

## Geometry evidence (from the recordings' `row_actor_bounds`)

- Reflect **branch** detector (100000): center (0,176,45), ext (45,**0**,45) → clean
  +Y plane. CORRECT (after 0097).
- Reflect **sequential** detector (row 10): center (0,130,45), ext (45,**45**,45) → NOT
  a clean +Y plane; rendered skewed ~45° → the "perpendicular / wrong orientation"
  square.
- Global Image (row 11): center (0,0,192), ext (160,160,0) — large +Z plane at the
  transmit end, redundant with the transmit branch detector.
- Reflect surfaces 7→10 march cleanly along +Y (gaps 3.8/3.5/51.7 mm) — so the
  surface POSITIONS are right; the bugs are in the overlay emit, not the positions.

## Likely roots + fix directions

1. **Redundant detectors (issue 1+2).** `derive_branch_detectors` adds branch
   detectors, but `drop_superseded_image_display` (scene_builder.py:816) only drops the
   sequential **"Image"** surface, not the **"Standard" per-arm detector** rows (6/10),
   and here it doesn't even drop the global Image. Fix: when branch detectors are
   present, also suppress the sequential per-arm detectors they cover (and the global
   Image) so each arm shows ONE clean detector. (This also removes the mis-oriented
   row-10 — issue 2 — by not drawing it.)
2. **Mis-oriented sequential reflect detector (issue 2).** Row 10's detector PLANE
   (tilt_x=-90 + decenter) renders ~45° (ext 45,45,45) instead of facing +Y like the
   ray-derived branch detector. The detector/Image plane frame doesn't follow the
   folded surface frame. Moot if the plane is suppressed (#1); otherwise the
   SurfaceCurve3D orientation for a folded detector row needs fixing.
3. **Missing reflect entry gap (issue 3).** 0097's `_is_cross_arm_gap` correctly skips
   the transmit-det→reflect-doublet gap (it spans arms), but the reflect arm then has
   no entry gap from the splitter to its first lens, while the transmit arm keeps its
   entry gap (the common→transmit gap S2=30mm). Fix: emit a branch-entry thickness
   from the splitter (last common row / BS) to each arm's first element, indexed/labelled
   by that first element.
4. **Reflect thickness overlays overlap + look non-perpendicular (issue 4).** The
   reflect doublet's internal dims appear dropped while the transmit's draw, and the
   lens / lens→image dims overlap and look skewed. The offset is `cross(view, segment)`
   = screen-perpendicular *by construction*, and the surface positions are right, so the
   skew is NOT in `offset_direction` — suspect the gap-split / overlap-resolution
   (`_overlay_axial_spans_within`) and label placement on the folded +Y arm, plus the
   doublet-internal emit being dropped for the folded rows. Needs a zoomed reflect-arm
   render to pin precisely.

## Notes

- The optics trace correctly; these are display overlays only.
- The clean fix for 1+2 is the same supersede pattern as 0092/0093, extended from the
  global Image to the sequential per-arm detectors. 3 is a refinement of 0097's
  cross-arm handling. 4 needs a closer render.
