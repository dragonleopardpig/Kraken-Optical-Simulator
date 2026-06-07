# 0027 — Selecting a hidden STEP pops up its rotation gizmo

**Status:** Fixed (2026-06-07).
**Component:** Open 3D scene-component browser selection + rotation handles
(`KrakenOS/UI/open3d_inspector.py`,
`KrakenOS/UI/services/open3d_scene_refresh.py`,
`KrakenOS/UI/panels/open3d_step_admin.py`).
**Reported via:** the in-app bug recorder —
`attachment/recorded_bug_repros/flag_20260607_201616_581/` ("left click the
Camera and/or Lens STEP in the right browser pop up handles"), with the user's
direction "this gizmo shouldn't pop up after the elements are hidden" and "hidden
elements should be grayed out / a different colour than the non-hidden ones".

## Symptom

After hiding a camera/lens STEP (bugs 0025/0026), left-clicking it in the
browser still popped up its rotation-handle gizmo, and a full refresh re-created
the gizmo even though the body was hidden. The browser also gave no visual cue
that an element was hidden.

## Root cause

The gizmo is created by two delegates — `_add_step_rotation_handles` (the scene
refresh, for the selected step) and `_ensure_step_rotation_handles_for_label`
(`show_step_rotation_handler`, on browser select) — neither of which checked the
hidden state. `_step_label_has_visible_body_actor` also keyed on actor
*existence*, not visibility, so a hidden body (actor present, `SetVisibility(0)`)
read as "visible" and let the handler proceed. `select_step_overlay_from_admin`
unconditionally entered rotation mode.

## Fix

* **Choke point** — both `_add_step_rotation_handles` and
  `_ensure_step_rotation_handles_for_label` now return 0 when
  `is_step_label_hidden(label)`, so *no* caller can create a gizmo for a hidden
  element.
* `_step_label_has_visible_body_actor` returns False for a hidden label.
* `select_step_overlay_from_admin` selects a hidden element for properties only
  — no highlight, no handles — with a "right-click ▸ Unhide to edit it" status.
* The refresh's three rotation-handle / carry-grid call sites are also gated on
  `not is_step_label_hidden(label)` (belt-and-suspenders).
* **Grey-out** — the browser tree tags hidden items with a `hidden` tag
  (grey foreground, `tag_configure`); `_set_element_hidden` refreshes the panel
  so the colour and the Hide/Unhide menu state update immediately.

## Result

Hiding the camera then selecting it from the browser leaves **0** visible gizmo
actors (was 6), and a full refresh keeps it at 0; unhiding restores the gizmo on
select (6). The hidden overlay/row shows grey in the browser. Verified on the
measured machine-vision layout.

## Tests

`KrakenOS/UI/validate_open3d_scene_browser_hide_delete.py` (harness Phase 35)
gains contracts that the two rotation-handle delegates + `select_step_overlay_from_admin`
+ `_step_label_has_visible_body_actor` consult `is_step_label_hidden`, and that
the browser tree configures + applies the `hidden` grey-out tag.
