# 0266 — marking a face as an illumination source shifts the image plane + detector onto the BS

User flag `flag_20260708_163419_833` (full session `recording_20260708_163455.json`, the MV-150 coaxial-LED
scene: Object / promoted BS cube / thin-lens blackbox groups / Image):

> *"after setting illumination surface, the image plane and detector shifted to the illumination plane of the BS."*

This is a **regression introduced by Feature B (bugs/0264)** — the ergonomic "Set as Illumination Source"
path. The moment a CAD/STL face is marked, the displayed image circle + branch detector jump off the imaging
axis and re-anchor onto the beam-splitter's +X illumination face. `state.json` confirms it: the optical axis
exploded to `z ∈ [-1588.29, 2307.53]`, a synthetic branch-detector row `100000` appeared on the BS +X face
(`x ∈ [27.59, 27.75]`, normal along +X), and only `ray_actor_count = 2` degenerate rays survived — while the
Image *row* (row 8) stayed at `z = 657`. The screenshot shows "Image circle (232.6)" + "Sensor 23.0×23.0"
draped over the BS, with the teal illumination disc off to the left.

## Root cause — a face marker is physical+enabled, so it REPLACES the imaging trace

Marking a face creates a real `SceneSource3D` (`physical=True, enabled=True`, role="illumination"). The live
preview trace treats **any** physical+enabled scene source as a launch that supersedes the object-driven
imaging trace. In `TracePreviewService._trace_preview_rays` (`services/trace_preview.py:59`):

```python
scene_source_bundles, scene_source_records = self._build_scene_source_bundles(wavelength)
if scene_source_bundles:
    rays.clean()
    self._trace_preview_bundles(system, rays, wavelength, scene_source_bundles, ...)
    ...
    return                      # ← early return: skips EVERY imaging launch path below
```

So a non-empty bundle list short-circuits the per-branch launch, world-envelope, full-pupil grid, and
finite-object paths. The face marker produced exactly one such bundle, so the imaging trace never ran. The
image circle, branch detectors, and optical axis are all **derived from the traced ray tree**, so with only
the lone illumination bundle traced they collapsed onto the BS +X face and the axis envelope blew up.

The image plane / detector / optical axis are **imaging conjugates fixed by the object** — an illumination
source must never define them.

## Fix — a face-bound marker is a designation, not a trace driver

New shared predicate `scene_source_spec_is_face_bound_marker` (`scene_source_analysis.py`) keys on a resolved
`face_anchor_row >= 0`. The key survives spec normalization AND rides in `SceneSource3D.settings`, so one
predicate covers both the dict-spec and the dataclass form. A face-bound marker is now **excluded from every
source-driven imaging launch**:

* `_build_scene_source_bundles` (`services/source_modeling.py`) — the primary fix. This feeds the live
  preview trace (sync **and** async, which routes through `_build_preview_system_rays_bundle` →
  `_trace_preview_rays`). A marker is `continue`d, so a marker-only scene yields **0 bundles** and
  `_trace_preview_rays` falls through to the imaging trace — conjugates stay put.
* `_collect_scene_sources` (`services/source_modeling.py`) — the physical-source short-circuit now ignores
  markers, so a marker-only scene falls through to the pupil/field imaging reference. That reference stays
  `sources[0]` (correct imaging-ray metadata tagging); the marker is **appended** so it still shows in the
  source table / drives the 0259–0262 illumination overlays.
* `build_saved_layout_rays` (`source_trace_helpers.py`) — the saved-layout snapshot/plot render excludes
  markers from its physical-source launch set (it keeps its own pupil/field fallback).

`scene_sources_from_settings` is **deliberately NOT filtered** — it must faithfully round-trip every source
(bugs/0264's guard depends on the marker surviving the settings round-trip for display). The exclusion is
applied at its call site instead. The guard pins this so a future well-meaning edit doesn't move it.

## Verification

* **Display-free guard** `validate_open3d_illumination_source_no_imaging_hijack` (`run_checks()`):
  * PREDICATE — dict-spec and `SceneSource3D` dataclass forms; positive rows incl. row 0, negatives / None /
    garbage / no-key → not a marker; and the full `scene_source_from_spec` builder carries the anchor through.
  * WIRING (source) — the three launch paths consult the predicate; `_trace_preview_rays` still gates on the
    early-return; `scene_sources_from_settings` does NOT filter markers.
  * BEHAVIOUR (headless, **STEP-free** hand-built specs, always runs) — marker-only → 0 imaging bundles AND
    `_collect_scene_sources[0]` is the non-marker pupil/field reference with the marker appended; a deliberate
    physical source → ≥1 bundle (unchanged); a mixed deliberate+marker scene → the deliberate source only.

## Guard / baseline

* **Phase 235** (`phase_235_illumination_source_no_imaging_hijack`) wraps the guard's `run_checks()`.
  Registered in the `phases` list; `tools/penta_validator_baseline.json` updated (235 → pass). The change only
  narrows which sources drive the trace, so no prior phase is affected — bugs/0264's phase 233 still passes
  (the marker still round-trips and emits for the overlays).

## Notes

* **In-app eyeball owed** (0264, 0265, 0266): headless can't drive the embedded-VTK inspector's live camera.
  The user should re-open the MV-150 coaxial scene, mark the BS illumination face, and confirm the image
  circle + detector now stay on the imaging axis (they no longer jump onto the BS +X face).
* **Follow-up (deliberately out of scope here):** a separate/additive per-source illumination trace so a
  marked face emits its **own** traced rays *without* touching the imaging conjugates. Nothing is lost today —
  the 0259–0262 illumination heatmap + "Illum rays" overlays already visualize the coaxial illumination from
  the imaging trace. Cramming a second trace into this regression fix would over-engineer it.
