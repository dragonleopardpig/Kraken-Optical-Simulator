# 0194 — BUG: on the folded RA-mirror scene the right-click "Snap detector to image plane (remove defocus)" does nothing — "best focus is not computable" — because every first-order best-focus extractor assumes a straight +Z axis and the mesh mirror folds it 90°

**Status: RESOLVED (source-level). The paraxial image-plane conjugate AND the real-ray
best-focus fallback now evaluate the folded layout through its unfolded straight-sequential
flat-plate equivalent (folding is a rigid transform, so the best-focus back distance is
invariant). Scoped to the folding-mesh-mirror path only: plain / sequential-mirror and
straight-through beam-splitter-cube layouts (bugs/0173) are byte-identical.**

## Flag

The user re-flagged the folded AZ85 layout (`machine_vision_AZ85_RA_Mirror.py`) after bugs/0192
fixed the reflection ("the reflection finally correct"), listing four residual issues. Two were the
placement/overlay strand fixed by bugs/0193. This is the third:

> "Defocus at the image"

Right-clicking the image plane / detector and choosing **"Snap detector to image plane (remove
defocus)"** did nothing — the status line read *"best focus is not computable for this layout."*

## Root cause — measured headlessly

`snap_detector_to_image_plane` (`scene_placement_commands.py`) moves the detector's back-focal gap
(`rows[-2].thickness`) onto the optics' best focus. It first asks `_paraxial_image_plane_z()`, then
falls back to `_real_ray_best_focus_shift_for_rows()`. On the AZ85 **both return `None`**:

Row 1 is a promoted **BK7 mesh MIRROR** (`surface="Standard"`, `Solid_3d_stl` set, placement
`desp_z=12.5`) whose internal 45° face folds the axis 90° onto +X. The prescription itself is
straight (all tilts / `axis_move` = 0), so the fold lives only in the mesh:

- `_paraxial_image_plane_z` → `_exact_paraxial_solution_for_rows(self.rows)` trips its
  *"Paraxial solve supports centered refractive systems only"* guard on the solid's `desp_z=12.5`
  → exception → `None`.
- `_real_ray_best_focus_shift_for_rows` keeps the mesh and calls PupilCalc, which **branches / throws
  on the 90° internal reflection** (the sequential trace can't follow the bend) → bare `except` →
  `None`.

So snap has no target and bails. Measured on the live AZ85 editor:

```
detector_z (unfolded cumulative)     = 347.2180
_paraxial_image_plane_z()            = None      # desp_z guard
_real_ray_best_focus_shift_for_rows()= None      # PupilCalc branch on the mesh fold
snap_detector_to_image_plane()       = False  "best focus is not computable"
```

## Fix (source-level — solve the unfolded straight equivalent)

Folding is a **rigid transform**, so the best-focus back distance, conjugates and magnification are
INVARIANT under the fold: they equal the UNFOLDED straight sequential system obtained by replacing
the folding mesh solid with a flat plate of the same axial thickness/glass.

`paraxial_tools.py` — new `_folded_optical_solid_straight_equivalent_rows()`: returns `None` unless a
row carries a **rotating** output-port fold (`_optical_axis_fold_world_transform_for_row(i)` has a
non-identity rotation); then it replaces each promoted mesh optical solid with its flat sequential
plate (mesh / faces / placement stripped, `rc`/decenter/tilt/`axis_move` zeroed, **thickness + glass
+ row count + every air gap preserved** so the result stays in the detector's cumulative-z frame).
A companion `_with_rows_swapped(rows, compute)` runs a computation with `self.rows` temporarily
swapped, so the helpers that read `self.rows` internally (analysis-surface index, aperture, cache)
all see the same straight equivalent.

Two consumers gain a fold-aware short-circuit:

- `layout_scene_bundle_display.py::_paraxial_image_plane_z` — when the equivalent exists, solve it
  swapped (returns the detector-frame image z directly).
- `paraxial_tools.py::_real_ray_best_focus_shift_for_rows` — when called on `self.rows` and the
  equivalent exists, trace the flat plate (PupilCalc no longer branches).

On the AZ85 both now agree and snap works:

```
_paraxial_image_plane_z()             = 354.9737   -> defocus +7.7557 mm
_real_ray_best_focus_shift_for_rows() = +7.7838 mm     (agree to 0.03 mm)
snap: rows[-2].thickness 150.3679 -> 158.1236 (+7.7557 mm); second snap = no-op
```

## Guard

`KrakenOS/UI/validate_open3d_ra_mirror_remove_defocus.py` (standalone, NOT penta):

1. BEFORE (`_folded_optical_solid_straight_equivalent_rows` shadowed → `None`): both extractors are
   `None` and snap returns `False` / "not computable" — the precondition, so the guard is not vacuous;
2. AFTER (real helper): the paraxial image plane and the real-ray shift AGREE (≤0.2 mm) and snap moves
   the gap ~+7.76 mm onto best focus, then is idempotent;
3. scope: `flat_mirror_45_deg.py` (sequential mirror) and `machine_vision_150mm_coaxial_led.py`
   (straight-through BS cube) build NO flat equivalent — the fix is inert off the folding path, so
   bugs/0173's keep-mesh cube snap is untouched.

## In-app eyeball owed

The fix is proven display-free (paraxial + real-ray agree; snap moves the exact +7.76 mm). The user
should quit + relaunch, right-click the folded detector, choose "Snap detector to image plane", and
confirm the defocus at the image is removed (the on-axis spot tightens).
