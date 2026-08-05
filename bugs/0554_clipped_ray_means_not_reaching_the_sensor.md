# 0554 — a clipped ray is any ray not reaching the sensor

**Flags:** `flag_20260805_110310_240` — *"zoomed in view, all rays which is not reflected by RA
mirror should not be shown. And why are there rays passing straight through the RA mirror?"*
(clipped rays OFF), plus `_101116` / `_101430` / `_101805` for the ON/OFF comparison.

**User's definition, 2026-08-05:** *"let's define 'clipped rays': any ray not reaching the
sensor. So if transmitted path of a BS has a lens and camera, the rays must be shown."*

## Two questions, one of them already answered by physics

**"Why are rays passing straight through the RA mirror?"** — They are not. A census settled it:

```
73 paths cross the prism's x-z footprint (what the TOP view draws)
  enter the 3-D AABB                      : 73     (0 pass beside it in y)
  interact with the prism (surface event) : 68
  no event on the prism                   :  5     <- crossing the box ABOVE the hypotenuse,
                                                      i.e. outside the glass. Correct.
```

The straight lines crossing the glass are **synthetic escape tails** — the direction cue drawn
for a ray that reached nothing (see bugs/0551 / bugs/0553). A tail is not traced, so it does not
collide with anything and will happily cross solid glass. Nothing pierces the mirror; display
scaffolding was painted over it.

*(The user was right to challenge the first reading: the TOP view collapses y, and the prism is
only ±12.67 mm deep there, so an apparent pierce could easily have been a projection artifact.
It wasn't — but the check was the correct one to demand, and it is the bugs/0389 lesson: settle
"broken ray" claims with a census, not with the picture.)*

## The display rule was approximating the wrong thing

Visibility with **Show Clipped Rays OFF** was decided by whether a ray had been *steered*:

* **bugs/0016/0018** — a deliberately folded branch (BS 2nd path, mirror leg, TIR, grating)
  stays visible even with no detector to land on, because the user authored it.
* **bugs/0390** — except when it then failed downstream (`stopped` / `missed_detector`).
* **bugs/0531** — except a same-splitter re-bounce ghost.

All three approximate the intent through the **mechanism** (did it fold?) rather than the
**outcome** (did it get anywhere?). On a splitter scene the approximation collapses: the BS folds
*every* ray, so the exemption covered **305 escaped fragments** instead of one authored branch.

## Fix

`ray_path_visible_without_clipping_from_events` now returns **visible ⟺ the ray reaches a
sensor**. The user's BS requirement is not lost — it is expressed correctly: a transmit arm
carrying its own lens and camera reaches *that* camera's sensor, so its rays are visible because
they **arrive**, not because they bounced.

Every prior special case falls out for free, and the ghost-specific branch was deleted:

| case | old rule | new rule | same outcome? |
|---|---|---|---|
| folded, reaches its camera | visible | visible | ✅ |
| folded, vignetted at the stop (0390) | hidden | hidden | ✅ |
| re-bounce ghost that lands on nothing (0531) | hidden (special case) | hidden (by definition) | ✅ |
| re-bounce ghost that lands on the detector | visible | visible | ✅ |
| folded, escapes with nothing to land on | **visible** | **hidden** | ⬅ the change |
| absorbed on a beam dump | **visible** | **hidden** | ⬅ the change |

## Measured

On the real AZ85 + RA-mirror + BS scene, rays kept with clipping OFF that never reach the sensor:

```
before 0554 : 374 kept, 374 spurious
after  0554 :   0 kept,   0 spurious
```

That check lives in `validate_open3d_0531_splitter_rebounce_ghost_hidden` and was **already red
at HEAD** — the user's complaint had a failing guard behind it.

## Guards

Five updated to the new contract, each with the reasoning recorded:
`validate_open3d_traced_rays_always_visible` (+ a new positive case: a folded arm that reaches
its sensor stays visible), `validate_open3d_reflected_branch_detector_bounds` (+ the same
positive case), `validate_open3d_clipped_vignetting_parity`,
`validate_open3d_folded_vignette_hidden`, `validate_open3d_0531_splitter_rebounce_ghost_hidden`.

The 0531 guard needed one more change: it asserted the **implementation** (does the source still
call the ghost predicate?), which would now fail on a correct implementation. It asserts the
**behaviour** instead — both ghost outcomes are still checked.

Its REAL check now makes "no spurious ray survives" the load-bearing assertion and reports the
equality half as unmeasurable, because that harness drives
`_build_preview_system_rays_bundle(sampling_mode=None)` and traces 0 detector-reaching rays on
this scene, where the live app traces 160. Worth fixing separately.

## Consequence to watch

`absorbed` rays now hide. Memory records an MV-150 coaxial scene where 117 absorbed second-path
rays were deliberately kept visible (bugs/0389's census); under this definition they are clipped,
since a beam dump is not a sensor. Flagged to the user when the rule shipped.
