# 0575 — a frozen-fold refusal fell through to the inverted write

Second of the three defects behind `flag_20260806_182735_708` ("changed FOV, lens body detached
from surrogate, rays defocus at sensor"). See [0574](0574_solve_pins_the_lens_body.md) for the
detach and [0576](0576_best_focus_measured_in_the_wrong_frame.md) for the measurement frame.

## What happened

On the 23×23 solve after the PYRITE swap the folded branch asked for a mirror→sensor leg of
**−10.2918 mm** — the sensor 10.3 mm behind the fold mirror. `apply_image_distance_frozen_aware`
correctly refused (`far_new <= 0`). The caller then read `False` as *"this is not a frozen scene,
do the plain prescription write"* and executed `rows[7].thickness += −42.9442`.

On a frozen fold the gap row runs backwards (bugs/0478, `world leg = const − thickness`,
derivative −1), so that write moved the sensor **+42.9442 mm the wrong way**: measured, the image
leg went 32.6524 → 75.5966 where it should have shortened. The whole of bugs/0478's inversion,
re-entering through a refusal path.

## Two distinct causes

**(a) `False` was ambiguous.** "Not a frozen scene" and "frozen, but you asked for a leg this fold
cannot hold" both returned it, and only the first justifies the plain write. Every refusal past the
point where the split and geometry read cleanly now leaves its numbers in
`_frozen_image_write_refusal`; a non-frozen scene leaves it empty. The caller keys on the string,
never on the bool alone. This is the same idiom 0572 uses for `_lens_leg_slide_refusal`.

**(b) `image_delta` was stale by exactly the object slide.** `_folded_conjugate_gaps_for_magnification`
computes it as an absolute z correction in the shared first-order frame, and its docstring calls it
"invariant" under the object move. That was true when the object move was `rows[0].thickness += d`,
which grows *every* downstream station — H′ and the image plane together, so the correction between
them does not change. Since bugs/0571 the object move is the compensated leg slide, which
deliberately leaves the rows past the lens block untouched (`rows[downstream].thickness -= d`
cancels the growth). H′ still gains `d`; the sensor's station gains nothing. So the true correction
is `image_delta + d`, and the old number was short by exactly the slide.

Measured: the finisher's residual immediately after the slide was **+28.4622 mm**, the slide to four
decimal places.

## Fix

1. **Order.** The image write now happens *after* the object move, not before it.
2. **Re-measure rather than hardcode.** Rather than encode "add the slide", re-solve the conjugate on
   the scene as it now stands: the object is already placed, so the fresh `object_delta` comes back
   ~0 and the fresh `image_delta` is exactly the remaining correction. Self-checking, and it also
   absorbs whatever the bugs/0573 fold-arm slide did on the way there.
3. **Defer, don't refuse.** When the frozen writer refuses, write nothing and let the traced-focus
   finisher place the sensor. A hard refusal would be refusing on the wrong number — the target comes
   from `_shared_first_order_reference`, whose `image_z` is a station sum, the very frame 0576
   measured as not-this-scene on a frozen fold. The finisher works in world off the rays that
   actually traced, so it is the authority. This is also the user's own principle: pin the section,
   refocus at the sensor, let the FOV readout follow.

## Measured after

The re-measure lands the paraxial target where it belongs (`image delta re-measured after the
object move −42.9442 → −14.4820 mm, object delta left +0.0000`), and the solve reports honestly
when it had to defer:

```
Solved (folded): object->lens 147.432 mm. The paraxial sensor plane was out of this fold's reach,
so the sensor was placed at the traced focus instead -- read the FOV box for the field that
actually results. Focus: residual -0.8688 -> -0 mm (snapped to the traced focus).
```

## Still latent, same inversion

Three other writers assign a *world* quantity into the frozen gap row and would invert the same way.
None fired on this scene; all are worth a guard when they are next touched.

- `scene_placement_commands.py` — `if not apply_image_distance_frozen_aware(target_gap):
  self.rows[-2].thickness = float(target_gap)`. Here `rows[-2]` *is* the far gap row and
  `target_gap` is an absolute world leg.
- `layout_table_workbench.py` — the swap's floor and mesh-clearance bumps,
  `rows[gap_index].thickness = gap` with `gap_index = len(rows)-2`. Raising that thickness
  *shortens* the world leg, so a floor meant to push the camera clear pulls the sensor toward the
  mirror. Both were no-ops in this run (floor 13.48 < 97.5374, deficit 0.0).
