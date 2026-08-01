# 0494 — sliding the splitter sideways turned its emitted leg 90°

`flag_20260731_225718` (build `ef53736d`) — *"drag again the LED, this time to the right, everything
misplaced."*

Its sibling `flag_20260731_225502`, one gesture earlier in the same session — *"drag LED down:
elements now follow"* — is a **confirmation**: bugs/0493 verified in the live app. So the carry was
working; only the sideways direction broke it.

## What the recording shows

Comparing the good snapshot against the broken one:

```
LED body            dx = +12.54   dz = 0        the drag
BS row 3 actor      dx = +12.53   dz = 0        glue carried it, correct
BS row 3 desp       desp_x -0.122 -> +12.418, desp_z and tilt UNCHANGED
axis:global:split   z 79.09 -> 66.55, still along +X          <- the fold POINT is right
row 7 tilt          (0,0,0) -> (0,-90,0)                      <- ROTATED
axis frozen-fold:7  along -Z  ->  along +X                    <- ROTATED 90 deg
row 1 actor         a plane perpendicular to X  ->  perpendicular to Z
lens body           dx = -95.85  dz = +86.42
camera body         dx = -168.83 dz = +299.47
rays                missed_image 255 -> 558
```

The fold point behaved correctly throughout: a 45° coating slid +12.54 in X drops the point where
the fixed Z axis crosses it by the same 12.54 in Z, and 79.09 − 66.55 = 12.54. Only the *direction*
was wrong.

## Root cause

The beam splitter is a **1.1 mm plate**, and its promotion flagged **both large parallel sides** as
`function="Beam Splitter"` / `port_role="Interaction Surface"` — 8123.5 mm² each, their planes
1.5556 mm apart along the incoming axis (= 1.1 / cos 45°). Measured on this scene:
`functions={'Transmit/Port': 4, 'Beam Splitter': 2}`.
`_interaction_fold_emission` walks bounce after bounce and returns `bounces[-1]`. It has to: a penta
prism deviates by reflecting off two *distinct* Mirror faces, and taking a single face emitted its
intermediate 45° leg (bugs/0485). But for the splitter, **which side the walk took first** depended
on where the body sat — the first bounce is chosen by *absolute* distance from a probe point that
does **not** move when the body slides (sign-agnostic on purpose, bugs/0224), so the ranking of the
two sides inverts at `desp_x = 0` exactly:

```
desp_x <= 0    near side first, far side 1.5556 mm BEHIND  -> forward_only rejects -> 1 bounce, +X
desp_x >  0    order INVERTED, other side 1.5556 mm AHEAD  -> accepted            -> 2 bounces, +Z

dx = 0        1 bounce    hit [0, 0, 53.803]                              direction [1, 0, 0]
dx = +12.54   2 bounces   hit [0, 0, 42.819] then [1.556, 0, 42.819]      direction [0, 0, 1]
```

**The trigger is the SIGN of the drag, not its size.** Any rightward nudge, however small, turned
the leg; leftward and axial drags never did. That is exactly what the user reported — "drag LED
down" worked, "this time to the right" did not. The hit radius never discriminates: it is
sqrt(8123.5) + 2 = 92.13 mm against a 15.9 mm miss.

Two reflections off one 45° plate send the beam straight back down the incoming direction:
+Z → +X → +Z. `_fold_slide_carry_apply` compares the emitted direction before and after and, seeing
a change, reads it as a rule-4 **rotation** — applying `new = fold_after + R (old − fold_before)`
with R carrying +X onto +Z, and rotating every follower's tilt to match.

Solving R from the recording confirms it: `R (229.93, 0, 0) = (1.56, 0, 227.80)`, i.e. +X → +Z. The
three bodies land where that predicts — row 7 at (0,0,296.5) against (1.56,0,294.35) measured, the
lens at (0,0,164.0) against (1.56,0,165.51), the camera z 296.5 against ~296. The stray `x = 1.556`
in the recording is the *second bounce's hit point*, which is how the fingerprint closes.

Nothing was wrong with the carry, the glue, or the rotation maths. The emission derivation handed
them a direction that a pure translation had silently turned.

## Why the drawn axis disagreed with the model

The drawn `axis:global:split` stayed along +X throughout, which is what made the recording look
self-contradictory. It comes from a **different derivation**: `beam_splitter_coating_world_frames`
(bugs/0428) calls `select_optical_solid_interaction_face`, which picks exactly ONE face by
(priority, area) and reflects once. Two geometry paths over the same solid, free to choose different
sides of the same plate — the very drift `axis_fold_emissions` was written to end ("the geometry
below is the SAME primitives the follower builder uses, so the two cannot drift").

## Fix

Two parts, both in the beam-splitter branch:

1. **Reflect off the face the drawing reflects off.** The branch now calls
   `select_optical_solid_interaction_face` — the same selector `beam_splitter_coating_world_frames`
   uses — so model and drawing agree by construction. (It falls back to the full walk if a
   Mirror/uncoated face outranks the coating, so a mixed solid is unaffected.)
2. **Walk one bounce** (`max_bounces=1`). A splitter's reflect leg is a single reflection off one
   coating. The multi-bounce walk stays exactly as it was for the Mirror path the penta cascade
   needs.

Part 1 alone fixes the reported turn; part 2 states the intent and keeps a second flagged side from
ever mattering again.

Verified by sweeping the splitter sideways on the real scene — the direction is now pinned and the
fold point still tracks 1:1:

| desp_x | bounces | direction | fold point z | slope |
| --- | --- | --- | --- | --- |
| −20.12 | 1 | [1,0,0] | 73.803 | |
| −0.12 | 1 | [1,0,0] | 53.803 | −1.000 |
| **0.00** | 1 | [1,0,0] | 53.681 | **−1.000** (no jump) |
| +0.08 | 1 | [1,0,0] | 53.603 | −1.000 |
| +12.42 | 1 | **[1,0,0]** (was [0,0,1]) | 41.263 | −1.000 |
| +19.88 | 1 | [1,0,0] | 33.803 | −1.000 |

## Guard

`validate_open3d_0494_translation_preserves_emitted_direction.py`, penta phase 399. Display-free —
it reads the scene's `SURFACES` directly, no Tk and no renderer, so it costs a second.

Held as the **invariant**, not as the one offset that was reported: *translating a folder moves its
fold point and leaves its emitted direction alone*. That is what a slide means (rule 3, bugs/0487),
and stating it that way also pins the property a rotation-carrying fix must not break (rule 4,
bugs/0488: a folder that genuinely turns must still take its leg with it). The sweep **straddles
zero** (−20 … +30), because the trigger was the sign of the drag rather than its size, and it runs
the along-axis slide as a control. C2 additionally pins model and drawing to the same coating plane
at every offset.

## The 1.5556 mm residual — also fixed

Capping the bounce alone would have left the *origin* wrong: the first-face pick still inverted at
`desp_x = 0`, so the fold point jumped 1.5556 mm to the plate's other side and the carried leg then
sat that far off the drawn coating axis for every subsequent lateral drag. Small enough to read as a
solver artefact, and it moves section 1 (the working distance) by the same amount.

Selecting the drawing's face removes it. Measured across the sweep, the fold point now tracks the
slide with slope −1.0000 **through `desp_x = 0`**, and its distance from the drawn coating plane is
below 1e-6 mm at every offset — guard checks C1 and C2.

Also seen while sweeping: at dx = +40 mm the RA mirror's own emitted direction flips from [0,0,−1]
to [0,0,1]. That is far outside anything the user did, and it is a different derivation (the mirror
has a single Mirror face), so it is recorded here rather than chased.
