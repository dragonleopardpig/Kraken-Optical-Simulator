# 0072 — Open 3D: the shaded FOV fill doesn't match its own green edge

## Symptom (user's words)

From the in-app bug recorder, `attachment/recorded_bug_repros/flag_20260612_150213_377`
(the `FOV 28.9×21.6` object plane, the M42 65 MP Bopixel sensor):

> the shaded light rectangle not matching the green edge.

After bug 0069 the green object-FOV **edge** drew correctly landscape (long side
horizontal), but the faint **shaded fill** behind it stayed portrait — rotated
90° from its own outline. The fill poked past the green edge top and bottom and
fell short left and right.

## Root cause

0069 was incomplete: it fixed the three *line* producers (the green object-FOV
edge, the orange sensor footprint, the yellow QE rect) but missed a **fourth**
in-plane rectangle — the faint, filled, *pickable* quad that
`DetectorCoverageOverlayService._pick_fill_actor` adds at the Object/Image planes
(bugs/0056, so the FOV plane can be hover-highlighted and double-clicked).

That fill built its corners with `_rect_points(c, u, v, half_w, half_h)`, and
`_basis(axis=+Z)` returns `u = +Y` (vertical) — so width (`half_w`, scaled along
the first axis `u`) landed on the vertical, exactly the transposition 0069 fixed
everywhere else. The green edge had moved to width → `v` (horizontal); the fill
had not, so the two no longer coincided.

(The Image-plane fill is a square — `half_w == half_h` — so it was unaffected;
only the non-square Object-plane FOV fill visibly disagreed with its edge.)

## Fix (display-only — the optical solve is untouched)

A new shared corner helper makes the fill build with the *same* orientation as
the green edge:

`KrakenOS/UI/services/detector_coverage_overlay.py`:

* `pick_fill_rect_points(center, u, v, half_w, half_h)` — returns the 4 corners
  via `_rect_points(center, v, u, half_w, half_h)[:4]`, i.e. width → `v`
  (horizontal), height → `u` (vertical), exactly matching
  `detector_coverage_overlay_specs`' green `object_fov_rect`.
* `_pick_fill_actor` now calls `pick_fill_rect_points(...)` instead of the inline
  transposed `_rect_points(c, u, v, ...)`. Its docstring no longer claims the
  fill is "square" (it tracks the sensor aspect now).

## Test (fails before, passes after)

`KrakenOS/UI/validate_open3d_fov_rect_orientation.py` (the 0069 guard) gained a
**Section D** (display-free, portable):

* **D1** (behavioral) — on the landscape fixture (FOV 60 × 40) the
  `pick_fill_rect_points` corners are `np.allclose` to the green `object_fov_rect`
  corners — the fill coincides with the edge.
* **D2** — the fill reads landscape (`ptpX > ptpY`).
* **D3 / D4** (source wiring) — `_pick_fill_actor` builds via
  `pick_fill_rect_points` and no longer maps width → `u` inline
  (`"corners = _rect_points("` absent — anchored to avoid the
  `pick_fill_rect_points` substring trap).

Reverting the helper to `_rect_points(center, u, v, ...)` flips D1 (corners no
longer coincide) and D2 (fill reads 40 × 60 portrait); reverting `_pick_fill_actor`
to the inline call flips D3/D4.

## Integrated

No new phase: **Phase 74** of `validate_open3d_penta_telescope_comprehensive.py`
already wraps this guard, so the four new checks ride along (it records
`len(notes)`, 11 → 15, with no hardcoded count). The baseline phase count is
unchanged (still 76 phases, 0–75); `tools/penta_validator_baseline.json` needs no
edit.

## Verification note

The display-free guard pins that the fill and the edge share one corner set. The
live render of this machine-vision layout can't be confirmed headless (it
SIGSEGVs the offscreen Xvfb llvmpipe renderer); the user confirms the shaded fill
now sits under its green edge in-app.
