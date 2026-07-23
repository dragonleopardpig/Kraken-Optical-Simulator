# 0425 — Long-press body carry moved the body even with "Move/Rotate whole body" off

**User:**
> "with 'Move/Rotate Whole Body' unchecked, clicking a STEP long enough will highlight the whole body,
> dragging it will move the body. This is not good, easy to move the body by mistake."

## Root cause

The left-press handler armed the **step-carry / row-carry** (a long-press "grab and drag the whole body"
gesture) whenever a STEP was under the cursor — *regardless of the mode*. So in face/edge-select mode
("Move/Rotate whole body" unchecked), holding on a STEP and dragging still grabbed and moved the whole
body. `_step_carry_label_from_current_pick` never checked `_show_rotation_handles()`.

## Fix

Gate the carry arming on the whole-body mode: the left-press handler now arms `_arm_step_carry_hold` /
`_arm_row_carry_hold` only when `_show_rotation_handles()` (the "Move/Rotate whole body" toggle) is on.
In face/edge-select mode nothing is armed, so a long press + drag can't move the body. Explicit
gizmo-widget drags (placement handles, thickness, axis slide) are resolved earlier in the same handler and
are unaffected — they still work in either mode.

## Verification (`validate_open3d_carry_gated_on_mode`, penta phase 343)

Display-free:

| check | asserts |
|---|---|
| GATE | the left-press carry arming (`_arm_step_carry_hold` / `_arm_row_carry_hold`) is guarded by `_show_rotation_handles()` |
| TOGGLE | the "Move/Rotate whole body" checkbox drives `show_rotation_handles_var`, which `_show_rotation_handles` reads |

2/2 pass. Baseline phase 343 = pass.

## Files

- `KrakenOS/UI/services/open3d_mouse_bindings.py` — gate the carry arming on the whole-body mode.
- `KrakenOS/UI/validate_open3d_carry_gated_on_mode.py` — guard (phase 343).

## In-app eyeball still owed

With "Move/Rotate whole body" **unchecked**, hold on a STEP and drag → it must **not** grab/move the body
(face/edge selection only). With it **checked**, the long-press carry works as before.
