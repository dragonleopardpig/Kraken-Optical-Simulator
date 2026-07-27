# 0456 — Frozen-scene FOV solve moves the STEP bodies OPPOSITE to their rows

**Flag `flag_20260727_195719_048`** ("changed FOV to 20x20 and set constraint, elements shifted off
optical axis, and others wrong as well"), recording `recording_20260727_195858.json`, build
`1ab4f101` (i.e. WITH 0447 + 0449 + 0453/0454/0455). Regression in the **bugs/0447** frozen-scene
solve — my work; owning it here.

## What the recording proves (one event, t=249.8 s: the constrained FOV solve)

| item | before (t=109.7 s) | after (t=249.8 s) | Δz |
|---|---|---|---|
| chain rows (front datum … rear datum) | 54.3 | 50.0 | **−4.3** |
| BS row | 56.0 | 51.6 | −4.4 |
| Image row | −48.7 | −53.0 | −4.3 |
| **lens STEP barrel** | 54.3 | 71.1 | **+16.8** |
| **camera STEP body** | 2.8 | 19.6 | **+16.8** |
| **LED STEP body** | 74.4 | 95.5 | **+21.1** ( = 16.8 + 4.3 ) |

Every ROW moved **−4.3** while every BODY moved **+16.8** — opposite directions, so the surrogate
and its CAD detach: the barrel now floats 21.1 mm off the datum rows it is pinned to, and the camera
body sits 72 mm from its sensor row. The LED's Δ is exactly the body shift PLUS the row shift, i.e.
it received both corrections where the others received one.

Everything up to that event is healthy (rows and bodies tracked together through the freeze at
t=88.4 s and the snap at t=109.7 s: rows 54.3 / barrel 54.3).

## Suspected root (to confirm before fixing)

`_apply_folded_object_split` / `_apply_folded_image_split`'s `frozen_world` branches (bugs/0447)
slide the pinned leg and then carry the bodies. Candidates, in order:

1. **Sign**: the body carry applies `+δ` along the leg while the rows are re-baked at `−δ` (or the
   carry uses the pre-move anchor after the rows were already re-baked — the 0433-C pivot lesson).
2. **Double application on the LED**: the LED is carried once by the object-side slide and again by
   the glue/assembly carry (its Δ is the sum of the other two deltas — a strong hint).
3. The ordinary conjugate solve (`_apply_conjugate_pair`) ALSO ran and moved gaps, on top of the
   frozen branch — the two corrections then compose instead of one replacing the other. bugs/0453
   changed which side that redirect holds (topology instead of the glue bool), so the two code paths
   now interact differently than when 0447 was verified.

The 0447 probe asserted chain rigidity to 1.4e-14 but compared **rows only** — it never asserted the
STEP bodies against their anchor rows after a frozen solve, which is exactly the gap this flag fell
through. Any fix must add that assertion (probe_0449's `_barrel_vs_datum` fold-aware helper is the
ready-made check).

## Repro (headless)

Pristine AZ85 → delete mirror-1 (freeze) → select row 1 → add plate BS → snap the chain onto
`axis:global:split` with a `picked_world` → open the FOV popup → set 20×20 → tick a fold-leg pin →
Solve for Thickness. Assert after the solve: every STEP body's world pose still agrees with its
anchor row (lens ↔ front datum, camera ↔ Image), and the chain stays on the leg.

## Status

Documented, not yet fixed — the session ran out of budget to fix AND verify this safely, and a blind
edit in the solve path is exactly what must not ship. The other round-7 flag
(`flag_20260727_160952`, "unable hide the manual thickness overlay") was already fixed by **0455**
(`6a8ca382`) on a later build.
