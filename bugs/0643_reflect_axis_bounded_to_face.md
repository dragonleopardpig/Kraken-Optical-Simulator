# 0643 — the BS reflect axis is bounded to the REAL coating face (user's illuminator-only call)

flag_20260824_144559: *"the glued illuminator source + BS Cube + LED moved together, the
optical axis is not moving."* Resolves the bugs/0642 triage; the user chose **illuminator-only**
semantics: moving the illuminator must NOT drag the object/lens/camera — instead the axis must
be honest.

## What was wrong

`_bs_reflect_axis_guide_records` crossed the incoming axis with the coating's **infinite plane**.
Slide the BS off the imaging beam and that crossing still exists — far from the cube — so a
second axis kept hanging at the old spot while the hardware moved away. (Measured: a +40 mm
lateral station drag left the guide anchored at x=0 while the coating sat at x=41.3.)

## Fix

- `beam_splitter_coating_world_records` (new, in nonseq_output_ports) carries `extent_mm` plus
  the face's in-plane `u_axis`/`v_axis`; `beam_splitter_coating_world_frames` is now a thin
  wrapper over it, so its five existing `(centroid, normal)` callers are untouched.
- `extent_mm` = `clear_aperture/2`, else `sqrt(area)/2` (the equal-area square half-width:
  38.945 mm for this 6067 mm² coating, vs its true 39.0/38.9 half-widths).
- The drawer now tests the crossing **per in-plane axis against the rectangle** (a coating is a
  rectangle, and a lateral slide walks the crossing along ONE of its axes — a circular bound is
  the wrong shape). Off the face → no reflect axis emitted. An unsized face keeps the old
  behaviour (no bound rather than a guess).

## Verified (headless, one app per process, plus display-free guards)

| state | result |
|---|---|
| at rest | BOTH axes drawn; fold point du 1.838 mm inside the 38.945 mm half-extent |
| lateral +40 mm (off-beam) | `axis:global:split` **absent** — du 58.407 mm > 38.945 mm |
| on-beam +30 mm | axis **present**, anchor 173.346 → 203.346 (exactly +30 z) — no false suppression |
| ray trace at rest | unchanged: 234 paths, **69 target_termination**, 117 absorb, 48 vignette |

Guard: phase 481 (`validate_open3d_0643_reflect_axis_bounded_to_face`) — extent rule, on-glass
emits, off-glass emits nothing, unsized unchanged, 2-tuple API preserved. Re-derived for the
moved row-walk: `validate_open3d_bs_reflect_axis` (MECHANISM) and `..._0640_...` (check D).

## Also confirmed (user: "all future optical elements that snap to the 2nd optical axis should
follow the 2nd optical axis") — ALREADY HOLDS, no code needed

`_fold_slide_carry_before/_apply` (bugs/0485 rule 3 / 0488 rule 4) captures the rows on the
folder's emitted leg via `optical_axis_tree.rows_on_emitted_leg` and re-seats them with one
rigid transform, preserving arc-length `s` and transverse offset; it is ACTIVE on the
illuminator-only path (the 0505 station write, the only thing that sets
`_suppress_fold_slide_carry`, never runs there). Measured: a test element on the reflect leg
kept **s to 0.0** and its transverse offset bit-for-bit across three gestures (+Z 30, live-drag
−Z 12, along-leg +X 20). The 0638 "Add Stock Lens on this axis" verb bakes desp so new rows
snap to that leg and are picked up automatically.

Two caveats worth knowing (not bugs today):
* `_fold_slide_carry_before` re-seats STEP BODIES only for the hardcoded labels `camera`/`lens`
  — a future element carried as a non-promoted overlay under another label would have its row
  carried and its drawn body left behind.
* `rows_on_emitted_leg` excludes Object rows by design.

## Open, deliberately not bundled

The MODEL's own "did the beam hit this face" threshold, `_face_hit_radius = sqrt(area) + 2`
(≈79.9 mm here), is ~45% beyond the coating's own corners (half-diagonal 55.1 mm), so between
~39 and ~80 mm of lateral offset the fold model still emits a leg while the display (correctly)
draws none. Aligning it would change fold emissions for every mirror/prism/BS scene and needs
its own change + a full marathon.
