# Proposal — Beam splitter creates TWO optical axes, and every component follows its immediate predecessor

Status: **design proposal, no code changed** — for review (flag_20260723_141437, scene
`machine_vision_AZ85_RA_Mirror_BS.py`).

## Your requirements (verbatim, numbered)

1. `machine_vision_150mm_measured_test.py`: imaging path is the **TRANSMIT** leg of the BS (cube).
2. `machine_vision_AZ85_RA_Mirror_BS.py`: imaging path is the **REFLECT** leg of the BS (plate).
3. A BS should **automatically create 2 optical axes**.
4. The imaging path can follow **either leg, or BOTH**.
5. Replacing the RA mirror must **auto-retain** the current imaging-lens + camera placement, *provided (3)*.
6. The BS must **not** re-aim the camera. **Every component follows the component immediately before it** —
   e.g. the camera follows the 2nd RA mirror, not the BS.
7. This proposal.

### Clarification (2nd round — supersedes the "assign the imaging leg" idea below)

> "Ray launch from Object Plane: sees a lens → focus; sees nothing → diverge; sees a Mirror → reflect;
> sees a BS → transmit **and** reflect; then if it sees an imaging lens → converge, and so on.
> Imaging-leg selection should be done **automatically by the ray tracing itself**. What I need is the ray
> tracing to do its physics after hitting the next component — the rays don't care whether it is imaging or
> diverging."
>
> Extended example: an LED+BS+illuminator (non-imaging) on one side, the object on another, and a **pure
> BS (no illuminator)** on a third — the 2nd BS is then just "situation (1)": rays transmit+reflect and
> carry on. "Both" = this multi-BS case.

**This is decisive: there is NO imaging-leg to designate. The trace does the physics at each hit; branches
(and therefore the axes) EMERGE from the trace.** The `_assign the imaging face role_` mechanism in the
draft below is dropped. The good news — the branching engine already exists:

- `KrakenSys.__BeamSplitterCoefficients` (`KrakenSys.py:4505`) already splits a ray into transmit +
  reflect at a BS coating.
- `auto_leg_graph.py` already "turns projected branch rays into stable user-facing path legs" —
  automatic leg/branch derivation from the traced rays.
- `branch_field_analysis` / `branch_throughput_analysis` / `detector_path_analysis` and the **Mach-Zehnder
  + Michelson** case studies are pure multi-arm BS branch scenes that already work.

So the physics + automatic branch derivation are **done**. What's missing for your scene is only the two
things below.

## Why it fails today (root cause)

Two facts collide:

- **The BS is deliberately skipped as a fold source.** `build_optical_solid_output_port_pose_overrides`
  (`nonseq_output_ports.py:1362`) computes, for a promoted mirror, a reflected frame
  (`_reflected_frame_from_interaction_face`, `:1274`) and re-positions the downstream rows onto that
  folded leg. But it `continue`s over a beam splitter (`:1392` top-of-loop, `:1543` follower re-source) —
  the fix for bugs/0396–0399 ("the camera should not follow the BS"). So the BS produces **no** reflected
  frame → **no second axis**, and no follower ever folds onto it.
- **Followers fold onto a specific fold SOURCE, not onto their predecessor.** The RA mirror was that
  source. Remove it and the override map empties → the lens + camera collapse back onto the straight
  `axis:global` — the "misplaced" symptom, and the flag's single 2-point axis record.

So the current model is "a designated fold source repositions the whole downstream chain," with the BS
excluded. Your point 6 asks for a *different, cleaner* model: **each row follows the one immediately
before it.** Adopting that model is what makes 3–6 all fall out together.

## The proposed model (physics-driven, revised)

The model has exactly two parts — **the trace does the physics (already works); the DISPLAY + PLACEMENT
must follow the trace.** No leg is ever "assigned"; both are real because both carry real rays.

### A. Draw the axes the trace already produces (points 3, 4 — automatic)

The trace already splits at a BS into transmit + reflect branches, and `auto_leg_graph` already derives
those branch legs. The gap is that the **optical-axis GUIDE** (the dotted line) only draws the primary
`axis:global`; it doesn't draw the branch legs as axis guides. So:

- **When rays are traced:** derive one axis guide per branch leg straight from the traced branch chief-ray
  polylines (`auto_leg_graph` already produces the leg nodes/polylines) — a BS → 2 guides, the multi-BS
  example → a branch tree, **automatically**, no per-scene wiring.
- **When rays are OFF** (the flag was captured rays-off): the current geometric axis-guide heuristic folds
  only at a *mirror* (`_folded_reflected_axis_guide_record`, `open3d_inspector.py:10706`). Extend it to
  also emit a reflect guide at a BS interaction face (the same `_reflected_frame_from_interaction_face`
  math), so the 2nd axis is visible even before a trace. This is the smallest, most visible first slice.

This satisfies "BS auto-creates 2 optical axes" (3) and "either/both" (4) with **zero** designation — the
axes are just where the rays go.

