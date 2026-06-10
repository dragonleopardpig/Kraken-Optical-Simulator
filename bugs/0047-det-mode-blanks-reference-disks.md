# 0047 — "Det" toggle blanks the Object/Image reference disks (no detector configured)

**Status:** Det-blanking root cause fixed (2026-06-10). One related, separable
display item — the on-axis Image disk reads as a 1 mm speck — is left open as a
design decision (see *Open follow-up* below).
**Component:** Open 3D scene refresh. `Open3DSceneRefreshService` in
`KrakenOS/UI/services/open3d_scene_refresh.py`.

## Symptom

User flag (`attachment/recorded_bug_repros/flag_20260610_112814_029/`):
*"Clicking Refs show only the Object disk, click Det, Object Disk vanish, not
showing any Image Disk."*

Repro scene (from `state.json`): the cemented doublet, rays ON. Row 0 Object is
±10 (20 mm Ø) at z = 0; row 6 Image is ±0.5 (1 mm Ø) at z ≈ 229. **No** real
detector is configured — the field is on-axis only.

Two distinct complaints:
1. **Det makes the Object disk vanish.** Toggling "Det" (detector overlays)
   blanked the Object-plane reference disk, leaving the image plane empty.
2. **"not showing any Image Disk."** With Refs on, the Image-plane disk was
   effectively invisible — it is a 1 mm disk next to the 20 mm Object disk.

## Root cause

### (1) The Det-blank — `suppress_reference_aperture` fired with nothing to replace it

bug 0033 introduced `suppress_reference_aperture`: when the detector coverage
overlay is shown, it draws an **image circle** at the image plane (cyan = covers
the sensor, amber = falls short) plus an object FOV rectangle. The Object/Image
reference *aperture disks* would otherwise sit at the same planes and read as
that coverage geometry, so when "Det" was on they were suppressed.

The gate was simply `detector_overlays_on and row_surface in {"Object","Image"}`
(`open3d_scene_refresh.py` ~line 507). But `DetectorCoverageOverlayService`
only actually *draws* anything when it has BOTH a detector target with usable
sensor dimensions AND a positive `max_real_image_height` (its image-circle
radius). On this on-axis-only scene the auto image plane registers as a 1 mm
"detector" but `max_real_image_height = 0` → the coverage overlay draws nothing.
So the suppression blanked the reference disks while drawing no replacement —
the image plane went empty. (Pressing "Det" alone was enough to trigger it,
since the gate keyed only on the toggle, not on whether coverage would draw.)

### (2) The 1 mm Image disk — on-axis Infinity focuses to a near-point

The cemented-doublet starter loads in **Infinity** object mode with an on-axis
(0°) field. A collimated on-axis beam focuses to essentially a point, so the
auto image-diameter (`_auto_image_diameter_value`) has no real image height to
size from and floors to 1 mm. The Image reference disk is therefore physically a
~1 mm disk: tiny, but a faithful read of the projected image extent. This is not
the same defect as (1); it is the disk *being correct but small*.

## Fix (for (1))

Add `Open3DSceneRefreshService._detector_coverage_will_draw(scene_bundle)`
(`open3d_scene_refresh.py:45`), which returns True only when the coverage
overlay's own preconditions hold:

- some `scene_bundle.targets` entry is `is_detector` **and**
  `scene_target_active_dimensions(target)` is not None (real sensor dims), AND
- `editor._field_metrics_summary()["max_real_image_height"]` is finite and > 0.

The suppression gate becomes
`detector_coverage_active = detector_overlays_on and self._detector_coverage_will_draw(scene_bundle)`
(line 183) and `suppress_reference_aperture` keys off that (line 507). This is a
strict **subset** of the old condition: it suppresses only when the coverage
overlay actually replaces the disks. The detector phases (37–39, off-axis with
`max_real_image_height > 0`) are logically unchanged — coverage still draws, the
disks are still suppressed there. On the flagged on-axis scene the disks now
survive the Det toggle.

## Open follow-up (symptom 2 — design decision, not yet implemented)

The 1 mm Image disk is *correct* for on-axis Infinity, but the user reads it as
"no Image disk." Two non-exclusive directions, both awaiting a decision:

- **Starter preset:** switch the Doublet starter to **Finite** object mode,
  where Auto already sizes the Image disk to ≈ |m|·object Ø (~22 mm) and the demo
  shows a meaningful image disk. (The user explicitly rejected *inflating* the
  disk to an arbitrary floor; this changes the *scene*, not the disk logic.)
- **Real-detector overlay (Fix B):** when a real detector IS present but
  `max_real_image_height` is 0 (on-axis), fall the coverage image-circle radius
  back to the traced image-bundle footprint, so the image circle and the sensor
  rectangle always overlay and the user can read vignetting vs overfill. Additive;
  does not touch phases 37–39.

## Tests

- `validate_det_coverage_gate` — display-free unit guard on
  `_detector_coverage_will_draw`: no detector → False; a 1 mm auto-"detector"
  with `max_real_image_height = 0` → False (the bug case); a real detector with
  `max_real_image_height > 0` → True; non-finite radius → False.
- `validate_det_mode_keeps_reference_disks` — live guard: boots the cemented
  doublet (no detector) with Refs ON, toggles Det OFF→ON, and asserts the
  Object/Image reference-aperture disk bodies and their z≈0 / z≈229 rim lines
  survive the toggle; renders a Det-ON PNG for eyeballing. SKIPs without a
  renderer.
- Folded into the comprehensive harness as **Phase 52**.
