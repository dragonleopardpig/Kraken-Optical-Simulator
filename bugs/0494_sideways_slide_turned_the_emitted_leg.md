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

A beam splitter promoted from a STEP carries its coating flagged on **both sides** — measured on
this scene, `functions={'Transmit/Port': 4, 'Beam Splitter': 2}`.
`_interaction_fold_emission` walks bounce after bounce and returns `bounces[-1]`. It has to: a penta
prism deviates by reflecting off two *distinct* Mirror faces, and taking a single face emitted its
intermediate 45° leg (bugs/0485). But for the splitter, whether the walk reached the coating's
second side depended on where the body sat:

```
dx = 0        1 bounce    hit [0, 0, 53.803]                              direction [1, 0, 0]
dx = +12.54   2 bounces   hit [0, 0, 42.819] then [1.556, 0, 42.819]      direction [0, 0, 1]
```

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

## Fix

The beam-splitter branch walks **one** bounce (`max_bounces=1`). A splitter's reflect leg is a
single reflection off one coating; the multi-bounce walk stays exactly as it was for the Mirror path
the penta cascade needs.

Verified by sweeping the splitter sideways on the real scene — the direction is now pinned and the
fold point still tracks 1:1:

| dx | bounces | direction | fold point z |
| --- | --- | --- | --- |
| 0 | 1 | [1,0,0] | 53.803 |
| 8 | 1 | [1,0,0] | 47.359 |
| 12.54 | 1 | **[1,0,0]** (was [0,0,1]) | 42.819 |
| 40 | 1 | [1,0,0] | 15.359 |

## Guard

`validate_open3d_0494_translation_preserves_emitted_direction.py`, penta phase 399. Display-free —
it reads the scene's `SURFACES` directly, no Tk and no renderer, so it costs a second.

Held as the **invariant**, not as the one offset that was reported: *translating a folder moves its
fold point and leaves its emitted direction alone*. That is what a slide means (rule 3, bugs/0487),
and stating it that way also pins the property a rotation-carrying fix must not break (rule 4,
bugs/0488: a folder that genuinely turns must still take its leg with it). The sweep brackets the
reported 12.54 so a knife-edge that merely *moves* still gets caught, and it runs the along-axis
slide as a control.

## Known residual, not fixed here

The same "which face does the walk pick" ambiguity survives at a much smaller scale. The coating's
two flagged sides sit 1.556 mm apart along the incoming axis, and the first bounce takes whichever
plane crossing is nearest in **absolute** distance — deliberately sign-agnostic, because the probe
point is an arbitrary point on the incoming line (bugs/0224). Which side wins therefore still flips
as the body slides, and the fold point jumps 1.556 mm when it does, moving section 1 by that much.
The guard measures and reports it (`NOTE C2`) rather than asserting on it.

Fixing it properly means collapsing a coating's two flagged sides into one optical surface before
the walk, which needs a rule for "same physical surface" that does not also merge a periscope's two
genuinely separate parallel mirrors. Worth doing; out of scope for the reported defect.

Also seen while sweeping: at dx = +40 mm the RA mirror's own emitted direction flips from [0,0,−1]
to [0,0,1]. That is far outside anything the user did, and it is a different derivation (the mirror
has a single Mirror face), so it is recorded here rather than chased.
