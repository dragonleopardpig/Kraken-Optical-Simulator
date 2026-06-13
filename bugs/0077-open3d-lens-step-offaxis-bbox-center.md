# 0077 — Open 3D: imaging-lens STEP glued off the optical axis (bbox centring vs. cylinder axis)

## Symptom (user's words)

> the Imaging Lens is glued, but not centered to the optical axis, you can see
> the offset from the surrogate lens.

`attachment/3D.png` (axial view): the imported Imaging-Lens STEP barrel rings and
the surrogate-lens circles are **not concentric** — the lens STEP sits at the
right axial station but is shifted laterally off the optical axis, with a small
mount tab / connector visible on one side.

## Root cause

`_cad_mesh_aligned_to_optical_axis` centred every imported STEP overlay on its
mesh **bounding-box midpoint** (`0.5 * (min + max)` in the transverse plane,
`layout_polyline_display.py`). That is correct only for a body whose silhouette is
laterally symmetric. A real lens barrel carries a one-sided **mount / flange /
connector**, so the bbox extends further on that side and its midpoint is pulled
toward the tab — placing the optical barrel off-axis from the surrogate.

`_step_primary_cylinder_axis` already extracted the lens cylinder **direction**
(`cylinder.Axis().Direction()`) to orient the overlay, but threw away
`cylinder.Axis().Location()` — the point that actually lies **on** the optical
axis. So the alignment knew which way the lens pointed but not where its axis sat
laterally, and fell back to the skewed bbox midpoint.

## Fix

Use the CAD's own axis geometry for the lateral centre instead of the bounding
box:

1. `_step_primary_cylinder_axis_frame` (refactored from
   `_step_primary_cylinder_axis`) now also collects each cylindrical face's
   `Axis().Location()` and returns a **radius-weighted point on the dominant
   cylinder axis** (the big barrel outvotes any small off-axis bore — a screw
   hole, a mount pin). Collinear cylinders (barrel inner/outer, etc.) share one
   axis line, so their locations all project to the same transverse centre.
   `_step_primary_cylinder_axis_point` exposes it; the disk axis-cache JSON gains
   an `axis_point` field (old caches without it are recomputed).
2. `_cad_mesh_aligned_to_optical_axis` takes `optical_axis_point_xyz`; in the
   vector-axis branch it projects that point into the transverse plane and uses
   it as `transverse_center` instead of the bbox midpoint.
3. The lens **display** path (`_transformed_imported_lens_step_mesh`) passes the
   axis point — gated on `_step_overlay_resize_active("lens")` being false, since
   the point is in the STEP-native frame and a resize scales the mesh into a
   different frame (resize → bbox fallback, no regression).
4. The **promotion / export** affine (`_step_export_alignment_params` +
   `_step_alignment_affine`) passes it too, so a promoted lens stays centred. That
   path aligns the raw (un-resized) mesh, so the native point is always
   consistent there.

Camera / LED / generic-optical overlays use a `"z"` (non-vector) source axis and
pass no point, so their bbox centring is byte-for-byte unchanged.

## Test

`KrakenOS/UI/validate_open3d_lens_step_centered_on_axis.py` (display-free):

- **A** — a synthetic lens barrel centred on the axis plus a one-sided +x mount
  tab. With the CAD axis point the barrel centroid lands on `(0, 0)` (the fix);
  with bbox centring it is pushed `4 mm` off-axis toward the tab (the bug,
  fail-before). The axial front datum is unchanged either way.
- **B** (skip-if-absent) — the real OCC extraction on an imported lens STEP
  returns a finite on-axis point and a unit axis direction. On
  `1072517_00165969_001.stp` the axis runs along X at native `x ≈ -169.78`
  (`y, z ≈ 0`), exactly the kind of offset the bbox midpoint misses.

## Status: FIXED — pending in-app visual confirmation

Headless VTK renders of this layout SIGSEGV on Xvfb llvmpipe, so the concentric
overlay is verified in-app: re-import the Imaging Lens and confirm its rings are
now concentric with the surrogate circles in `attachment/3D.png`.

## Follow-on — "Glue to Surrogate" action (user: automatic + right-click; snap to a clicked LED face)

The auto-centring above happens on import. To also make it **re-invokable** (the
user asked for glue to be automatic *and* on the right-click menu), and to support
the **beam-splitter↔LED** ask (snap to a face the user clicks on the LED STEP):

- `ScenePlacementMixin.glue_step_overlay_to_surrogate(label)` re-applies the
  automatic placement by **clearing the manual drag offsets**
  (`<label>_step_axis_offset_xy` + `_step_placement_offset_xyz`) — so a lens
  re-centres on its cylinder axis, the camera sensor returns to the Image plane,
  the LED to its object station. Orientation/resize preserved; no-op when already
  glued. Wrapped by `Kraken3DInspector.glue_selected_step_to_surrogate`.
- Menu wiring: **"Glue STEP to Surrogate"** on the CAD/target dropdown and the
  canvas right-click STEP menu; plus a one-click **"Snap Picked Face → Optical
  Axis"** on the right-click menu that snaps the already-picked face's
  centre+normal onto the nearest optical axis (delegates to the tested
  `snap_step_feature_normal_to_optical_axis`, `axis_frame=None`) — i.e. right-click
  the beam-splitter face on the LED STEP and it glues to the axis.
- Guard `validate_open3d_glue_step_to_surrogate` (display-free, penta Phase 77):
  re-glue clears offsets, clean overlay is a no-op, per-label isolation, unknown
  label rejected. The menu wiring + the right-click snap are verified in-app
  (headless SIGSEGV).
