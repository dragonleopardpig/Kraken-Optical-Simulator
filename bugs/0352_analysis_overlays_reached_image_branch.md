# 0352 — Image Analysis Overlays vanish when a beam-splitter branch reaches Image

**Status:** Fixed (2026-07-19).
**Reported via:** `recording_20260719_095137.json`, flag
`flag_20260719_095106_746`: “All other Analysis Overlay no longer working, only the
Illumination Overlay is working now.”

## Symptom

On `attachment/machine_vision_150mm_test.py`, the **Illumination** heatmap rendered but
**Focus surf**, **Distortion**, **Astigmatism**, **Spot map**, and **Pixel grid** produced no
actors. The toggles were not mutually exclusive: the running debug log recorded all five as
enabled and each took the cached-scene refresh path, but the actor count did not change.

The flag screenshot is KrakenOS's simulated detector relative-illumination overlay, not a
physical-camera recording. Its two side-dark bands are therefore separate from the user's
reported physical ~35 × 39 mm usable-bright measurement.

## Root cause

All five missing overlays ultimately use
`ThreeDSceneToolsMixin._best_focus_surface_anchor_target`. That selector was intentionally
limited to a single non-branch image and returned `None` as soon as *any* synthetic branch
detector existed.

The MV-150 bundle contains two beam-splitter leaves:

- `S1/reflect`: a non-imaging `converging_rays` detector beside the cube, draw-suppressed;
- `S1/transmit`: the unique unsuppressed `reached_image` detector at the real Image plane,
  `[0, 0, 657.0871]` mm, with the 23.04 × 23.04 mm HR25 sensor.

Scene construction removes the duplicate sequential Image target after the reached-Image
branch supersedes it. The selector therefore saw a branch and rejected the only correct
anchor. Illumination remained visible because it has a separate branch-aware anchor resolver.

## Fix

The shared image-analysis selector now applies an explicit policy:

1. Prefer a canonical, non-branch Image/detector target when one exists.
2. Otherwise accept exactly one unsuppressed detector branch stamped
   `focus_source="reached_image"`.
3. Return `None` for zero candidates or multiple reached-Image arms; per-arm analysis still
   needs an explicit branch selector, so KrakenOS must not choose arbitrarily.

Unrelated reflected, parked, converging, or draw-suppressed branches no longer disable the
canonical imaging analysis.

## Verification

`validate_open3d_analysis_overlays_reached_image_branch` builds the exact MV-150 fixture through
the public scene bundle and public overlay-spec APIs. It verifies that the transmitted branch
is selected and all five specs are non-empty. It also pins canonical-target precedence,
suppressed/non-imaging rejection, and ambiguous two-image-arm rejection.

The existing `validate_open3d_best_focus_surface` branch policy was updated from the obsolete
global veto to the same selection matrix, and comprehensive phase 305 runs the focused guard.
