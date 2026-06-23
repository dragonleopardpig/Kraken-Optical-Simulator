# 0115 — Manual measurements should align with the optical axis, side by side

**Request (2026-06-23, flag_20260623_090232_054):**
> "Can put these manual measurement align with the optical axis so that all of them
> can align side by side adjacent to each other?"

Clarified with the user: *"what I mean is center of the FOV and center of the
Camera, Center of the Lens, etc.."* — measure between **component centres**, and
draw the resulting axis-aligned dimensions in stacked lanes so they don't overlap.

The manual Measure tool (bugs/0108) recorded raw point-to-point picks: each click
took the exact surface point under the cursor, so a camera↔lens dimension started
on some arbitrary rim point, ran at a skew angle, and overlapped the next
measurement. Component centres all sit **on the optical axis** (x≈0, y≈0), so a
centre-to-centre dimension is naturally parallel to the axis — the user just wanted
the picks to snap to centres and the dimension lines to fan out cleanly.

---

## Agreed scope (user-approved)

Four consolidated sub-features, built in two commits:

1. **Centre snap (always-on, edge fallback)** — a click on a recognised component
   snaps to its on-axis centre; a bare-edge click keeps raw point-to-point.
2. **Axis-aligned stacked lanes** — visible dimensions draw parallel to the axis,
   each auto-assigned a lane so they don't overlap.
3. **Live rubber-band preview** — after the first pick a dimension line + live
   distance label follows the cursor until the second click (CAD "arrow on mouse").
4. **Draggable offset** — a grab handle at each dimension midpoint; drag
   perpendicular to override that segment's lane.

**Commit 1 (this change, testable headless):** #1 + #2.
**Commit 2 (in-app eyeball):** #3 + #4.

---

## Commit 1 — centre snap + stacked lanes

`KrakenOS/UI/open3d_inspector.py`:

- **`_measure_center_for_actor(actor_key)`** — the on-axis centre of the component
  the picked actor belongs to. A STEP overlay (camera/lens/LED) resolves via
  `_live_step_body_world_bounds(label)`; a CAD/STL/promoted optical-solid row
  resolves via `_row_actor_center_world(row_index)` (union-bounds centre of all the
  row's actors). Returns `None` for anything else — the **edge fallback**.
- **`_on_left_button_press` measure branch** — after the pick computes `world`, it
  calls `_measure_center_for_actor(self._actor_key(hit_actor))`; when a centre comes
  back it overrides `world = center` and drops the normal (`normal = None`) so the
  span is a straight centre-to-centre point-to-point. The centre survives the
  `_anchor_measure_point` → `_resolve_measure_point` z-station round-trip because
  that path preserves x,y (kept at 0) and re-derives z to the same centre station.
- **`_measure_segment_offsets()`** — `{seg_id: offset_mm}` lane allocator. Visible
  segments fan out `base=45 mm + lane*18 mm` in id order; a hidden segment is
  excluded entirely; a segment carrying an explicit `seg['offset']` (a future drag,
  Commit 2) keeps that standoff and is **excluded from lane numbering** so a dragged
  dimension never shifts the rest.
- **`_measure_segment_offset_endpoints(seg, offset_amt=None)`** — now takes the
  assigned lane; the existing +Y perpendicular standoff places each lane clear of
  the axis. The **draw loop** (`_refresh_measure_overlays`) and the **right-click
  proximity finder** (`_measure_segment_index_near_display_xy`) both compute the
  offsets dict once and pass the per-segment amount, so a right-click lands on
  exactly the line that is drawn.

Blast radius is tight: centre-snap only fires inside the armed Measure click; an
unrecognised pick falls straight through to the old raw point-to-point. Lane
stacking only changes the dimension-line standoff (the measured value is unchanged).

---

## Tests

- `python -m KrakenOS.UI.validate_open3d_measure_center_snap_lanes` — display-free
  `run_checks()` (5 assertions): centre-snap source wiring in the Measure branch;
  `_measure_center_for_actor` returns STEP/row centres and `None` for an edge pick;
  `_measure_segment_offsets` stacks lanes 45/63, honours an explicit offset, skips
  hidden; `_measure_segment_offset_endpoints` honours `offset_amt` with a +Y
  axis-aligned standoff; the draw loop + proximity finder share the lane offsets.
  Plus `geometry_lane_proof()`: two axial segments land on distinct, parallel,
  non-overlapping lanes (y=45 / y=63, 18 mm gap) — the "side by side" guarantee.
- Penta **phase 105** (new; baseline → 106 phases) runs `run_checks()` only.

In-app eyeball owed (Commit 1): with Measure armed, click a camera then a lens — the
dimension should snap to each body's centre, run parallel to the optical axis, and a
second measurement should stack in a higher lane without overlapping the first.

Commit 2 (live rubber-band preview + draggable offset) is the follow-up.
