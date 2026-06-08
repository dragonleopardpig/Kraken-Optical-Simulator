# 0033 — Coverage overlay on load: auto-fill without reselecting the camera, label the rings, drop the competing clear-aperture disks

**Status:** Fixed (2026-06-08).
**Component:** layout load / camera coverage auto-fill
(`KrakenOS/UI/services/layout_table_workbench.py`), detector coverage overlay
labels (`KrakenOS/UI/services/detector_coverage_overlay.py`), Open 3D scene
refresh (`KrakenOS/UI/services/open3d_scene_refresh.py`).
**Reported via:** two in-app bug recorder bundles on the machine-vision 150 mm
measured layout with the `Allied Vision hr25MCX` camera:
- `attachment/recorded_bug_repros/flag_20260608_103346_251/` — *"why the cyan
  image circle is still within the sensor? What is that dotted line circle
  means?"*
- `attachment/recorded_bug_repros/flag_20260608_103444_078/` — *"the object cyan
  circle is less than the FOV green box?"*

This is the direct follow-on to bug 0032, which added the real ray-traced image
circle, the object FOV rectangle, and a **camera-select** auto-fill. The user
exercised it by *loading* the saved layout rather than re-picking the camera, and
hit three rough edges.

## Diagnosis

**(251 — image circle still inside the sensor.)** Bug 0032's auto-fill fired only
from `_on_camera_model_changed`, i.e. an interactive camera pick. A full layout
**load** restores the saved camera by setting `camera_model_var` directly (no
widget commit, see `layout_settings._apply_layout_settings`), so the auto-fill
never ran. The saved layout still carries the stale non-covering field
(`Real Image Height = 11.52`), so on load the image circle stayed **inside** the
sensor and the amber dashed *required* ring (sensor half-diagonal, Ø32.58) showed
the gap. That dashed ring is exactly the "dotted line circle" the user couldn't
identify — it had no label. The user's own words elsewhere: *"I have to reselect
the camera after loading the machine vision lens in order to get it right."*

**(078 — object cyan circle smaller than the green FOV box.)** On the object
plane two unrelated things were drawn at once: the green coverage **FOV
rectangle** (`sensor / |m|`, the real mapped field) and the generic object-row
**clear-aperture disk** (a cyan ring at the Object surface's `diameter/2`). They
mean different things and don't match, so a cyan ring sitting inside the green box
read as a contradiction. The same competing disk on the image side is the cyan
ring bug 0032 already explained as the surface clear aperture rather than a
coverage indicator.

## Fix

Three changes, all gated on the existing **"Det"** overlay toggle so nothing
changes when coverage overlays are off.

**(a) Auto-fill on load — no reselect, no hardcoding.**
`layout_table_workbench.load_layout_by_name` now re-applies
`_apply_camera_coverage_autofill(loaded_camera)` after the table syncs, unless
appending into an existing scene or the layout has no camera
(`CAMERA_NONE_LABEL`). The value is **computed** from the vendor sensor
(`camera_image_coverage_mm` → diagonal / half-diagonal), not read from the saved
layout, so every machine-vision layout lands in the covered state out of the box
and the stale saved `field_value` is irrelevant. This answers the user's "make it
auto compute without hard coded" directly — the saved 11.52 is overridden by the
half-diagonal 16.29 on load.

**(b) Direct 3D labels on every coverage element.**
`detector_coverage_overlay.detector_coverage_label_specs(...)` emits pure-geometry
`{text, anchor, color}` specs anchored just outside each ring at widely separated
clock angles so labels never overlap each other or the geometry: `Sensor W×H`
(35°), `Image circle ØD` / `… (short)` (150°), `Needs ØD` for the dashed required
ring (275°, only when short), and the object-plane `FOV W×H` (90°, finite object
only). `DetectorCoverageOverlayService._label_actor` renders each as a
`vtkBillboardTextActor3D`. The "Needs Ø32.6" label now names the previously
mysterious dotted ring.

**(c) Suppress the competing clear-aperture disks while Det is on.**
`open3d_scene_refresh` sets `suppress_reference_aperture = detector_overlays_on
and row_surface in {"Object", "Image"}`; when true it forces the row body opacity
to 0 and skips the rim/edge clear-aperture geometry. With the overlay on, the
object plane shows only the green FOV rectangle and the image plane only the real
image circle (+ required ring when short), so there is no second cyan ring to
contradict them.

## Tests

`KrakenOS/UI/validate_detector_coverage.py` (display-free) extended to assert the
label specs: a short configuration emits the `Sensor`, `Image circle … (short)`
and `Needs Ø…` labels with the right colors and non-overlapping anchors, a
covering configuration drops the `Needs` label, and the object FOV label appears
only for a finite object. It also guards `_apply_camera_coverage_autofill` is
callable so the load-time wiring can't silently break.

Folded into the comprehensive harness as **Phase 39**
(`phase_39_detector_coverage_live`): on the real machine-vision layout it loads
the layout (verifying the camera-restore auto-fill lands the covered state),
forces reference surfaces on, and toggles the Det overlay. Turning it on must
drop the Object/Image **clear-aperture disk** opacity to ~0 while leaving the
overlay's own filled sensor square in place, and must raise the billboard label
count. To target the disk and not the sensor square (both are Surface actors on
the Image row), the scene refresh tags the disk body
`_kraken_reference_aperture_disk`, and the phase reads only tagged actors via
`_reference_aperture_disk_max_opacity` (plus `_billboard_label_count`).

The bug is fundamentally about *which geometry is drawn*, so the visuals were
verified live on a real display. The headless harness instead inspects the
*built* scene's actor properties: live-painting a freshly-swapped scene into the
embedded Tk render window segfaults on software GL (Xvfb/llvmpipe) even though
the same layout renders fine from scratch and on a real GPU, so the phase no-ops
`inspector.render` for its two refreshes — every property bug-0033 changes is set
during the scene build, before the final paint.
