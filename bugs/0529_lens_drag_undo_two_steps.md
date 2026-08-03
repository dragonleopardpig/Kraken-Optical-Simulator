# 0529 — Ctrl-Z didn't take the lens drag back (gesture split across two undo entries)

## Flag

`flag_20260804_073309`: "dragged lens to the right, FOV changed, ray refocus. Ctrl-z not
going back to previous state." Same frozen AZ85 scene; first half of the description is
the 0528 fix working.

## Diagnosis

The recorded state IS the smoking gun: lens offset still at the dragged
`[+53.14, 0, −53.14]` while the prism→sensor gap is back at the FRESH 44.12 with the
defocused ray census — i.e. the user's Ctrl-Z **did** fire and popped exactly one entry:
the refocus. The gesture had pushed TWO history entries (the drag commit's own capture,
then the snap's own capture), so the first press only un-seated the sensor — an ~18 mm
move, invisible at scene zoom — and the drag looked un-undoable. Reproduced headlessly on
both drag surfaces: 2 presses to restore, +2 entries per gesture.

## Root cause

Drag = Solve for FOV makes the refocus PART of the gesture, but history still treated it
as a second command. This is precisely the 0449 doctrine ("group EVERYTHING a public
command does into ONE undo step") applied to the new composite gesture.

## Fix

- **Gizmo-arrow finish** (`_finish_step_translate_drag`): the translate + snap now run
  inside `history_transaction()` — inner captures are suppressed, one pre-gesture
  snapshot is pushed at exit.
- **Carry finish** (`_finish_step_carry_drag`): the pending capture (begun on the first
  carry frame) is committed AFTER the snap instead of before it. The snap's inner begin
  no-ops against the open capture and its commit pushes the pre-gesture snapshot; when the
  snap is skipped/refused/raises, the explicit commit right after the block closes the
  capture exactly as before.

One Ctrl-Z now restores gaps + lens offset + sensor seat; one redo reapplies the whole
gesture. Verified on both surfaces.

## Guard

`validate_open3d_0529_lens_drag_single_undo.py` (penta phase 424): each gesture pushes
exactly ONE undo entry; a single undo restores the pre-gesture snapshot; redo reapplies.
