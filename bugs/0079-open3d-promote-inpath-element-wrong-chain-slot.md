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

## Status: IN PROGRESS — placement core landed + verified; promote wiring next

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
