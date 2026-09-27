# 0909 -- an active STEP carry lost its status; a traced STEP could not be selected

Found by reviving `validate_step_carry_open3d_smoke`, an ungated validator that had been failing
since late May without anyone noticing. Two product bugs, both in
`services/open3d_scene_refresh.py`, plus four stale expectations in the smoke test.

## Product bug 1: carry ACTIVE with nothing on screen saying so

The carry status line ("STEP carry: OPTICAL | free plane movement | ...") was drawn only in the
branches that also draw the SELECTED STEP's gizmo. Entering another pick mode (Center Row ->
Optical Axis) clears the selection but leaves the carry armed, so after that round trip the carry
was still active and nothing on screen said so.

- Measured: carry `optical`, selected `None`, overlay empty.
- Fix: when a carry is active and none of those branches reported it, draw its status from the
  carried body's mesh. The gizmo stays tied to the selection; the status line follows the mode.

## Product bug 2: a live-trace STEP counted as "promoted"

95615f05 (2026-05-29) stopped a STEP from being drawn twice when a SAVED, promoted row already
represents it. It computed "promoted" from the preview rows, and those include the TRANSIENT
live-trace row of a STEP that is merely being traced. So a traced, unpromoted STEP was deselected
on every refresh, and its gizmo branch never ran, although that branch exists for exactly the
live-trace case.

- Traced by patching `_selected_step_label` with a stack-printing property: the clear came from
  the promoted-row check, with the editor holding only Object and Image rows.
- Fix: rows flagged `transient_live_trace` (`_live_trace_step_overlay_label_by_row`) are excluded
  from the promoted set.
- Saved promoted rows never carry that flag, so the ghost suppression still works:
  `validate_open3d_saved_step_native_trace` passes.

## The smoke test's stale expectations

- **Rotation handles with the whole-body toggle OFF.** Since bugs/0338 the gizmo is opt-in. The
  test now asserts both states: no handles with the toggle off, handles with it on.
- **The grip actor.** It moved into `Open3DCarryGripService` (b1ad9eec), so the test reads the
  service's actor.
- **The face selection.** The axis actions read ONE `StepFeatureSelection` (pick point, surface
  centre, normal), which is what a real face click stores. The test set three loose attributes
  those actions no longer consult.

The smoke test now passes end to end.
