# 0280 — source-illumination heatmap must draw only for a scene illumination source

## Symptom (flag_20260709_150933_595)

> "still seems 4 sided dark edges to me"

The user's pushback on the bugs/0278 note, which had guessed the sensor's radial "4 sided dark
edges" was "likely correct radial LENS vignette." The user had loaded
`attachment/machine_vision_150mm_test.py` — a full MV-150 **imaging** system (object → BS cube →
real lens with thin-lens groups + aperture stop r=9.678 → 23.04×23.04 HR25 sensor), with
`scene_sources: []`. The relative-illumination heatmap still painted a radial 4-dark on the sensor.

Direction (durable, saved to memory):

> "Please note your fix should be general, not to particular case."

## Root cause — a coverage artifact, NOT lens vignetting and NOT a builder bug

The heatmap bins detector-hit **local density** and reads it as relative illumination. That mapping
is only valid when the binned rays are a dense **area** sample that floods the sensor — the coaxial
LED case (~60k illumination rays tiling the FOV). With **no** scene source, `_trace_preview_rays`
instead traces the sparse **imaging** pupil/field fan; those rays converge to the central image
region and never reach the rim. Binning their density paints the un-sampled rim dark → a fabricated
radial "4 sided dark edges" that is neither illumination coverage nor lens relative-illumination.

Proven three ways (diagnostics kept under `bugs/`):

* **`diag_0280_real_scene_heatmap.py`** — loads the user's ACTUAL scene, traces it exactly as the
  Open 3D inspector does (`world_envelope`, HR25 override), dumps the detector hits: **117 hits
  spanning only ±6.8 mm of the ±11.52 mm sensor, in 4 x-columns** — a sparse meridional fan, not an
  area tiling. Overlay corner read ≈0.084 (false radial dark).
* **`diag_0280_builder_probe.py`** (pure numpy, decisive) — feeds synthetic hits straight through
  `source_illumination_map_data_from_samples` → `build_source_illumination_overlay` with the exact
  **sensor window** (`target_model` detector dims, `coord="local"` → no data-footprint pad):
  * **Control A** — uniform fill tiling the FULL sensor (±11.52) reads relative **1.000 everywhere**.
    The builder does NOT fabricate a vignette from a uniform input.
  * **Control B** — uniform fill of only the central ±6.8 reads edge≈0.10 / corner≈0.03. A correct
    builder SHOULD report the un-sampled rim dark; that confirms the real-scene 4-dark is a
    sparse-sample artifact, not a builder defect.

So: the builder is correct; the error is feeding it an imaging sample. True imaging
relative-illumination (cos⁴ / vignetting) would be a **separate** future feature, computed from the
lens, not from binning preview-ray density.

## Fix (`services/three_d_scene_tools.py`, `_compute_source_illumination_overlay_spec`)

Gate the heatmap on scene-illumination-source **presence**, using the SAME predicate
`_build_scene_source_bundles` uses to decide whether the preview traces illumination bundles at all:

```python
has_scene_source = bool(
    self._normalize_scene_source_specs(getattr(self, "layout_scene_source_specs", []) or [])
)
...
if not has_scene_source:
    return None
```

* General for **any** loaded scene: the map is built iff the rays it bins are genuine
  source-illumination rays. A pure imaging scene (any lens, any detector, any hit count) → `None`.
* Keys off source **presence**, not hit count — so it can't be defeated by a scene that happens to
  land ≥50 imaging rays on the detector.
* Not `_collect_scene_sources` (which synthesizes one imaging object source even for
  `scene_sources: []`); `layout_scene_source_specs` is the true scene-source list.
* On any predicate exception it preserves prior behavior (never hides a real LED map).

## Verification

New display-free guard `validate_open3d_illumination_heatmap_source_gated` (reuses the coaxial-LED
override fixture; no VTK/Tk):

* **SOURCE-PRESENT** — with the LED scene source the heatmap still builds and still reads the fold
  (tangent) edge darker than the perpendicular edge (the real 2-dark / 2-uniform coverage; no
  regression of bugs/0275–0277).
* **SOURCE-ABSENT** — clearing ONLY `layout_scene_source_specs` (same traced rays, same detector
  hits) makes the SAME compute path return `None`, proving the gate keys off source presence, not
  hit count.

Wired as penta phase **246** ("source-illumination heatmap draws only with a scene illumination
source"); baseline `phases["246"]="pass"` added surgically. Sibling heatmap validators
(`_override`, `_full_sensor`, `_extent`, `source_illumination_overlay`) all use the coaxial LED
layout (which HAS `scene_sources`) → still pass, no regression.

## Notes

* **Corrects the bugs/0278 over-confident read.** The 4-dark on the real 23×23 sensor was NOT a
  correct lens vignette — it was a sparse-sample coverage artifact. The user was right to push back.
* **In-app eyeball owed.** The headless guard + real-scene diag lock the logic (imaging scene now
  yields no heatmap); a running-app visual check that loading `machine_vision_150mm_test.py` shows
  no fabricated 4-dark, while the coaxial LED scene still shows its heatmap, is still owed.
* Future feature (separate): a genuine imaging relative-illumination overlay computed from the lens
  (cos⁴ / vignetting), which would legitimately draw for imaging scenes.
