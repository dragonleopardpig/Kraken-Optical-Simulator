# 0267 — a marked illumination face floods a full-surface emission (visible feedback)

User flag `flag_20260708_171116_895` on the MV-150 coaxial-LED scene:

> *"how do I know it is successfully assigned Illumination Surface? The rays seem not changing. No additional
> full surface rays from that surface."*
> *"I think the ray should sample across the full surface, just like the existing object emission (but bigger
> surface)."*

Marking a CAD/STL face as an illumination source (bugs/0264) produced **no visual feedback**. Two reasons:
the marker is deliberately excluded from the imaging trace (bugs/0266, so it can't hijack the image
plane/detector/axis), and even the stored marker was a fixed **2 mm collimated disk** — nothing a user could
see. This is Stage 1 of the Source+Object separation proposal (`bugs/DESIGN_source_object_separation.md`).

## Fix — the marked face floods its whole surface with emission rays

A new **"Illum emission"** overlay draws the additive full-surface emission from every face-bound marker:
a straight ray from each sampled point on the marked face, out along its launch direction, sized to flood
the **whole face** (an area-matched disk of `optical_solid_face_effective_radius_mm(face)`, not the 2 mm
disk). On the MV-150 BS face that is ~14–37 mm instead of 2 mm — an obvious, immediate "it worked".

* `_illumination_marker_full_surface_source` (`services/source_modeling.py`) — copies a marker sized to the
  live face record's effective radius (fallback: the stored source when no face resolves).
* `_build_illumination_marker_bundles` — the deliberate **complement** of `_build_scene_source_bundles`:
  keeps ONLY markers (which bugs/0266 excludes from imaging), builds each sized emitter's launch bundle.
* `build_illumination_marker_rays_overlay` (`services/source_illumination_rays_overlay.py`) — bakes a
  2-vertex emission segment per sampled ray (starts → ends), one emissive-cyan colour, subsampled.
* `illumination_marker_rays_overlay_spec` / `_compute_...` (`services/three_d_scene_tools.py`) — lazy +
  signature-cached; the emission length scales with the emitting face (6× its radius).
* `_add_illumination_marker_ray_overlays` (`open3d_inspector.py`) + `show_illumination_marker_rays_var`
  (defaults **ON** so marking a face gives immediate feedback; cheap when no marker exists) + the
  **Overlays → "Illum emission"** checkbutton + the `refresh_scene` live-read.

## Why source EMISSION, not a through-system trace

This draws the **source emission** (the face flooding rays), **not** illumination traced through the optics
onto the detector. That was a deliberate call after the trace was tried and rejected for Stage 1:

* A face marker is a source **in the middle** of the optical system. Launched into the imaging trace it is
  immediately **stopped at S0** (the object surface) — verified: NsTraceLoop engaged (non-seq), yet all 400
  rays returned `status='Stop @ S0'`, collapsed to a dot at the emitter. The existing trace machinery
  expects sources ahead of S0 (like the LED), so a mid-system face source never propagates.
* Making illumination refract/scatter through the optics and land on the detector **is the Stage-3 coupling**
  (Option B, irradiance-weighted; `bugs/DESIGN_source_object_separation.md`), not a Stage-1 hack. The design
  doc scopes Stage 1 as exactly *"mark a face, see rays flood off the whole surface"* — the emission flood.

So Stage 1 shows honest source physics (the sampled launch rays), and Stage 3 will trace them through the
Object scatter onto the detector.

## 0266 preserved — render-only, never traces

The overlay is built **purely from the marker launch bundles** and **never traces**, so it cannot touch
`last_rays` / `_last_scene_bundle`; the imaging image plane / detector / optical axis stay fixed. The guard
pins this: `_compute_illumination_marker_rays_overlay_spec` contains no `_trace_preview_bundles` / `raykeeper`
/ `build_system` and no `last_rays` / `_last_scene_bundle` reference.

**Cache correctness:** `_preview_trace_signature()` captures only the PRIMARY UI source, not the scene-source
list where markers live, so the overlay cache folds in a **marker fingerprint**
(`_illumination_marker_fingerprint`) — otherwise a prior empty (None) spec would persist after a face is
marked and suppress the emission.

## Verification

* **Display-free guard** `validate_open3d_illumination_marker_emission` (`run_checks()`): WIRING (builder keeps
  only markers; the spec compute is stub-only — no trace, no imaging-state reference; render-only consumer;
  refresh + menu wiring), PURE (2-vertex segments, zero-span/non-finite dropped, subsample cap), BEHAVIOUR
  (marker-only → emission bundle + **0 imaging bundles** + imaging state untouched; mixed 1/1; marker-free →
  nothing), BINDING (real promoted face sized to its full surface, radius >> 2 mm; SKIPs without the STEP).
* **Phase 236** wraps the guard; `tools/penta_validator_baseline.json` updated (236 → pass). Siblings 0264
  (phase 233) and 0266 (phase 235) re-verified — no regression.

## Notes

* **In-app eyeball owed:** headless can't drive the embedded-VTK inspector. The user should open the MV-150
  coaxial scene, mark the BS illumination face, and confirm the cyan full-surface emission floods off the
  whole face (Overlays → "Illum emission").
* **Next — 0268 (Face Editor feedback):** add an "Illumination Source" value to the Face Editor function
  dropdown so the editor CONFIRMS the role instead of showing "Absorbing" (the other half of the flag).
* **Later — Stage 2/3:** the "Diffuse / Scatter Object" face role (0269) and the Option-B coupling (0270)
  that traces the illumination through the Object scatter onto the detector.
