# 0303 — Measure snaps along the optical axis on folded layouts (X-cursor object-snap)

Flagged recording `flag_20260714_145421_497`. On a two-fold RA-mirror system the user measured from an
RA-mirror centre (where the folded optical axes cross) to the imaging lens. The first pick snapped; the
second — aimed at the lens **edge** — misbehaved:

> *the second [click] won't highlight, I see the closest surface then clicked, the second arrow just landed
> [in the] wrong place.*

Two explicit requirements for the fix:

> *I need the distance to be measured along the optical axis (although the Lens Edge is selected).*
>
> *When I hover my mouse over the mirror surface, please change the mouse pointer to some kind of 'X' and
> have a snap feel before I click.*

## Root cause — a thin-edge pick miss, NOT a folded-geometry bug
The optical-axis projection is already correct on a folded arm: `_project_world_onto_optical_axis` iterates
**every** branch in `_optical_axis_pick_records` (incl. the +X reflected arm at `z=87.3` where the lens sits),
so a lens point projects onto the reflected arm keeping its axial position. The failure is upstream of the
snap: the lens silhouette **EDGE** actor is drawn `PickableOff` (it registers `track_row_index` /
`follow_step_label`, not the `pick_*` keys the registration guard requires). Aiming at that thin edge grazes
the ray **past** the lens to whatever is behind → the pick key is not a recognised component →
`_measure_axis_snap_for_pick` never fires → the raw off-axis edge point is recorded and nothing highlights.
So the fix is object-snap magnetism + visible feedback, **not** new folded geometry.

Proven numerically headless first (`bugs/diag_0303_measure_folded_snap.py`, real recording geometry): the
lens-edge pick `[194.545, 27.66, 87.312]` projects to `[194.545, 0.0, 87.3]` (on-axis), the mirror→lens axial
distance is `72.531 mm` vs the raw off-axis `77.626 mm`, and the snap fires only when the picked actor is
recognised.

## The fix — a Measure object-snap UX (localised to the tool, `open3d_inspector.py`)
Rather than change STEP-overlay edge pickability globally (which would risk selection/rotation regressions),
the magnetism lives entirely in the Measure resolve path and runs **only** when the exact-cursor pick finds no
component — the working body-hit case and perf are untouched.

* **`_measure_pick_offset_ring(radius_px=9.0)`** (pure, `@staticmethod`) — screen-space sample offsets: the
  exact cursor `(0,0)` **first**, then 8 symmetric points on a radius-9 ring. Display-free so its ordering and
  geometry are unit-testable.
* **`_measure_recognised_component(hit_key)`** — the single recognition gate (key in `_actor_step_map` or
  `_actor_row_map`), shared by hover, click and the resolver so all three agree.
* **`_measure_resolve_snap(x, y)`** — picks the exact cursor; if that is unrecognised, walks the ring and
  returns the first recognised sample (leaving the picker at `(sx, sy)` so the gold face highlight resolves
  there); else restores the exact pick and returns it raw. Returns `(hit_key, world, normal, sx, sy)`.
* **`_set_measure_snap_cursor(over_surface)`** — swaps the Tk `X_cursor` in while the cursor is over a
  snappable surface (the OSNAP "you will snap here" feel), back to `crosshair` over empty space.
* **`_show_measure_snap_marker(world)` / `_clear_measure_snap_marker()`** — draw a small view-facing "X" (two
  crossed `vtkLineSource` diagonals spanned by the camera right/up vectors, colour `(1.0, 0.55, 0.0)`, width
  2.6) at the resolved snap point, `PickableOff`. Cleared + redrawn each hover, cleared on click and in
  `clear_measurements`.

Hover (`_update_measure_hover_highlight`) and click (`_on_left_button_press`) both route through
`_measure_resolve_snap`, then `_measure_axis_snap_for_pick` — so the recorded point equals the "X" the user
was shown, and on the folded layout the lens-edge pick is measured **along** the optical axis.

## Files
- `KrakenOS/UI/open3d_inspector.py` — snap resolver, ring, recognition gate, X-cursor, X marker; hover + click
  + `clear_measurements` wiring; `_measure_snap_marker_actors` state; status text now says "(snaps to the
  optical axis)".

## Verified (display-free — headless VTK segfaults under Xvfb llvmpipe)
- `bugs/diag_0303_measure_folded_snap.py` — numeric proof on the real recording geometry: projection lands on
  the +X arm, axial 72.531 vs raw 77.626, recognition gate correct. **ALL PASS**.
- `KrakenOS/UI/validate_open3d_measure_folded_axis_snap.py` (`run_checks()`) — offset-ring purity
  (centre-first, 8 symmetric samples at radius 9), folded projection (y=0, z=87.3, axial x kept), axial
  distance = `|267.0755−194.545|` and < raw, recognition gate (recognised snaps / unrecognised → None keeps
  the raw point), plus source-text asserts for the hover/click/clear/cursor/marker wiring (marker is
  `PickableOff`). **PASSED**.
- Penta **phase 266** (`phase_266_measure_folded_axis_snap`) delegates to the guard; baseline updated to
  `"266": "pass"`.

## Notes / remaining
- In-app eyeball owed: the X cursor + X snap marker + folded-axis measurement need a GLX display to see live
  (the render/cursor path can't be exercised under headless Xvfb llvmpipe without segfaulting).
