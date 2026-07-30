# 0484 — the FOV solve slid the beam splitter off its LED

The object-side half of bugs/0482, reported across three messages on the same
`recording_20260730_103754` session:

> the BS Plate is shifted down, the subsequent elements shifted down as well. This should not be
> the case. The BS should glue to the LED, cannot be displaced

> I pressed Ctrl-Z, now I notice the 23x23mm already shifted the BS plate, which is wrong

> just now I tried right click BS and glue to LED, then changed FOV, the BS moved as well

## Cause

Sections, as the object split names them: **1** = `object → beam splitter` (`near`), **2** =
`beam splitter → lens front` (`far`). The solve wrote its whole object-distance change into the gap
row — which is section 1 — and **section 1 IS the BS's world position**: the split's `fold_point`
tracks it exactly. Measured:

    as loaded   sec1  53.803   sec2  71.660
    23x23       sec1  64.871   sec2  71.660     BS +11.068, LED +0.000
    30x30       sec1  90.696   sec2  71.660     BS +36.892, LED +0.000

So the BS slid up the axis while the LED body — anchored separately, by its own placement offset —
stayed exactly where it was. Every downstream element moved with the BS, which is the "subsequent
elements shifted down as well" half of the report. And it was already happening at 23 × 23, which
is why Ctrl-Z revealed it.

**The glue bool was never the gate.** bugs/0453 built `_object_locked_redirect_row` for precisely
this failure and made it fire on `_optical_led_glued` **or** an imported LED STEP — but only when
the topology also matches *"a promoted solid immediately after the object gap"*. This scene's BS is
**row 3**, sitting between Group 1 and the aperture and thrown back to the object end by its
`desp`, so the structural test fails and the redirect stands down whatever the flag says. That is
why gluing by hand changed nothing — confirmed live by the user.

## Fix

The user's call, having weighed the alternatives: *"OK, I think make it easier, just change the
section 2 distance."*

Hold section 1 at its pre-solve value, so section 2 absorbs the entire change and the **lens**
moves. Both ends of section 1 are then pinned — the object plane is the station anchor and the BS
sits a fixed distance along the axis from it — so neither the inspected part nor the illuminator
moves. Applied through `_apply_folded_object_split`, the same writer the manual leg constraint uses
(frozen-world aware, bugs/0447), via the shared `_rebalance_split_sections` that bugs/0482
introduced: the object side passes `target = pre_near`, the image side `pre_near + Δ/2`.

Growing section 2 only increases the mirror-to-lens clearance, so the common direction is always
safe. A shrink clamps at the split's own `far_min` (37.689 mm — *"so the mirror does not collide
with the lens"*), and because the writer holds the total the remainder falls back onto section 1,
moving the BS only when there is no alternative.

### The glue needed enforcing as a relative pose

The writer slides the BS **and the LED together** by its own delta — right when a user drives it by
hand, wrong here. The solve had already moved the BS alone through the station shift, so cancelling
the BS's motion left the LED displaced by the same amount:

    BS dz +0.000   LED dz -11.068 / -36.892 / -55.339 / -73.785   across 23/30/35/40

i.e. the glue broken in the opposite direction. Fixed by capturing the BS → LED world vector and
restoring it after the writer runs. **It must be captured before any write:** measured at the
rebalance's own entry point the vector already carries the delta (−16.946 instead of +19.946),
which put the LED at z 37.513 instead of 74.405 — the first attempt did exactly that, and guard
check B5 pins it.

## Verification

Real scene, camera re-seated after each solve, 23/30/35/40 mm sweep:

| field | sec 1 | sec 2 | BS dz | LED dz | BS→LED gap dz | lens dx | collisions |
|---|---|---|---|---|---|---|---|
| as loaded | 53.803 | 71.660 | — | — | — | — | — |
| 23×23 | **53.803** | 82.727 | +0.000 | +0.000 | **+0.000** | +11.068 | none |
| 30×30 | **53.803** | 108.552 | +0.000 | +0.000 | **+0.000** | +36.892 | none |
| 35×35 | **53.803** | 126.998 | +0.000 | +0.000 | **+0.000** | +55.339 | none |
| 40×40 | **53.803** | 145.444 | +0.000 | +0.000 | **+0.000** | +73.785 | none |

The lens's x displacement equals section 2's growth exactly, and sections 3/4 keep bugs/0482's
behaviour throughout.

`KrakenOS/UI/validate_open3d_0484_object_leg_holds_section_one.py`, penta **phase 391**,
display-free, 17 checks: section 1 held and section 2 absorbing (A1–A4, including that this is a
HOLD and not the image side's 50:50 — half the delta would still have moved the BS 18.4 mm), the
glue restored exactly and the contaminated-offset bug pinned (B1–B5), the shrink clamp and the
impossible case (C1–C2), the three no-ops (D1–D3), and the wiring with the capture-before-write
ordering (E1–E3).

## Also fixed here: the 0468 guard was reading the inverted quantity

`validate_open3d_0468_fov_solve_respects_collision_floor` compared `rows[7].thickness` against a
world-space floor. On this frozen fold the world leg runs as `const − thickness` (bugs/0478,
measured derivative −1), so the row is the *inverted* quantity — the comparison was only ever right
by coincidence, while `const` happened to be twice the leg. After a 35 × 35 solve the row reads
91.854 mm for a world leg of 38.814 mm. Both its checks now read the split's world `far`. Its
`== floor` assertion is also relaxed to `>= floor`: 0468's contract was "slide by exactly the
deficit", which lands the leg ON the floor, and bugs/0482's share now carries the sensor further
from the mirror than the floor requires (38.8 mm against 24.98 mm) — strictly safer than what the
guard was written to pin. Landing *below* it is what must never happen, and that is what it now
asserts.
