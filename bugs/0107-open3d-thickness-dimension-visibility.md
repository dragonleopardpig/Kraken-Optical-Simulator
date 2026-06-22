# 0107 — Each Thickness overlay can be turned off; each blue arrow can be dragged to point at a measured edge/face

**Requested:** 2026-06-22 — *"each Thickness measurement overlay can be turn
off, each blue arrow can be drag to point to a desired measured edge or face."*

A feature, not a bug. Two capabilities on the blue Thickness dimension arrows,
both **measurement-only** — the optical model (`rows[i].thickness`) is never
touched.

## Part 1 — turn an individual Thickness dimension off

The existing `show_physical_distances_var` is a **global** master toggle (all
arrows on/off). The ask is per-arrow. New editor state:

```python
# layout_editor.py
self._hidden_thickness_dimension_rows: set[int] = set()
```

Toggle API (`scene_placement_commands.py`): `set_thickness_dimension_hidden`,
`toggle_thickness_dimension_hidden`, `show_all_thickness_dimensions`,
`_thickness_dimension_is_hidden`. Each mutation is wrapped in the
history-capture pair (undo/redo) and refreshes the 3D views.

The draw path (`open3d_thickness_dimensions.py` `add_overlays`) skips a hidden
row right after the zero-thickness skip:

```python
if self.editor._thickness_dimension_is_hidden(row_index):
    continue
```

The hidden set is persisted in `layout_settings.py` as
`hidden_thickness_dimension_rows` (saved sorted, restored onto
`editor._hidden_thickness_dimension_rows`), so a turned-off dimension survives
save/reload.

## Part 2 — drag a blue arrow to re-anchor what it measures

The bugs/0053 **re-anchor backend already exists**: a dimension endpoint can be
pointed at a picked surface/edge z (stored in `editor._dimension_anchor_overrides`
`{row → {endpoint, ref_z, ref_label, fixed_z}}`), MEASUREMENT only. It was
reachable only via a Ctrl-click → bare-move → plain-click modal — undiscoverable.

This exposes it two ways without disturbing the existing **plain-drag = change
the thickness VALUE** gesture (the QuickEstimation live conjugate/FOV slide):

1. **Drag-to-point.** In `open3d_mouse_bindings.py` `left_release`, when
   `_dimension_anchor_pick_mode` is active and the release ended a real drag
   (`dimension_anchor_was_drag = _left_drag_active and _left_drag_moved`), commit
   the re-anchor on release (`_commit_dimension_anchor_pick`, which cancels
   cleanly if released over empty space) — in addition to the legacy
   click-move-click path.
2. **Right-click menu.** A new right-click overlay menu
   (`open3d_inspector._maybe_show_thickness_dimension_menu` /
   `_show_thickness_dimension_menu`, wired in front of the QE-role menu in
   `open3d_face_assignment._show_surface_function_context_menu`) offers:
   *Re-anchor to a surface/edge…* (enters the pick modal via
   `_begin_dimension_anchor_pick_for_row`), *Reset to model thickness* (enabled
   only when an override exists), *Hide this thickness dimension*, *Show all
   thickness dimensions* (enabled only when something is hidden), plus the
   existing Quick-Estimation-role cascade for conjugate gaps.

## Why not just reuse plain-drag for re-anchoring

Plain-drag of the arrow is already a shipped gesture: it slides the thickness
**value** with live conjugate/FOV feedback. Overloading it would be ambiguous and
would need a fragile endpoint-proximity heuristic on the hot mouse path. The pick
modal (Ctrl-drag-release / right-click) is an explicit, separate mode, so both
gestures coexist.

## Repro / test

`.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_thickness_dimension_visibility`
— display-free guard. Checks: (A) toggle semantics — fresh row not hidden,
hide→hidden, a different row unaffected, toggle un-hides, two hidden then
`show_all` clears; (B) `add_overlays` consults `_thickness_dimension_is_hidden`
(source); (C) `layout_settings` save/load round-trips
`hidden_thickness_dimension_rows` (source); (D) the right-click context menu
calls `_maybe_show_thickness_dimension_menu` and the menu offers *Hide this
thickness dimension* + *Re-anchor to a surface/edge…* (source); (E) the
left-release commits the re-anchor on a drag (`dimension_anchor_was_drag`) and
`_begin_dimension_anchor_pick_for_row` exists (source). Penta phase 93.

## Owed

In-app eyeball: headless can't drive the VTK right-click menu or the Ctrl-drag
pick. The user should confirm the menu appears on a blue arrow and that
*Hide this thickness dimension* / *Show all* and the Ctrl-drag-onto-face commit
behave.
