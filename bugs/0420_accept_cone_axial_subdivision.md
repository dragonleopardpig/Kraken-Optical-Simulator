# 0420 — Accept cone needs axial subdivision to actually bend (0419 follow-up)

**Flags `flag_20260723_093738` ("still the same") + `flag_20260723_095018` ("3D view")**, AZ85 RA-mirror
scene, build `7172649d` (which *has* 0419, confirmed running — a fresh restart still showed it).

## What the 3D view finally showed

The `flag_095018` 3D-perspective screenshot made the failure unambiguous: the acceptance cone is a
**straight diagonal wedge** from the FOV rectangle (top-left, object leg) to the lens (centre) — it cuts
across the corner instead of bending down the object leg then along the lens leg.

## Root cause — a 2-ring loft can't crease

`build_receiving_cone_overlay` built exactly **two** rings (the FOV rectangle at `object_z`, the pupil
disc at `pupil_z`) and lofted between them. A loft between two rings is a **straight ruled surface**. So
even though 0419's reflection correctly places the pupil ring on the lens leg and the FOV ring on the
object leg, the surface *between* them is a straight diagonal — it has no vertices in the middle to follow
the bend. No fold logic can crease a 2-ring cone; the geometry itself has to be subdivided.

## Fix — sample the section along the axis

`build_receiving_cone_overlay` now builds `RECEIVING_CONE_AXIAL_SEGMENTS + 1` rings (default 41) morphing
the FOV rectangle into the pupil disc along the axis (`(1−t)·rect + t·disc` at `z = z0 + t·(z1−z0)`), with
quad faces between consecutive rings. With intermediate rings, 0419's per-point mirror-plane reflection
bends each ring onto its leg: **upstream rings stay on the object leg (x≈0), downstream rings land on the
lens leg (z≈53)**, and the rings straddling the mirror crease. The cone now follows the folded axis —
down the object leg, hinge at the mirror, along the lens leg.

On an unfolded scene the reflection is a no-op, so the extra rings just make a smoother straight cone.

## Verification (`validate_open3d_accept_cone_fold_aware`, penta phase 339)

Display-free, on a subdivided cone straddling a Z→X fold (hinge z=53):

| check | asserts |
|---|---|
| MECHANISM | the crease reflects about the mirror plane (0419) |
| CREASE-MATH — subdivided | the cone has ≥ 5 axial rings (a 2-ring loft can't bend) |
| CREASE-MATH — **bend** | rings upstream of the mirror keep centre x≈0 (object leg); downstream rings land at centre z≈53 (lens leg) — i.e. it bends, not a diagonal |
| CREASE-MATH — isometry | the reflected pupil ring keeps its radius (no twist) |
| CREASE-MATH — unfolded | a `None` transform is a no-op |

5/5 pass. Baseline phase 339 = pass.

## The saga (4 iterations, all headless-untestable)

| # | attempt | flag result |
|---|---|---|
| 0416 | rigid whole-mesh fold onto the lens leg | flat along the lens leg ("not folding") |
| 0418 | horizontal split + rigid rotation | twisted surface ("goes haywire") |
| 0419 | reflect downstream about the mirror plane (isometry) | rings on right legs, but still a straight wedge |
| **0420** | **axial subdivision so the loft can bend** | (this fix) |

Folded geometry can't render headless (VTK segfaults under Xvfb), so each mode needed an in-app flag; the
`flag_095018` 3D view is what pinned the 2-ring root cause. Method lesson recorded.

## Files

- `KrakenOS/UI/services/receiving_cone_overlay.py` — axial subdivision + `RECEIVING_CONE_AXIAL_SEGMENTS`.
- `KrakenOS/UI/validate_open3d_accept_cone_fold_aware.py` — guard: subdivided + bend checks.

## In-app eyeball still owed

On the AZ85 scene, **Accept cone** should now bend: a cone up the object leg from the FOV that creases at
the RA mirror and runs along the lens leg to the pupil — no diagonal wedge, no twist, no flat sheet.
