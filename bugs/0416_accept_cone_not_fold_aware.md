# 0416 — "Accept cone" overlay is not fold aware

**Flag `flag_20260723_073901_461`** (build `1ed19858`, AZ85 RA-mirror scene, 0703 lens swapped in):
> "Acceptance Cone overlay is not fold aware."

The imaging lens's receiving-angle cone (the "Accept cone" toggle, `show_receiving_cone_var`, bugs/0354)
shot straight **down the unfolded optical axis** — a big pale cone hanging off the object box — while the
real optics fold at the RA mirror and run horizontally to the lens/beam-splitter.

## Root cause

`build_receiving_cone_overlay` builds the cone on the **straight sequential object-space axis**: the
imaged-FOV rectangle at `object_z` lofted to the entrance-pupil disc at `pupil_z`, all as `(x, y, z)` in
the unfolded system frame. `_add_receiving_cone_overlays` then drew those points **directly**
(`pv.PolyData(points, faces)`) with no display-fold transform — so on a folded scene the cone stayed on
the unfolded axis. Its sibling illumination-volume overlay (bugs/0355) was already fold aware; this one
was the odd one out.

## Fix — fold it onto the imaging arm, exactly like the lens STEP overlay

The Accept cone is a straight-sequential object-space construct that belongs to the imaging arm — the
same arm the lens STEP overlay rides. So it gets the **same rigid fold**: in
`_add_receiving_cone_overlays`, after building the mesh,

```python
fold_transform = self.editor._optical_axis_fold_world_transform_for_row(
    self.editor._lens_front_datum_row_index()
)
mesh = self.editor._mesh_with_world_transform(mesh, fold_transform)
```

`_optical_axis_fold_world_transform_for_row` returns the rigid `F(v) = C + R·(v − S)` that carries the
straight axis onto the lens row's folded pose (via `optical_solid_output_port_pose_overrides`), and
`_mesh_with_world_transform` applies it. Anchoring on the **same lens front-datum row** as the lens STEP
overlay keeps the cone and the lens barrel coherent on the folded leg. On an unfolded layout the transform
is `None` → the mesh is unchanged, so straight scenes are untouched (no regression).

This is the two-arm display-fold philosophy (trace straight & sequential, fold the display rigidly per
arm), consistent with how every other overlay on the imaging arm is placed.

## Verification (`validate_open3d_accept_cone_fold_aware`, penta phase 339)

Display-free:

| check | asserts |
|---|---|
| MECHANISM | `_add_receiving_cone_overlays` folds the mesh via `_optical_axis_fold_world_transform_for_row(_lens_front_datum_row_index())` + `_mesh_with_world_transform` |
| FOLD-MATH | on a real cone mesh, the shared `_mesh_with_world_transform` maps the pupil ring by the rigid transform (centre → R·centre + t), and a `None` transform leaves the mesh untouched |

2/2 pass. Baseline records phase 339 = pass.

## Files

- `KrakenOS/UI/open3d_inspector.py` — `_add_receiving_cone_overlays` applies the lens-row fold.
- `KrakenOS/UI/validate_open3d_accept_cone_fold_aware.py` — guard (phase 339).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — register phase 339.
- `tools/penta_validator_baseline.json` — phase 339 = pass.

## In-app eyeball still owed

The folded geometry can't run headless (VTK segfaults under Xvfb; folded scenes don't populate via the
headless loader). On the AZ85 RA-mirror scene, toggle **Accept cone** → the cone now rides the folded
imaging leg with the lens barrel instead of hanging straight off the object box. Please confirm; if the
cone should CREASE at the mirror (piecewise) rather than fold rigidly onto the lens leg, that's a further
refinement — the rigid fold matches the lens/camera overlays and is the low-risk first cut.
