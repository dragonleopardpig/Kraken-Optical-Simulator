# 0576 — best focus was measured in the prescription frame, not the scene

The "rays defocus at sensor" half of `flag_20260806_182735_708`, and the reason flag 2 (the bare
swap, before the user touched the FOV) already shows a broad unfocused column. See
[0574](0574_solve_pins_the_lens_body.md) and [0575](0575_frozen_image_refusal_inverts.md) for the
other two defects on the same screenshot.

## Root cause

`snap_detector_to_image_plane`'s frozen branch had two candidate measures and reached for the wrong
one first:

```python
delta = self._real_ray_best_focus_shift_for_rows()      # straight-equivalent, STATION frame
if delta is None:
    delta = self._traced_bundle_best_focus_shift()      # the rays that actually traced, WORLD
```

bugs/0515 chose that order believing the first was "immune to station/world offsets". It is not. It
traces `_folded_optical_solid_straight_equivalent_rows`, which keeps the **thicknesses** and drops
the placement — and on a 0433-frozen fold the prescription is not the scene:

- the bugs/0571 compensated slide grows the lens block's stations and cancels them again past the
  block, so station spacing and world path diverge by construction;
- this scene's beam splitter is authored *after* the lens rows (row 6) while sitting ~180 mm
  *upstream* in world.

Measured after the solve, the straight equivalent's lens-rear → sensor spacing is **148.458 mm**
where the real world path is **76.902 mm**.

## The measurement

`bugs/probe_0576_best_focus_frame.py` does not take either estimator's word for it. It scans the
sensor along its own folded leg and reads the real traced axial spot RMS at each stop. The
as-loaded Apo75 — the state whose screenshot is in focus — is the **control**: without it a
monotone curve cannot be told from a broken measurement.

| state | true best focus | straight equivalent says | traced bundle says |
|---|---|---|---|
| flag 1 Apo75 (control, in focus) | −2.17 mm off | **−36.67** | −0.0006 |
| flag 2 after the swap | −69.25 mm off | **3.06e-14** | −71.04 |
| flag 3 after the solve | −60.02 mm off | **5.70e-16** | −57.43 |

The straight-equivalent measure reported "already in focus" to fourteen decimal places on a scene
69 mm out. `snap_detector_to_image_plane` bails at `abs(delta) <= 1e-6`, so the swap's auto-refocus
and the solve's finisher both declined to move — and the adaptive 5-iteration loop, when it did run,
exited after one pass because its *re-measure* used the same broken frame.

Note the control also fails it (−36.67 against a true −2.17): the straight equivalent was never
right on this scene, in any state. It only looked right because nothing measured it.

## Fix

Prefer the world-frame traced bundle on a frozen scene, and keep the straight equivalent as the
fallback for when no bundle is measurable (a headless run with no inspector, or fewer than four
axial rays reaching the detector). The same swap applies to the loop's re-measure — seed and
re-measure must be in one frame or the adaptive sign flip compares two different quantities.

## Measured after

| state | sensor vs true best focus | before |
|---|---|---|
| flag 1 (control) | −2.17 mm | −2.17 mm (unchanged) |
| flag 2 after the swap | **+1.80 mm** | −69.25 mm |
| flag 3 after the solve | **−2.59 mm** | −60.02 mm |

Residuals under the ~5.3 mm scan step, i.e. at the minimum. `_traced_bundle_best_focus_shift` reads
−0.0 in both post-fix states.

Note what this costs in hardware terms and tell the user plainly: focusing the PYRITE 85 at the
preserved conjugates moves the sensor 71 mm along its leg, and the camera body is station-anchored
so it travels with it. That is a real machine change, not a drawing change — but it is what the
optics demand, and the old behaviour simply hid it by refusing to move at all.

## Open

`_shared_first_order_reference` builds `image_z` as a station sum, so the *paraxial* conjugate
target is in the same suspect frame. 0575 defuses that by deferring to the traced focus whenever
the paraxial target is out of the fold's reach, but a frozen-aware first order would be the real
answer, and it is the same §5b per-branch-pupil work the non-sequential seam is waiting on.
