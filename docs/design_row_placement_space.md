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


## Step 2 — the site is located; one design question blocks the first move

`_compute_folded_layout_geometry_for_rows` (`services/layout_scene_projection.py`) is where the
drawn pose is produced, and the double count is this line:

    center_point = current_point + branch_dir * float(row.desp_z) + branch_tangent * float(row.desp_y)

`current_point` is already accumulated from the chain's thicknesses. Adding `desp_z` on top is
CORRECT for a SEQUENTIAL row (there, `desp_z` is an offset along the branch) and WRONG for a WORLD
row (there, `desp_z` is an absolute world coordinate, so the fold displacement lands twice). That
is the measured 51.50 mm on row 8, and `must_not_display_fold(row)` already identifies exactly
which rows are affected.

**The blocker is not the predicate — it is the frame.** This walk operates in a 2-D FOLDED DISPLAY
space: `point`/`direction`/`branch_dir` are 2-vectors, the chain is unrolled into a plane, and
mirrors reflect the walk direction. A WORLD row's placement is a 3-D world coordinate. Substituting
one for the other requires the world -> folded-display mapping, which does not exist as a function
today; the walk never needed it because every row was assumed sequential.

So Step 2's first move needs a decision, not a patch:

* **(a) Give the walk an explicit world -> display frame map.** Then a WORLD row's centre is
  `map(world_pose(row).position)` and the walk stops accumulating for it. Most faithful, and it is
  the honest form of `world_pose()` from step 1. Costs: the map must handle the mirror reflections
  the walk applies, and every consumer of `extent_points` inherits it.
* **(b) Keep the walk sequential-only and place WORLD rows in a second pass**, after the walk, from
  their absolute poses — the walk then skips them entirely (no accumulate, no desp add). Smaller
  blast radius; the risk is that `current_point` continuity across a skipped row must still be
  defined for the rows that FOLLOW it.

(b) looks smaller but may be wrong for a WORLD row mid-chain, which is exactly the AZ85 case
(rows 1-8 are world-placed, row 3 is not). (a) is the change the design actually argues for.

Not attempted: choosing between these by inference is how this bug already cost three reverts.
Whichever is picked, the verification loop is now cheap and real -- `tools/pose_audit.py` reports
row 8's 51.50 mm going to zero in about two minutes.


## Step 2 attempt with option (a) — REVERTED, inert: wrong producer

Implemented (a) in `_compute_folded_layout_geometry_for_rows`: a parallel WORLD walk mirroring the
display walk step for step, so a WORLD row's true position is expressed in local
(along, transverse) coordinates and re-applied in display space, with SEQUENTIAL rows keeping
their original arithmetic byte for byte.

`tools/pose_audit.py` afterwards: **completely unchanged** — row 8 still 51.50 mm, row 7 still
1.78 mm. The edit was inert, so that function is NOT the producer of the drawn geometry for this
scene. Reverted (no unverified code left in the walk).

That is a useful elimination: the double count is real and the arithmetic in that walk really does
double-count a WORLD row, but this scene reaches the drawn actor by a DIFFERENT route.

**Check next, in order:**
1. `_compute_world_folded_layout_geometry` (`layout_scene_projection.py`, just below the patched
   one) — the name says world, and this scene is world-placed.
2. Whether `scene_builder` even receives `folded_geometry` here: it uses
   `_build_folded_surface_curves` only when `folded_geometry is not None`, otherwise
   `_build_sequential_surface_curves` — and a fold may then be applied later.

The one-line diagnostic that settles it: instrument BOTH producers to print when they run for
`machine_vision_AZ85_RA_Mirror_BS.py`, then patch only the one that fires. The audit turns any
guess into a two-minute yes/no, so the loop is cheap — the mistake to avoid is patching a
plausible-looking site without first proving it runs.


## Step 2, elimination round 2 — NEITHER curve builder runs in-process

Wrapped `scene_builder._build_folded_surface_curves`,
`scene_builder._build_sequential_surface_curves`, and every
`_compute_*_layout_geometry*` on the projection mixin, then loaded the BS scene, opened the
viewer and forced `refresh_from_editor(force_retrace=True, geometry_changed=True)`.

**Not one of them fired** — while the audit, run the same way, reports twelve row actors. And it
is not the async worker hiding them: `maybe_begin_inspector_async_trace` documents that
"explicit force_retrace flows expect synchronous completion", so that refresh took the
in-process path.

So the drawn row-8 actor is NOT produced by the surface-curve path at all. Three sites are now
eliminated by measurement rather than by argument:

1. `_compute_folded_layout_geometry_for_rows` — patched, audit unchanged (inert).
2. `_build_folded_surface_curves` / `_build_sequential_surface_curves` — never called.
3. the async worker — bypassed by force_retrace.

**Where to look instead.** The bundle carries `targets`, `planes` and `surface_meshes` as well as
`surface_curves`, and the Image draws as a "Sensor 23.0x23.0 / Image circle" — detector
iconography, not a surface ring. The next probe should wrap the ACTOR-CREATION side in
`services/open3d_scene_refresh.py` (whatever populates `_row_actor_map`) and record, for the entry
keyed row 8, which bundle member it came from and what coordinates it was handed. That answers
"who drew this" directly instead of guessing which producer fed it — the question every attempt so
far has answered wrongly.
