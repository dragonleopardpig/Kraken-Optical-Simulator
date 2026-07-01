# 0193 — BUG: in the folded RA-mirror scene a row-backed scene PLACEMENT (aperture-stop reference grid) floats on the UNFOLDED +Z axis, not on the reflected +X branch

**Status: RESOLVED (source-level). The parallel scene PLACEMENT now folds onto the reflected +X
branch at the bundle source with the identical per-row rigid fold that bugs/0188 applies to the
detector TARGETS. bugs/0188 folded the targets but left the placements — built from the same
pre-fold targets — stranded on the straight axis.**

## Flag

The user re-flagged the folded AZ85 layout (`machine_vision_AZ85_RA_Mirror.py`) after bugs/0192
fixed the reflection ("the reflection finally correct"), listing four residual issues; two of them:

> "there still exist S2 overlay" · "one arrow wrong location"

A reference grid / marker stranded high on the straight +Z axis, above the folded optics, far from
where the mirror sends the beam.

## Root cause — measured headlessly

`scene_builder._build_scene_bundle` builds the placements right after the targets:

```
scene_targets    = build_scene_targets(rows, ...)          # unfolded +Z poses
scene_placements = build_scene_placements(rows, targets=scene_targets)   # copies those poses
```

`build_scene_placements` copies each row-backed placement's world pose straight from its target
(`center = target.center_world`, etc.). Both are on the straight cumulative-thickness +Z axis at
this point — the bugs/0185 fold lives in the mesh system / output-port overrides, not in
`editor.rows`. The DISPLAY layer then folds the targets in `_fold_promoted_mirror_table_row_targets`
(bugs/0188) but there was **no parallel fold for the placements**, so the aperture-stop placement
(row 5) kept the unfolded center and every consumer (the grid overlay, the drag gizmo) drew it
there.

Verified on the live AZ85 editor — only two placements exist, and exactly one is stranded:

```
row 1  optical_solid  center (0, 0, 71.90)     fold_override=none   # mirror pivot — CORRECT
row 5  scene_target   center (0, 0, 169.35)    fold_override=FOLD   # aperture grid — UNFOLDED
```

The row-5 aperture stop is genuinely downstream of the mirror; its detector TARGET already folds to
(109.95, 0, 71.90) on the +X arm (bugs/0188), but the placement grid stayed at (0, 0, 169.35).

## Fix (source-level — the placement folds with the same transform as its target)

`KrakenOS/UI/services/layout_scene_bundle_display.py` — new
`_fold_promoted_mirror_scene_placements(bundle)`, called in `_build_scene_bundle` on the single-axis
path immediately after `_fold_promoted_mirror_table_row_targets(bundle)`. It applies the SAME rigid
fold `_optical_axis_fold_world_transform_for_row(row_index)` to each placement's
`center_world`/`normal_world`/`tangent_world`:

```
F = self._optical_axis_fold_world_transform_for_row(placement.row_index)   # bugs/0185
center  = F @ [center, 1];  normal = F[:3,:3] @ normal;  tangent = F[:3,:3] @ tangent
```

On the AZ85 scene this folds **1** placement — the row-5 aperture grid — from (0, 0, 169.35) to
(109.95, 0, 71.90), coinciding exactly with its folded detector target. The mirror pivot (row 1)
has no fold override (`transform is None`) and stays byte-identical, as do plain / sequential-mirror
layouts (`_optical_axis_fold_world_transform_for_row` returns `None`).

## Guard

`KrakenOS/UI/validate_open3d_ra_mirror_placement_fold.py` (standalone, NOT penta) — binds the REAL
wired method inside `_build_preview_system_rays_bundle`:

1. BEFORE (method shadowed with a no-op): the row-5 scene_target placement floats unfolded at
   X≈0, Z>90 (the precondition — the guard is not vacuous);
2. AFTER (real method): that placement folds onto +X (X>40) at the mirror plane (Z≈71.9) and its
   center matches the row-5 folded detector target (consistency);
3. the mirror-pivot placement (row 1, no fold override) is byte-identical BEFORE/AFTER;
4. scope: the sequential `flat_mirror_45_deg.py` scene folds 0 placements (inert on non-promoted /
   plain-mirror layouts).

## In-app eyeball owed

The placement grid / drag gizmo are VTK-only 3-D overlays (headless VTK on this scene is
segfault-prone). The fold is proven display-free (the folded placement center coincides exactly with
the correct folded detector target). The user should quit + relaunch and confirm the stranded +Z
reference grid is gone (it now sits on the +X aperture stop with the rest of the folded optics).
