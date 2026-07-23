# 0421 — Accept cone: sharp crease via clip (kill the wavy reflection surface)

**Flag `flag_20260723_112658_264`** (AZ85 RA-mirror scene, build `087be6c8`):
> "illumination volume wavy at reflection surface."

(The folded translucent volume in the flag is the steel-blue **Accept cone**, not the amber illumination
volume — the fold direction is correct after 0420; the complaint is the crease *edge*.)

## Root cause — a ragged crease

0419/0420 fold the cone by reflecting each point that lies past the mirror plane. But the mirror plane is
**tilted** (`z = 53 + x`), so the cone's triangles **straddle** it — some vertices reflect, some don't —
and each straddling triangle bends unevenly across the plane. Along the crease this reads as a wavy,
torn band.

## Fix — clip at the mirror plane, then reflect

`_crease_overlay_mesh_at_fold` now, instead of per-point reflection:

1. `up = mesh.clip(normal, origin=hinge, invert=True)` — the object-leg half; the clip inserts **exact
   vertices on the mirror plane**, so no triangle straddles it.
2. `down = mesh.clip(..., invert=False)` — the lens-leg half (also cut cleanly on the plane).
3. Reflect `down` about the plane (its plane edge is a fixed point of the reflection, so it stays put and
   coincides with `up`'s edge).
4. Merge → a single mesh with a **clean crease line** along the mirror.

The per-point reflection is kept as a **fallback** (if `clip` is unavailable it still folds, just less
crisp). Verified headless: a 432-point cone becomes 624 points (192 clean edge vertices inserted on the
plane), every point lands on the object-side half-space (`max signed = 0`), and both legs are present.
`None`/unfolded → unchanged.

## Verification (`validate_open3d_accept_cone_fold_aware`, penta phase 339)

Display-free:

| check | asserts |
|---|---|
| MECHANISM | the crease REFLECTS about the mirror plane **and** CLIPS at it (`.clip(`) for a sharp edge; not the old rotate |
| CREASE-MATH — sharp | the clip inserts crease-edge vertices (`out.n_points > in.n_points`) |
| CREASE-MATH — clean fold | after the crease every point is on the object-side half-space (`max signed ≤ 0`) — a ragged mis-fold would leave some past the plane |
| CREASE-MATH — bend | both the object leg (x≈0) and the lens leg (z≈53) are present |
| CREASE-MATH — unfolded | a `None` transform is a no-op |

5/5 pass. Baseline phase 339 = pass.

## Files

- `KrakenOS/UI/open3d_inspector.py` — `_crease_overlay_mesh_at_fold` clips + reflects + merges (per-point fallback).
- `KrakenOS/UI/validate_open3d_accept_cone_fold_aware.py` — guard: clip + clean-fold.

## In-app eyeball still owed

On the AZ85 scene, the **Accept cone**'s crease at the RA mirror should now be a **clean straight edge**
along the mirror face — no wavy/torn band.
