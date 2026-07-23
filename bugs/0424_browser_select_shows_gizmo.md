# 0424 — Selecting a promoted solid from the browser must raise the gizmo, not just highlight

**Flag `flag_20260723_131812_993`** + follow-up:
> "successfully right click to resize the BS Plate. I need to move it so that I can align to particular
> section of the LED. However, I can't select it while the LED is not hidden. Any better approach to
> select it?" … "click the right browser only highlight it, no gizmo."

The beam splitter is glued behind the LED, so a 3D click picks the occluding LED. Selecting it in the
Scene Components browser worked for *highlighting* — but did **not** raise the move/rotate handles, so the
user still couldn't move it without hiding the LED.

## Root cause

The in-canvas placement gizmo builds during a scene rebuild for `_placement_handle_selected_row_index`,
gated on whole-body handle mode (`_show_scene_placement_handles`). A 3D whole-body pick set both the
target row and (with the mode on) rebuilt the handles. `select_promoted_step_row_from_admin` (the browser
path) set only `_stl_placement_row_index` + `highlight_row` — neither `_placement_handle_selected_row_index`
nor a rebuild — so the gizmo never appeared.

## Fix

`select_promoted_step_row_from_admin` now, in addition to selecting/highlighting the row:

- sets `_placement_handle_selected_row_index = row_index` (the gizmo's target),
- enables whole-body handle mode (`show_rotation_handles_var`) — selecting a body *from the browser* is
  an explicit "I want to manipulate this",
- rebuilds the scene (`refresh_from_editor`) so the handles are built.

So clicking the occluded BS (or any promoted solid) in the browser both selects it **and** shows its
move/rotate handles — no need to hide the LED.

## Verification (`validate_open3d_browser_select_gizmo`, penta phase 342)

Display-free:

| check | asserts |
|---|---|
| WIRING | `select_promoted_step_row_from_admin` sets `_placement_handle_selected_row_index` + enables the handle mode + rebuilds |
| GATE | `_show_scene_placement_handles` builds the gizmo for that row, gated on the handle mode |

2/2 pass. Baseline phase 342 = pass.

## Files

- `KrakenOS/UI/open3d_inspector.py` — `select_promoted_step_row_from_admin` raises the gizmo.
- `KrakenOS/UI/validate_open3d_browser_select_gizmo.py` — guard (phase 342).

## In-app eyeball still owed

Click the BS in the Scene Components browser (LED visible) → it selects **and** shows the move/rotate
handles. (Because the BS is glued to the LED, dragging moves them together — unglue first to reposition
the BS relative to the LED.)
