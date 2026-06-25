# 0137 — a glued beam splitter does not follow the LED during a live drag

## Symptom

Recording `recording_20260625_073038.json`, flag `flag_20260625_073016_268`:

> *"after glued, moving the LED, BS is not following live."*

The user glued the beam splitter to the LED (item-3 BS↔LED rigid glue), then grabbed
the LED and dragged it. The LED body tracked the cursor, but the glued beam splitter
**stayed put during the drag** and only snapped into place when the mouse was released
(the post-drag refresh rebuilds it from the carried data). The glue looked broken mid-drag.

## Root cause

The live drag splits each frame into a **data** carry and an **actor** carry:

- `editor.translate_step_overlay(label, delta, refresh=False)` updates the dragged
  body's DATA and — via `_carry_glued_optical_led` (`scene_placement_commands.py:2636`) —
  the glued **partner's DATA** (the BS overlay offset, or the promoted-BS row pose via
  `translate_scene_row_pose_vector`). Neither primitive touches any VTK actor.
- `inspector._translate_step_overlay_actors(label, delta)` then `AddPosition`s the
  **dragged label's** actors so the body tracks the cursor without a rebuild.

So per frame the partner's *data* advanced but its *actors* were never moved. The actor
carry only ever moved the dragged label (`_step_follow_actor_map[label]`), so the glued
partner sat frozen until mouse-up, when the refresh rebuilt it from the (correct) carried
data. Live drag = partner lag; commit = partner snap.

(Compare bugs/0133, which carried the glue across an LED *distance* edit; that fixed the
DATA path. This is the live *actor* path — the data was already carried, the actors were not.)

## Fix

Mirror the same world delta onto the glued partner's **actors** at the actor chokepoint
(`open3d_inspector.py`):

```python
if carry_glue:
    self._mirror_glued_partner_actors(label, delta)
if render:
    self.render()
```

`_mirror_glued_partner_actors` resolves the partner exactly as `_carry_glued_optical_led`
does (BS = the `optical` overlay **or** a promoted optical-solid row; LED = always an
overlay) and moves its actors:

- partner is an overlay → `_translate_step_overlay_actors(partner, delta, carry_glue=False, render=False)`
- partner is the promoted BS row → `_translate_row_actors(row_index, delta, render=False)`

The partner move is **glue-suppressed** (`carry_glue=False`, so it cannot mirror back onto
the dragged body) and **render-deferred** (`render=False`, so the single `self.render()` at
the end of the dragged label's actor carry repaints both bodies together — one render per
frame, no double-paint). `_translate_row_actors` gained a `render` keyword for the same
reason. Data and actors stay in lock-step every frame; mouse-up's rebuild is a no-op move.

This covers every LED-drag path — the three carry-follow sites
(`_apply_carry_follow_transition`, `_apply_step_carry_follow_motion`,
`_apply_step_carry_motion_delta`) that carry data per-frame, and the translate-arrow drag
(`_apply_step_translate_drag_motion`) whose data is deferred to mouse-up — because they all
funnel their actor motion through `_translate_step_overlay_actors`.

## Test

- `KrakenOS/UI/validate_open3d_glue_live_actor_carry.py::run_checks` — display-free:
  - **Logic**: the real `_mirror_glued_partner_actors`, run against a stub, mirrors an LED
    drag onto an overlay BS (`_translate_step_overlay_actors("optical", …, carry_glue=False,
    render=False)`) and onto a promoted BS row (`_translate_row_actors(row_index, …,
    render=False)`), is a no-op when nothing is glued, and never carries back onto the
    dragged label.
  - **Source**: `_translate_step_overlay_actors` calls `_mirror_glued_partner_actors`
    under the `carry_glue` gate and `_translate_row_actors` honours a `render` keyword.
- Penta phase **127**.

## Status

Fixed; guard green standalone and in the penta harness (phase 127, display-free). In-app
eyeball owed — the embedded-VTK live drag cannot run headless; the user should confirm that,
with the BS glued, dragging the LED now drags the beam splitter with it in real time (no
snap-on-release). Scope is the flagged direction (LED drag → BS follows) plus the free
symmetric case (BS-overlay drag → LED follows, same code path); a promoted-BS-*row* drag
pulling the LED is a separate `_translate_row_actors` caller and was not flagged.
