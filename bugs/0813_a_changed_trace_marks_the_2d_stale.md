# 0813 -- a changed trace marks the 2D stale

Found by the validation census ("fix them all"): penta phase 262 failed on its bugs/0298 invariant --
"no inspector method forces a retrace without marking the 2D stale" -- naming two methods. Both are
real: after either action, **Done 2D** kept showing the old layout, because `finish_stl_placement`
re-plots only when `_stl_placement_dirty` is set.

## 1. `_finish_step_translate_drag` (a lens gizmo-arrow drag)

The commit (`translate_step_overlay`) writes the section gaps -- `_last_translate_row_shifts` is set --
and bugs/0528 then refocuses at the sensor and retraces with `refresh_from_editor(force_retrace=True)`.
The prescription changed twice; the 2D was never told. The same drag with no refocus (the snap
refused) also left rows moved and the 2D unmarked.

Fix: the 2D is marked stale whenever the commit shifted rows, and the refocus retrace goes through
`_apply_model_change` (retrace + stale, together). One undo step is unchanged (bugs/0529).

## 2. `_on_illumination_rays_toggled` ("Illum rays", bugs/0542)

The master switch decides which sources `_build_scene_source_bundles` launches into the SHARED preview
trace, and the main 2D draws that trace while the inspector is open. Toggling it retraced the 3D only.

Fix: mark the 2D stale before the retrace.

## Verified

* Phase 262 (the invariant) passes; on the committed code it names both methods.
* Phases 423 (0528 gizmo lens drag refocuses), 424 (0529 one undo step) and 432 (0542 Illum rays
  master switch) pass.
