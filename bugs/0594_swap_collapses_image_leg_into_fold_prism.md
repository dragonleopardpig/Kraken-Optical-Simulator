# 0594 — a swap collapsed the image leg and planted the detector INSIDE the fold prism (OPEN)

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

## Fix — what it needs

1. An image-leg clearance rule that is the counterpart of bugs/0583's lens-leg one: after any
   refocus, the detector's world position must clear the fold solid's exit face by
   `_SWAP_REFOCUS_MIN_CLEARANCE_MM`, measured in **world** (bugs/0576: the frame is not the scene;
   a station-frame gap of 125 mm reads as healthy while the world leg is 4.6 mm).
2. It must be a **refusal with numbers**, in the 0572/0577 style, not a silent clamp — the user
   should be told the swap cannot be refocused without moving the camera, and by how much.
3. Guard the invariant, not the instance (penta 262): assert across a **lens-swap matrix** that the
   detector's world bounds never intersect any promoted optical solid's bounds. That is a cheap,
   display-free box-overlap test computable from the same `row_actor_bounds` the recorder captures,
   and it would have caught this on any of the "few times" the user swapped.

## Related

* bugs/0478 — frozen gap rows run backwards (the mechanism here).
* bugs/0583 — the lens-leg clearance this bug is the image-side twin of.
* bugs/0576 — why the clearance must be measured in world, not station frame.
