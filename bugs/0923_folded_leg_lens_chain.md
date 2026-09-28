# 0923 -- optics appended on a folded leg are traced where they are drawn

`validate_open3d_penta_telescope_chain` (ungated until now) builds on the five-penta cascade. The
beam leaves the cascade along world -X, and the chain appends on that leg:
- a ball-lens pair,
- a DCV and an achromat,
- a cylindrical lens.

It failed in every version: "rays terminated before Achromat: 55.69 < 190.96". The real state was
worse: **no ray reached any appended optic.** Every ray ended in the 90 mm missed-image stub past
prism 5 (x = 37.5), 30 mm short of ball 1.

## The chain's measurements hid it

- Phase 1 "passed". It projected every vertex of every ray, the folded cascade included, onto
  the exit axis. Prism 2 sits at x = -23, so the cascade itself reached 55.69 mm "along" the
  axis, past ball 2. The same projection gave a 199 mm "focal spot".
- Now only each ray's **exit leg** counts: the vertices after its last point on the axis line at
  or before the exit.
- The claim is stronger too: every ray has a **traced vertex inside each element's body**. The
  terminal stub is excluded, because the display draws it a fixed length past the last hit.

## Three breaks, in the order the rays met them

1. **The chain never rotated anything (test).**
   - The exit direction is traced: (-1, -2.3e-6, -1.6e-6).
   - `np.allclose`'s default atol (1e-8) rejected it, so `_tilts_to_align_local_axis_to_world`
     fell back to "identity".
   - Every optic was promoted with its axis along Z, across a -X beam.
   - Fix: snap to the axis within 1e-3, and raise instead of falling back silently.

2. **A rotated promoted STEP was traced un-rotated (product).**
   - `_saved_promoted_step_native_trace_plan` rebuilds the prescription from the **unrotated
     source STEP** along +Z, and poses it with the row tilts only.
   - Promotion leaves those tilts at zero, because it bakes the overlay rotation into the mesh
     and records it only in `StepOverlayPromotion.step_rotation_deg`.
   - So a ball turned onto the beam was drawn on it but traced as a Z-axis surface pair every
     ray ran parallel to.
   - Fix: a row whose baked rotation turns about X or Y traces the drawn mesh, the one pose the
     display and the trace share.
   - A roll keeps the axis, so it keeps the native trace, as before.
   - Every native-capable fixture measured rebuilds with axis (0, 0, 1). The cylinder is never
     native-ready (three unsupported planes).

3. **A lens on a folded leg read as a 90-degree fold (product).**
   - Next, every ray ended with `termination='image'` at x = -108.95, between the DCV and the
     achromat.
   - The row table still had the Image at a zero pose; the output-port follower builder had
     re-seated it.
   - The DCV is a **top-level** source there. The prisms establish no frame (their output picks
     return None), so nothing tells it which way the beam runs.
   - `select_optical_solid_output_face` measures "straight through" against world +Z (the
     bugs/0084 axial preference). On the -X leg no face qualified.
   - The side-priority pick then took the DCV's **upstream** face (normal +X, side "Down"), and
     `_exit_frame_is_non_folding`, also comparing with +Z, called it a fold.
   - The walk carried that backwards frame into the achromat and seated the Image one row
     thickness past the achromat's upstream face: -148.95 + 40 = -108.95.
   - Fix, in two parts:
     - `_is_straight_through_transmit_optic`: a body whose assigned faces are all Transmit
       faces on one line, with faces on both sides, is a lens or window. It cannot fold a beam
       whichever way the beam runs, so it is non-folding, generalising bugs/0022/0084. A cube
       (three lines), or anything with a mirror / beam-splitter / other interaction face,
       keeps the existing path.
     - Inside the follower walk the running beam is known, so the output pick takes
       `incoming_axis=frame_rotation[:, 2]`. With no axis given, the pick still prefers +Z.
   - Tried and reverted: carrying the last walk's direction into the next top-level source. No
     walk runs before the DCV here, so it changed nothing, and it moved the reference axis for
     other scenes.

## After

Every ray passes every element:

| Element | Rays through |
|---|---|
| ball 1, ball 2 | 13 / 13 |
| DCV, achromat | 13 / 13 |
| cylinder | 13 / 13 |

## Still open (not this bug)

- **The cylinder's line-focus aspect is 1.07.** The chain's soft check expects >= 3. The
  cylinder is thin along local Y (25.4 x 4.31 x 25.4 mm), so the roll onto -X is right. The
  toroid is traced as a tessellated mesh, which the chain's author had already recorded as a
  soft limitation.
- **The native rebuild merges a ball's two hemispheres into ONE sequential cap**
  (`_fit_sphere_group`, F001+F003, max error 9.5 mm) and still marks it `supported=True`. An
  un-rotated ball lens therefore traces as a plano-convex.
  - Clean catalogue lenses fit to ~1e-9 mm.
  - The multi-element barrels (PYRITE, ELS-85) fit to mm-to-60 mm and may rely on today's
    behaviour.
  - So tightening sphere support needs its own measured pass.

## Guards

- `validate_open3d_penta_telescope_chain`, penta phase **701**. It runs in its own process,
  because it opens its own editor (bugs/0661).
- `validate_open3d_0923_folded_leg_lens_chain`, penta phase **702**. It is display-free:
  - **R**: which baked rotations skip the native plan.
  - **S**: the straight-through test (a lens both ways; never a cube, a mirror-faced body or a
    one-sided body).
  - **P**: the output pick's incoming axis. With no axis, the pick is still F001, the old
    upstream pick.
  - **T**: the axis helper maps a traced direction and refuses an unmappable one.

## Two causal controls re-pointed (they pinned the old mechanism)

The first full gate of this fix blocked on phases 26 and 190. In both, only the CAUSAL control
flipped; every main check passed. A/B-measured, one change each:

- **Phase 26** (0397), flipped by the straight-through rule:
  - The control asserted "an unflagged tilted plate WITHOUT the BS mark folds the chain".
  - A clear plate (every face Transmit, one line, both sides) shifts the beam sideways but never
    folds it, so it no longer folds.
  - The control now asserts that (keys == []).
  - The mark's own effect stays proven by 2f: a folding explicit port stops folding once
    marked.
- **Phase 190** (0214), flipped by the running-beam output pick:
  - The control asserted that stripping the Mirror face flings the detector UP (+Z), "the
    flagged bug".
  - That UP came from the walk picking the stripped block's exit face by the world-+Z
    preference while the beam ran +X, the very root cause fixed here.
  - Stripped, the detector now stays on the incoming line at the mirror's height (70.598 vs
    70.6).
  - The control now asserts "neither DOWN (that needs the Mirror, so the Mirror is still
    causal) nor UP".

## Tooling found on the way

- The first full-suite run of this fix, with `tools/penta_shard_gate.py --shards 4`, ended in a
  **forced logout** a minute after it started:
  - the tty2 session ended at 14:14;
  - `/proc/vmstat` counts `oom_kill 5` this boot;
  - the machine has no swap.
- The runner budgeted 4 GB per shard. A shard reaches ~6 GB, and the tail shard also starts
  isolated child apps.
- The runner now:
  - budgets 7 GB per shard, so a 30 GB machine gets 3 shards;
  - runs a memory watchdog that kills every shard process below 3 GB available and fails the
    run loudly.
