# 0132 — object→LED arrow re-anchor must persist and MOVE the LED on a value edit

## Symptom

Two recordings, immediately after shipping bugs/0130:

`flag_20260624_115328_911` — "reanchor the Object LED distance." The amber
**"Object → LED"** arrow correctly snapped onto the picked LED body face: the label
read `Object → LED = 213.2 mm  [z=213.2]` (the bugs/0130 override worked, LED parked at
z[200, 276.4]).

`flag_20260624_115350_660` — "changed the value of the Object LED distance by input in
the pop up dialog. **The segment arrow shorten but the arrow point to the wrong location
just like before anchor, and the LED is not moving.**" After the dialog edit the label
reverted to `Object → LED = 200 mm` (no `[z=…]` suffix) and the LED body was still at
z[200, 276.4].

## Root cause

bugs/0130 made the row `-7` re-anchor **measurement-only**: it stored an override on the
sentinel row and `_emit_led_object_edge_dimension` honored it, but it never touched the
LED's real object-edge reference. Worse, `set_led_edge_distance` called
`_clear_led_edge_dimension_override()` on every value-change, so:

1. editing the dialog **dropped** the override → the arrow fell back to the typed
   endpoint, which on this LED STEP lands on a protruding cable ("the wrong location
   just like before anchor"); and
2. the LED never moved, because the picked face was never wired into
   `led_step_object_edge_local_z` (the edge that placement pins at
   `led_object_edge_distance_mm`).

That was the wrong model. The user wants the arrow to be the LED's **distance handle**:
re-anchor onto a face, then edit the number to *move the LED* with the chosen face
tracking the value.

## Fix — reverses the 0130 "measurement-only" decision

Route the row `-7` re-anchor to a new `apply_led_object_edge_reanchor`, which makes the
picked face the LED's persistent object-edge reference **without jumping the body now**:

1. New pure helper `ScenePlacementMixin._led_reanchor_reference(face_world_z,
   current_translation) -> (local_z, edge_distance)`:
   - `local_z = face_world_z − current_translation` (the face in the LED's
     pre-translation frame), and
   - `edge_distance = face_world_z` (the face's *current* object distance).

   The placement model pins the edge at `led_step_object_edge_local_z` to world z
   `led_object_edge_distance_mm` via `_led_step_z_translation() = distance − reference`.
   With `edge_distance` set to the face's current world z, the recomputed translation
   equals the current one → **no jump on the pick**. A later edit to `V` gives
   `translation = V − local_z`, so the face lands at `local_z + translation = V` →
   **the LED moves, the face tracks**.

2. `apply_led_object_edge_reanchor` sets `led_step_object_edge_local_z` + 
   `led_object_edge_distance_mm` from the helper, clears any stale override, and
   refreshes. `apply_dimension_anchor_override` routes `int(row_index) == -7` here
   (row 0 `start` still routes to the legacy `apply_led_object_edge_pick`).

3. The measurement-only machinery is removed: the `-7` `led_offset_z` capture in
   `apply_dimension_anchor_override`, the override branch in
   `_emit_led_object_edge_dimension` (it now always measures to the live object edge,
   `distance + axial drag`), and the dead `led_edge_override_endpoint` helper are gone.
   `_clear_led_edge_dimension_override` stays as a defensive drop of any stale `-7`
   override from undo history / a pre-fix session.

## Test

- `KrakenOS/UI/validate_open3d_led_edge_reanchor.py::run_checks` — rewritten for the new
  contract: the pure reference math, the **no-move** invariant on the pick, the
  **move-on-edit** invariant (face lands at the typed value), routing through
  `apply_dimension_anchor_override`, and source contracts (the `-7` measurement path /
  `led_edge_override_endpoint` are gone; the overlay still registers a drag handle).
  Mutation-tested: dropping the `led_object_edge_distance_mm` assignment reintroduces
  the legacy jump and the guard fails (B/C/D).
- `KrakenOS/UI/validate_open3d_led_reanchor_moves.py::run_checks` — the literal
  flag_115350 repro: re-anchor an LED (typed 200, front extremum) onto a face at z=213.2
  (no jump), then edit the dialog and assert the LED **translates** so the face lands at
  the new value.
- Penta phase **120** (rewritten contract) + new phase **122** (the flag_115350 repro).

## Status

Fixed; guards + both penta phases green. In-app eyeball owed (headless cannot drive the
right-click re-anchor pick / dialog).
