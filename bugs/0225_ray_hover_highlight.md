# 0225 — Pick-rays mode: hovering a traced ray now highlights it

**Status: FEATURE SHIPPED. With "Pick rays" checked, moving the mouse over a traced ray draws a
light hover highlight on that ray (and names it in the status bar); clicking still selects it and
opens the Ray Inspector with the brighter selection highlight. In-app confirm owed (hover is a
mouse gesture; headless proves the overlay mechanics + wiring, not the gesture).**

## The request

`flag_20260705_100834_387`: "Checked the 'Pick rays' box, mouse hover does not show highlight of
ray. Clicked on each ray, ray info window pop up." Clicking worked (which also confirmed the
bugs/0223 merged-actor cell picking in-app); hover gave no feedback. Not a regression — the
`_on_mouse_move` hover handler had never highlighted traced rays.

## What was added

- **`_apply_ray_hover_overlay(ray_index)`** (`open3d_inspector.py`): draws the hovered ray's stored
  display polyline (`_ray_display_points`, bugs/0223) as a pale-yellow overlay (width 2.6) —
  deliberately lighter than the click-selection overlay (bright yellow, width 4.0) so the two read
  differently. Tracked by its own `_ray_hover_overlay_key/_index`, so hovering never disturbs the
  selection highlight. Returns True only when the overlay actually changed — the caller renders
  only then (hover moves are frequent). Cleared by `_clear_merged_ray_state` on every scene rebuild.
- **The `hover_default` branch of `_on_mouse_move`** (`services/open3d_interaction.py`): gated on
  `_ray_pick_enabled()` (the Pick-rays toggle), resolves the hovered ray from the picked merged
  actor via the live picker cell (`_ray_index_for_actor`, bugs/0223 Fix B), skips the currently
  SELECTED ray (the selection overlay owns it), applies the hover overlay, sets the status text
  ("Ray N: click to open it in Ray Inspector."), and renders on change — including the un-hover
  clear, after which the normal step-face hover flow continues.

## Verification

Display-free guard `validate_open3d_ray_hover_highlight` (4/4): the overlay lifecycle (add →
same-ray no-op → replace → clear, exactly one actor at a time), separation from the selection
overlay (distinct keys; the selection actor survives a hover clear), scene-rebuild clearing, and
the wiring (mode gate + merged-actor cell resolve + selected-ray skip + render-on-change). Penta
**phase 201**, baseline `pass`. Regression sweep green: `ray_toggle_scene_retention`,
`live_transient_step`, `async_trace_equivalence`.

## In-app checklist

1. Show Rays on + "Pick rays" checked → hover a ray: it brightens (pale yellow) and the status bar
   names it; move off: the highlight follows the cursor away.
2. Click the ray: the brighter selection highlight + Ray Inspector appear (hover no longer doubles
   it while it stays selected).
3. Un-check "Pick rays": hover does nothing again (mode-gated).
