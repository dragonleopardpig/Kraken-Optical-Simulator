# 0188 — BUG: in the folded RA-mirror scene the image/sensor detector-coverage overlay draws on the UNFOLDED +Z axis (a stray faint plane far from the folded image)

**Status: RESOLVED (source-level, superseding the first coverage-overlay-only patch). The
scene detector TARGET itself now folds onto the reflected +X branch at the bundle source, so
ALL THREE consumers that read its world pose — the 3-D detector footprint actor, the 2-D
footprint projection, and the detector-coverage overlay (image circle / sensor square / labels /
pickable fill) — draw on the folded sensor from one shared pose. The ray TRACE (bugs/0187) and
the image SURFACE disc were already correct; these were display-only overlays that never folded.**

## Follow-up flags — the first (overlay-only) fix was insufficient

The first fix (commit `f505d1ad`) folded ONLY the coverage overlay's local `img_pt`/`image_axis`
inside `DetectorCoverageOverlayService.add_overlays`. After relaunch the user re-flagged twice on
2026-07-01:

- `attachment/recorded_bug_repros/flag_20260701_074930_725/` — *"Image circle shifted to correct
  axis, but the detector still in original wrong axis."*
- `attachment/recorded_bug_repros/flag_20260701_075019_938/` — *"the reflection still follow the
  fainted line normal to the hypotenuse."*

Row-8 actor bounds moved from `[-16.29, 287.82, -16.29, 16.29, 55.6, 347.2]` to
`[-11.52, 287.82, -16.29, 16.29, 55.61, 347.22]` — the X-min shifted (the folded overlay circle)
but **Z-max was STILL 347.22**. The residual half-extent 11.52 ≈ 16.29/√2 is the inscribed-sensor
square the coverage overlay draws. The overlay-only fold was a band-aid on ONE of three consumers;
the detector TARGET (`center_world`/`normal_world`/`tangent_world`) stayed on the unfolded +Z axis,
so every consumer that reads the target directly — chiefly the footprint actor
(`three_d_scene_tools._scene_detector_overlay_specs` → `scene_target_active_footprint_polylines`)
and the coverage overlay's own sensor square (which re-reads the target, not `img_pt`) — kept
drawing at (0, 0, 347.22). The correct fix folds the shared target ONCE at the source.

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

## Fix (source-level — the shared target folds once, all consumers follow)

`KrakenOS/UI/services/layout_scene_bundle_display.py` —
`LayoutSceneBundleDisplayMixin._fold_promoted_mirror_table_row_targets(bundle)` +
`_fold_table_row_target_world_pose(target)`. `_build_scene_bundle` calls the former on the
**single-axis path** (the `else` of the two-arm `fold_targets` replacement), folding each
`target_source == "table_row"` target's `center_world`/`normal_world`/`tangent_world` in place
with the SAME rigid fold the lens/camera STEP overlays use:

```
F = self._optical_axis_fold_world_transform_for_row(target.row_index)   # bugs/0185
center  = F @ [center, 1]
normal  = F[:3,:3] @ normal
tangent = F[:3,:3] @ tangent
```

`F(v) = C + R·(v − S)` maps the straight anchor S = (0, 0, 347.218) to the folded centre
C = (287.82, 0, 71.90) and rotates +Z → +X. Because the fold lands on the ONE `SceneTarget3D`
object held in `bundle.targets`, every consumer that reads it draws on the folded sensor:

- the 3-D detector footprint actor — `three_d_scene_tools._scene_detector_overlay_specs` →
  `scene_target_active_footprint_polylines` (the residual +Z actor the follow-up flags saw);
- the 2-D footprint projection — `scene_projector._project_detector_footprints`;
- the detector-coverage overlay — `detector_coverage_overlay.add_overlays` (image circle / sensor
  square / labels / pickable fill), which now reads the folded `center_world`/`normal_world`
  directly (the band-aid `_fold_table_row_detector_frame` was **removed** to avoid a double-fold).

On the AZ85 scene the fold moves **2** table-row targets: the Aperture (row 5) and the Image
detector (row 8) — both are genuinely downstream of the mirror on the +X branch. The Object
reference (row 0) has no fold override (`transform is None`) and stays on the entry axis.

Scope guards keep every other scene byte-identical:

- runs only on the single-axis path — a BRANCH detector (beam-splitter two-arm fold) is replaced
  upstream with its own per-arm folded centre (`two_arm_display_fold`), so it never reaches this
  branch (no double-fold);
- `_optical_axis_fold_world_transform_for_row` returns `None` unless the row has a promoted
  optical-solid output-port pose override, so unfolded and plain sequential-mirror layouts are
  untouched (verified 0 targets folded on `flat_mirror_45_deg.py`).

The `axis_dets` best-focus image-plane marker block (single-axis, X≈0, Y≈0) stays inert here:
`_paraxial_image_plane_z()` returns `None` for a scene with a 3-D promoted solid (the cube defeats
the centred-refractive paraxial solve — same as bugs/0173), so it never draws a +Z circle.

## Guard

`KrakenOS/UI/validate_open3d_ra_mirror_detector_coverage_folds.py` (standalone, NOT penta) — now
binds the REAL bundle-source fold helper + the REAL footprint polyline builder:

1. AZ85 image detector is unfolded at (0, 0, ~347.22) +Z as `build_scene_targets` emits it;
2. `_fold_promoted_mirror_table_row_targets` carries the shared target to X ≈ +287.82, Z ≈ 71.9,
   normal +X, with the in-plane basis in the Y-Z plane (the coverage disc is square to +X);
3. **the detector FOOTPRINT built from the folded target lands on +X, not the +Z axis** — this
   binds the consumer the overlay-only fix missed (a test sensor is applied because the AZ85
   detector has no explicit sensor of its own);
4. the folded detector centre coincides (≤1 mm) with the real mesh image surface;
5. a non-folded sequential-mirror layout (`flat_mirror_45_deg.py`) is left byte-identical (the
   fold helper reports 0 folded, target unchanged).

Sibling AZ85 guards (0185 fold-follows-reflection, 0186 launch-is-cone, 0187 folded-sequential
trace) + `validate_detector_coverage` + `validate_detector_overlay_vendor_sensor` +
`validate_machine_vision_azure_85_ra_mirror` all still PASS. (`validate_two_arm_display_fold`
fails on a PRE-EXISTING tkinter `__getattr__` RecursionError during the trace, before bundle
build — unrelated to this change; confirmed identical with the fix stashed out.)

## In-app eyeball owed

The detector footprint + coverage overlay are VTK-only 3-D overlays (not part of the 2-D
projectable scene_bundle), so they can only be eyeballed in the live 3-D view — headless VTK
rendering of this scene is segfault-prone. The geometry is proven display-free (the folded
detector target coincides exactly with the correct mesh image surface, and a footprint built from
it lands on +X). The user should fully quit + relaunch, confirm the faint +Z plane / detector is
gone (the image circle, sensor square AND the orange detector footprint now sit on the +X sensor),
and re-flag if not.
