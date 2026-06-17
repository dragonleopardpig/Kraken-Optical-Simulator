# 0092 — Open 3D: the old sequential Image marker still drew beyond the new beam-splitter branch detector

## Symptom (user)

> [flag_20260618_001227_407] there is a previous 1mm detector after the new detector.

After promoting the beam splitter, the transmit arm got its derived branch
detector at the focus (bugs/0090) — but a small (~1 mm) marker still appeared
further along the axis, beyond it.

## Root cause

The branch detectors are display-only `SceneTarget3D` derived per terminal leaf.
The transmit/straight-through leaf gets one at its focus (z≈233), but the
**existing sequential Image** plane (z≈266, here ~zero diameter) is still drawn as
its clear-aperture reference disk — a ~1 mm marker beyond the new detector. The
branch detector supersedes the Image for that arm, so the Image marker is
redundant.

## Fix (this commit)

`Open3DSceneRefreshService._suppress_reference_aperture` (extracted from the inline
gate) now also suppresses the **Image** clear-aperture reference disk when the
scene has a branch detector (`scene_has_branch_detector`, computed from the
bundle's `target_source == "branch_detector"` targets), in addition to the
existing detector-coverage-overlay suppression (bugs/0033/0047). So once a split
produces a transmit branch detector, the redundant sequential Image marker is no
longer drawn beyond it. Object planes and plain single-path scenes are unaffected;
the Image body actor is still added at opacity 0 (pickable), as before.

## Regression gate (display-free)

`validate_open3d_branch_detector_supersedes_image.py` (`run_checks()`) drives the
real `_suppress_reference_aperture`: Image suppressed when a branch detector
exists; not suppressed in a plain single-path scene; Object not suppressed by the
branch rule; the bugs/0033/0047 coverage-overlay suppression still fires for both
Object and Image; a Standard surface is never suppressed. Penta **Phase 85**;
baseline → 86.

## Notes

- Display-only; the sequential Image row is untouched in the data (still the
  sequential terminal). Reconciling the sequential image-plane position with the
  branch focus (so 2D analyses agree) is Phase C (auto-solve).
- Confirm in-app (VTK SIGSEGVs headless): after promotion, only the two branch
  detectors should show — no stray marker beyond the transmit one.

## Status: FIXED (pending in-app confirmation)
