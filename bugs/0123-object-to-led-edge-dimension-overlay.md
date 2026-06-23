# 0123 — dedicated, clickable object→LED-edge thickness overlay (Increment 1)

## Request

`flag_20260623_211507_666`:

> "I still need the thickness overlay from object to LED edge. The arrow should be
> dragable for me to drag the arrow to the correct edge of the LED."

and (follow-up):

> "but click the arrow segment, pop up dialog, input value will change the actual
> distance of the LED."

After bugs/0122 made the optical `S0` arrow a clean object→lens **working
distance** (and stopped the LED decoration from carving it), the user still wants
to *see* the object→LED distance they typed (the dialog value, e.g. 191.7 mm) as
its own arrow. The two interactions, mirroring how the optical thickness arrows
already behave:

- **click the arrow → dialog → value moves the LED** (placement edit);
- **drag the endpoint → re-measure to the correct LED edge, LED stays put**
  (pure measurement; the user confirmed "re-measure only, LED stays").

## Design

The LED is an **independent decoration** (confirmed by the user; LED↔lens in-line
coupling and BS↔LED glue are separate later stages). So the object→LED overlay is
a stand-alone annotation, not tied to any prescription row.

It is given a **sentinel row id** (`LED_OBJECT_EDGE_DIM_ROW = -7`) so it rides the
existing dimension render/pick path without colliding with a real table row:

- **render** — `Open3DThicknessDimensionService._emit_led_object_edge_dimension`
  draws an amber arrow from the object plane
  (`_surface_reference_world_point(0)`) to `object + led_object_edge_distance_mm`
  along the optical (+z) axis, labeled `Object → LED = <dist> mm`, offset further
  off-axis (band 2.4) than the blue `S0` arrow so the two object-anchored arrows
  don't overlap. Drawn only when an LED STEP is imported with a set edge distance.
  Called at the end of `add_overlays`.
- **click → moves the LED** — `edit_dimension` special-cases the sentinel and
  re-opens the LED edge-distance dialog (`editor.set_led_edge_distance()`), the
  same proven path that re-places the LED to the typed object→edge distance.
- **no drag yet** — `_emit_span_dimension` gained a `register_drag` flag; the LED
  overlay passes `register_drag=False`, so it is clickable but does not yet engage
  the bugs/0053 re-anchor drag (that re-anchor moves table rows / the LED; the
  "re-measure only, LED stays" drag is **Increment 2**).

## Increment 2 (next, not in this commit)

Drag the overlay's LED-end handle → snap to the nearest LED face → store the
chosen edge in the LED's local frame and report object→that-edge **without moving
the LED** (pure measurement). Needs in-app iteration (embedded-VTK drag pick).

## Test

`KrakenOS/UI/validate_open3d_object_to_led_dimension.py::run_checks` —
display-free, drives the real `_emit_led_object_edge_dimension` with
`_emit_span_dimension` monkeypatched to capture the emitted geometry:

- with an LED + set distance → one amber dimension, object plane → object+distance,
  sentinel row, `register_drag=False`, label naming the LED and the distance;
- no LED imported → no overlay; zero distance → no overlay;
- `edit_dimension(sentinel)` opens the LED edge-distance dialog and bypasses the
  table-row edit guard; a non-sentinel invalid row still hits the guard and never
  opens the LED dialog;
- source contract — `_emit_span_dimension` gates the drag on `register_drag`, and
  `add_overlays` draws the object→LED overlay.

Penta **phase 115** runs the guard.

## Note — in-app eyeball owed

Headless can't render the embedded-VTK dimension or drive its click, so the amber
arrow + click→dialog are verified in-app. The guard pins the emit geometry, the
sentinel routing, and the no-drag-yet contract.
