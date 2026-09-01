# 0685 — browser click re-enabled "Move/Rotate whole body" (user, 2026-09-01)

## User
"Sidetrack: clicking those prism at right panel browser auto re-enable the
Move/Rotate Whole Body checkbox which is not the correct behaviour."

## Root cause
bugs/0424 ("click the right browser only highlight it, no gizmo") made browser-select
raise the placement gizmo by setting `_placement_handle_selected_row_index` AND
force-enabling the whole-body handle mode (`show_rotation_handles_var.set(True)`)
on every click. That second part overrode the user's explicit UNCHECK each time a
row was selected from the Scene Components browser.

## Fix
`select_promoted_step_row_from_admin` (open3d_inspector.py) still sets the gizmo
target row and rebuilds, but never touches the checkbox: with the mode ON the
handles raise exactly as 0424 intended; with it OFF the click selects + highlights
only, and the status line says how to get the handles. The source-gizmo path
(bugs/0426, `select_scene_source_from_admin`) is left as-is — no user report
against it.

## Guard
`validate_open3d_browser_select_gizmo` (phase 342) re-pinned: WIRING now REQUIRES
the absence of the force-enable and keeps the gizmo-target + rebuild + mode-gate
checks. Passes.
