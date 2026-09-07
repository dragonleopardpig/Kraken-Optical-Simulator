# 0735 — a rectangular field fills a rectangular sensor on ONE axis (closes the reserved 0720)

Flag `flag_20260907_104239_564`: *"is this something correct?"* — the scene showed the lens driven
**13.03 mm into RA mirror 1** by the auto-applied force from bugs/0732, for a request of
**"21 × 1.05 mm (needs |m| 1.549)"**.

The crash was displayed correctly. It should never have happened.

## Why

The solve sized its target by the **diagonal**: sensor semi-diagonal ÷ object semi-diagonal. That
is right for a round image circle and wrong for a long thin field. The user's device is 20 × 1 mm,
so with the +5% margin the field is 21 × 1.05 mm, whose diagonal (21.026) is essentially its long
side. The diagonal rule therefore demanded

    |m| = 16.292 / 10.513 = 1.549

where filling a 23.04 mm sensor on the long axis needs only

    |m| = 23.04 / 21 = 1.097

That extra 41% of magnification asked the lens for 172 mm of travel against 158.9 mm of physical
room — 13.03 mm short, which is exactly the penetration the banner reported.

## Fix

`QuickEstimationService._rectangular_target_magnification(W, H)` returns `min(Sw/W, Sh/H)` — the
axis that runs out first — and `fov_solve` encodes it in the image semi it hands
`_apply_conjugate_pair` (which uses the semi ratio as |m|). The idempotence gate (bugs/0727) and
the refusal stash use the same target, and it is computed before both.

A bare lens with no sensor rectangle keeps the diagonal rule, where the image circle really is the
constraint; a zero field or sensor dimension returns None rather than an infinite target.

## Measured (om05a, the user's 20 × 1 mm device)

| | before | after |
|---|---|---|
| target for 21 × 1.05 | \|m\| 1.549 (diagonal) | **\|m\| 1.097** |
| lens move needed | −172 mm (158.9 available) | **−135 mm** |
| outcome | forced crash, **13.03 mm into RA mirror 1** | **clean solve**, nothing penetrates |
| gaps | — | (180.47, 17.93) → (45.43, 152.97) |

## Guard

`validate_open3d_0735_rectangular_fov_target` = penta phase 534: A the rule and its
orientation-awareness, including a non-square sensor; B a bare lens keeps the diagonal rule and
degenerate inputs return None; C the wiring — the target reaches `_apply_conjugate_pair`, the
idempotence gate and the refusal banner, and is computed before them.

bugs/0732's A1 pin was updated for the new call signature.

## 0736 — the banner toggle was where nobody looks

Same session: *"I can't find the off button for the banner in 3D UI."* The bugs/0732 toggle went
into the image-plane **analyses** submenu. A switch for something drawn over the scene belongs in
the top toolbar's **Overlays** menu, with Refs / Det / Miss / Clipped / Focus surf. Moved there as
"Solve banner"; verified reachable and that toggling removes and restores the actor. Pinned by
bugs/0732's guard (check C4).
