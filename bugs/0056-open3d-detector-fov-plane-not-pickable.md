# 0056 — Open 3D: detector-coverage FOV plane is not hover/double-click pickable

## Reported (in-app recorder)

Flag `flag_20260611_111656_853` (recorded 2026-06-11T11:16:56):

> still no hover highlight the FOV plane and can't double click select.

The recorded scene is the measured machine-vision 150 mm layout (hr25MCX camera,
sensor 23.04×23.04). The visible plane is the **green square** labelled
`FOV 23.0×23.0` sitting at the Object plane. User clarification:

> it should be square in this case.

i.e. the **square shape is correct** — do *not* change it to a circle. The bug is
purely that the square FOV plane is not pickable: no hover highlight, no
double-click to open the bugs/0055 FOV popup.

## Root cause

This is the same class as bugs/0055, but in a *different overlay service* than the
one the 0055 follow-up (commit `1dd4b9e`) patched.

- The visible `FOV 23.0×23.0` green square is drawn by
  **`DetectorCoverageOverlayService`** (`services/detector_coverage_overlay.py`)
  as its `object_fov_rect` — a **line actor** (`_line_actor`), which has no fill
  and is not registered for picking.
- An actor is pickable only when `_add_mesh_actor(...)` is called with a `pick_*`
  argument (it populates `_actor_row_map`, which the hover/double-click picker
  reads); with no `pick_*` arg `_add_mesh_actor` calls `PickableOff()`. Line
  actors never go through that path, so the FOV rectangle was never a pick target.
- Per bugs/0047, while the detector coverage overlay draws, the main surface loop
  **suppresses the Object/Image clear-aperture reference disk to opacity 0**
  (`suppress_reference_aperture` in `open3d_scene_refresh`). The Image plane stays
  pickable through the `_add_scene_detector_overlays` footprint, but the **Object
  plane gets no pickable actor** when "Det" is on and "Refs"/"QE" are off — which
  is exactly the recorded toggle state.
- The bugs/0055 follow-up added a faint pickable `pv.Disc` via the **Quick
  Estimation** overlay (`_pick_disk_actor`), but that is gated on QE being
  enabled. In this scene QE is off and Det is on, so no pick geometry was created
  — hence "still no hover highlight … can't double click."

## Fix

Give the detector-coverage overlay its own pickable geometry, so whenever the
green FOV square is visible the *whole plane* is a pick target — independent of
the QE / Refs toggles.

`DetectorCoverageOverlayService._pick_fill_actor(center, u, v, half_w, half_h,
color, row_index)` builds a filled quad (`pv.PolyData` with one 4-vertex face from
`_rect_points(...)[:4]`) and adds it via `_add_mesh_actor(..., opacity=0.08,
flat_shading=True, backface_culling=False, pick_row_index=int(row_index))`. The
faint fill matches the **square** FOV plane the user sees (kept square per the
clarification) and registers the row for hover + double-click.

`add_overlays` now places one such square on **both** planes, mapped to the same
rows the reference points use:

- Object plane → row `0`, sized to `object_fov_half_width/height` (finite object
  only), green `_OBJECT_FOV`.
- Image plane → terminal row `len(rows) - 1`, sized to
  `max(image_circle_radius, sensor_half_diagonal)`, cyan `_IMAGE_CIRCLE_COVERS`.

The fill is untagged (no `_kraken_reference_aperture_disk`), so the bugs/0047
disk-suppression and the Phase 39 `_reference_aperture_disk_max_opacity` guard
(which filters to that tag) are unaffected; it adds no billboard text, so the
label-count guard is unaffected too.

## Tests

- `validate_detector_coverage.py` item 7 (display-free): with real pyvista,
  `_pick_fill_actor` adds an actor carrying its `pick_row_index`, and the
  `add_overlays` source wires a fill on **both** planes (≥2 calls + the
  `len(rows) - 1` terminal-row mapping).
- Phase 61 in `validate_open3d_penta_telescope_comprehensive.py` (live): on the
  measured machine-vision layout with Det on, both the Object row (`0`) and the
  terminal Image row register in `_actor_row_map` so the planes hover/double-click.
- Phase 39 (detector coverage live) re-checked: still passes — the new fills are
  invisible to the disk-opacity and billboard-label guards.
