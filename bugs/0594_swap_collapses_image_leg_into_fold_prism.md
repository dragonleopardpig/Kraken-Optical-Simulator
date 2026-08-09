# 0594 — a swap collapsed the image leg and planted the detector INSIDE the fold prism (FIXED)

Flag `flag_20260809_102408_191`: *"swapped a few times with different lens, final swap crash the
camera."* Scene `machine_vision_ELS85.py`, lens STEP swapped to
`PYRITE_45_85_05x-20x_V38_1072517`, build `5b3962d5`.

"Crash" is literal: the detector — and the camera body glued to it — ends up **inside the
right-angle fold prism**.

## Diagnosed from the recordings, arithmetically

The flag records `row_actor_bounds`, so the collision is visible without a repro. Comparing the
crash against a working recording of the same hardware (`flag_20260809_100904_100`, Apo75 scene,
identical BS + RA prism promotion bounds, prism sitting at the same world z):

| | row 7 thickness | prism centre z | sensor z | world image leg |
|---|---|---|---|---|
| Apo75 (works) | 70.8191 | 54.353 | −5.050 | **59.402** |
| ELS85 + PYRITE (crash) | 125.5793 | 54.358 | 49.711 | **4.647** |

```
thickness change  +54.7602 mm
world-leg change  -54.7550 mm
derivative d(leg)/d(thickness) = -0.9999
```

That derivative is the documented **frozen inverted gap** (bugs/0478: on a frozen fold,
`world leg = const − thickness`). Two independent recordings reproduce it to 1 part in 10⁴, so the
mechanism is established without assuming any scene constant.

The consequence, straight from the recorded bounds:

```
row 7 (RA prism):  x 289.410 .. 314.836   y ±12.749   z 41.645 .. 67.071
row 8 (sensor)  :  x 285.795 .. 318.378   y ±16.292   z 49.699 .. 49.723
```

The sensor's z = 49.711 lies **inside** the prism's z span, and its x span contains the prism's.
In the working scene the sensor sits at z = −5.05, well clear below the prism, which is where a
+X→−Z fold should put it.

## Root cause

The final swap's refocus booked a row-7 thickness of 125.58 mm. On this frozen fold that
**shrinks** the world image leg one-for-one, collapsing it from ~59 mm to ~4.6 mm and driving the
detector into the fold solid.

Nothing refused it:

* `negative_gap_rows` is **empty** — 4.647 mm is positive, so the existing negative-gap trap
  (`reference_negative_gap_off_axis`) cannot fire. The defect is a *too-small positive* leg, which
  is a physical-clearance question, not a sign test.
* bugs/0583 added clearance accounting (`_lens_leg_room_to_fold`, `_SWAP_REFOCUS_MIN_CLEARANCE_MM`)
  but charged it on the **lens** leg only. The **image** leg has no equivalent, so a swap may book
  a thickness that seats the detector inside the very solid that folds the beam to it.

## Reproduced by construction

Setting the recorded thickness on the as-loaded scene lands the sensor exactly where the flag
recorded it — the diagnosis is now proven, not inferred:

```
as-loaded        th=  75.6226  far= 54.5673  sensor_z=  -0.246   INSIDE=False
th=125.5793      th= 125.5793  far=  4.6106  sensor_z=  49.711   INSIDE=True   <-- flag: 49.711
```

## Root cause — the clearance guarantee was conditional

`_swap_auto_refocus_to_best_focus` already had two clearance layers (bugs/0388/0391/0392), and
they are frozen-aware (bugs/0578). But it opened with:

```python
        moved = self.snap_detector_to_image_plane()
        if not moved:
            self._swap_refocus_note = str(... "_snap_detector_refusal" ...)
            return          # <-- skips BOTH clearance layers
```

A refused refocus is a **real and documented outcome** (bugs/0566/0575/0577). So whenever best
focus was unreachable, the camera was left exactly where the previous state had put it, with no
collision check and no collision message. That is the "final swap" in the user's sequence.

Two further faults in the same function:

* The clearance writes called `apply_image_distance_frozen_aware(gap)` and **discarded both the
  bool and `_frozen_image_write_refusal`** — whose own docstring says *"the caller keys on the
  string, never on the bool alone"* — then reported "focus limited to N mm so the camera body
  clears" whether or not anything had moved.
* That report went to `status_var`, which `swap_imaging_lens_from_folder` **overwrites** with its
  own success line at the end of the swap. So the clearance message never reached the user at all;
  it was only ever visible to a validator calling the method directly.

## Fix

1. A refused refocus **falls through** to the clearance layers. The refocus is an optical nicety;
   the clearance is a physical invariant.
2. `_write_gap` keys on the refusal string and refuses with numbers instead of claiming success.
3. A third layer **verifies** rather than assumes: the body-vs-solid deficit is re-measured on the
   final geometry, and any residual is reported as a collision with its number.
4. Two message channels — `_swap_refocus_note` (why focus was not reached, prefixed "NOT
   refocused:") and `_swap_clearance_note` (what the clearance did) — both appended by the swap to
   the status the user actually sees.

Measured after, on the reproduced crash state with the refocus forced to refuse:

```
refocus_note  : 'best focus needs more leg than this fold has'
clearance_note: 'focus limited to 26.0 mm so the camera body clears the upstream element'
after refocus : th= 104.2099  far= 25.9800  sensor_z= 28.341   INSIDE=False
```

The camera body now ends 2.00 mm clear of the prism's near face — exactly
`_SWAP_REFOCUS_MIN_CLEARANCE_MM`.

## Guard — phase 452

`validate_open3d_0594_refused_refocus_still_clears_the_camera` (A fixture non-vacuity, B the
refused refocus still clears, C both channels speak, D three source contracts, E the invariant
across four real lens swaps). Verified to FAIL on every check but A before the fix.

`validate_open3d_lens_swap_auto_refocus` was updated to assert on `_swap_clearance_note` instead
of `status_var`: its clamp *values* were always right, but the message assertions were reading a
channel the user never saw — which is why this shipped.

## What this fix does NOT do

It does not stop a *non-swap* writer from collapsing the same leg. The clearance now runs on every
swap path, but a FOV solve or a drag that books a large image thickness reaches the same geometry
by a different door — the recurring shape bugs/0588 catalogued for the refusal family. The
door-independent version would be a scene-level invariant asserted after ANY image-side write:
no detector may sit inside a promoted optical solid. Phase 452's check E is that assertion; it is
currently only applied across swaps.

## Related

* bugs/0478 — frozen gap rows run backwards (the mechanism here).
* bugs/0583 — the lens-leg clearance this bug is the image-side twin of.
* bugs/0576 — why the clearance must be measured in world, not station frame.
