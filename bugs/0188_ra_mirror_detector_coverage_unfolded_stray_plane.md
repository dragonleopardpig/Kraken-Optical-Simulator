# 0188 — BUG: in the folded RA-mirror scene the image/sensor detector-coverage overlay draws on the UNFOLDED +Z axis (a stray faint plane far from the folded image)

**Status: RESOLVED. The image detector-coverage overlay (image circle / sensor square / labels +
the pickable fill) now folds onto the reflected +X branch with the same rigid transform the
lens/camera STEP overlays use. The ray TRACE (bugs/0187) and the image SURFACE disc were already
correct; this was a display-only overlay that never folded.**

## Flag

`attachment/recorded_bug_repros/flag_20260630_212049_339/` on the folded AZURE ELS-85 layout
(`KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py`):

> "still the same."

This was logged AFTER the user relaunched with bugs/0187 fix (3) + the diagnostic commit
`056973a`, so the new flag fields prove the trace is now correct:

- `actual_trace_backend: Scalar TraceLoop`  (folded-sequential engaged, NOT NsTraceLoop)
- `folded_sequential_engaged: true`
- the traced chief ray segment runs along +X at Z = 71.897 (the folded path)

…yet the user still reported "still the same." The tell was in `row_actor_bounds["8"]` (the Image
row): a 45-degree diagonal

```
[-16.291740, 287.820892, -16.291740, 16.291740, 55.605399, 347.218037]
```

i.e. X ∈ [-16.29, 287.82], Y ∈ [-16.29, 16.29], Z ∈ [55.6, 347.2]. The user described it across
three flags: *"the rays are separated into 3 sections, reflected by its own even not touching the
surface"*, *"there is a faint line, reflected from there!"*, *"the reflection from the faint line
is wrong direction. the faint line is at perpendicular direction with the hypotenuse surface."*

## Root cause — measured headlessly, not eyeballed

The row-8 actor-bounds union is two actors:

1. the **image surface disc** — correctly folded to world (287.82, 0, 71.90), normal +X
   (`_surface_reference_world_point(8, system)` reads the mesh system, which bugs/0185 folds);
2. the **detector-coverage pickable fill** (+ the image circle / sensor / labels it sits with) —
   at the UNFOLDED world (0, 0, **347.218**), normal **+Z**.

`347.218` is exactly the row-8 bounds Z-max. The detectors come from
`scene_builder.build_scene_targets(editor.rows)`, whose `_scene_target_frame` places each target
at `(desp_x, desp_y, cumulative_thickness)` along the straight +Z axis — it has no knowledge of
the bugs/0185 fold (which lives in the optical-solid output-port pose overrides / the mesh system,
not in `editor.rows`). So the table-row Image detector lands on the straight axis at Z = 347.218
while the folded image is at X = 287.82, Z = 71.9. The coverage overlay drawn there is the "faint
line": a thin (±16.29 in Y) plane whose bounding box, unioned with the folded disc, reads as a 45°
diagonal from ≈(-16, 0, 55.6) to ≈(288, 0, 347.2).

Verified with `build_scene_targets` on the live editor:

```
detector target  is_detector=True  row_index=8  target_source=table_row
    center_world = (0, 0, 347.218)   normal_world = (0, 0, 1)
```

vs. the actual mesh image surface `_surface_reference_world_point(8) = (287.82, 0, 71.90)`,
normal `(1, 0, 0)`.

## Fix

`KrakenOS/UI/services/detector_coverage_overlay.py` —
`DetectorCoverageOverlayService._fold_table_row_detector_frame(target, img_pt, image_axis)`. In
`add_overlays`, right after reading `img_pt`/`image_axis` from the target, carry a plain
**table-row** image detector onto the reflected branch with the SAME rigid fold the lens/camera
STEP overlays use:

```
F = editor._optical_axis_fold_world_transform_for_row(target.row_index)   # bugs/0185
img_pt    = F @ [img_pt, 1]
image_axis = F[:3,:3] @ image_axis
```

`F(v) = C + R·(v − S)` maps the straight anchor S = (0, 0, 347.218) to the folded centre
C = (287.82, 0, 71.90) and rotates +Z → +X, so the image circle, sensor square, required-ring,
labels and the pickable fill all draw in the Y-Z plane at X = 287.82, coinciding with the image
disc.

Scope guards keep every other scene byte-identical:

- only `metadata.target_source == "table_row"` targets fold — a BRANCH detector (beam-splitter
  two-arm fold) already sits on its own per-arm folded centre (`two_arm_display_fold`), so it is
  left alone (no double-fold);
- `_optical_axis_fold_world_transform_for_row` returns `None` unless the row has a promoted
  optical-solid output-port pose override, so unfolded and plain sequential-mirror layouts are
  untouched.

The `axis_dets` best-focus image-plane marker block (single-axis, X≈0, Y≈0) stays inert here:
`_paraxial_image_plane_z()` returns `None` for a scene with a 3-D promoted solid (the cube defeats
the centred-refractive paraxial solve — same as bugs/0173), so it never draws a +Z circle.

## Guard

`KrakenOS/UI/validate_open3d_ra_mirror_detector_coverage_folds.py` (standalone, NOT penta):

1. AZ85 image detector is unfolded at (0, 0, ~347.22) +Z as `build_scene_targets` emits it;
2. the fold helper carries it to X ≈ +287.82, Z ≈ 71.9, normal +X, with the in-plane basis in the
   Y-Z plane (the coverage disc is square to +X);
3. the folded detector centre coincides (≤1 mm) with the real mesh image surface;
4. a non-folded sequential-mirror layout (`flat_mirror_45_deg.py`) is left byte-identical (the
   fold helper no-ops).

Sibling AZ85 guards (0185 fold-follows-reflection, 0186 launch-is-cone, 0187 folded-sequential
trace) + `validate_detector_coverage` still PASS.

## In-app eyeball owed

The detector-coverage overlay is a VTK-only 3-D overlay (not part of the 2-D projectable
scene_bundle), so it can only be eyeballed in the live 3-D view — headless VTK rendering of this
scene is segfault-prone. The geometry is proven display-free (the folded detector coincides
exactly with the correct mesh image surface). The user should fully quit + relaunch, confirm the
faint +Z plane is gone (the image circle / sensor square now sit on the +X sensor), and re-flag if
not.
