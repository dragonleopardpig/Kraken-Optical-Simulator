# 0019 — Slide handle: no hover highlight, and a bare click retraced hard

**Status:** Fixed (2026-06-05).
**Component:** Open 3D interaction — passive hover pick + hover decision
(`KrakenOS/UI/services/open3d_interaction.py`) and the placement-translate click
widget (`KrakenOS/UI/services/open3d_placement_widget.py`).
**Reported via:** in-app recorder, `attachment/recorded_bug_repros/flag_20260605_153157_448/`.

## Symptoms (user's words)

> Mouse hover on the slide handle does not highlight, left click (not dragging)
> can feel background computing hard, although not drag, it jerk a little bit.

A promoted optical-solid row shows a **Move (slide)** handle and a **Rotate**
handle. Hovering the slide handle gave no gold highlight (the rotate handle did),
and a bare left click on it visibly nudged the element one step and stalled.

## Root cause

Two independent gaps, both specific to the placement **MOVE** handle
(`_actor_placement_move_map`); the rotate handle was wired correctly.

1. **Hover never picked the slide handle.**
   `_passive_hover_pick_rotation_handle` built its VTK pick list from the
   step-rotate, step-translate and placement-**rotate** maps, but **not**
   `_actor_placement_move_map`. And both hover-decision branches in
   `_on_mouse_move` (the axis-pick path and the default path) checked
   `step_rotate` / `step_translate` / `placement_rotate` and called
   `_set_rotation_handle_hover(actor_key)`, but had no `placement_move` branch.
   So the slide handle was never in the pick set and never highlighted.

2. **A bare click slid + retraced.** A click (no drag) on a handle routes through
   `left_release` -> `_on_left_button_press` -> the WidgetRegistry, where
   `PlacementTranslateWidget.process` applied a discrete `delta_mm` translate via
   `_apply_scene_placement_translate_handle`. For a promoted optical solid that
   forces a full retrace (~0.5 s, see bugs/0012), so the click "computed hard" and
   the element jerked one snap step. Sliding is a *hold-drag* gesture — the drag
   path (`_apply_placement_drag_motion` / `_finish_placement_drag`) is already
   cheap and owns the slide — so a bare click should do nothing but hint.

## Fix

* **`open3d_interaction.py`** — `_passive_hover_pick_rotation_handle` now adds
  `_actor_placement_move_map` to the hover pick set, and both hover-decision
  paths gained a `placement_move` branch that applies the same gold hover via
  `_set_rotation_handle_hover(actor_key)` (the service highlights any handle
  actor key generically) plus a `"S{n} move handle: hold-drag {AXIS} to slide."`
  status hint.
* **`open3d_placement_widget.py`** — `PlacementTranslateWidget.process` no longer
  calls `_apply_scene_placement_translate_handle`; it consumes the click with the
  same hold-drag hint and a cheap `render()`, so there is no nudge and no retrace.
  (The `_block_if_busy` pick-mode guard is unchanged, and the drag path is
  untouched.)

## Tests

`KrakenOS/UI/validate_open3d_slide_handle_hover_and_click.py`
(`python -m KrakenOS.UI.validate_open3d_slide_handle_hover_and_click`) — entirely
display-free:

* **A/B (hover, source):** `_passive_hover_pick_rotation_handle` includes
  `_actor_placement_move_map`; `_on_mouse_move` has a `placement_move` read + an
  `if placement_move is not None:` highlight branch in **both** hover paths.
* **C (click, source):** `PlacementTranslateWidget.process` no longer calls
  `_apply_scene_placement_translate_handle(`.
* **D (click, behaviour):** dispatching a `PLACEMENT_TRANSLATE` `mouse_press` to a
  `PlacementTranslateWidget` bound to a mock inspector consumes the event, sets a
  "move handle … hold-drag" hint, and makes **zero** calls to the translate
  handler (a sentinel on the mock).

Verified fail-before / pass-after by stashing the fix: pre-fix all six checks
fail (hover pick set omits the map, 0 hover branches, click still translates +
applies one translate + sets no hint); post-fix `[PASS]`. Wired into the
comprehensive harness as `Phase 30`; gate baseline regenerated.
