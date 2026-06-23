# 0115 — Manual measurements should align in a plane along the optical axis

**Request (2026-06-23, flag_20260623_090232_054):**
> "Can put these manual measurement align with the optical axis so that all of them
> can align side by side adjacent to each other?"

Clarified with the user over two rounds: measure between component features pulled
onto the optical axis, and draw all the dimension arrows **coplanar in a single
plane** (e.g. Y=0) so they line up adjacent to each other instead of being scattered
at arbitrary 3D points/orientations.

The manual Measure tool (bugs/0108) recorded raw point-to-point picks: each click
took the exact surface point under the cursor, so a camera↔lens dimension started on
some arbitrary rim point, ran at a skew angle, and overlapped the next measurement.
Component features all sit on (or project onto) the optical axis, so an on-axis
dimension is naturally parallel to the axis — the user wanted the picks pulled onto
the axis and the dimension lines fanned out within one plane.

---

## Agreed scope (user-approved)

Four consolidated sub-features, built in two commits:

1. **Axis snap (always-on, edge fallback)** — a click on a recognised component
   pulls the pick onto the optical axis **at the clicked feature's z** (a lens FRONT
   edge snaps to the front, the object plane to the on-axis FOV centre); a bare-edge
   click keeps raw point-to-point.
2. **Coplanar stacked lanes** — visible dimensions draw parallel to the axis, all
   **within the X=0 plane** (offset in +Y), each auto-assigned a lane (45 mm base,
   +18 mm each) so the arrows sit adjacent to each other without overlapping.
3. **Live rubber-band preview** — after the first pick a dimension line + live
   distance label follows the cursor until the second click (CAD "arrow on mouse").
4. **Draggable offset** — a grab handle at each dimension midpoint; drag
   perpendicular to override that segment's lane.

**Commit 1 (testable headless):** #1 + #2.
**Commit 2 (in-app eyeball):** #3 + #4.

### Two clarifications after the first cut (both folded into #1/#2)

- *"I clicked the Imaging Lens front edge, the arrow snapped to the lens body centre
  — wrong, should snap to the lens front edge."* → the snap is **not** the body
  centre; it projects the **clicked point** onto the axis, keeping its z. The object
  plane (a flat disk) still resolves to the FOV centre because its only z is the
  plane's.
- *"The whole point is to align the measurements in a plane (e.g. X=0) so the arrow
  segments go adjacent to each other."* → the lane offset is **+Y within the X=0
  plane**, not +X out of plane, so every axis-aligned dimension stays coplanar. (The
  user works in the **-YZ view**, where the X=0 plane is seen face-on.)

---

## Commit 1 — axis snap + coplanar stacked lanes

`KrakenOS/UI/open3d_inspector.py`:

- **`_project_world_onto_optical_axis(world)`** — projects a world point onto the
  nearest optical-axis polyline segment (iterates `_optical_axis_pick_records` — the
  dotted global guide + any folded-branch axes — and keeps the closest point on the
  closest segment; falls back to the global z-axis at (0,0)). This is what KEEPS the
  clicked feature's axial position: a lens front edge stays at the front.
- **`_measure_axis_snap_for_pick(actor_key, world)`** — returns that projection when
  the picked actor is a recognised component (`_actor_step_map` STEP overlay or
  `_actor_row_map` row), else `None` — the **edge fallback**.
- **`_on_left_button_press` measure branch** — after the pick computes `world`, it
  calls `_measure_axis_snap_for_pick(self._actor_key(hit_actor), world)`; when a
  point comes back it overrides `world = snapped` and drops the normal
  (`normal = None`) so the span is a straight on-axis point-to-point. The point
  survives the `_anchor_measure_point` → `_resolve_measure_point` z-station
  round-trip (that path preserves x,y and re-derives z to the same station).
- **`_measure_segment_offsets()`** — `{seg_id: offset_mm}` lane allocator. Visible
  segments fan out `base=45 mm + lane*18 mm` in id order; a hidden segment is
  excluded entirely; a segment carrying an explicit `seg['offset']` (a future drag,
  Commit 2) keeps that standoff and is **excluded from lane numbering** so a dragged
  dimension never shifts the rest.
- **`_measure_segment_offset_endpoints(seg, offset_amt=None)`** — now takes the
  assigned lane; the perpendicular standoff is **+Y (within the X=0 plane)** — it
  falls back to +X only when the segment itself runs along Y — so the dimension lines
  stay coplanar at x=0. The **draw loop** (`_refresh_measure_overlays`) and the
  **right-click proximity finder** (`_measure_segment_index_near_display_xy`) both
  compute the offsets dict once and pass the per-segment amount, so a right-click
  lands on exactly the line that is drawn.

