# 0826 Phase D -- the fold moves inside `lower()`

The last phase of `docs/design_scene_ir.md`, and the only one that changes physics. `to_world`
is now a real world pose: the design's invariant, `is_fully_post_fold()`, turns green.

## Phase D is the OVERRIDE, not the fold transform

The plan said "the fold moves inside `lower()`" and I assumed that meant moving
`_optical_axis_fold_world_transform_for_row`. It cannot. That transform is

    F(v) = C + R (v - S)     S = the row's straight-axis STATION [0, 0, z]

so it is valid only on a row whose prescription IS `[0, 0, z]`. Measured over all 25 rows of
`om05a_folded` against the pose audit's DRAWN column, it mis-places 8 of the 23 override rows:
RA mirror 2 lands at `[124.49, 0, 244.14]` instead of `[-269.14, 56.31, -25.0]`, and the front
datum's inert `desp_x = -8.78` (bugs/0832's marker) arrives in world as a Z offset, `-33.78`
where the scene draws `-25.0`.

The **output-port pose override** reproduces DRAWN on all 23 rows that have one. A row without
one is drawn where its own numbers put it. That is bugs/0836's finding, and it is what
`lower()` now resolves.

Both lowering paths -- the whole-scene walk and `_surface_entity_for_row` -- call the same
`_post_fold_surface_pose`, so the pre-lowered and single-row answers cannot drift. A divergence
there would be invisible and would break exactly the consumers Phase C re-pointed.

## Measured

    IR vs DRAWN (om05a, 25 rows)     the whole folded chain  ->  1 (row 0, the Object plane)
    is_fully_post_fold()                   False by design   ->  True
    override rows moved / left alone                      -  ->  12 / 11, both asserted
    machine_vision_ELS85                                  -  ->  0 overrides, provably untouched
    lens axis (om05a)                   7.01 mm / 12.41 deg  ->  0.0000 / 0.0000
    _lens_leg_room_to_fold                     -378.42 mm    ->  +0.6366 mm

Row 0 is the Object plane, whose drawn actor is the object-plane overlay rather than the row's
own surface. Rows 2/4/6/23 carry no drawn actor and are reported as NOT COMPARED -- see below.

## Both lens-axis sides moved together

`_lens_surrogate_optical_axis_line` now gets post-fold datums, so the CHORD is right in either
space -- which is what Phase D was for. bugs/0832's sequential special case (direction from the
chain, transverse from the median `desp`) survives only for rows NOT repositioned by an
override, where `desp` still means "off the chain axis".

`_lens_step_overlay_axis_world_line` had to move with it, or 0832's comparison would be
cross-frame again -- the exact defect it fixed, from the other side. Its probe points now get
the same fold transform `_transformed_imported_lens_step_mesh` ends with. Applying it THERE is
correct where applying it to a row pose is not: the aligned mesh really does sit on the
straight axis at `[0, 0, z_front]`, which is the precondition row poses violate.

## The audits moved, on purpose, and one of them moved wrongly first

The design says the audits are expected to move at Phase D. Five checks across two guards
failed because the historical defect can no longer reproduce from post-fold poses. They are
re-based onto the PRESCRIPTION, where the defect still lives -- not weakened. Every check that
asserts CURRENT behaviour passed before and after, untouched.

One honest correction inside that: bugs/0832's "old chord" now reads **4.39 mm**, not the live
7.0128, because the reconstruction cannot reach the CAD probe Phase D moved. The TILT
(12.4076 deg) reproduces exactly and is what the guard now asserts; the offset is stated as a
lower bound. A number printed next to a parent it does not belong to is the bugs/0828 defect,
and it was in my own guard message for one run.

`tools/pose_audit.py`'s IR column now compares against DRAWN. Its first Phase D draft fell back
to the prescription for rows with no drawn actor -- comparing a post-fold pose against a
straight-equivalent one and counting the difference as a defect, which is the audit's own
founding mistake reappearing from the other side. A row with no actor is an ABSENCE, not a
disagreement, and now says so.

## Gate

Full sweep, phases 1-615 in six shards: **611 pass, 1 fail, no PASS->FAIL regressions.** The
one failure is Phase 52, listed by the gate as known-failing (allowed) and red in the baseline
before this work.

The phases that read poses and had to hold -- 373, 439, 443, 447, 448, 451, 493, 509, 518 --
all held.

A note on the harness: the first run of that sweep silently skipped shard 6 (phases 516-615,
every phase this work touched) because `shards.txt` had no trailing newline and
`while read -r` drops the last line -- and still printed "ALL SHARDS COMPLETE". Completion
reported for work never done. The shard was re-run; the numbers above include it.
