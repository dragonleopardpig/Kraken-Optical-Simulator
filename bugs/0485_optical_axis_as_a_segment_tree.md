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

## Stage 1a: naming the decision, and what measuring it exposed

The user's refinement, which the model needs before any auto-re-snap is written:

> the BS replace or slot in existing optical element chain, those elements should stay because there
> are 2-axis. Let the user rubberband select and snap to the optical axis he wants.

So a folder has a **kind**, and the code already distinguished the two under different bug numbers:

* `FOLD_KIND_CONSUMING` — a full mirror. bugs/0185: *"a full mirror has NO straight-through path --
  the beam physically reflects off the mirror face (the user's 'only one way the ray can go')"*. One
  leg leaves, the incoming axis ends, downstream elements have a single place to go, so
  delete/replace/slide/flip may re-snap them without asking.
* `FOLD_KIND_BRANCHING` — a beam splitter. bugs/0398: *"a BEAM SPLITTER never folds the downstream
  imaging chain ... the reflected 2nd branch is handled separately"*; bugs/0428 exposes its coating
  as *"the geometry needed to draw its REFLECT-branch axis (the '2nd optical axis'; the transmit leg
  is axis:global)"*. Two axes exist, so membership is ambiguous and elements must STAY — the user
  assigns them with the bugs/0433 rubber-band snap, whose `_row_explicitly_axis_snapped` flag
  already means "this element's axis is the user's choice, not an inference".

`nonseq_output_ports.axis_fold_emissions(rows)` names that decision, reusing the follower builder's
own primitives so the two cannot drift, and threading the incoming direction down the chain so a
second mirror reflects the FIRST mirror's leg (bugs/0213: *"the fold direction is the mirror's
orientation, never a hard-coded axis"*).

**Measured, it finds nothing on the scene that matters** — and that is the finding:

| scene | folders found | expected |
|---|---|---|
| AZ85 RA mirror + BS | **0** | 2 (BS row 3, mirror row 7) |
| AZ85 RA mirror (no BS) | 2 (rows 1, 8) | 1 |
| Beam Splitter Two Path Doublets | 0 | 1 |
| five penta prism cascade | 1 | 5 |
| plain doublet | 0 (correct) — all invariants hold | 0 |

The classifier is faithful to the follower builder; the builder simply has nothing to say about the
AZ85 scene, because that scene is **FROZEN**. `_frozen_scene_has_no_fold_overrides()` is true there
— which is exactly why the frozen conjugate splits are what describe its folds at all (bugs/0447).

**There are therefore TWO parallel fold representations:**

1. the **live** one — assigned face functions, output ports, `optical_solid_output_port_pose_overrides`;
2. the **frozen** one — baked world poses plus `_folded_object_conjugate_split` /
   `_folded_image_conjugate_split`.

Stage 0 read (2) and got the AZ85 scene exactly right; stage 1a reads (1) and gets it empty. And a
third gap: the Two Path Doublets BS is not a promoted solid, so neither path sees it.

That duplication is the deeper reason this session kept finding bespoke "frozen" branches --
bugs/0447, 0448, 0478, 0479, 0482, 0484 each carry one. The authoritative emission source has to
span both representations (and non-promoted BS rows) before any of the four rules can be
implemented on top of it, because a rule that fires on one representation and not the other is
worse than no rule.

`axis_fold_emissions` is committed as-is: additive, read-only, called by nothing in production. Its
value right now is the measurement above.

## Stage 1b: one derivation for live AND frozen

Stage 1a's classifier found nothing on the flagged scene, and the reason turned out not to be
frozenness at all. Instrumenting every guard, per row:

* **row 3 (the BS)** -- coating faces present, ``marked_BS=True``, but ``specular=False``.
  ``_reflected_frame_from_interaction_face`` refuses a ``Beam Splitter`` function on purpose
  (``_is_specular_fold_interaction_face`` accepts Mirror/uncoated only) because a BS must never
  fold the FOLLOWER chain (bugs/0398). It does still EMIT a reflect axis -- bugs/0428's coating
  geometry -- so the axis derivation has to reflect off the coating directly.
* **row 7 (the RA mirror)** -- ``full_mirror_face=True``, ``specular=True``, and STILL no frame,
  because of the bugs/0224 hit-radius test: *"a mirror face only folds the frame when the beam
  LINE actually crosses the face"*. The mirror sits at x = 229.93 on the BS's reflect leg, and the
  probe line ran from ``(0, 0, z_station)`` along +Z, which never reaches it. The helper was right;
  the input was wrong.

