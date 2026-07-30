# 0485 — the optical axis as a segment tree (stage 0: derive it, measure against it)

Anchor bug for the redesign the user set out after flags `20260730_160140` ("changed to FOV 30x30,
RA mirror shifted, not centered to optical axis, the fold axis also slanted") and
`20260730_160244` ("drag the LED down ... the BS move together with LED. However, the fold optical
axis should follow as well"):

> 1) When a user delete a BS or Mirror or whatsoever elements that introduce a fold axis (with
>    elements already snap to the fold axis), deleting it means the user no longer want the fold
>    axis, all elements should snap back to the original non-fold axis.
> 2) ... if the user now replace the deleted element ... the subsequent elements snap to the newly
>    formed new axis.
> 3) If the user slide the elements that introduce a fold axis, then all the snapped elements
>    should follow the fold axis.
> 4) Same as (3), if the element ... is now flipped, then all snapped elements should also follow
>    the flipped snap axis.
>
> Strictly speaking, the previous fixes that forces the elements to stay after the BS plate is
> deleted is wrong, it is temporary solution ...
>
> **Mainly there is a optical axis, everything follows.**

## The model

The axis is a **tree of directed segments**. A root segment carries the unfolded axis. A
fold-introducing element at arc-length `s` on segment `P` *emits* a child `C`: origin = the fold
point, direction = `P`'s direction reflected in that element's surface (a BS emits two — transmit
continues `P`, reflect starts `C`). Every other element is **snapped**: it stores
`(segment, s, transverse)` and its world pose is *derived*.

The four rules are then consequences, not features: delete → children re-parent to `P` keeping `s`;
replace → they re-parent to the new child; slide → the child's origin moves; flip → its direction
changes. So do folders in series, both BS arms, non-90° tilts, and "stay put" (an element stays put
*iff* its segment did not move — which is why forcing elements to stay after a delete hard-codes an
outcome that should be a consequence).

`KrakenOS/UI/services/optical_axis_tree.py` implements it as a **pure, read-only** derivation:
`build_axis_tree`, `snap_rows`, `world_pose_from_snap`, `check_invariants`. It stores nothing and
changes nothing. Stage 0's only job is to make the tree measurable against the poses the editor
currently keeps in world space, so a disagreement is a number rather than an argument.

## Stage 0 results

**The parameterisation is sound.** `origin + direction * s + transverse` reproduces every stored
pose on every scene tried:

| scene | rows | folders found | derive-vs-stored worst |Δ| |
|---|---|---|---|
| AZ85 RA mirror + BS | 9 | 2 (rows 3, 7) | **0.000e+00 mm** |
| AZ85 RA mirror (no BS) | 10 | 6 (over-detected, see below) | 3.553e-15 mm |
| Beam Splitter Two Path Doublets | 12 | 0 (not detected) | 0.000e+00 mm |
| five penta prism cascade | 7 | 1 of 5 | 0.000e+00 mm |
| plain doublet | — | 0 (correct — no fold) | 0.000e+00 mm |

**Where the app has authoritative fold data, the tree is exactly right.** On the AZ85 BS scene it
derives the three segments the app draws, with matching origins and directions:

    axis:root     origin (0, 0, 0)          dir (0, 0, 1)     <- the object axis
    axis:fold:3   origin (0, 0, 53.803)     dir (1, 0, 0)     <- == axis:global:split (the BS)
    axis:fold:7   origin (229.93, 0, 53.803) dir (0, 0, -1)   <- == axis:global:frozen-fold:7

## Flag 160140, diagnosed: a CONTINUITY violation

A child segment's origin **must lie on its parent** — a beam cannot leave an axis it never met.
As loaded that holds. After a 30 × 30 FOV solve:

    CONTINUITY axis:fold:7 (from row 7) starts 5.3302 mm OFF its parent axis:fold:3
      origin (253.495, 0, 48.473); parent runs (0, 0, 53.803) along (1, 0, 0)

The mirror's fold point hangs 5.33 mm below the beam feeding it. That *is* "RA mirror not centered
to optical axis", and it is why the emitted leg draws slanted (3.39° measured): the leg starts off
the beam. Pre-existing — measured at −6.12 mm before bugs/0482/0484 and −5.33 mm after, so those
fixes did not introduce it (my first attribution said otherwise and was wrong: it normalised
against the as-loaded axis z while the object-side hold moves where that axis is).

The 0.1221 mm TRANSVERSE report on row 3 is the BS's own authored decentre (`desp_x = −0.1221`),
not a defect.

## The structural finding

**There is no authoritative "which rows fold the axis, and what does each emit" function.** Stage 0
had to reconstruct it from three unrelated sources — the object conjugate split, the image
conjugate split, and the promoted-solid pose-override map — and that reconstruction is wrong on 3
of 5 scenes:

* the override map's keys are the rows a fold *repositions*, not the rows that fold, so the
  single-fold AZ85 scene reported 6 folders (rows 2–7, all emitting +x);
* the Two Path Doublets BS is not a promoted solid and has no split record, so 0 folders were
  found and its two arms read as 70–130 mm transverse offsets on the root;
* the penta cascade needs 5 folders and only the first is visible this way.

That absence is the root cause of the pattern this session kept hitting: with no model object for
"the axis", every mutation path has to keep world poses consistent by hand, and the freeze state
(`stay_put_freeze`, `last_axis_to_axis_move`) is written from **nine different modules**. The
detection heuristics deliberately were NOT hardened in the probe — the fix belongs in the model.

## Next (stage 1)

Introduce the authoritative emission source — one function answering "does this row fold the axis,
and what does it emit?" covering marked BS coatings, `Mirror` surfaces and folding promoted solids
— and make the **axis records** derive from the tree instead of from poses. That fixes flag 160244
(the axis follows a dragged BS) and the slanted leg, without yet changing how poses are stored.
Stages 2–3 (flip the storage to `(segment, s)`, then retire `stay_put_freeze` as a mode) will
deliberately change guards that pin today's behaviour — 0433's stay-put, 0447, 0448, 0478, 0479,
0482, 0484 — each with its reasoning recorded.
