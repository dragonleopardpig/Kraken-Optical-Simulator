# 0567 — best focus was unmeasurable on a frozen scene

flag_20260805_164242: *"solve for FOV 55x55, ray still defocus at the sensor."*

## Chain

`_real_ray_best_focus_shift_for_rows` returned `None`. That is the function the frozen detector
snap's **adaptive corrective loop** re-measures with, so `None` breaks the loop after ONE
application — and bugs/0515 established these shifts are station-frame and UNDER-measured, so a
single shot always leaves residual defocus. Measured after the fix, the true shift was **35.85 mm**.

Two faults, both the same class: code written for unfrozen scenes meeting a 0433-frozen one.

1. **Fold detection** keyed only on `_optical_axis_fold_world_transform_for_row`, which is `None`
   for every row on a frozen scene. The guard reported "no fold" and handed the FOLDED mesh
   mirror to `PupilCalc` — exactly what bugs/0194 built it to prevent. PupilCalc threw
   `IndexError: index 0 is out of bounds for axis 0 with size 0` on the 90° internal reflection,
   and a blanket `except Exception: return None` hid it. **Fourth** consumer of that gate to need
   a breadcrumb fallback (0517 camera frame, 0519 solve gate, 0525 cone crease).
2. **Placement stripping** covered only the promoted solids. On a frozen scene every row carries
   a baked world placement — the lens block kept tilt `(0, -90, -180)` and desp
   `(82.04, 0, -64.69)` — so the "straight equivalent" was neither straight nor centred, the
   sequential trace it exists to feed lost every ray, and those empty direction cosines are what
   PupilCalc choked on.

## Fix

A promoted solid carrying a MIRROR face is a rotating fold by construction, so fold detection
falls back to `_promoted_mirror_fold_row_indices()` when the transform gate finds nothing. This
keeps bugs/0173 intact: a straight-through beam-splitter cube carries Beam Splitter faces, not
Mirror ones, so it still reports no fold and keeps its mesh. And world-placed rows now lose their
baked tilt/desp in the equivalent, while a genuinely decentred row on an unfrozen scene keeps its
decenter.

Measured: `_real_ray_best_focus_shift_for_rows` goes `None` → **35.849 mm**, from 127 traced
samples (was 0 — PupilCalc never returned).

## Guard

`KrakenOS/UI/validate_open3d_0567_frozen_straight_equivalent.py` (penta phase 442).

## Open

* The equivalent also zeroes the fold mirror's 72.5194 mm row (off-beam classifier calling an
  in-beam mirror "parked clear"). Possibly a third instance of the same frozen-scene assumption —
  it would bias the measured shift. NOT addressed here.
* End-to-end confirmation that the solve now leaves the sensor in focus was still running when
  this was committed; the unit-level result (None → 35.85 mm, loop can iterate) is what is proven.
* Phase 414 B2 ("residual traced defocus … got None") is expected to change with this; not
  re-baselined here.
