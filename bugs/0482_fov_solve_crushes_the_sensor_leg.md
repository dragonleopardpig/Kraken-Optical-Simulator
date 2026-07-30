# 0482 — the FOV solve crushed the sensor leg until the camera sat inside the fold mirror

**Flag `flag_20260730_103719`** (recording `recording_20260730_103754.json`, build `3007c362`,
scene `attachment/machine_vision_AZ85_RA_Mirror_BS.py`):

> change to 30x30 not working: the sensor misplaced to RA mirror. The camera crash to RA mirror.

Fourth flag of a four-flag recording whose first three confirm 0475 ("reset camera to image plane
works"), the defocus snap ("remove defocus works") and a 23 × 23 solve.

The user's four SECTIONS, which the app already models by name:

| | section | source | as loaded |
|---|---|---|---|
| 1 | object → beam splitter | object split `near` | 53.803 |
| 2 | beam splitter → lens front | object split `far` | 71.660 |
| 3 | lens rear → RA mirror | image split `near`, row 6 | 103.270 |
| 4 | RA mirror → sensor | image split `far`, row 7 | 51.500 |

## Two defects

**The whole image-side change landed on section 4.** The solve fixes the lens→sensor TOTAL; how it
splits between sections 3 and 4 is a free mechanical choice — exactly the reasoning bugs/0468 used
to justify sliding the mirror rather than refusing. In practice it was not a choice, because the
delta was written to whichever row the solve holds:

    23x23:  sec3 103.270 (unchanged)   sec4 51.500 -> 38.728
    30x30:  sec3 103.270 (unchanged)   sec4 38.728 -> 18.860

Section 3 sat at 103.270 mm throughout, with room to spare.

**The floor protected the wrong thing.** `_image_gap_collision_floor` returned `far_min` = 12.5 mm
— half the mirror's own along-axis extent, i.e. the clearance for the SENSOR PLANE. The leading
edge is not the sensor: it is the camera BODY bolted behind it, reaching its vendor front-to-sensor
distance (11.48 mm on the hr25MCX) back up the leg toward the mirror. 18.86 mm cleared the 12.5 mm
sensor floor, so bugs/0468's resolver stood down — and the body, needing 11.48 mm out of the
6.36 mm left past the mirror face, ended **5.3 mm inside the prism**. The screenshot shows the
prism drawn over the camera's corner.

## Fix

Both halves of the user's stated policy, for the unconstrained case: *"I prefer 50:50 split but
with Anti-collision check … the imaging lens and camera should not crash the RA mirror."*

* `_image_gap_collision_floor` = `far_min` + camera-body reach + `IMAGE_LEG_ASSEMBLY_MARGIN_MM`
  (12.5 + 11.48 + 1.0 = **24.98 mm** here). Unchanged at `far_min` when no camera STEP is
  imported — then the sensor plane really is the leading edge — and 0 when the scene has no
  image-side fold at all.
* `_rebalance_image_leg_sections` shares the leg-total change evenly between sections 3 and 4,
  clamped to `[near_min, total − floor]`, applied through `_apply_folded_image_split`. That writer
  holds the total, so anything a clamp takes off one section lands on the other; and on a frozen
  scene it slides the breadcrumbed mirror and re-seats the sensor AND camera on the exit leg
  (bugs/0447), which a raw thickness write does neither of. It runs LAST, after
  `apply_image_distance_frozen_aware` has re-baked world centres — 0447's ordering rule.

The conjugate is untouched in both cases: the two sections still sum to the solved total, so focus
and magnification are exactly as solved.

## Verification

Real scene, camera re-seated after each solve (the user's own sequence), with bugs/0483 applied so
the mirror's box is truthful — **without 0483 the clearance cannot be measured at all**, which is
what made the first attempt at this fix look like a failure:

| field | sec 3 | sec 4 | camera→mirror z-gap | baseline sec 4 / gap |
|---|---|---|---|---|
| 23×23 | 96.884 | 45.114 | **+21.13** | 38.728 / +3.68 |
| 30×30 | 86.950 | 35.180 | **+11.20** | 18.860 / **−44.86** ← the report |
| 35×35 | 82.287 | 30.517 | **+6.54** | 12.500 / −26.89 |
| 40×40 | 79.525 | 27.755 | **+3.78** | 12.500 / −24.07 |

`camera_body_collisions()` returns `[]` at all four sizes with the fix, and reports the promoted
solid at 30/35/40 without it.

`KrakenOS/UI/validate_open3d_0482_fov_solve_shares_image_leg.py`, penta **phase 389**,
display-free, 15 checks: the floor's three terms and its two stand-down cases (A1–A5), the even
share and its status line (B1–B3), the clamp and the both-floors-impossible report (C1–C2), the
no-change / unreadable / writer-refused no-ops (D1–D3), and that the share is wired in AFTER the
frozen write (E1–E2).

## Still open, deliberately

* **The object side.** Sections 1 and 2 have the same defect mirrored: 100% of the object-side
  change lands on section 1, which IS the BS's world position (the split's `fold_point` tracks it
  exactly), so the BS slides while its separately-anchored LED body stays put — the user's *"the BS
  should glue to the LED, cannot be displaced"*, already visible at 23 × 23. bugs/0453 built a
  redirect for exactly this, but its topology test wants *"a promoted solid immediately after the
  object gap"* and this scene's BS is row 3, so it never fires — gluing by hand changes nothing,
  which the user confirmed by trying it. Deferred because it needs a decision this fix does not:
  holding the BS means section 1's share has to move either the LED assembly or the object plane,
  and that is a machine question, not a solver one.
* **"23 × 23 works, although not sharp focus at the image plane"** (flag_20260730_103558) — a
  focus question, not a placement one.
* The bugs/0477 stale-convergence point that made the drawn sensor jump into the mirror at 30 × 30
  ((229.6, 0.1, 91.0), byte-identical to 0477's measurement) should stay out of reach now that the
  leg keeps its clearance, but the `reliable_forward` window that admits it is still brittle.
