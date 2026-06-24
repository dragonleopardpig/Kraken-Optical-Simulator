# 0125 — object→LED amber arrow must track the LED's LIVE edge (0123 Increment 2, measurement half)

## Symptom

`flag_20260624_075900_372`:

> "dragging the LED still show wrong Object LED measurement."

The dedicated amber `Object → LED = <dist> mm` arrow that bugs/0123 added keeps
reading the value the user **typed** into the LED edge-distance dialog. After they
drag the LED along the axis, the LED body moves but the arrow stays frozen at the
old number, so it now points past (or short of) the real LED edge.

`step_overlay_poses` pins the drag: `led` carries
`placement_offset_xyz = [-0.0, -0.0, -36.1658]` with `axis_anchor = None` — i.e. a
**free carry-drag** slid the LED 36.17 mm toward the object, but the arrow still
showed the typed distance.

## Root cause

The LED is placed by two independent transforms:

1. **the dialog placement** — `_led_step_z_translation()` shifts the STEP so the
   user's chosen edge (`led_step_object_edge_local_z`) lands at world
   `z = led_object_edge_distance_mm` (the typed "object → LED" distance);
2. **a free carry-drag** — `_set_step_placement_offset_xyz("led", …)` adds
   `led_step_placement_offset_xyz` *on top*, and (this is the trap) it does **not**
   touch `led_object_edge_distance_mm`.

`_emit_led_object_edge_dimension` drew the arrow to `p0 + axis * distance` using
only the typed `distance`, so the drag's axial slide was invisible to it:

```python
axis = np.array([0.0, 0.0, 1.0])
p1 = p0 + axis * distance            # <- stale: ignores the carry-drag
label = f"Object → LED = {distance:.4g} mm"
```

## Fix

The drag's axial (`+z`) component is exactly how far the chosen edge slid, so the
**live** object→edge distance is `distance + placement_offset_z`. Measuring to that
keeps the arrow on the dragged edge and — because the offset is `0` when undragged
— still equals the value the user typed on first render (no jump):

```python
offset_z = float(editor._step_placement_offset_xyz("led")[2])
live_distance = distance + offset_z
if not np.isfinite(live_distance) or live_distance <= 1e-6:
    return 0                                   # edge at/behind object -> no arrow
p1 = p0 + axis * live_distance
label = f"Object → LED = {live_distance:.4g} mm"
```

Using the placement offset (not the live actor bounds) is deliberate: it tracks the
user's *chosen* edge, agrees with the typed value at zero drag, respects x/y drags
and z-rotations (which don't change the axial measure), and is headless-testable —
no rendered actor required.

This is the **measurement half** of bugs/0123 Increment 2. The other half —
*dragging the arrow's LED-end handle to re-measure to a different LED face without
moving the LED* — is an embedded-VTK drag-pick and remains an in-app increment
(2b); the overlay still passes `register_drag=False`.

## Test

`KrakenOS/UI/validate_open3d_object_to_led_dimension.py::run_checks` — display-free,
drives the real `_emit_led_object_edge_dimension` with `_emit_span_dimension`
monkeypatched to capture the emitted geometry. New coverage on top of the 0123
checks:

- **F** — with the LED dragged `-36.1658` mm (the flag), the arrow endpoint and
  label track the LIVE `155.5342` mm and no longer read the stale typed `191.7`;
- **G** — an LED dragged to/behind the object (`offset_z = -200`) draws no
  degenerate arrow;
- **source contract** — the emit reads `_step_placement_offset_xyz` / `live_distance`
  and the stale `axis * distance` form is gone.

Penta **phase 115** runs this guard (broadened from 0123 to 0123 + 0125; no new
phase — the live-edge behaviour rides the same guard). Mutation-tested: reverting
the construction to `live_distance = distance` flips F/G to FAIL.

## Note — in-app eyeball owed

Headless can't render the embedded-VTK dimension or drive its drag, so the amber
arrow following a live LED drag is verified in-app. The guard pins the live-edge
measurement math; if a live case still misreads, `step_overlay_poses[led]` plus the
drawn arrow value isolate any remainder to the placement-offset read.