Blast radius is tight: the snap only fires inside the armed Measure click; an
unrecognised pick falls straight through to the old raw point-to-point. Lane stacking
only changes the dimension-line standoff (the measured value is unchanged).

---

## Tests

- `python -m KrakenOS.UI.validate_open3d_measure_center_snap_lanes` — display-free
  `run_checks()` (6 assertions): axis-snap source wiring in the Measure branch;
  `_measure_axis_snap_for_pick` keeps the clicked feature's z (lens front stays at
  the front) and returns `None` for an edge pick; `_project_world_onto_optical_axis`
  lands on the nearest segment (folded branch); `_measure_segment_offsets` stacks
  lanes 45/63, honours an explicit offset, skips hidden;
  `_measure_segment_offset_endpoints` offsets in +Y within the X=0 plane (coplanar);
  the draw loop + proximity finder share the lane offsets. Plus
  `geometry_lane_proof()`: two axial segments stay coplanar in X=0 and stack on
  distinct, parallel, non-overlapping lanes (y=45 / y=63, 18 mm gap).
- Penta **phase 105** runs `run_checks()` only.

In-app eyeball owed (Commit 1): with Measure armed, click the object plane then the
imaging-lens front edge — the dimension should snap each pick onto the optical axis
at its own z (front edge stays at the front), run parallel to the axis within the
X=0 plane, and a second measurement should stack in an adjacent lane (also at x=0)
without overlapping the first.

---

## Commit 2 — live rubber-band preview + draggable lane handle

`KrakenOS/UI/open3d_inspector.py`:

- **Live rubber-band preview (#3)** — after the FIRST Measure pick, the Measure
  hover (`_update_measure_hover_highlight`, driven by the VTK mouse-move) calls
  **`_refresh_measure_preview(cursor_world)`**: it draws a dashed dimension line +
  live `↔ … mm` label from the anchored first point to the **snapped** point under
  the cursor (same `_measure_axis_snap_for_pick` the click uses), so the dimension
  forms on the mouse ("arrow on mouse"). Torn down (`_clear_measure_preview`) when
  the second point lands, on Clear, and whenever the cursor leaves a pickable face.
- **Draggable lane handle (#4)** — `_refresh_measure_overlays` now draws a
  **pickable grab sphere** at each visible dimension's midpoint and registers it in
  **`_actor_measure_handle_map`** `{actor_key: seg_id}`. The Tk mouse bindings
  (`open3d_mouse_bindings.py`) grab it: **`_measure_offset_drag_state_from_current_pick`**
  (press, suppressed while a fresh Measure is armed) →
  **`_apply_measure_offset_drag_motion(current_xy)`** (B1-motion) →
  **`_finish_measure_offset_drag`** (release). The new standoff is the **line-to-line
  closest approach** of the cursor ray to the segment's +Y offset direction
  (`_measure_offset_amount_for_cursor`, exact for any view, clamped to a 12 mm min),
  written to `seg['offset']`. Because an explicit `seg['offset']` is excluded from
  lane numbering (`_measure_segment_offsets`), a dragged dimension keeps its standoff
  and never shifts the other auto-stacked lanes.

Blast radius is tight: the preview only draws while a Measure is half-placed; the
handle drag only fires on a press that lands on a measure handle (priority over the
other drag detectors, but `None` for any other pick falls straight through to the
existing ladder).

### Tests (Commit 2)

- `python -m KrakenOS.UI.validate_open3d_measure_preview_drag` — display-free
  `run_checks()` (6 assertions): the drag standoff math (closest approach along +Y,
  clamped to 12 mm); `_apply_measure_offset_drag_motion` sets only the dragged
  segment's explicit offset; the explicit offset stays out of lane numbering (others
  keep their base lane); the preview build/teardown wiring in the Measure hover; the
  per-segment pickable handle + `_actor_measure_handle_map`; the Tk
  press/drag/release gesture wiring.
- Penta **phase 106** (new; baseline → 107 phases) runs `run_checks()` only.

In-app eyeball owed (Commit 2): with Measure armed, click the first feature — a
dashed line + live distance should follow the cursor until the second click; then
grab the midpoint handle of a finished dimension and drag it in ±Y — its standoff
should follow the cursor while the other dimensions stay on their lanes.
