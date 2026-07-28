# Design: make a row's COORDINATE SPACE explicit (the root behind 0433→0457)

Status: proposal, not implemented. Written 2026-07-28 after five bugs in one day turned out to
be the same defect wearing different clothes.

## The observation

Every bug fixed or chased today was two consumers disagreeing about **what a row's numbers mean**:

| bug | the disagreement |
|---|---|
| 0448 | rows baked by the freeze traced BACKWARDS — drawn vs traced tilt convention |
| 0456 | the solve moved ROWS in prescription space and BODIES in world space — opposite directions |
| 0451 | detector synthesis vs the designed Image — a dead-end arm drew sensor iconography |
| 0457-A | the display folded a row whose placement was ALREADY folded — 54.23 − 2×51.5 |
| 0457-B | a SEQUENTIAL trace applied to rows carrying absolute world placement — every ray vignettes |

That is not five bugs. It is one missing concept, surfacing wherever two subsystems meet.

## The root

`SurfaceRow.desp_x/desp_y/desp_z` has **two incompatible meanings**, and nothing in the type says
which one is in force:

1. **Sequential** — an offset from the row's station, where the station comes from accumulated
   `thickness` along a nominal axis. The chain is straight; folds are applied afterwards for
   display and for the folded trace.
2. **World** — an absolute placement, already final, already folded. This is what the 0433
   freeze/snap bakes in (`ScenePlacement.stay_put_freeze`, `last_axis_to_axis_move`), and what
   promoted solids carry.

Which meaning applies must be INFERRED from side-channel state. And every consumer infers it
independently, with its own predicate:

| consumer | its private inference |
|---|---|
| sequential trace builder | assumes station + desp along the nominal axis |
| folded display overlay | folds whatever it believes is straight-equivalent |
| STEP body anchoring | anchors bodies to row *stations* (0456 bit exactly here) |
| solvers (0447, 0456) | rewrite gaps, which silently moves every downstream station |
| branch detectors + the supersede rule | pure world-space ray geometry |
| 2-D projection | a slice of whatever the 3-D produced |

Six inferences of one fact. They drift; each drift is a bug; each fix teaches one more consumer a
special case, which is why the fixes keep landing next to each other without converging.

**The evidence that this is architectural, not incidental:** the live viewer and a headless probe
consume the SAME bundle builder, yet the live scene has a row-8 actor for which the probe's bundle
contains no geometry at all. Two code paths, same input, different answer about where a row is.
No amount of local patching removes that class of failure.

## The change

### 1. Placement space becomes explicit

Each row carries its space as data, not as a guess:

    placement_space: "sequential" | "world"

The freeze/snap/promote paths SET it. Nothing infers it.

### 2. Exactly one resolver

    def world_pose(row_index) -> Pose:    # position + orientation, in world coordinates

This is the ONLY function permitted to turn a row into world coordinates. A `sequential` row's
pose is computed from stations AND has the fold applied inside the resolver; a `world` row is
returned as-is. Every consumer above calls it and deletes its private inference.

**0457-A becomes impossible by construction**: the fold lives inside the resolver, so a `world`
row cannot be folded a second time — there is no second place that folds.

### 3. Trace mode follows placement space

Any `world` row in the chain ⇒ the scene MUST be traced non-sequentially (real geometry), because
a sequential trace is *defined* over stations along one axis. This is the existing
`trace_mode_north_star` rule, finally enforced by a type rather than by convention. It is also
0457-B's answer: the rays vignette because a world-placed chain was handed to a sequential trace.

### 4. The invariant that would have caught all five

For every row: **drawn pose == traced pose == body-anchor pose.** One assertion, run over the real
attachment scenes. 0456, 0448 and 0457-A each violate it; today's probes each checked only ONE of
the three and so each missed its bug.

## Migration — strictly incremental, each step shippable

* **Step 0 (do this FIRST, no behaviour change): the audit.** A read-only report that, for a given
  scene, prints each consumer's world pose per row and flags disagreements. It must run against the
  LIVE viewer, because that is where today's divergence appears and where three headless probes
  saw nothing. This step both reproduces 0457-A and becomes the permanent guard from §4.
* **Step 1:** introduce `placement_space` + `world_pose()`, implemented by EXTRACTING the current
  display logic verbatim. No behaviour change; the audit must stay green.
* **Step 2:** point the display at the resolver, then bodies, then solvers — one consumer per
  commit, audit green after each. 0457-A and 0456's class die here.
* **Step 3:** drive trace-mode selection from placement space. 0457-B dies here. This is the only
  step that changes physics, so it gets its own gate run and eyeball.

## Why not patch 0457-A directly first

Three attempts on it were reverted today — a stale-actor theory (refuted by a fresh-app test), a
launch re-aim (broke the healthy baseline), and a load-rebuild hook (redundant; the viewer was
already rebuilding). All three failed the same way: **a fix written before a reproduction existed.**
Step 0 exists precisely to stop that, and no further code should be written on this bug until the
audit reproduces the −48.8.
