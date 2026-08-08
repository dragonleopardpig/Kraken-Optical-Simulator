# 0583/0584 — body clearance for the fold mirror, and a block that cannot tear

The 2026-08-07 late-morning flags (104813 / 104943 / 105146 / 105355 / 110323) on
`machine_vision_Apo75.py`, build `2c880ae4`. One root cause and one layer on top.

## 0583 — the room was measured to the DATUM, the crash happens at the BARREL

`_lens_leg_room_to_fold` (bugs/0572) measured from the block's rear **datum** to the fold
mirror's **aperture**. But the lens barrel extends past the rear datum — ~8.8 mm on the PYRITE
body — so a make-room that stopped 1 mm short of the aperture parked the barrel *inside* the
prism. Measured on flag 104943: rear datum 268.26, prism near face 269.09, bodies overlapping
while 220 rays still landed. Nothing in the trace complains, because the surrogate surfaces were
legal; only the *bodies* interpenetrated.

Flag 105146 is the same defect via the other door: a **longer replacement block** keeps the front
datum, so its rear — and its barrel — land inside the prism that the stage-(c) world bracket had
just faithfully held in place. The bracket was right; nobody had ever written the mechanism that
makes room for a longer lens.

Flag 105355 ("changed 35x35 FOV, it is prohibited, it does not make sense") was bugs/0582's
contiguity guard, correctly refusing on the overlapped state. It was guarding wreckage created a
step earlier. Fix the cause and it goes quiet on its own — which it did.

**Fix.** The room measure charges the barrel overhang (lens STEP bounds projected on the leg)
plus the camera's 2 mm mechanical margin *whenever a lens body is present*; with no body the
datum-to-aperture formula is untouched, keeping bugs/0572's pure-stub arithmetic exact. Every
make-room and every refusal inherits it, because they all read this one measure. And the swap
gains the missing mechanism: after seating a new block it measures the body-aware room and, on a
deficit, slides the fold arm (mirror + camera — the bugs/0573 mover) down the leg to clear it,
saying so in the swap message.

## 0584 — the block could be torn, because membership was geometric

The DRAG write-through shares the solve's slide plan, and bugs/0582 had guarded only the solve —
the instance, not the invariant. `_lens_leg_slide_plan` decided membership by an axis-tree
*arclength window* between the datums, so a lens row displaced past the fold point (exactly the
overlapped state above) silently fell out: flag 110323, "dragged the lens forward, 1pcs of lens
surrogate remain stuck in RA mirror" — rows [1, 2, 3, 5] followed the drag while row 4 stayed at
x=282.34 inside the prism, and 88 of 558 rays came back `missed_image` off the stray surface.

**Fix.** Membership is by **identity**: between the front and rear datums every row is the lens's
own block, excluding parked promoted solids (bugs/0546, which are independent elements the swap
lifts out and a drag must not carry). Geometry still decides the leg *direction* and whether it
is a fold leg — it no longer gets to decide *who belongs to the lens*. A displaced row is now
carried back with its block instead of left behind, on every consumer of the plan. The 0582 belt
remains for genuine inconsistency, now ignoring legitimate 0546 holes so it cannot false-fire on
a parked BS cube.

## Verified (2026-08-07 evening, M90aPro)

`bugs/diag_0583_swap_body_clearance.py`, replaying the flagged sequence:

| stage | flagged as | after |
|---|---|---|
| A PYRITE swap | ok | clearance +38.96 mm, 205 rays |
| B 55×55 unconstrained | "the lens crashed to RA mirror" | clearance **+3.000 mm**, 220 rays |
| C ELS-85 swap | "block inside the mirror" | clearance **+2.000 mm**, 247 rays, arm move reported |
| D 35×35 | "prohibited, it does not make sense" | **applies**, clearance +87.14 mm, 114 rays |
| E drag −30 along the leg | "1pcs remain stuck in RA mirror" | members move `30.000 ×5`, **spread 0.000000 mm** |

`min thickness +0.0000` at every stage. B and C landing exactly on the +3.000 / +2.000 floors is
the mechanism computing the deficit and stopping at the margin, not a coincidence.

Phases 447 / 448 / 449 / 450 all pass. The two that prove the change is *live rather than inert*:

- 0572 A1 (pure stub, no body): room **45.729 mm — unchanged**, as designed.
- 0572 B1 (real scene, body present): room **45.73 → 36.96 mm** — the refusals now bite ~8.8 mm
  earlier, which is precisely the barrel overhang that used to reach into the prism.
- 0573 B2@35: the make-room arm move grew **+28.07 → +36.84 mm** to absorb the tighter budget,
  and the FOV readout still lands on the request (49.497).

**Live confirmation** — the user's own recording `recording_20260807_195854` (flags 195532 /
195617 / 195845), swap → 23×23 → 35×35 → 55×55 on build `547ef145`: rays landed 205 → 211 →
247 (climbing, where every broken state fell 247 → 112 → 62 → 0), barrel-to-prism clearance
+38.84 → +10.38 → +2.83 mm, no negative gaps, and the FOV readout on the final state reads
55.0×55.0. The first clean recording of the arc, with no complaint text on any flag.

## Open, from the same runs

Rays fall 247 → 114 across the 35×35 in stage D. Non-zero and consistent with the focal-length /
conjugate vignetting pattern the 0579 sweep found (short lenses collapse, long ones keep). Decide
it by **termination reason**, not by the count — `aperture_stop_vignette` is honest vignetting,
`no_next_intersection` is geometry missing the sensor — folded into the ELS-85 scan-verify that
bugs/0578 already owes.
