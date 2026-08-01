# 0499 — a lens drag along a FOLDED optical axis is treated as lateral, so the optics stay behind

`flag_20260801_210453` (build `e78c7c59`) — *"clicked glue STEP to surrogate, drag right, it is
still detached."*

## The glue worked; the drag undid it

The recorded state is the as-loaded scene in every respect **except** the lens: rows 1/6/7/8, both
axis records, the LED and camera overlays are all at their original values. Only the lens differs —
overlay offset x **119.26** against the reference **97.406**, body at x[89.66, 148.85].

Read in the order the user wrote it — glue, *then* drag right — that is 97.406 restored by the glue
(bugs/0497 working) plus a 21.85 mm drag. The complaint is that the drag detaches it again: the body
moves and its optical surrogate does not follow.

## Root cause

`translate_step_overlay` decides axial-vs-lateral for a lens with

```python
if label == "lens" and overlay_on_axis and abs(float(delta[2])) > 1e-9:
```

`delta[2]` is the **world Z** component. The intent is documented right there: an AXIAL drag
redirects into the gap before the front datum so "every lens row and the glued rear datum move
together ... the optics respond to the new lens position", while "lateral drag still only centres
the body".

That test is only the optical axis on an **unfolded** scene. Here the lens sits on the beam
splitter's +X leg, so dragging along its own optical axis produces `delta = (21.85, 0, 0)` and
`delta[2] == 0`. The drag is classified lateral, the optics are left behind, and the body slides off
its surrogate — exactly "still detached".

The same world-axis assumption is what bugs/0475 fixed for the camera and bugs/0497 for the lens
placement. This is the third instance, in the drag classifier.

## Fix — not yet written

Project the drag onto the lens's ACTUAL optical axis instead of testing world Z: the surrogate's
front and rear datum rows already give that direction (`_lens_datum_row_index("front"/"rear")` plus
`_fold_carry_row_world_pose`, both used by bugs/0497), so

```
axial   = dot(delta, leg_dir)      # redirect into the gap before the front datum, as today
lateral = delta - axial * leg_dir  # centre the body, as today
```

On an unfolded scene `leg_dir` is +Z and this reduces to the present behaviour exactly — the same
reduction test bugs/0497 used, and the check that it is a generalisation rather than a new rule.

Care needed: the axial branch rewrites `rows[lens_front_idx - 1].thickness`, so it changes the
object-to-lens gap and the focus. Worth confirming on the folded scene that the redirect lands on
the gap that is actually upstream of the lens on its leg, not merely the row before it in index
order — the two coincide unfolded and need not when frozen (see the bugs/0448 "frozen gap rows run
backwards" family).

## Guard it needs

Drag the lens along its leg on the FOLDED scene and assert the surrogate rows follow, so body and
optics stay together; drag perpendicular and assert only the body centres; and assert the unfolded
scene is unchanged.