### B. Every row follows its immediate predecessor (points 5, 6)

Replace the "one global fold source repositions the chain" model with a **local chain**:

> row *i*'s world frame = **row *i−1*'s OUTPUT frame** ∘ (row *i*'s own tilt / desp / thickness).

- A plain surface's output frame = its input frame advanced by its thickness (no bend).
- A mirror's output frame = its **reflected** frame.
- A BS's output frame = its **assigned imaging** leg's frame (transmit or reflect); the *other* leg spawns
  a parallel branch chain (point 4, "both").

Consequences, exactly as you specified:

- **The camera follows the 2nd RA mirror** — its immediate predecessor — never the BS (point 6). A fold
  element only sets the frame for *its own* immediate follower.
- **Removing/replacing the first RA mirror retains placement** (point 5): each row keeps following its
  neighbour; whatever occupies the fold slot hands the same kind of output frame to the next row. Nothing
  downstream jumps, because nothing downstream ever pointed at the *removed* element directly.
- **150 mm vs AZ85 need no distinction in code** — the rays transmit+reflect at both; the camera simply
  ends up on whichever branch its predecessor sits on. The trace, not a setting, decides.

This is the North Star's "sequential is the ordered-path special case of the scene" (invariant 1) made
literal: placement is just per-row predecessor frames; **physics is the non-sequential trace** (invariant
4). The two are decoupled — geometry places the parts, rays do the optics.

## Implementation plan (phased, each shippable + eyeball-able)

| Phase | Deliverable | Touches | Risk |
|---|---|---|---|
| **1. See the 2nd axis** | Draw an axis guide per BS branch. Rays-ON: from the `auto_leg_graph` branch legs. Rays-OFF: extend the geometric fold guide to emit a reflect guide at a BS interaction face too. Render-only. Directly answers "no second axis". | `_folded_reflected_axis_guide_record` / `_folded_multifold_axis_guide_records` (`open3d_inspector.py:10706`); `auto_leg_graph`. | Low — display only. |
| **2. Predecessor-chain placement** | `row i frame = row (i−1) output frame ∘ own tilt/desp/thickness`, where a fold element's output frame is its reflected frame and a BS's is BOTH. So RA-mirror removal retains placement + the camera follows the 2nd RA mirror. | `build_optical_solid_output_port_pose_overrides` (`nonseq_output_ports.py:1362`) — replace "global fold source repositions chain / skip BS" with the local predecessor chain (fold only the immediate follower; BS included). Must NOT resurrect the 0396-0399 whole-chain camera drag — the local rule is what prevents it. | Med/High — the central change; pure-geometry validator below. |
| **3. Rays follow the geometry** | The traced branches + detectors sit on the placed chain (transmit + reflect arms), so `machine_vision_150mm` (transmit imaging) and AZ85 (reflect imaging) both image correctly with no per-scene flag. Multi-BS (your situation-2 example) is a branch tree, handled recursively by the existing splitter trace. | `two_arm_display_fold.py`; per-branch detectors ([[project_open3d_detector_redesign]]); the `KrakenSys.__BeamSplitterCoefficients` split already exists. | Med. |

Recommend **1 → 2 → 3**, one at a time, with your eyeball between each (folded/BS geometry is
headless-untestable — the Accept-cone fold took five in-app passes for this reason).

## Validators (North Star invariant 6)

- **Phase 1:** a BS scene's axis-guide record set contains **≥ 2** guides (transmit + reflect); the
  multi-BS scene contains a guide per branch (display-free check on the records).
- **Phase 2:** on a synthetic `[object, BS, lens, mirror, camera]` chain, assert *pure geometry*: each
  row's frame = its predecessor's output frame; the camera's frame = the **mirror's** output (not the
  BS's); deleting the first fold leaves lens+camera frames unchanged.
- **Fixtures:** `machine_vision_150mm_measured_test.py` (transmit imaging) + `machine_vision_AZ85_RA_Mirror_BS.py`
  (reflect imaging) as the two reference scenes; the existing **Mach-Zehnder / Michelson** case studies as
  the multi-arm regression.

## Resolved + remaining questions

- **Imaging-leg selection — RESOLVED:** none. The trace does the physics; both branches are real; the
  camera lands wherever its predecessor sits (points 1–4 of your clarification).
- **Multi-BS ("both", situation 2) — RESOLVED:** the splitter trace already branches recursively, so a 2nd
  BS is just another split node; `auto_leg_graph` labels the tree. Phase 1's per-branch guides + Phase 2's
  predecessor placement cover it with no special case.
- **Remaining, minor:** (a) rays-OFF axis guides for a BS are a geometric *approximation* of the reflect
  leg — confirm you want them drawn pre-trace, or only once rays are on. (b) The non-imaging branch: draw
  the guide only, or also drop a detector on it so throughput/field there is analyzable?

Nothing is committed beyond this document. **Phase 1 (draw the second axis) is the low-risk first slice** —
say go and I'll build it, then we iterate 2 → 3 with your eyeball.
