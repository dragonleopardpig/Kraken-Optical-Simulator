# 0104 — Object plane stays visible after a beam-splitter cube is promoted

**Flagged:** 2026-06-22 (recorded `flag_20260622_071429_544` "Missing object plane
after promotion", `flag_20260622_080859_497` "promoted, object plane missing").
Reported symptom: *the OBJECT PLANE disappears from the Open 3D view after the
beam-splitter cube is promoted in a finite-conjugate (machine-vision) scene.*

## The scene
MV 150mm 1X (finite-conjugate, machine-vision) with a **50 mm beam-splitter cube
BEFORE the single lens**. The TRANSMIT arm images through the 150 lens to the
camera; the REFLECT arm is a **BARE pickoff** — no lens, no aperture.

That is **ONE imaging arm**, so it is *not* a two-arm display fold. The detectors
are ray-tree **branch detectors** ("Branch detector (S1/transmit)", "…/reflect")
created by `derive_branch_detectors`, which carry **no `two_arm_magnification`**
metadata. (`build_two_arm_fold_parts` only fires when `_imaging_branch_leaves()`
finds ≥2 arms, each with its own Aperture + branch_selector — here there is one.)

## What "the object plane" is in this view
With the **Det** (detector-coverage) overlay ON, the row-0 clear-aperture reference
disk is suppressed to opacity 0, so the only thing drawn at the object plane (z≈0)
is the green **object-FOV rectangle** (color `(0.2, 0.9, 0.35)`). That rectangle is
`detector_coverage_metrics(...).object_fov_half_width`, which is `sensor_half /
|magnification|` — **and it is only > 0 when the magnification is finite & non-zero.**

## Root cause
With no `two_arm_magnification` on the branch detectors,
`DetectorCoverageOverlayService.add_overlays` falls back to the system magnification
`editor._current_finite_paraxial_magnification()`.

That method computed the principal-plane conjugate solve on the **raw rows**, only
straightening the layout (`_paraxial_reference_rows_for_layout`) when a folding
**Mirror** was present:

```python
if any(row.surface == "Mirror" for row in self.rows):
    solve_rows, _ = self._paraxial_reference_rows_for_layout(self.rows)
```

A **beam splitter** (and a promoted mesh solid) has no clean sequential paraxial
form, so `_exact_paraxial_solution_for_rows` **threw** on the splitter, the method
returned **None**, and the two-arm fallback found <2 imaging arms → still None.

`mag = None` → `object_fov_half_width == 0` → **the object-FOV rectangle (the visible
object plane) vanished** after the cube was promoted.

## Fix
Straighten the layout to its transmissive (straight-through) reference whenever
`_layout_needs_paraxial_reference()` is True — **Mirror OR beam splitter OR promoted
mesh solid** — not just for a Mirror. `_paraxial_reference_rows_for_layout` already
replaces a beam splitter / mesh solid with the transmissive flat-plate equivalent
(the straight-through transmit path), which every other first-order consumer
(quick-estimation, FOV tools) already uses. The single imaging arm's conjugate solve
then succeeds and yields the transmit arm's magnification (≈1X here).

`KrakenOS/UI/services/layout_scene_bundle_display.py`,
`_current_finite_paraxial_magnification`:

```python
if self._layout_needs_paraxial_reference(self.rows):
    solve_rows, _last_source_index = self._paraxial_reference_rows_for_layout(self.rows)
```

This is a net positive beyond the object plane: the same method feeds
quick-estimation, trace-preview sampling, and the layout-table workbench, all of
which previously got `None` (→ "--") for any beam-splitter / promoted-solid scene.

## Repro / test
- `bugs/diag_object_plane_overlays.py` — instruments the REAL
  `DetectorCoverageOverlayService.add_overlays` against the user's traced scene
  bundle and records every actor. Before: `mag=None`, 0 object-plane actors. After:
  `mag≈1.0`, 4 green actors at z=0 + "FOV 23.0×23.0" label.
- `.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_object_plane_after_promote`
  — display-free guard. Checks: (A) the beam-splitter single-imaging-arm scene now
  yields a finite, non-zero `_current_finite_paraxial_magnification()` and
  `_layout_needs_paraxial_reference()` is True; (B) that magnification makes
  `detector_coverage_metrics(...).object_fov_half_width > 0`; (C) a plain refractive
  MV 150 1X scene is unchanged (~1X) and a source check confirms the straightening is
  gated on `_layout_needs_paraxial_reference` (so it can't silently regress to
  mirror-only). Penta phase 90.

## Owed
In-app eyeball: headless VTK SIGSEGVs on the machine-vision render, so the visible
green object-FOV rectangle after a real cube promotion still wants a user confirm.
