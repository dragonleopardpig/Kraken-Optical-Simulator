# 0130 — "can't reposition the object→LED arrow to point to the correct LED edge"

## Symptom

`flag_20260624_083930_719`:

> "dragging the LED does change the value, but I can't reposition the arrow to point
> to the LED correct edge ... it is measuring the cable, not the LED edge, I need to
> be able to drag the arrow to point to the correct LED edge/face."

The amber **"Object → LED"** overlay (bugs/0123) terminates wherever the typed LED
edge-distance lands on the optical axis. On the user's LED STEP that point sits at a
protruding cable, not the LED's body face, so the arrow visibly measures the wrong
feature — and there was no way to correct it.

## Root cause

`Open3DThicknessDimensionService._emit_led_object_edge_dimension` always drew its
LED-side endpoint at `live_distance = led_object_edge_distance_mm + led axial drag`
(the bugs/0125 live distance). It **never consulted a re-anchor override**. So even
though the right-click menu's *"Re-anchor to a surface/edge…"* mode could run and
store an override (the amber label actor already carries a drag record, so
`_begin_dimension_anchor_pick_for_row(-7)` begins fine), the committed override on
sentinel row **-7** had no effect on the drawn arrow — it snapped straight back to the
typed point.

The existing re-anchor plumbing is measurement-only for any row that is *not* the S0
object/LED placement edge: `apply_dimension_anchor_override` routes row 0 `start` to
`apply_led_object_edge_pick` (which **moves** the LED) but stores every other row —
including -7 — as a pure measurement override. So the data path was correct; only the
*render* ignored it.

## Fix

**Honor the re-anchor override in the amber overlay (measurement-only; the LED never
moves).**

1. New pure helper `Open3DThicknessDimensionService.led_edge_override_endpoint(p0,
   current_offset_z, override)` resolves the LED-side endpoint from a stored override:
   `effective_z = ref_z + (current_offset − pick_time_offset)`. The picked face sits
   on the LED body, so it **rides the LED's later axial carry-drag** (with the LED
   undragged since the pick, it stays exactly at `ref_z`). Returns `(p1, live)` on the
   axis, or `None` when there is no usable override.
2. `_emit_led_object_edge_dimension` looks up
   `editor._dimension_anchor_override_for_row(LED_OBJECT_EDGE_DIM_ROW)` and, when set,
   draws to `led_edge_override_endpoint` instead of the typed distance; the label
   gains a `[z=…]` suffix. The arrow now also `register_drag=True` so it is itself a
   re-anchor handle — a stray value-drag is harmless because
   `drag_state_from_current_pick` rejects the negative sentinel row.
3. `apply_dimension_anchor_override` captures the LED's pick-time axial offset
   (`led_offset_z`) for row -7, so the render can add the live delta.
4. Re-seating the LED (`set_led_edge_distance` dialog or `apply_led_object_edge_pick`)
   calls the new `_clear_led_edge_dimension_override`: a measurement pinned to a world
   z can't follow a body re-seat, so the override is dropped and the arrow falls back
   to the typed distance (the user can re-anchor again on the new pose).

## Test

`KrakenOS/UI/validate_open3d_led_edge_reanchor.py::run_checks` — display-free; binds
the real re-anchor commands (`apply_dimension_anchor_override`,
`_dimension_row_is_object_led`, `_dimension_anchor_override_for_row`,
`_clear_led_edge_dimension_override`) onto a light fake editor and calls the real
`led_edge_override_endpoint`:

- **A** a missing / malformed override yields no endpoint;
- **B** an override repoints the endpoint onto the picked face (`ref_z=60`), *not* the
  typed distance (50) — and stays on the optical axis;
- **C** after a +12 axial LED carry-drag the endpoint tracks to 72; equal pick/current
  offset stays at `ref_z`;
- **D** re-anchoring row -7 stores `ref_z` + the pick-time LED offset and **never**
  calls `apply_led_object_edge_pick` (measurement-only), whereas row 0 `start` *is* the
  LED placement edge; clearing drops the override;
- **source contract** — the overlay honors the override via
  `led_edge_override_endpoint` + `_dimension_anchor_override_for_row` and registers a
  drag handle; the commit captures `led_offset_z`; both LED re-placement paths clear it.

Penta **phase 120** runs this guard. Mutation-tested: dropping the LED-drag tracking
term (`effective_z = ref_z`) flips C; routing row -7 through `apply_led_object_edge_pick`
flips D (both "stored no override" and "MOVED the LED").

## Note — in-app eyeball owed

Headless llvmpipe can't drive the embedded-VTK hover/click pick, so the actual
right-click → pick-the-LED-face → arrow-jumps-to-the-face gesture is verified in-app.
The guard pins the override-honoring math, the measurement-only invariant, the
LED-drag tracking, and the wiring.
