# 0195 — BUG: on the folded RA-mirror scene the right-click "Quick Estimation" at the image plane / detector reported the wrong picture — the object/image conjugate SOLVE threw and the in-focus indicator went blank — because the paraxial solve assumes a straight +Z axis and the mesh mirror folds it 90°

**Status: RESOLVED (source-level). The Quick-Estimation conjugate solve
(`_compute_paraxial_solve_result`) now evaluates the folded layout through its unfolded
straight-sequential flat-plate equivalent (folding is a rigid transform, so the object/image
conjugates and the in-focus test are invariant). The magnification readout was already correct
before this fix. Scoped to the folding-mesh-mirror path only: plain / sequential-mirror and
straight-through beam-splitter-cube layouts (bugs/0173) are byte-identical. Shares the
`_folded_optical_solid_straight_equivalent_rows` / `_with_rows_swapped` helpers with bugs/0194.**

## Flag

The user re-flagged the folded AZ85 layout (`machine_vision_AZ85_RA_Mirror.py`) after bugs/0192
fixed the reflection, listing four residual issues. Two were the placement/overlay strand fixed by
bugs/0193; the "Defocus at the image" strand is bugs/0194. This is the fourth:

> "wrong magnification" — asked that right-click **Quick Estimation** (image plane / detector) also
> work on the fold.

## Root cause — measured headlessly

Quick Estimation (`quick_estimation.py::current_state`) shows three things: the finite paraxial
MAGNIFICATION, the object/image conjugate SOLVE, and an in-focus indicator. On the folded AZ85:

- The **magnification was already correct** (|m| = 1.1418): `_current_finite_paraxial_magnification`
  substitutes the transmissive reference rows (`_paraxial_reference_rows_for_layout`), so it never
  touched the mesh mirror's decenter. RAW == FLAT == ground truth.

- The **conjugate solve threw**. `_compute_paraxial_solve_result("image")` calls
  `_exact_paraxial_solution_for_rows(self.rows)` on the RAW rows, whose row-1 promoted BK7 mesh
  MIRROR (`surface="Standard"`, `Solid_3d_stl` set, placement `desp_z=12.5`) trips the
  *"Paraxial solve supports centered refractive systems only"* guard → `RuntimeError`.

- Because the solve threw, the **in-focus indicator went blank**: `current_state()["in_focus"]`
  swallows the exception → `None`, so the detector's 7.76 mm defocus never surfaced in QE.

Measured on the live AZ85 editor, BEFORE the fix:

```
magnification (display)          = 1.1418            # already correct
solve('image')                   = EXC RuntimeError  # centered-refractive guard on desp_z=12.5
solve('object')                  = EXC RuntimeError
in_focus (inline check)          = None              # exception swallowed
```

## Fix (source-level — solve the unfolded straight equivalent)

Folding is a **rigid transform**, so the object/image conjugates and the in-focus test are
INVARIANT under the fold: they equal the UNFOLDED straight sequential system obtained by replacing
the folding mesh solid with a flat plate of the same axial thickness/glass.

This reuses the bugs/0194 machinery in `paraxial_tools.py`:

- `_folded_optical_solid_straight_equivalent_rows()` — returns `None` unless a row carries a
  **rotating** output-port fold (`_optical_axis_fold_world_transform_for_row(i)` has a non-identity
  rotation); then it replaces each promoted mesh optical solid with its flat sequential plate (mesh
  / faces / placement stripped, `rc`/decenter/tilt/`axis_move` zeroed, **thickness + glass + row
  count + every air gap preserved** so the result stays in the detector's cumulative-z frame).
- `_with_rows_swapped(rows, compute)` — runs a computation with `self.rows` temporarily swapped, so
  the helpers that read `self.rows` internally (analysis-surface index, aperture, cache) all see the
  same straight equivalent.

New consumer short-circuit: `_compute_paraxial_solve_result` — when the equivalent exists, solve it
swapped (the returned object/image distances stay in the detector's cumulative-z frame). This is the
one call that QE's conjugate readout and in-focus indicator both flow through, so fixing it restores
both at once.

On the AZ85 the solve now lands and the defocus is flagged:

```
magnification (display)          = 1.141846860242257            # unchanged
solve('image').solved_distance   = 158.12359954970324           # = 150.368 gap + 7.76 defocus (best focus)
solve('object').solved_distance  = 65.3136506363522
QE state: mag=1.1418  in_focus=False  object_mode=Finite  fov_semi=14.267885
```

`in_focus=False` correctly flags the detector sitting ~7.76 mm short of best focus — the same
defocus that bugs/0194's "Snap detector to image plane" removes.

## Guard

`KrakenOS/UI/validate_open3d_ra_mirror_quick_estimation.py` (standalone, NOT penta):

1. BEFORE (`_folded_optical_solid_straight_equivalent_rows` shadowed → `None`): both solves raise and
   the inline in-focus check is unavailable (`None`) — the precondition, so the guard is not vacuous;
2. AFTER (real helper): `solve("image")` → ~158.12 mm (best focus), `solve("object")` → ~65.31 mm,
   the magnification stays 1.1418, and the in-focus check reads `False` (correctly flagging the
   7.76 mm defocus at the detector);
3. scope: `flat_mirror_45_deg.py` (sequential mirror) and `machine_vision_150mm_coaxial_led.py`
   (straight-through BS cube) build NO flat equivalent — the fix is inert off the folding path.

## Residual (separate display issue, NOT fixed here — in-app eyeball owed)

The QE **overlay** (`quick_estimation_overlay.py`) draws the object/image FOV circles perpendicular
to `axis = img_pt - obj_pt`. On the fold the object reference point is at ~(0,0,0) and the image
reference point is at the folded ~(287.82, 0, 71.9), so that axis is the diagonal ~(0.97, 0, 0.24)
and the circles are drawn on a skewed diagonal rather than square to the object (+Z) and detector
(folded +X) normals. This is a rendering-only concern (the numeric magnification / conjugates above
are correct) and is left for an in-app eyeball to confirm whether it is what the user perceived as
"wrong magnification". Candidate follow-up bug 0196.

## In-app eyeball owed

The conjugate solve + in-focus fix is proven display-free. The user should quit + relaunch,
right-click the folded detector, choose **Quick Estimation**, and confirm the magnification reads
~1.14, the object/image conjugates populate, and the in-focus indicator flags the defocus (then goes
green after bugs/0194's "Snap detector to image plane"). Note whether the FOV overlay circles look
skewed (the residual above).
