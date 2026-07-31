# 0491 — the fold carry moved the model and left the drawing behind

Two flags describe the same thing from opposite ends:

* `flag_20260730_160244` — *"drag the LED down to test the glue function. The BS move together with
  LED. However, the fold optical axis should follow as well."* `axis:global:split` was
  **byte-identical** (z = 53.803249) after the BS had moved 22.16 mm.
* `flag_20260731_192318` — *"BS glued to LED and drag down: the rest not following."* Row 7's
  `desp_z` moved −235.102 → −209.831 (**+25.27 mm**) while its `row_actor_bounds` stayed at
  z[41.16, 66.50].

In both, **the model was right and the drawing was not** — which is worse than a plain bug,
because it makes correct behaviour look broken and it defeats every eyeball check on the fold work.
On 192318 the chain had carried properly and still read as "not following".

## Cause

The bugs/0487 carry rewrites carried rows' `desp` directly, outside the ordinary edit path. The
preview trace is cached against `_last_preview_trace_signature`, so the refresh that follows a drag
can legitimately reuse a bundle built before the carry — and the actors keep their old poses.

Earlier evidence that the *derivation* was never the problem: on a moved BS row, the coating
centroid follows exactly (z 54.070 → 76.227 for a +22.157 mm move) and so does the axis derivation
(53.803 → 75.960). Nothing computed is stale; only what was cached.

## Fix

`_fold_slide_carry_apply` marks the preview trace dirty
(`_invalidate_preview_scene_trace`) once the carry has moved rows and bodies, so the next build
cannot reuse the pre-carry bundle. Verified:

    dirty before carry            False
    dirty after mirror slide      True
    dirty after glued LED drag    True

## The second half, measured after the first fix shipped

`flag_20260731_210040` — *"dragged glued BS and LED, the rest not followed. This is after quit
Kitty and relaunched."* — on build `bf06e2b9`, i.e. with the cache invalidation in and no possible
stale-process explanation:

| | as loaded | in the flag | |
|---|---|---|---|
| LED body | z 5.60 | z 20.99 | +15.39 (the drag) |
| BS row 3 `desp_z` | −103.676 | −88.285 | **+15.39** model |
| mirror row 7 `desp_z` | −235.102 | −219.711 | **+15.39** model carried |
| mirror row 7 **actor** | z[41.30, 66.30] | z[41.16, 66.50] | unchanged |
| lens body **actor** | z[26.30, 81.30] | z[26.30, 81.30] | unchanged |
| `axis:global:split` | z 53.803 | z 53.803 | unchanged |

Every carried row's `desp` moved and **not one** actor or axis record did. Only row 3's actor moved
(+15.25) — that is the body being dragged, which gets a cheap live transform.

So invalidating the cache was necessary and not sufficient: **no retrace ran at all**.
`_apply_scene_placement_translate_handle` calls `refresh_from_editor()` with no `force_retrace`,
and nothing else asked for one.

`refresh_from_editor` now promotes itself to a retrace whenever the EDITOR reports
`_preview_scene_trace_dirty`, whatever the caller asked for. Enforced there rather than at each
call site deliberately: this is the third time the family has been fixed one caller at a time
(bugs/0248, 0296, 0298 — *"eleven others retraced the 3D and left the 2D showing the OLD
prescription"*). Guard the invariant, not the instance.

## Scope — what this does not do

It removes the **cache** cause. It does not force a refresh to happen: the row-gizmo commit
(`_apply_scene_placement_translate_handle`) calls `refresh_from_editor()` **without**
`force_retrace=True` and does not route through `_apply_model_change()`, which is the bugs/0298
pattern. `validate_open3d_model_change_marks_2d_stale` does not catch it because that guard is
about pairing a retrace with 2D staleness and accepts `_stl_placement_dirty = True` as the marker —
a different concern.

Actors still cannot be built headlessly here, so the retrace promotion is verified by its
precondition (the dirty flag flips) and by regression rather than by observing the actors move.
That last step needs a live drag.

0487, 0489, 0437, 0486 and the model-change pairing guard all PASS; 54/54 pytest. Gate --phases
8,251,381,382,386,389,392..395 = 9 pass, 1 known-failing (251, in baseline) -- phase 8 included on
purpose, since it is the "second rays-on lost segments" check the force_retrace path warns about.


## Third attempt: the flag the mid-drag refresh was eating

`flag_20260731_211354` — *"Ctrl+z LED move back the position, glue the BS, slide down, the rest of
the components are not following"* — on `4e793239`, i.e. WITH the forced-retrace promotion in:

    BS row 3 desp_z   -103.676 -> -79.355   +24.32   model
    mirror row 7      -235.102 -> -210.781  +24.32   model carried
    row 3 ACTOR       z[16.77,92.15] -> z[40.95,116.61]   +24.2   (mirrored live, bugs/0137)
    row 7 ACTOR       z[41.30,66.30] -> z[41.16,66.50]    unchanged
    lens / camera ACTORS, axis:global:split               unchanged

So the promotion never fired. `_preview_scene_trace_dirty` is **consumed by any build** —
`three_d_scene_tools` sets it to `not trace_rays`, the async trace clears it outright — and the
glue carry runs every drag FRAME (bugs/0137). By the time the drag is released the flag is already
False, so a refresh keyed off it does nothing. Demonstrated directly:

    pending_rebuild after carry   True
    trace_dirty after one build   False      <-- consumed
    pending_rebuild survives      True

`_fold_slide_carry_apply` now also sets `_fold_carry_pending_rebuild`, a marker no intermediate
build touches, and `refresh_from_editor` promotes to a retrace when it sees it — clearing it only
then, and only when no drag is still in flight so the interactive path never becomes a ~2 s rebuild
per frame (bugs/0024).

Why bugs/0137 makes this hard to see: during a drag the glued partner's ACTORS are mirrored by the
same world delta, so the BS tracks the LED live. Everything the fold carry moves has no such
mirror, so the chain depends entirely on the rebuild at release. That is why row 3 looks right and
nothing else does.

Gate --phases 8,24,251,382,386,389,392..395 = 9 pass, 1 known-failing (251, in baseline); 54/54
pytest. Phases 8 and 24 included on purpose: the rays-on segment check and the drag-interactivity
check are what a wrongly-scoped retrace would break.
