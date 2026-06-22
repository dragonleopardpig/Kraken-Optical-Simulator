# 0102 — Scene Components tree right-click mirrors the 3D-canvas element actions

**Requested:** 2026-06-22 (user feature ask, not a recorded flag).
Live ask: *"Can you add right click to the element browser to be the same as if
right click to the components on 3D canvas?"* with two stated reasons:

1. **The 3D-canvas right-click is slow.** *"Right click the element takes long time."*
2. **Overlapping bodies can't be reached.** *"If components overlaps, hard to select
   underneath component without first hiding the overlap component."*

## Why the canvas right-click is slow
The 3D-canvas right-click (`_show_surface_function_context_menu` →
`_right_click_pick_context`) does a VTK cell pick, then resolves the **exact face
under the cursor** so it can offer face-specific commands ("Set {function}",
"Promote and set …", "Snap Picked Face → Optical Axis"). That face resolution is
the cost:
- `_row_face_ray_pick_for_display_xy` rebuilds the runtime trace surface mesh
  (`_runtime_trace_surface_mesh`), transforms every triangle to world, and brute-
  forces `pick_face_from_ray` (no spatial index), then
- `_traced_row_face_hit_near_display_xy` scans **every traced ray** for a near hit.

The always-on timing log shows this pipeline at **~12 s on the first click** (cold
mesh build) and **~1 s warm** (`lookup_method: "display_ray_face+trace_event"`).

The Scene Components tree already knows *which element* a row/overlay is, by name.
A tree-keyed menu therefore skips the whole face-pick pipeline → **instant**, and
because the tree lists **every** element by name, the user can pick the one
**underneath** an overlap directly (canvas only reaches the front-most actor).

## Fix — one shared element-level helper, two callers
The element-level (non-face-specific) actions are factored into a single helper so
the canvas menu and the tree menu can never drift:

- `KrakenOS/UI/services/open3d_face_assignment.py`:
  new `append_element_context_actions(menu, *, row_index=None, step_label=None) -> bool`.
  - **STEP overlay** (`step_label`): "Glue STEP to Surrogate", the conditional
    Glue/Unglue BS↔LED pair, "Resize Solid…", and "Promote to Optical Element"
    **only when the label is not a decoration** (bugs/0101 holds here too — an
    LED/camera tree row offers Glue/Resize but never Promote).
  - **Row** (`row_index`): file-backed → "Open Face Editor…", conditional
    "Unpromote to STEP overlay", `_build_row_actions_cascade`; promoted-analytic →
    conditional Unpromote + cascade.
  - Returns True if it added anything (unknown label → adds nothing, returns False).
- The 3 canvas branches (file-backed row / promoted-analytic row / STEP overlay) in
  `_show_surface_function_context_menu` now **delegate** their element-level block to
  the helper, keeping only the face-specific items (which need the VTK pick).
- `KrakenOS/UI/panels/open3d_step_admin.py::_show_element_context_menu`: the tree
  right-click resolves its iid to a row/overlay and calls the **same** helper
  (`inspector._face_assignment_service().append_element_context_actions(...)`).

Face-specific assignment is unavailable from a tree click (there is no picked
point/normal), so the tree routes per-face work through **"Open Face Editor…"** —
the deliberate element-vs-face split.

## Repro / test
`.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_tree_element_context_menu`
— display-free. Behavioral on the shared helper (optical overlay gets
Promote+Glue+Resize; an `led` decoration gets Glue but **no** Promote; an unknown
label adds nothing) + source-inspection that **both**
`_show_surface_function_context_menu` and `Open3DStepAdminPanel._show_element_context_menu`
delegate to `append_element_context_actions`. Penta phase 88.

## Follow-up (not in this fix)
- Directly speeding up the **canvas** right-click (cache the per-row world-triangle
  array to kill the 12 s cold build; short-circuit the redundant traced-ray scan
  once the ray-pick resolves a face) is a separate optimization — the tree menu is
  the instant path for now.
- In-app eyeball still owed: headless can't drive a real tree right-click pick.
