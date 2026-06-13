# 0079 — Open 3D: promoting an in-path element puts it in the wrong chain slot (after the lens) → 0 rays, wrong orientation

## Symptom (user's words)

`attachment/recorded_bug_repros/flag_20260613_203812_658`:

> I can't orientate the promoted analytical beam splitter. Wrong orientation.
> How to snap to LED STEP? the Object plane is missing after promotion.

The user promoted the beam-splitter cube via **"Promote STEP to Analytic
Surfaces"** (the simple `Object → BS → Lens → Image` system; the LED / camera /
lens STEPs are decoration).

## What the recording shows

- `ray_actor_count = 0` — **no rays trace at all** (hence the "Object plane
  missing": the trace produced nothing to draw, so the object/image look gone).
- The beam splitter became **rows 6 & 7, inserted AFTER the lens** (rows 1–5 are
  the lens at z=275–324), but the surfaces physically span **z≈141–292** — before
  / overlapping the lens. So the chain ORDER is `Object → Lens → BS → Image`
  while the geometry is `Object → BS → Lens → Image`. That mismatch breaks the
  trace.
- The BS surfaces span **150 mm in z** for a 55 mm cube → tilted ~45°: the
  analytic fit / chain-tilt oriented them along the fold, not flat on the axis.

## Root cause

`promote_imported_step_to_analytic_surfaces` (and the solid-row path) were built
for **folded penta-prism cascades**: they append the new surfaces at the chain
*end* and place each one with `desp_z = placement_z − z_station` + a fold
`chain_tilt`. For a **simple on-axis in-path element** that is wrong twice over —
wrong chain slot (after the lens) and a spurious tilt — and the non-sequential
trace, finding the chain order inconsistent with the geometry, yields no rays.

Neither promote path places a straight in-path element correctly: the mesh-solid
path can't separate "glass depth" from "gap to the next element" (one row), and
the analytic path mis-orders + mis-orients it.

## Fix direction — position-aware in-path placement (general)

Insert a promoted in-path element **at the axial position where it physically
sits** (the gap that contains its front face), splitting that gap so the lens and
image plane stay exactly put, with **no axial decenter and no spurious tilt** — so
the chain order matches the geometry and the trace runs. General for any
light-through element (beam splitter, lens, window); the off-beam / folding-mirror
paths (bugs 0065–0076, which pass a `chain_exit_direction`) keep their behavior.

## Direction corrected by the user (the architecture, not just placement)

> the penta prism, I promote to Optical Solid Rows and it traces correctly. This
> beam splitter should do the same thing. I need to have the Face Editor pop up
> after promoting whatever optical element, assign the face role, and the ray
> should trace according to physics. This analytical surface is designed for
> sequential only, no gizmo pop up, no face editor pop up. … just one function is
> enough: "Promote to Optical Element", it should apply to all imported STEP, no
> more different kind of promotion for the user to select.

So the **mesh optical-solid path is the correct model** (it pops the Face Editor,
shows the move gizmo, and traces per-physics **non-sequentially** — the penta
prism proves it). The analytic/native paths are sequential, no Face Editor — the
wrong model for the user, and the source of the earlier confusion.

**Done now:** the three user-facing promote options (Optical Solid Row / Analytic
Surfaces / Native Rows) are collapsed into one **"Promote to Optical Element"** in
both the CAD/target dropdown and the canvas right-click; it runs
`promote_selected_step_to_optical_solid_row` (mesh solid + Face Editor pop +
gizmo). The analytic/native methods remain as internal helpers for the scripted
folded-cascade builders, just not offered to the user. Guards
(`validate_open3d_toolbar_layout`, `validate_open3d_row_actions_parity`) updated to
expect the single option.

**Still to verify / fix:** whether an on-beam element parked between object and
lens still needs the position-aware *axial* slot fix (the `desp_z = center −
z_station` of the mesh-solid promote — recording flag_20260613_190358_687 showed
`desp_z = −556` when parked at z≈39 but inserted at the chain end). The penta
prism traces because it sits near its appended slot; a beam splitter parked up the
chain may still need the slot match. The `plan_inpath_insertion` planner (below)
is reused for that mesh-solid placement (insert the solid + a trailing AIR spacer
at the gap that physically contains it, `desp_z = 0`, lens/image fixed), gated to
on-beam so the off-beam / folding paths (0065–0076) are untouched.

## Physics check (user) + the wired fix

> it should be determined by physics … adding a 50 mm glass to a ray path makes
> the focusing earlier or later on the image plane, correct?

Correct. A plane-parallel plate displaces the image by **Δ = t·(1 − 1/n)** in the
propagation direction (**later** / downstream), and to first order this is
**independent of where the plate sits** in the beam. For 50 mm BK7 (n ≈ 1.5168),
Δ ≈ **17 mm later**. The lens + camera are fixed physical parts, so that ~17 mm is
a defocus at the sensor — it must NOT be the ~50 mm the old promote produced by
dumping the cube's raw thickness into the chain after the lens (a bookkeeping
artifact, not refraction).

**Wired (mesh-solid promote):** `promote_imported_step_to_optical_solid_row` gains
`inpath_axial_placement`; the UI "Promote to Optical Element" passes it (threaded
via `open3d_step_state.promote_imported_overlay_to_row`), scripted/folded-cascade
callers keep the default (no-op, identical to before). When set AND the solid
**straddles the optical axis** AND has axial depth, the promote uses
`plan_inpath_insertion` to drop it in the gap it physically occupies, splits that
gap (object→front distance, the cube's glass depth, then a flat **AIR spacer** to
the next element) and sets `desp_z` to the body half-depth — so the **lens and
image plane do not move** and the cube's two glass faces provide the refraction
(the t(1−1/n) focus shift). The non-sequential split is unaffected (it happens at
the mesh, whose centre is unchanged).

## Status: FIXED (pending in-app ray confirmation) — promote unified to one mesh-solid function; on-axis in-path placement wired + guarded

Guard `validate_open3d_inpath_element_placement` (display-free): planner gap-split
+ a real `_build_system_from_specs` round-trip (element before the lens, lens &
image vertices unmoved, no `desp_z`) + a source guard that the promote wiring uses
the placement core. The off-beam suite (0065–0076, build-only, no promote) is
unaffected, and the scripted promote path is byte-identical (default-off). The
actual ray focus is verified in-app (headless SIGSEGV).

This commit lands the **pure, display-free placement core**
(`KrakenOS/UI/services/optical_chain_insert.py`):
`plan_inpath_insertion` / `insert_inpath_element_into_specs` split the host gap and
splice the element's fitted surfaces in at its true Z. Guarded by
`validate_open3d_inpath_element_placement` (a real `_build_system_from_specs`
round-trip): the element lands **before the lens** (chain order == geometry), the
lens & image vertices **do not move**, and the spliced surfaces carry **no
`desp_z`**.

**Remaining (next pass):** wire this into `promote_imported_step_to_analytic_surfaces`
for the on-axis case (`chain_exit_direction is None`) — take the element's world
front-Z + depth from the overlay mesh bounds, place via the core (zero desp/tilt),
gated so folded cascades are untouched; then re-run the penta + off-beam suites.
Orientation control / "snap to LED STEP" is a follow-on (a flat on-axis plate needs
no tilt; an explicit snap-to-LED-face is the separate face-mate request).
