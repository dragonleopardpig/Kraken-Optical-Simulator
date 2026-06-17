# 0089 — Open 3D: right-clicking a snapped beam-splitter overlay lost the Promote / face-assign menu

## Symptom (user)

> I placed a beam splitter in front of a doublet just like before; after snapping
> to the optical axis, right click doesn't have the option to directly assign the
> face, and is also missing the promotion option.

(Same class as `flag_20260617_211953_617` "right click no promotion option, can't
select individual face".)

## Root cause

An axis-snap marks the imported STEP overlay **physics-preview-ready**, so with
Show Rays on it is folded into the trace and **also drawn as a transient
live-trace ROW** (the cube exists as two coincident actors: the STEP-overlay
actor, `step_label="optical"`, and a live-trace row actor with no `step_label`,
not file-backed). When the right-click VTK pick lands on the **live-trace row
actor**, `_right_click_pick_context` (open3d_inspector.py) resolves
`step_label=None`, `row_index=<live-trace row>`, and `_file_backed_stl_row_at` is
None — so `_show_surface_function_context_menu` (open3d_face_assignment.py) skips
both the file-backed-row branch and the STEP-overlay branch and falls through to
the `else` ("requires a file-backed optical CAD/STL row"). The
**Promote to Optical Element** + **Promote and set \<face\>** options vanish.

(Confirmed display-free: after import → mark physics-preview-ready → Show Rays on,
the scene has *both* a `step_label="optical"` actor AND a live-trace row whose
`_live_trace_step_overlay_label_by_row()` maps it back to `"optical"`, while
`_file_backed_stl_row_at(row)` is None. NOT caused by the bugs/0085-0086 hover
gate — the right-click pick path does not use `_step_feature_pick_any_for_display_xy`.)

## Fix (this commit)

`_right_click_pick_context` now calls a new `_resolve_picked_step_overlay(step_label,
row_index)`: when the picked actor is a row with no `step_label` and that row is a
transient live-trace STEP overlay (`_live_trace_step_overlay_label_by_row()`), it
maps the pick back to the overlay's label and drops the row index. The context
then enters the STEP-overlay menu branch, so Promote / Snap / Glue / Resize /
"Promote and set \<face\>" reappear regardless of which coincident actor the click
hit. Real CAD/STL rows, promoted rows, and non-overlay picks are unchanged.

## Regression gate (display-free)

`validate_open3d_right_click_live_trace_overlay.py` (`run_checks()`) drives the
real `_resolve_picked_step_overlay`: a live-trace overlay row → mapped to the
overlay (row dropped); a non-overlay row → unchanged; an explicit step actor →
unchanged; empty pick / no live-trace overlays → unchanged. Penta **Phase 83**;
baseline → 84.

## Note

The full right-click VTK pick can't be driven headlessly (embedded-VTK screen
picks don't resolve under Xvfb), so **confirm in-app**: place a beam splitter,
snap to the optical axis, Show Rays on, right-click the cube → Promote to Optical
Element + face-assign options should be present. (The coincident
overlay + live-trace double-draw is a separate latent display nicety, not fixed
here.)

## Status: FIXED (pending in-app confirmation)
