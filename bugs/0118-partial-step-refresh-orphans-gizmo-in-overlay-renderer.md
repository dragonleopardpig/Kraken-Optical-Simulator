# 0118 — Rotate a STEP once, then its gizmo can no longer be selected

## Symptom

Import an LED STEP (it auto-selects, carry-primes, and draws its move/rotate
gizmo). Click a rotation arrowhead **once** — the LED rotates correctly. Then the
gizmo is **dead**: hovering or clicking a handle does nothing; you can no longer
rotate or move it.

Reported (flag `flag_20260623_143844_675`):

> "I can only rotate once, then no longer can select the gizmo."

The re-recorded state is the tell: the screenshot still shows a **full gizmo**
(translate arrows + rotation arcs) drawn around the LED, yet the live scene state
reports `selected_step_label: null`, `selected_step_rotation_active_label: null`,
and `rotation_handle_count: 0`. So the gizmo actors are still on screen, but no
handle is registered in any pick map — a **ghost gizmo** you can see but cannot
pick.

## Root cause

Gizmo handles render in a dedicated always-on-top overlay renderer
(`_gizmo_overlay_renderer`, bugs/0112) — they are added with `overlay_on_top=True`
and so live **only** in the overlay layer, never the main renderer.

A discrete rotation (clicking a rotation arrowhead) runs
`Open3DStepRotationHandleService.apply_handle`. With Live Mode off (the normal
positioning state) `physics_requested` is False, so it takes the **partial**
refresh path:

```python
refreshed = bool(inspector.refresh_imported_step_overlay(label))
```

`refresh_imported_step_overlay` (`open3d_step_overlay_refresh.py`) first tears the
old overlay down via `_remove_step_overlay_actors(label)`, then rebuilds the body
and — because `editor._selected_step_label == label` — re-adds the gizmo handles.

The teardown is the bug. `_remove_step_overlay_actors` removes each actor with:

```python
inspector._remove_renderer_view_prop(actor)   # MAIN renderer only
```

`_remove_renderer_view_prop` calls `self._renderer.RemoveViewProp(actor)` — it
touches **only the main renderer**. The gizmo handle actors live in
`_gizmo_overlay_renderer`, so they are **not** removed from the overlay; they
orphan there, still visible. Meanwhile `_remove_actor_registration` clears their
pick-map entries (`_actor_step_rotate_map`, …). The rebuild then adds a fresh set
of handles to the overlay + maps.

The full scene refresh does not have this problem: it wipes the overlay wholesale
(`_gizmo_overlay_renderer.RemoveAllViewProps()`, `open3d_scene_refresh.py`) before
rebuilding. Only the **partial** STEP-overlay refresh leaked.

Across one rotate → re-pick cycle the orphans accumulate. When the user next
clicks "the gizmo," the overlay-first pick (`_traced_pick(... overlay ...)`,
bugs/0112) lands on an **orphaned** handle actor whose key is in **no** map, so it
resolves to no handle target — the click falls through to a scene pick that
deselects the LED (`editor._selected_step_label = None`). The follow-on partial
refresh then clears the maps (`rotation_handle_count: 0`) and, with nothing
selected, does **not** rebuild the gizmo — yet the orphaned overlay actors stay
drawn. Final state: gizmo visible, `selected_step_label: null`,
`rotation_handle_count: 0`. Exactly the recorded snapshot.

A sibling omission compounds it: `_remove_actor_registration` pops
`_actor_step_rotate_map` but **not** `_actor_step_translate_map`, so a torn-down
translate arrow leaves a stale map entry pointing at an overlay-orphaned actor.

## Fix

`_remove_step_overlay_actors` must clear actors from **both** renderers. Swap the
main-only `_remove_renderer_view_prop` for `_remove_actor_from_renderers`, which
removes from the main *and* the gizmo overlay renderer (and is a harmless no-op
for an actor that only lived in one):

```python
inspector._remove_actor_from_renderers(actor)   # main + gizmo overlay
```

Also pop `_actor_step_translate_map` in `_remove_actor_registration` alongside the
existing `_actor_step_rotate_map` pop, so the teardown fully clears the gizmo
pick-maps.

With both, a partial refresh leaves exactly one gizmo (the freshly rebuilt,
fully-mapped set) on the overlay — no orphans — so every handle stays pickable and
the LED rotates as many times as you like.

## Test

`KrakenOS/UI/validate_open3d_step_overlay_removes_gizmo_from_overlay.py::run_checks`
(display-free; uses fake renderers that record `RemoveActor`/`RemoveViewProp`):

1. behavioral — register a gizmo handle actor in `_actor_step_rotate_map` +
   `_actor_by_key` and add it to **both** a fake main renderer and a fake overlay
   renderer; call `_remove_step_overlay_actors('led')`; assert the actor was
   removed from the **overlay** renderer (not just the main) and that
   `_actor_step_rotate_map` is empty;
2. behavioral — a torn-down translate arrow is popped from
   `_actor_step_translate_map`;
3. source contract — `_remove_step_overlay_actors` calls
   `_remove_actor_from_renderers` (not the main-only `_remove_renderer_view_prop`).

Penta phase 110 runs this guard.

## Note — in-app eyeball owed

Headless Xvfb cannot drive the embedded-VTK pick that exercises the live
rotate→re-pick loop, so the "rotate many times" behaviour is verified in-app. The
guard pins the source + bookkeeping contract that removes the orphan.
