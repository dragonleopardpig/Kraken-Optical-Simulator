# 0133 — editing the Object→LED distance must CARRY a glued beam splitter

## Symptom

Two recordings, after bugs/0132 made the Object→LED distance edit move the LED:

`flag_20260624_130423_829` — "changing the Object LED distance move the LED. However,
this is **after glue to BS. Obviously BS is detached.** And notice those thickness overlay
in **Blue not updating**. Is the 'gap to solid' measure BS distance?" The LED moved
forward to z[136.9, 213.3] (distance 200→150), but the promoted beam-splitter solid (row 1,
BK7, bounds z[200.4, 255.4]) stayed put — visibly detached/overlapping the LED. The amber
**"Object → LED = 150 mm"** updated; the blue **"gap to solid = 200 mm"** did not.

`flag_20260624_130325_946` — "seems like there are **2 object to LED thickness overlay**."
With the LED at distance 200 the beam splitter is glued at the LED's object edge, so the
amber object→LED arrow (=200) and the blue object→solid gap (=200) span the same distance
and **look like a duplicate**.

## Root cause

The BS↔LED two-body glue (bugs/0127) is carried by handing `_carry_glued_optical_led` a
**world delta** — but only the drag *primitives* do that (`translate_step_overlay`,
`translate_scene_row_pose_vector`, `translate_scene_row_pose`). The Object→LED **distance**
paths never issue a delta. They reposition the LED by rewriting
`led_object_edge_distance_mm` / `led_step_object_edge_local_z` and letting
`_led_step_z_translation() = max(distance, 0) − reference` recompute the LED's base
placement at the next scene rebuild. No `_carry_glued_optical_led` call ever fires, so a
glued beam splitter is left behind.

Three writers move the LED this way and all dropped the glue:

- `set_led_edge_distance` — the edge-distance dialog **and** the object→LED dimension
  click (`Open3DThicknessDimensionService.edit_dimension` re-uses it). This is the flagged
  path.
- `apply_led_object_edge_pick` — the legacy object-edge pick (jumps the LED so the picked
  edge lands at the current typed distance).
- `_move_led_for_reanchored_value` — editing a re-anchored object→LED dimension value.

The **"blue not updating"** symptom is the same root cause: the blue "gap to solid" is the
object→promoted-solid (BS, row 1) gap. Because the BS didn't move, its gap didn't change.
And the user's question — *"Is the 'gap to solid' measure BS distance?"* — **yes**: it
measures the object→beam-splitter-solid distance, distinct from the amber object→LED
arrow; they only coincide because the BS is glued at the LED's object edge.

## Fix

New `ScenePlacementMixin._carry_led_glue_over_translation_change(before_translation)`:
capture `_led_step_z_translation()` *before* the LED-distance write, then after the write
derive `dz = translation_after − before_translation` and, when `|dz| > 1e-9`, hand it to
`_carry_glued_optical_led("led", (0, 0, dz))`. That reuses the proven 0127 carry (overlay
partner → placement offset; promoted-solid partner → row pose vector, behind the
re-entrancy guard). A no-op when nothing is glued or the LED did not move.

Wired into the three movers (capture before the attribute write, carry inside the same
history frame so undo reverts both bodies together):

- `set_led_edge_distance`,
- `apply_led_object_edge_pick` (the captured translation also feeds the existing `local_z`
  computation, so it stays exact),
- `_move_led_for_reanchored_value`.

`apply_led_object_edge_reanchor` (bugs/0132) is intentionally **not** wired: it sets the
typed distance to the picked face's *current* object distance, so the LED translation is
unchanged (the body stays put) — there is nothing to carry. The carry fires on the later
edge-distance edit that actually moves the body.

With the BS now following the LED, the blue object→solid gap recomputes on the next
refresh, so it tracks the LED in lockstep with the amber arrow.

## Not fixed here (open design question)

The "2 overlays" appearance is a *separate* display concern, not the glue bug: the amber
object→LED arrow and the blue object→solid gap are two legitimately distinct measurements
that **coincide** whenever the BS is glued at the LED's object edge — and they will keep
coinciding after this fix (both now track together). Whether to suppress one of the two
when the BS is glued to the LED at the same plane is a UX call left to the user.

## Test

- `KrakenOS/UI/validate_open3d_led_distance_glue_carry.py::run_checks` — binds the real
  distance/glue/carry methods onto a fake editor (promoted BS row + LED overlay,
  display-free): a 200→150 distance edit carries the BS by −50 in z only (LED offset
  untouched); a reference-attribute move carries it too (the helper is agnostic to which
  attribute moved the LED); a zero-shift change and an unglued scene carry nothing; and a
  source contract that the three movers route through the helper, which delegates to
  `_carry_glued_optical_led`.
- Penta phase **123**.

## Status

Fixed; the new guard + 0127 + both 0132 guards green. In-app eyeball owed (headless cannot
drive the right-click glue + dialog). The "2 overlays" dedup is deferred pending the user's
UX preference.
