# 0764 -- the focus snap may not make focus worse (and the measure that proves it was blind)

Flag: *"kill Kitty, restarted, set FOV to 30x30, click Apply+Solve FOV for this face. Image is
not landed on sensor."* Plus `error.png`, an `AttributeError` traceback out of the solve.

This is the same 5.932 mm bugs/0762 could not reproduce. It reproduces exactly once the device
is **30 mm deep** -- the flag's part was 30x1x30, and the scene default is 50 deep. bugs/0762
tested width changes; a **depth** change is a different code path, because the part is centred on
z = -25 and shrinking its depth moves the inspected face (the object row's `desp_z` goes to
-10.000, bugs/0713). Nothing in the bundle recorded W/D/H, so that had to be guessed. It is
recorded now -- see the last section.

```
W=30 H=1 D=50  ->  residual [ 0.0257,  0.0266]     (the control: lands)
W=30 H=1 D=30  ->  residual [-5.9325, -5.9342]     (the flag, to 3 decimals)
```

## Two defects, stacked

### 1. `error.png`: `object_slid` is None  (tagged **bugs/0763** in the code; documented here)

`quick_estimation.py:2076` did `object_slid.get(...)` on the residual-reporting path. On a scene
whose object row carries the device face the lens does not move by a *slide*, so `object_slid` is
None and this raised `AttributeError: 'NoneType' object has no attribute 'get'` -- killing the
solve mid-write. Guarded with an `isinstance` check; report 0 mm of slide when there was none.

Fixing it stopped the crash but **not** the 5.932 mm, so there was a second defect underneath.

### 2. The snap moved the sensor off a focus that had already landed

Instrumenting the solve's own writes settles it. The two-motor booking is **exact**:

```
D=30: arm(-65.6983)   image_delta -65.6983 -> -4.5e-12      (perfect)
      ...then, before the solve returns:
      row 24 thickness -56.0283 -> -50.1464  (+5.8819)
      image_delta 0.0000 -> -5.8819,  measured residual -0.0506 -> -5.9325
```

`-0.0506 - 5.8819 = -5.9325`, the flagged number to four decimals. The writer is
`_finish_solve_on_traced_focus` -> `snap_detector_to_image_plane`. **The scene was already in
focus and the snap moved it out.**

Why it computed a fabricated correction, and why nothing caught it:

**(a) The traced measure was blind.** `_traced_bundle_best_focus_shift` filtered ray paths on
`termination_reason == "target_termination"` -- the *older* spelling. The scene builder stamps
`"image"` (`scene_builder.py:1699/3363`), and `_measure_focused_image_plane` accepts both. Census
on this scene: **644 rays land as `"image"`, 0 as `"target_termination"`.** So the measure matched
nothing and returned `None` on every call, on every scene using the current spelling.

`None` is not inert. It is the signal `snap_detector_to_image_plane` reads as "no bundle is
measurable", and it is what made the finisher's bugs/0645 before/after verification degrade to
`NaN` -- at which point the finisher reports *"Snapped the detector to the traced focus"*
unconditionally, having verified nothing.

**(b) With no real-ray measure, the snap fired an unverified station-frame shot.** om05a is a fold
that `_folded_image_conjugate_split()` does not classify as frozen (it returns `{}`), so the snap
takes its *unfrozen* branch, where

```python
delta = self._paraxial_image_plane_z() - sum(float(r.thickness) for r in self.rows[:-1])
```

Both terms are **station-frame sums**. They equal the world defocus only when every row sits at
its cumulative thickness -- but om05a seats rows 16-23 absolutely by `desp` and its image gap row
runs backwards ([[reference_frozen_gap_row_inverted]]). The number is measured in a frame that is
not this scene, and the *sign* a gap row consumes is scene-dependent too. Measured here:
`d(residual)/d(row24) = -1`, so the correct delta was `-5.93` and the branch applied `+5.88`.

bugs/0577 already wrote the rule for the frozen branch:

> A refocus that cannot improve the scene must leave it exactly as it found it.

It is not a frozen-only rule. The unfrozen branch enforced nothing.

## The fix

1. `_traced_bundle_best_focus_shift` accepts **both** termination spellings, exactly as
   `_measure_focused_image_plane` documents. This restores a working real-ray measure everywhere
   -- and with it the finisher's before/after verification, which stops claiming focus it did not
   achieve.

2. The snap's unfrozen branch measures the traced defocus **before and after** its write and
   restores the row snapshot when the move made focus worse. The first guess is unchanged, so
   every scene it already gets right is untouched; only a measured regression is reverted, and it
   returns `False` with a refusal string instead of reporting success.

   The verification is deliberately **real-ray only** (`_traced_bundle_best_focus_shift`, with the
   bugs/0752 per-image measure as the split-field fallback). Verifying a station-frame correction
   with another station-frame walk would only agree with the mistake
   ([[reference_straight_equivalent_not_an_unfold]]).

   Tolerance `_SNAP_REGRESSION_TOL_MM = 0.05` mm -- a third of one pixel of depth of focus
   (0.153 mm), below anything visible but clear of re-trace sampling noise.

## Result

| scene | W x H x D | before | after |
|---|---|---|---|
| om05a_folded_80mm | 30 x 1 x 30 (the flag) | **-5.9325** | **-0.0506** |
| om05a_folded_80mm | 30 x 1 x 50 (control)  | +0.0257 | +0.0257 (unchanged) |
| om05a_folded_80mm | 30 x 1 x 20 | -- | -0.0512 |
| om05a_folded_80mm | 30 x 1 x 40 | -- | -0.0497 |
| om05a_folded_80mm | 30 x 1 x 60 | -- | -0.0486 |
| om05a_folded_80mm | 20 x 1 x 30 | -- | -0.1001 |
| om05a_folded_80mm | 50 x 1 x 30 | -- | -0.0196 |

Every case lands inside the 0.153 mm depth of focus (one pixel).

`attachment/om05a_folded.py` (the production 85 mm build) still reports large residuals -- 74.55 mm
at 30 x 1 x 30. That is **not** this change: A/B'd by disabling only the revert, the number is
identical to four decimals either way. The cause is scene setup, not code -- that scene carries
`'camera_focus_stage': None`, so no motor stage is declared, the image-side correction cannot be
booked at all and the solve honestly reports the residual (bugs/0731). Declaring its stage means
stating real travel limits for the production bench, which is the user's call, not something to
infer ([[feedback_vendor_hardware_immutable]]).

## Two user requests handled in the same pass

> "can you rearrange the dialog to W, D then H?"

The inspection-part dialog now reads **W, D, H**.

> "Also, it is wierd that the bug reporting Flag not recording the W,D,H information?"
> "we have wasted so much token from this."

Fair, and it is the direct cause of how expensive this diagnosis was: the flag recorded the scene
file and every row but not the part at the object plane, so 30x1x30 was reproduced as 30x30x50 and
the depth path -- the actual defect -- went unexamined. The 3D flag bundle's `state.json` now
carries an `inspection_part` block with the normalised W/H/D, axis reach, face offset and active
face, as floats a repro script can feed straight back into `set_inspection_part_spec`.

## Guard

`KrakenOS/UI/validate_open3d_0764_focus_snap_may_not_make_focus_worse.py`, penta phase **551**.
Checks: the measure accepts both spellings and finds a synthetic cone's waist under each (A); the
unfrozen branch measures before and after, restores, and refuses (B); the guard stands down when
nothing is measurable and never reverts an improving snap (C); verification is real-ray, never a
station-frame walk (D); the flag records W/D/H and the dialog reads W, D, H (E).