**Each folder must be probed from the axis that actually feeds it, and which axis that is, is told
by the folder's own POSE.** That single change is also what removes the live/frozen split: a frozen
scene has no live fold overrides but it still has poses (``station + desp``) and the same face
records, so there is no frozen branch in the derivation at all.

Two further corrections the measurement forced:

* **a full mirror outranks an inferred port.** The old order tried the output face first and only
  reached the mirror when ``_exit_frame_is_non_folding`` fired -- a test against the INCOMING
  direction, so it worked only while every probe used the nominal +Z axis. Once row 7 was correctly
  probed from (1,0,0), its +Z Transmit/Port face stopped looking codirectional and it emitted
  ``(0,0,1)`` from an inferred port. Rank on what the face IS (bugs/0185), not on where the beam
  came from.
* **an axis wants the CROSSING, not the exit frame.** ``_reflected_frame_from_interaction_face``
  returns ``hit + reflected * (thickness - pre_hit_run)`` with ``pre_hit_run`` measured from the
  row's station marker (bugs/0207) -- correct for follower bookkeeping, but it moves when the probe
  point moves along the same line. Measured: penta prism 1's fold point shifted z 57.626 -> 96.517.
  ``_interaction_fold_emission`` intersects the leg with the face plane instead, keeping the
  bugs/0224 hit test, so the answer depends only on the line.

### Result

On the flagged scene the derivation now reproduces the app's own frozen records to machine
precision, from faces and poses alone:

| fold | app's record | classifier | \|Δorigin\| | \|Δdir\| |
|---|---|---|---|---|
| BS row 3 | (0, 0, 53.8032) → (1,0,0) | identical | **7.11e-15** | 4.58e-12 |
| mirror row 7 | (229.9299, 0, 53.8032) → (0,0,−1) | identical | **2.38e-10** | 2.40e-15 |

and it classifies them correctly: row 3 ``branching`` (the transmit leg carries on), row 7
``consuming`` with ``parent_row=3`` -- i.e. it knows the mirror hangs off the BS's reflect leg,
which is the fact stage 1a could not represent.

### Both gaps closed

**Multi-bounce solids.** A penta prism carries TWO ``Mirror`` faces and deviates the beam 90° by
reflecting off both; taking a single interaction face emitted its intermediate 45° leg, after which
the rest of the cascade no longer lay on the axis (1 of 5 found). ``_interaction_fold_emission`` now
WALKS the leg through the solid -- reflect, then look for the next accepted face the beam actually
reaches -- and returns every bounce. The first crossing stays sign-agnostic in distance (bugs/0224:
the probe point is an arbitrary point on the incoming line, so only the lateral offset
discriminates a real fold); every later bounce must be strictly forward, or the beam would re-hit
the face it just left at distance zero.

**Plain surface rows.** ``Beam Splitter Two Path Doublets``' splitter has no optical solid at all,
so the face-record path could not see it. ``_surface_row_fold_emission`` folds such a row about its
own plane, taking the normal from ``rotation_matrix_from_kraken_tilts(...) @ (0,0,1)`` -- the
convention the 3-D tools, the 2-D polyline display and the face-roles dialog already share, rather
than a fresh one (bugs/0448 is what a second tilt convention costs).

All five scenes now resolve correctly:

| scene | folders | detail |
|---|---|---|
| AZ85 RA mirror + BS | **2** | row 3 branching, row 7 consuming with `parent_row=3`; matches the app's records to 7e-15 |
| AZ85 RA mirror (no BS) | **2** | a genuine two-fold periscope -- verified, the scene really carries two mirror-bearing rows (S1, S8). The earlier "expected 1" was an unverified guess, not a defect |
| five penta prism cascade | **5** | 2 bounces each, a clean 90° per prism, chained +z → −y → +x → +z → +y → −x, each parented to the previous |
| Beam Splitter Two Path Doublets | **1** | surface-row BS, branching at (0,0,45) → (0,1,0), matching its reflect doublet at y = 70–130 |
| plain doublet | **0** | no fold |

``axis_fold_emissions`` remains called by nothing in production.

## Next

Introduce the authoritative emission source — one function answering "does this row fold the axis,
and what does it emit?" covering marked BS coatings, `Mirror` surfaces and folding promoted solids
— and make the **axis records** derive from the tree instead of from poses. That fixes flag 160244
(the axis follows a dragged BS) and the slanted leg, without yet changing how poses are stored.
Stages 2–3 (flip the storage to `(segment, s)`, then retire `stay_put_freeze` as a mode) will
deliberately change guards that pin today's behaviour — 0433's stay-put, 0447, 0448, 0478, 0479,
0482, 0484 — each with its reasoning recorded.
