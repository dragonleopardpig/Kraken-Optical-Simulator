# 0826 -- Scene IR Phase A: lower a scene to flat data, read it from nowhere

`docs/design_scene_ir.md`, Phase A. Not a flag.

## Why "read from nowhere" is the whole point

Step 2 of the earlier design (`design_row_placement_space.md`) stalled because **nobody could
find the producer** of the drawn geometry. One patch was implemented and the audit came back
completely unchanged -- inert. A second round wrapped `_build_folded_surface_curves`,
`_build_sequential_surface_curves` and every `_compute_*_layout_geometry*`, then forced a
synchronous refresh: **not one fired**, while the audit reported twelve row actors.

You cannot re-point a consumer you cannot locate. So Phase A builds the thing that can state
what every consumer believes -- `compare_to_consumer` -- and moves nothing.

## What Phase A found

The design assumed one uniform `derived_from` anchor. Measured across the gate scenes, the
metadata is **not uniform**, and a design built on that assumption would have been wrong on
half the gate set:

    machine_vision_ELS85.py   3 rows declare ScenePlacement.anchor='row_pose',
                              2 carry StepOverlayPromotion.placement_offset_xyz
    om05a_folded.py           NO anchors, NO placement offsets at all -- yet its
                              11 promoted bodies resolve at 0.0000 mm through the
                              output-port pose graph

Two mechanisms, differently shaped. `lower()` reads both and records which produced each body.
Nothing before the IR could see that.

**And ELS85's declared mechanism cannot be reconstructed.** Row 6's `center_world`
(6.295, 0, 47.615) is not its row pose (-0.12, 0, 54.46) plus `placement_offset_xyz`
(6.295, 0, 9.926), which would give (6.17, 0, 64.39). That offset's z equals
`bounds_min_world`'s z, so it is not a datum delta from the row at all. Those bodies fall back
to their authored snapshot and say so, with a `scene_ir.anchor_not_reconstructible` warning.
Finding the real datum is Phase B's job; inventing one here would have been fiction.

## Three defects caught in my own first pass

Each would have shipped a confident, precise, wrong number -- the failure this design exists to
stop, reproduced while building the tool meant to prevent it.

1. **A fallback claimed a derivation.** A body whose pose came from the authored snapshot was
   labelled `DERIVE_ROW_POSE`. It derived nothing.
2. **A fake zero.** When the pose falls back to the authored snapshot, an "authored delta"
   computed against that snapshot is 0.0000 -- a precise number meaning only that a value
   equals itself, reading exactly like agreement. `authored_center` is now withheld whenever
   the pose fell back to it.
3. **Cross-kind pairing.** `compare_to_consumer` paired bodies against surface-row consumers,
   because a surface entity and a body derived from it share a `source_row`. That is the same
   vertex-vs-centroid mistake that produced 132-480 mm of nonsense in the pose audit the day
   before. `kind` now defaults to `"surface"`.

## The frame tag

The design's invariant is *"`to_world` is always post-fold"*. Today it is not, because
`row_placement.world_pose` does not fold -- that is Phase D. Shipping a straight-equivalent
under the name `to_world` would BE the defect the invariant exists to prevent, so every entity
carries a `frame` tag (`post_fold` / `straight_equivalent` / `already_world`) and
`SceneIR.is_fully_post_fold()` reads **False**.

The guard asserts it is False. A guard that passed today would be measuring nothing; it turns
green at Phase D, on purpose.

## Guard

`KrakenOS/UI/validate_open3d_0826_scene_ir_phase_a.py`, penta phase 605. Purity (desp untouched,
re-lowering identical), identity, honest frames, cycle detection naming the WHOLE cycle including
self-reference, a 50-deep chain terminating (no depth limit), cross-kind pairing refused, unpaired
never counted as agreement, and both gate scenes lowering with every surface agreeing with the
prescription consumer (9/9 and 25/25) and every output-port-derived body at 0.0000 mm from
authored.

## Phase B follow-up: the ELS85 datum does not exist, and cannot

Measured on both promoted rows:

    row 6  station-neutral, thickness 0
           cw (6.2946, 0, 47.6146)   po (6.2946, 0, 9.9258)
           cw - po = (0, 0, 37.6888) == R @ (0, 0, half_z)    EXACT

    row 7  45-degree plate, thickness 40, station_neutral unset
           cw (206.1534, 0, 71.8971) po (212.4034, 0, 65.6471)
           cw - po = (-6.25, 0, 6.25), |d| 8.8388
           R @ (0,0,half_z) = (0, 12.5, 0),  |d| 12.5         NO MATCH
           its bounds describe a 25 mm cube while axial_reserve_mm says 40

The rule holds for one row, fails for the other, and row 7's metadata is internally
inconsistent. **But it would not help even where it holds**: `center_world` and
`placement_offset_xyz` are both AUTHORED snapshots, so reconstructing one from the other is
circular. A datum must relate the body to its anchor ROW, and the only available expression --
`cw - row_pose` -- can be computed only from the CURRENT pose. That is right exactly while
nothing has moved, which is precisely the condition it cannot detect; deriving from it would
bake prior movement into the datum and call it authored intent.

So there is no lowering-side fix. The promotion WRITER must record the datum at promote time,
which is a behaviour change and belongs after Phase B, and even then only helps scenes promoted
afterwards.

The guard pins this negative result: both bodies must report unreconstructible, the warning must
say *why* (circular, not merely unavailable), and neither may claim a derivation or offer an
authored check value. A later partial reconstruction now fails here instead of quietly
reintroducing the circularity.

This does not block Phase C -- om05a-class scenes, whose body drift generates the live bugs,
derive correctly through the output-port graph at 0.0000 mm.
