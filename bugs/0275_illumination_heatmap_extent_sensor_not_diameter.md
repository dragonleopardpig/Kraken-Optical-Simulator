# 0275 — Relative-illumination heatmap window = the sensor, not the round catch diameter

## Symptom (flag_20260709_093800_013)

On the MV-150 **folded** coaxial-LED scene, the on-detector relative-illumination heatmap (Feature A,
bugs/0179 + 0259–0262, phase 231) read **wrong** two ways:

1. *"within the detector orange square, it should show 2 dark edges and 2 uniform illumination edges.
   But this seems showing sym[m]etrical."* — the map looked dark on **all four** edges instead of 2
   dark (fold / X axis) + 2 uniform (perpendicular / Y axis).
2. *"why there is a big square with dark edges beyond the Image Circle?"* — the heatmap quad extended
   **past** the sensor / image circle.

Both are **one** root cause: the heatmap quad was drawn at **78 × 78 mm** (twice the sensor) instead
of the **39 × 39 mm** sensor. Because the imaged 39 × 39 FOV then filled only the central quarter of
the quad, its dark border went all the way around → the real fold-vs-perp asymmetry was buried under a
symmetric frame.

## Root cause

`source_illumination_map_extent` (`KrakenOS/UI/source_illumination_analysis.py`) chose the heatmap
window. For a detector in surface-local coordinates it returned the explicit rectangular active area
`(±½w, ±½h)` **but otherwise fell back to the round clear-aperture DIAMETER** (`±½·diameter`). The
folded return-path detector plane has a **78 mm** diameter (`2 × FOV`, sized as a generous catch
aperture) and — unlike the unfolded layout — declared **no** explicit active sensor. So the map spanned
`±39 mm`: a 78 mm square, exactly twice the 39 mm sensor.

This directly violates **bugs/0163**: a detector's round clear-aperture *diameter is not a sensor
size*. The orange sensor square (`scene_geometry.scene_target_has_explicit_sensor`) is drawn **only**
from explicit rectangular dims and pointedly does **not** fall back to the diameter — but the heatmap
extent did.

## Fix (two parts, physics + data)

* **Fix B — kill the diameter fallback** (`source_illumination_map_extent`). Only an explicit
  rectangular active area (both dims > 0) defines the window. With no explicit dims the extent now
  falls through to the illuminated **data footprint** (data min/max + 20 % pad) rather than the catch
  diameter, so an undeclared detector can never draw a square up to 2× the real sensor. This aligns the
  heatmap window with the same bugs/0163 rule the orange square already follows.
* **Fix A — declare the folded sensor** (`common_optical_layouts/machine_vision_150mm_coaxial_led_folded.py`).
  The return-path detector surface now carries `advanced.Detector = {active_width_mm: FOV_MM,
  active_height_mm: FOV_MM}` (39 × 39), mirroring the unfolded layout. Its **trace** diameter is
  unchanged (still `2 × FOV` — the wide catch aperture); this only sets the analysis / heatmap window,
  pinning the map to the `±19.5 mm` sensor the Monitor shows, so the fold dark edges land **at** the
  sensor edge.

Fix B is the universal safety net (any undeclared detector); Fix A is the specific declaration for the
scene the user flagged. Together the folded heatmap is the 39 × 39 sensor, and the two dark fold edges /
two uniform perp edges read correctly inside the orange square.

## Verification

Guard `validate_open3d_illumination_heatmap_extent` (phase **242**), display-free (pure numpy + one
headless trace, no VTK):

* **PURE** (`source_illumination_map_extent`) — an explicit 39 × 39 local sensor returns `±19.5`
  regardless of where the hits landed; a **diameter-only** detector (active dims 0, diameter 78) does
  **NOT** span `±39` (the catch aperture) but falls to the data footprint (`x∈[-10,11]` + 20 % pad →
  `[-14.2, 15.2]`); non-local (world) hit coords ignore the sensor window; a missing target model falls
  to the data footprint; deterministic.
* **LAYOUT** (static) — the folded coaxial detector declares `active_width/height = FOV_MM`, while its
  trace diameter stays the wider `2 × FOV` catch aperture (window ≠ aperture).
* **INTEGRATION** (clean coaxial-LED fixture, 8000 seeded rays) — the real overlay quad spans the
  39 × 39 sensor (half **18.3 mm** bin-centres), **not** the 78 mm catch diameter (half 39), and still
  reads the fold edge darker than the perpendicular edge (fold **0.787** < perp **1.234**).

Sibling regressions confirmed green after the edit: phase 231 `validate_open3d_source_illumination_overlay`
(fold 0.716 < perp 1.040), `validate_open3d_coaxial_led_dark_edges` (Fix-B path, fold 0.683 / perp 1.233),
and `validate_open3d_coaxial_led_folded` (edited layout, object footprint 56 × 79, 79 image-plane hits).
Baseline updated in place (242 → pass).

## Notes

* **In-app eyeball owed.** The headless **folded** module fixture cannot drive this overlay end-to-end:
  its scene bundle builds a swarm of synthetic per-branch detectors (all `trace_surface=None`) and no
  real `trace_surface`-keyed detector target, so the anchor resolves to a branch detector and
  `_compute_source_illumination_overlay_spec` returns `None` (no heatmap). In-app the anchor is the real
  detector surface (which produced the 78 mm quad the user saw), so the fix is validated at the extent
  **function** level (the true root cause) + the layout + the clean-fixture plumbing; the folded scene
  itself still owes a visual check in the running app.
* Sibling **"beyond the box"** symptom, different feature: `bugs/pixel-grid-beyond-detector-box.md`
  clipped the camera *pixel-grid* overlay (a magnified pixel lattice) to the sensor box. Same
  don't-draw-past-the-sensor principle, unrelated code path.
