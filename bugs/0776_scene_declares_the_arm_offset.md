# 0776 -- the split-field arm offset is the scene's to declare

> "let the scene declare it, like camera_focus_stage"

about `k` in the strip-POSITION law bugs/0774 measured:

```
|strip centre| = k * |m|      k = object-space half-separation of the two arms' axes
```

k is a property of the BENCH, not of optics -- 8.778 mm on `om05a_folded_80mm` -- so hardcoding it
would bake one machine's geometry into the simulator. It now persists exactly as
`camera_focus_stage` does, and the check is inert on any scene that declares nothing.

## It does NOT catch the 21 mm bug

Stated plainly because it is why the check was proposed. Measured with the correct statistic,
device 21's strips sit **0.25%** off the law -- correctly positioned:

| device | Face A | Face B | expected | worst |
|---|---|---|---|---|
| 23 | 8.3745 | 8.3745 | 8.3745 | 0.00% |
| 21.5 | 8.9587 | 8.9587 | 8.9588 | 0.00% |
| 21 | 9.1954 | 9.1954 | 9.1721 | 0.25% |

The "1.393 mm excess" that motivated it was measured on the strip's outer EDGE, and an edge moves
when a strip WIDENS -- which is what defocus does. So "right size, wrong place" is **withdrawn**:
at 21 mm the strips are correctly positioned and correctly sized, and arm A is simply defocused,
which was already known. What ships is a legitimate invariant guard, not a diagnostic for that bug.

## The first cut was wrong, and how

Grouping rays by LAUNCH POINT gave one group per field point -- **14** on a 23 mm device, 7 per
face -- and comparing each against `k*|m|` is meaningless, because a field point imaging away from
the axis is the field doing its job. It fired on every correct scene at 50-68%. Grouping is now by
FIELD BAND, the rule `_focus_image_partitions` already uses to decide which landings form one
image, so the strip centres and the focus images agree by construction.

The centre, not the edge, is the measured statistic: the mean landing point's in-plane distance
from the sensor centre, which does not depend on which way the constructed u/v axes fell.

## From the adversarial review

21 findings; the refutation stage was mis-designed (files edited mid-review, refuters told to
default to refuted) so its 21/21 all-clear was discarded and the findings read directly. Three
confirmed against the diff and fixed:

- **no clipped-strip guard**, where the sibling `traced_m` check has one. A clipped strip loses
  its outer rays, the surviving mean drifts inward, and the law is charged for it -- while the
  banner would contradict the `FIELD OVERFLOWS` line printed directly above.
- **no minimum ray count** before a mean is called a centre. A mostly-vignetted arm can leave a
  handful of rays at one END of the strip. Now 8 per arm.
- **the banner claimed "the field is the right SIZE"** -- a thing it never measures, and which
  the overflow line above it may be denying. Removed.

Plus, from the persistence lens: a **non-finite** offset passed the sanitizer. `1e400` parses to
`inf`, clears a bare `> 0.0` test, and `pformat` writes it back as the bare token `inf` -- not a
Python literal, so the scene `.py` fails to import, both loaders fall back to surfaces-only, and
every persisted setting is silently discarded. Now rejected, as
`_portable_clear_aperture_rect` already rejects non-finite components.

## Known and NOT fixed

- `np.hypot` discards sign: two strips stacked on the SAME side of the sensor would pass.
- Groups are keyed by band NAME; two identically-named bands merge into one and disable the check.
- `_solve_summary_info` can be stale across a scene load, so `|m|` may not describe the current
  geometry. (On a plain load it is None and the check correctly stays quiet -- verified.)

## Open question for the user

**8.778 is a fit to three measurements, not a number from the drawing.** If the true arm
half-separation is known, the scene should carry that instead. A fitted constant becoming the
reference is how the invented motor-rail limits cost a 0.66 mm miss in bugs/0772.

## Guard

`KrakenOS/UI/validate_open3d_0776_scene_declares_the_arm_offset.py`, penta phase **560**.
