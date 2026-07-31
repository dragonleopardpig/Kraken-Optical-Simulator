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

## Scope — what this does not do

It removes the **cache** cause. It does not force a refresh to happen: the row-gizmo commit
(`_apply_scene_placement_translate_handle`) calls `refresh_from_editor()` **without**
`force_retrace=True` and does not route through `_apply_model_change()`, which is the bugs/0298
pattern. `validate_open3d_model_change_marks_2d_stale` does not catch it because that guard is
about pairing a retrace with 2D staleness and accepts `_stl_placement_dirty = True` as the marker —
a different concern.

So if the drawing is still stale after this, the remaining half is "no full retrace runs after the
carry", which is an inspector-side change. That needs a live check: actors cannot be built
headlessly here, so this fix is verified at the cache level only.

0487, 0489, 0437 and the model-change pairing guard all PASS; 54/54 pytest.
