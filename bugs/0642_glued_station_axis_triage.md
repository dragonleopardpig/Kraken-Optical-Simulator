# 0642 — TRIAGE (OPEN): the glued illuminator station moves, the optical axes do not

flag_20260824_144559 (build ccb9344b): *"the glued illuminator source + BS Cube + LED moved
together, the optical axis is not moving."* Scene machine_vision_150mm_standoff_145mm.py.
(Same root complaint as flag_20260824_130527; 0640/0641 fixed the axis's EXISTENCE and
LENGTH, this is about it FOLLOWING the station.)

## Root cause (verified headless, two experiments + a forced pre-fix baseline)

The drag does move the optical model — but not the OBJECT:

- Every glued LED/BS drag funnels into `translate_step_overlay("led", delta)`
  (scene_placement_commands.py:5232+). It writes the LED STEP offset, the glued source
  origin, and the promoted BS row's `desp` (measured: BS desp_x 1.3 → 41.3 on a +40 x drag).
- The 0505 ATOMIC STATION WRITE (which is what carries the Object) is gated on
  `_led_station_slide_plan()`, which returns **None** here. Its member search takes "rows on
  the BS's own leg strictly UPSTREAM of it" — but a promoted BS sits AT its own fold point,
  so it snaps to `axis:fold:1`, **the leg it itself emits**, where it is the only row
  (`rows_along_leg('axis:fold:1') == [1]`) → members `[]` → plan None.
- Consequences, both measured:
  * `axis:global` is anchored at `axis_root_origin` = the **Object row's lateral desp**
    (nonseq_output_ports.py), and the Object never moved → the axis cannot move at all.
  * `axis:global:split` = (pinned incoming line at x=0) ∩ (moved 45° coating plane) → its
    anchor slid **−40 in z** (173.35 → 133.35) instead of +40 in x. Correct physics for a
    LONE plate move; not what a station move should look like. (This is the trap already
    documented in bugs/0505.)

## Attempted fix — REVERTED, do not re-apply as-is

Re-anchoring the member search to the PARENT segment when the BS snapped to a leg it emits
(`segment.source_row == bs_row` → use `parent_id` at `start_on_parent`) DOES work
geometrically: plan returns `([0], 1, +X)`, and both axes then translate rigidly by
(+40, 0, 0) with z held. But it was reverted because:

1. **It darkens the sensor on this very scene.** Here the BS's emitted leg (+X, the coaxial
   illumination arm) is PERPENDICULAR to the imaging axis (+Z). 0505's station semantics were
   designed for the AZ85, where the emitted leg IS the imaging leg (a collinear slide = a pure
   section-2 edit). Applied here, the station write carries the Object 40 mm laterally while
   the lens/aperture/image (rows 3–8, desp 0) stay at x=0: measured census went
   `69 target_termination` → **0** (76 no_next_intersection, 12 missed_image).
2. **Two measured member-selection defects** (adversarial review, on real scenes):
   * ONE parent hop is not enough when the BS's incoming leg is itself a fold leg. On
     attachment/machine_vision_ELS85.py the members became `[1,2,3,4,5]` — the ENTIRE LENS is
     translated while the Object stays — the opposite of the plan's contract.
     (`optical_axis_tree.leg_upstream_neighbour` does a `while` walk with a visited set for
     exactly this question.)
   * The member filter has no upper bound beyond the fold point's arc length, and the patch
     newly aims it at the ROOT leg where the whole imaging chain lives.
3. **No guard coverage on this host:** the two guards aimed at this
   (`validate_open3d_0505_led_station_drag_slides_section_2`, `..._0504_led_glue_restores_
   reference`) both SKIP — the AZ85 BS scene is a gitignored attachment not in this checkout.

## The open design question (user's call)

What should dragging the glued coaxial illuminator (LED + BS + source) SIDEWAYS do?

(a) **Illuminator-only move** (recommended): object/lens/camera stay put. Then the honest axis
    behaviour is that the reflect axis must be tied to the ACTUAL coating FACE, not an
    infinite plane: once the BS slides off the imaging beam, no reflection occurs, so the
    guide should stop being drawn (or be drawn from the face showing no interaction) instead
    of being computed at x=0 where the cube no longer is — which is precisely the "axis not
    moving" the user sees.
(b) **Station move** (object comes along): keeps the illumination geometry rigid, but slides
    the object off the lens (dark sensor) and requires fixing the multi-fold member selection
    (walk UP the parent chain; bound the member set to the Object row) first.

## Incidental finding

The saved scene persists `show_rays = False`, so a plain load reports 0 ray paths and an empty
census (the flag's state.json shows exactly this). That is a view preference, NOT a broken
trace — any probe must toggle `show_rays_var` before reading a census on this scene.
