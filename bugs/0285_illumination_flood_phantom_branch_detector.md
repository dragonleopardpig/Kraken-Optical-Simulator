# 0285 — an illumination flood draws a phantom detector/image plane beside the BS cube

## Symptom (flag_20260710_085210_625, "after adding Scene Source")

After adding a physical scene-illumination source (the LED of bugs/0283/0284) to the MV-150 imaging
scene, a **second "Sensor 23×23 / Image circle" detector plane** draws off to the **side of the
beam-splitter cube** (at x≈80), alongside the real detector on the sensor at z≈657. The user's directive:

> "please note phantom detector and image plane shown at the side of the BS cube."

(Distinct from the sibling flag_20260710_085240_847 "illumination overlay still show nothing" — that empty
heatmap is the illumination→object→detector coupling, a separate/deferred piece.)

## Root cause — a flood arm that never images, with no scatter gate to catch it

The scene is `attachment/machine_vision_150mm_test.py`. Its beam splitter forks every ray into a
transmit and a reflect arm. The added LED **floods** the cube, and the **reflect arm sprays sideways
with no lens in its path**, so its rays never converge:

* `derive_branch_detectors` parks a branch detector on that arm at the **default distance**
  (`focus_source == "default_distance"`), ~50 mm out at **x≈80** — a real focus was never found.
* The **only real detector in a flood** is the arm that reaches the sequential Image
  (`focus_source == "reached_image"`, on the sensor at z≈657).
* The existing draw gates missed it: the bugs/0182/0183 gates key off **scatter/bounce branch-path
  tokens** (this branch has none), and the bugs/0184 whole-scene gate requires a **diffuse-scatter
  object** — this flood has **none** (`diffuse_scatter=False`). So the phantom's plane **and** its 3-D
  footprint **and** its detector-coverage "Sensor/Image-circle" all drew.

Reproduced headlessly on the real scene (`bugs/diag_phantom_branch_detector.py`, LED added, 2246 ray
paths, `diffuse_scatter=False`):

| row | branch arm | focus_source | center | before | after |
|-----|-----------|--------------|--------|--------|-------|
| 100000 | `…/reflect` | `default_distance` | (+79.9, +1.1, +229.7) | **DRAWN** ✗ (phantom beside cube) | **draw_suppressed** ✓ |
| 100001 | `…/transmit` | `reached_image` | (+0.0, +0.0, +657.1) | drawn (real sensor) | drawn (unchanged) ✓ |

Image-plane curves drawn: **2 → 1**. Heatmap anchor stays row 100001 (z=657.1). The reflect target is
**kept as a ray hard-stop** (only its draw is gated), so the flood rays stay bounded in 3-D.

## Fix

Generalize the bugs/0184 idea from "a diffuse-scatter object is present" to "a physical illumination
**flood** is present" — a flood's non-imaging arms are noise exactly like scatter leaves.

* `scene_builder._scene_has_illumination_flood(sources)` — True when a **physical, enabled illumination**
  source is present that is **not a face-bound marker** (bugs/0282's `scene_source_spec_is_face_bound_marker`,
  so a display-only marker never over-suppresses — matches the heatmap gate exactly).
* `scene_builder.build_scene_bundle` — the branch-detector loop stamps a single
  `metadata["draw_suppressed"]` on every detector whose draw must be gated (scatter / internal bounce /
  whole-scene scatter, **and now** `illumination_flood and focus_source != "reached_image"`), computed
  where the flood + scatter context is known.
* The one flag is honoured by **every** downstream draw path:
  * `scene_projector._target_branch_detector_draw_suppressed` (2-D projection) returns True on the flag;
  * `three_d_scene_tools._scene_detector_overlay_specs` skips the flagged target's 3-D footprint;
  * `detector_coverage_overlay.add_overlays` skips the flagged target's Sensor/Image-circle coverage.

No illumination source → `illumination_flood` is False → **nothing changes** (a clean beam splitter still
shows a detector on both arms, bugs/0090). In a scatter scene the flag is set exactly where the old
per-path/whole-scene logic already suppressed, so that behaviour is identical (guards below still pass).

## Guard / phase

`validate_open3d_illumination_flood_phantom_branch_detector.run_checks()` (display-free) —
Phase 251:

* **PREDICATE** — `_scene_has_illumination_flood`: physical LED → True; face-bound marker / disabled /
  non-physical / Pupil-field ref / empty → False.
* **PROPAGATE** — the shared 2-D predicate honours the stamped flag; a stamped-yet-drawable target proves
  the 3-D/coverage skip is load-bearing (not vacuous); a clean reached-image arm is not falsely suppressed.
* **REAL SCENE** — `attachment/machine_vision_150mm_test.py` + an added LED: the reflect phantom is
  draw-suppressed, the on-sensor reached-image detector + heatmap anchor survive, exactly ONE image-plane
  curve draws, and clearing the source drops the flood predicate (no over-suppression of pure imaging).

## Files

* `KrakenOS/UI/scene_builder.py` — `_scene_has_illumination_flood` + branch-loop `draw_suppressed` stamp.
* `KrakenOS/UI/scene_projector.py` — `_target_branch_detector_draw_suppressed` honours the flag.
* `KrakenOS/UI/services/three_d_scene_tools.py` — 3-D footprint loop skips the flag.
* `KrakenOS/UI/services/detector_coverage_overlay.py` — coverage loop skips the flag.
* `KrakenOS/UI/validate_open3d_illumination_flood_phantom_branch_detector.py` — guard.
* `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 251.
* `bugs/diag_phantom_branch_detector.py` — headless repro.
