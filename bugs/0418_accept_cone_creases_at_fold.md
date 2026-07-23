# 0418 — Accept-cone overlay must CREASE at the fold (0416 follow-up)

**Flag `flag_20260723_083109_099`** (AZ85 RA-mirror scene, build `52b811be` — which *has* 0416):
> "Acceptance Cone is not folding."

## Why 0416 was wrong

0416 made `_add_receiving_cone_overlays` fold the cone onto the imaging arm with the lens STEP overlay's
rigid transform — applied to the **whole mesh**. That's right for a compact overlay (the lens barrel sits
entirely on the lens leg) but wrong for the cone, which **spans the fold**: it runs from the FOV at the
object plane, up the object leg, to the entrance pupil past the mirror. Folding every point rigidly onto
the lens leg swung the object end onto the lens leg too, so the whole cone lay flat along it — "not
folding."

The folded axis for this scene (from the flag's `optical_axis_records`, world coords) makes it concrete:

```
object leg : [0,0,-293.4] -> [0,0,53]     (along world Z, the object/FOV is up here)
lens leg   : [0,0,53]     -> [235.9,0,53]  (along world X, the RA-mirror fold at z=53)
```

The FOV ring belongs on the **object leg** (world Z, up); only the pupil end is past the mirror on the
**lens leg** (world X).

## Fix — crease at the fold hinge

New `Kraken3DInspector._crease_overlay_mesh_at_fold(mesh, fold_transform)`: fold **only the points
downstream of the fold hinge** onto the reflected leg; leave the upstream points in the base object-leg
frame. The hinge is the fold transform's **fixed point** on the straight axis — `F(a) = a` ⇒
`(I − R)·a = t` — solved by least squares; points with straight-z past `hinge_z` get the rigid fold
`R·p + t`, the rest stay put. So the cone goes up the object leg **and** bends onto the lens leg, hinged
at the mirror. `fold_transform` `None` (unfolded scene) → mesh returned unchanged (no regression). The
loft faces spanning the hinge are left as a direct skin (a translucent cone reads fine without an
inserted crease ring).

`_add_receiving_cone_overlays` now calls `_crease_overlay_mesh_at_fold` instead of the 0416 whole-mesh
`_mesh_with_world_transform`, with the same lens front-datum anchor.

## Verification (`validate_open3d_accept_cone_fold_aware`, penta phase 339)

Display-free:

| check | asserts |
|---|---|
| MECHANISM | `_add_receiving_cone_overlays` creases via `_crease_overlay_mesh_at_fold`; the old whole-mesh fold is gone |
| CREASE-MATH | on a real cone straddling a Z→X hinge at z=53, the upstream FOV ring is left put while the downstream pupil ring folds onto the leg (centre (0,0,100) → (47,0,53)); a `None` transform is a no-op |

2/2 pass. Baseline phase 339 = pass (retitled "creases at the display fold").

## Files

- `KrakenOS/UI/open3d_inspector.py` — `_crease_overlay_mesh_at_fold` + `_add_receiving_cone_overlays` uses it.
- `KrakenOS/UI/validate_open3d_accept_cone_fold_aware.py` — guard updated to the crease.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` + `tools/penta_validator_baseline.json` — phase 339.

## In-app eyeball still owed

Folded geometry can't render headless. On the AZ85 RA-mirror scene, toggle **Accept cone** → the cone
should now go **up the object leg toward the FOV** and **bend onto the lens leg** at the RA mirror, not
lie flat along either one. (If a sharp crease line at the mirror is wanted rather than a smooth skin, that
needs an inserted crossing ring — a further refinement.)
