# 0256 — Navigation cube: corner ISO flip must be ONE global decision (adjacent corners agree)

User flags (2026-07-08, after testing 0255) — three in-app recordings:

* `flag_20260708_092959_812` — **"Upside down Left"**: a LEFT face view rolled to
  view-up `(0, 0, -1)`.
* `flag_20260708_093018_972` — **"clicked Right Top Corner, it is reversed."**
* `flag_20260708_093049_413` — **"clicked Right Bottom corner, completely wrong."**

## Forensics

All three recordings are on the 0255 build (~10 min after that commit). The camera states:

| flag | corner offset | resulting view-up | vs. ISO up |
| --- | --- | --- | --- |
| …972 "Right Top … reversed" | `iso_corner_pose((-1, 1, -1))` | `(-0.31, -0.914, -0.261)` | **= −abs_proj (FLIPPED)** |
| …413 "Right Bottom … wrong" | `iso_corner_pose((-1, 1, 1))` | `(0.31, 0.914, -0.261)` | **= +abs_proj (UPRIGHT)** |

Both corners kept the wide-screen fit (parallel scale 178.2 on each — `±abs_up` give the same
orthographic fit, as designed in 0255). So this round is **not** about zoom; it is about
**orientation**: two adjacent corner clicks resolved to **opposite** up/down senses — one flipped,
one upright — which reads as "reversed" then "completely wrong."

## Root cause

0255's `relative_up_about_sight` decided the 180° flip from
`dot(current_up_projected_onto_THIS_corner's_sight_plane, abs_proj) < 0`. Both operands are
projected onto **each corner's own** sight plane, and adjacent corners have **different** sight
planes, so the sign of that dot can differ between neighbours. From a **tumbled** starting view
(flag 1's up = `(0, 0, -1)` is a 90° roll, where `current_up · world_+Y = 0` — the up/down sense is
exactly ambiguous), the per-corner projection tips one way for one corner and the other way for its
neighbour. Result: neighbouring corners flip inconsistently.

## Fix — one global up/down decision for all corners

`relative_up_about_sight` now decides the flip from a **corner-independent** quantity: the live
camera up vs the **absolute** ISO up itself (not their per-corner projections):

```
flip 180°  iff  dot(current_up_hat, abs_up_hat) < -_UPSIDE_DOWN_EPS
```

* **Consistent:** the decision no longer depends on the corner's sight plane, so **every** corner
  flips together — adjacent corners can never disagree again.
* **Keeps the 0254 ask:** a clearly upside-down view (`dot < 0`) flips all corners → the visible
  labels stay upside down.
* **Keeps the 0255 wide screen:** the returned up is still the absolute ISO up **projected onto the
  corner's sight plane**, only optionally negated — always collinear with `abs_proj`, so `±abs_up`
  fit identically and the long optical axis still spreads across the wide screen.
* **Tumbled deadband:** a ~90° view (`dot ≈ 0`, e.g. flag 1's `(0,0,-1)`) has no well-defined
  up/down, so it stays **upright** rather than guessing a side (`_UPSIDE_DOWN_EPS = 1e-6` at the
  `dot = 0` boundary). This is the intended, predictable resolution of the ambiguous case.

`iso_corner_pose` / `orientation_pose` and the inspector/widget wiring are **unchanged** — only the
helper's flip criterion changed (per-corner projected dot → global unprojected dot), so the
0249/0252/0253 guards stay green and the inspector call site (`GetViewUp()` + gate on
`orientation_kind == "corner"`) is untouched.

**Tradeoff (intended):** the tumbled 90° start resolves to upright for all corners rather than
keeping the "upside down" feel — but a 90° roll has no well-defined upside-down ISO, and the user's
complaint was the *inconsistency* between adjacent corners, which this removes.

## Guard

`validate_open3d_nav_cube_corner_local_up` (display-free) **refines penta Phase 230** in place (no
new phase — 0256 changes 0255's exact flip criterion, so its guard is updated rather than
duplicated):

* **A** — unchanged per-corner checks: unit, ⊥ sight, collinear with the projected ISO up
  (`|dot| == 1`, wide-screen fit); an upside-down current up flips + stays world-Y < 0; an upright
  current up stays upright.
* **E** — **global consistency (the crux of 0256):** a given current up drives **all 8** corners to
  the **same** side — clearly-upside-down flips all, clearly-upright flips none — and every corner
  stays collinear with the ISO up regardless of side. Directly pins out the "Right Top reversed /
  Right Bottom completely wrong" split.
* **F** — **tumbled deadband:** a ~90° view (`current_up · world_up ≈ 0`, incl. flag 1's
  `(0,0,-1)`) stays upright for **every** corner.
* **B/C/D** — unchanged: degenerate fallback; inspector reads `GetViewUp()` + gates on
  `orientation_kind == "corner"`; widget forwards the picked `sign`.

Phase 230 title updated to "nav cube corner ISO — one global up/down flip for all corners keeps the
current sense and the wide-screen fit"; baseline title updated to match. Standalone guard PASSes.

## Notes

* Pure-math + source-contract guard is display-free. The **live** feel (roll a face, click two
  adjacent corners, confirm they now agree on up/down **and** fill the wide screen) is still owed an
  in-app eyeball — headless can't drive the embedded-VTK camera.
* Corners only. Faces still snap to their exact cardinal preset and edges to their projected-up.
