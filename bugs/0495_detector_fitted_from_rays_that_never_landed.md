# 0495 — the arm's detector was fitted from rays that never landed

`flag_20260801_190613` — *"drag LED + BS down, sensor misplaced"* — and `flag_20260801_190818` —
*"drag up down: sensor misplaced, object plane missing"*.

Their two siblings are **confirmations** of bugs/0494: `flag_20260801_190650` *"drag it right, it
looks correct"* and `flag_20260801_190720` *"drag left, it looks correct"*.

## What was actually misplaced

Not the sensor. Row 8 sits 58.8–58.9 mm below the fold point in **every** recording, exactly where
it belongs. What moved was the branch **detector** (the synthetic row ≥ 100000), drawn as a tilted
patch on the RA mirror instead of a flat plane at the sensor:

| recording | split z | detector 100000 | sensor row 8 |
| --- | --- | --- | --- |
| `225502` down (pre-0494, "follows") | 79.1 | plane z 20.2 | z 20.2 — coincident |
| `190650` right ✓ | 55.5 | plane z −3.4 | z −3.4 — coincident |
| `190720` left ✓ | 73.9 | plane z 15.0 | — |
| `190613` down ✗ | **66.3** | **patch z[58.1, 74.0], on the mirror** | z 7.5 |
| `190818` up/down ✗ | **66.7** | **patch z[58.4, 74.4], on the mirror** | — |

Every bad state sits at split-axis z ≈ 66.5; every good one is outside that band. **Not a bugs/0494
regression** — the pre-0494 recording `flag_20260731_225718` is in the same band. Fixing the
sideways drag stopped masking it.

## Root cause

`_exit_rays_for_group` takes the LAST segment of **every** ray in the leaf. On a folded arm that
mixes two populations: a ray that dies at the mirror contributes the PRE-mirror direction (+X here),
a ray that reaches the sensor contributes the POST-mirror direction (−Z). Their mean is a 45°
phantom, and everything downstream is computed from it —

* `_closest_approach_point` over the mixed bundle puts the focus **on the mirror**, and
* the bugs/0097 "is the image on this leaf" test (`cos > 0.7`) **fails** on a 45° mean direction, so
  the pin that would have rescued it never fires either.

Measured by hooking `derive_branch_detectors` on the AZ85 scene and dragging the glued LED down
12.54 mm. The arm is `S3:S3/reflect`, and `reaches_designed_image` is **True in both columns** — the
arm was never the problem:

```
before   focus_source=converging_rays   center [229.28, 0.18, 66.04]   normal [0.689, 0, -0.725]
after    focus_source=reached_image     center [229.93, 0.00,  7.46]   normal [0.000, 0, -1.000]
```

7.46 is where that recording put the sensor (row 8 at z 7.5).

## Fix

bugs/0448 had already named the principle — *"read the exit bundle from the SURVIVORS only so the
plane's normal is the beam that actually lands"* — but applied it only inside its `< 0.5` branch,
for the vignette-dominated case. So a **healthy** arm, the majority of whose rays land, kept the
contaminated bundle. The re-read now happens whenever any rays land and some do not, and the focus
is re-fitted from that bundle rather than left over from the mixed one.

The two poses the user called correct are untouched: baseline −5.08 and the +X drag −3.37, both
already pinned before and after.

## Guard

`validate_open3d_0495_detector_reads_the_rays_that_land.py`, penta phase 400. Section A holds the
principle at source level (the re-read precedes the `< 0.5` test, and the focus is re-fitted).
Section B drives the user's two gestures in order on the real scene and asserts the imaging arm
stays pinned, flat (|n·ẑ| = 1) and on the folded arm at x 229.93. Against the pre-fix code it fails
with exactly the recorded numbers — `focus_source='converging_rays'`, normal `[0.689, 0, −0.725]` —
while the two good poses pass in both, so it isolates the defect rather than the scene.

## On "object plane missing"

Row 0's actor is present and byte-identical across all four recordings (`x[−14.3,14.3] z[0,0]`).
The visible difference is that `190650` had the LED selected, which draws the "FOV 20.0×20.0" plate.
Nothing moved or vanished in the model, so it is not addressed here and wants a look at the render.

## Instrumentation gap this exposed

A detector-placement flag records only the drawn bounds. `BranchDetector` already carries
`focus_source`, `reaches_designed_image` and the draw-suppression flag — the three fields that named
this bug in one run — and the recorder captures none of them. Adding them would have turned several
rounds of inference into one string.
