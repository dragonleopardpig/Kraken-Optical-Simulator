# 0353 — Measure tool: edge-to-edge picks (click one edge, then the other, read the opening)

**Status:** IMPLEMENTED 2026-07-19 (guard `validate_open3d_measure_edge_pick`, penta phase 306,
baseline appended surgically per the bugs/0280 precedent). Implementation notes at the bottom.
**Flags:** 20260719_142831_679 ("LED Botton view"), 20260719_142846_785 ("LED Front view") — snapshots of
the OPT-CO90 module's two window openings, taken because the Measure tool could not produce the numbers.

## The ask

> "I wish the Measure tool can help me click one edge and the other edge so that I can measure them.
> Unfortunately, the measure tool does not function this way."

Today's Measure (`MEASURE` interaction mode, bugs/0100 + 0115) is point-based: every click resolves a
snap POINT (`_measure_resolve_snap` → axis snaps, centre-snap lanes, surface points) and two points make
a segment. There is no way to pick an EDGE as an entity, so "width of this opening" requires landing two
points that happen to be perpendicular across it.

## Motivating case — the CO90 window openings, measured out-of-app instead

`bugs/diag_co90_window_openings.py` reads them straight from the vendor STEP
(`attachment/LED/OPT-CO90-X-V1.6.2-H.STEP`, housing only — no internal splitter/diffuser glass is
modelled; STEP-local coordinates, module bbox 110.2 × 90.0 × 76.4 mm):

| Opening | Clear size | Where |
|---|---|---|
| Camera-side window | **51.00 × 51.50 mm** | rounded-corner cutout through a 4 mm frame (z 36.53→40.53), inside a 55.5 × 55.5 recess seat |
| Emitting/object-side window | **54.70 × 74.00 mm** | stepped recess at the opposite face: top-plate rails y span 74.00, left plate edge x −21.14, right edge = interior wall x +33.56 ending just below the plate |

Both windows share the y centre (−1.37); their x centres differ by 0.65 mm (5.56 vs 6.21). The scene
mounts the module with `led_step_rotation_x_deg: 180`, so the 54.70 × 74.00 window faces the object —
it is the physical source aperture the authored 55 × 74 LED models. The camera-side 51.0 × 51.5 window
sits ~56 mm behind it in the imaging path and is currently NOT modelled as an aperture anywhere in the
scene. Connection to `docs/source/knowledge_base/coaxial_led_dark_edges.rst`: these are exactly the
"unmodelled clear apertures" the corrected page lists as candidate mechanisms — the fold-axis margin of
the emitting window over the 39 mm FOV is (54.7−39)/2 ≈ 7.9 mm/side versus (74−39)/2 ≈ 17.5 mm/side on
the perp axis, so an extended-source penumbra eats the fold axis first (two dark edges), and the page's
fitted A_equivalent ≈ 49.5 mm lands within ~3 % of the real 51-mm-class camera window. Feed these
numbers to the future trace-through-true-apertures rework.

## Design

**Contract: in MEASURE mode, Alt+click picks the nearest DRAWN edge.** Plain click keeps today's point
snap unchanged. This mirrors the hover contract (plain = face, **Alt = nearest drawn edge**, penta
287/288) so the modifier means the same thing everywhere.

- Resolver: reuse the analytic-STEP drawn-edge machinery behind the Alt hover refine (front-depth-ranked
  nearest drawn edge under the cursor) to return `(edge_id, polyline_world)`; apply the same
  `_measure_recognised_component` gate as point picks.
- State: the pending measure pick becomes POINT or EDGE. Combination rules reduce every pair to TWO
  WORLD POINTS before recording:
  - edge + edge → closest pair between the two polylines (pairwise segment-segment min distance, numpy;
    for the parallel edges of an opening this IS the clear width);
  - point + edge (either order) → closest point on the edge to the point;
  - point + point → unchanged.
- The reduced pair feeds the existing `_record_measure_point` pipeline, so the segment, label, offset
  handle, snap lanes, session persistence and STEP-export dimensioning all work with zero changes.
- Feedback: while Alt is held in measure mode, highlight the candidate edge (reuse the hover edge
  highlight actor). Lesson 0324 applies: Alt state and pick are on two event streams — re-resolve on the
  Alt key transition itself, do not wait for the next `<Motion>`.

## Risks / guard plan

- Do NOT make edge-pick always-on (0317→0323: un-gating edge refine caused hover flicker; penta 287).
- Plain-click path must stay byte-identical — the 5 existing measure validators
  (`validate_open3d_measure_*`) must pass untouched.
- New guard `validate_open3d_measure_edge_pick.py`: PURE (closest-pair math: parallel edges → width;
  skew pair; point+edge projection), WIRING (Alt routes to the edge resolver, recognised-component gate
  honoured), INTEGRATION (two parallel drawn edges 51.00 mm apart → recorded segment length 51.00).
  New penta phase at the next free slot + baseline regen.

## Implementation notes (as shipped)

- Pure geometry: `services/measure_edge_pick.py` — clamped segment-segment closest pair (Ericson
  5.1.9) over polylines, `closest_point_on_polyline`, the `reduce_measure_picks` rules, and
  `collinear_edge_run` (extends the picked outline segment to its full straight run; corners, forks
  and chain ends stop the walk, so one side of a rounded-rectangle window is ONE edge).
- Edge source: the click resolver `_measure_resolve_edge` rides `_measure_resolve_snap` (same
  magnetism + recognised gate), maps the hit to its STEP label, then hit-tests the label's
  literally-drawn edge/rim polylines (`_step_component_edge_outline`, the bugs/0304 machinery
  guarded by phase 267) with the shared front-depth-ranked `nearest_display_edge`. Row-actor
  bodies have no drawn-edge outline; point picks still work there.
- Flow: `_on_measure_edge_pick` — edge-first ARMS `_measure_pending_edge` (persistent orange
  highlight, `_show_measure_pending_edge`); edge+edge completes via closest pair; point-first +
  edge-second projects the LIVE first point onto the edge; a re-anchor edge pick reduces against
  the segment's LIVE other endpoint; a plain click with an armed edge reduces in the point path.
  All reductions feed the untouched `_record_measure_point`, so lanes, the offset-adjust modal,
  session persistence and STEP export work unchanged.
- Alt truth at click time is the press-time capture (`mouse_bindings.py` left_press), and the live
  measure hover already promotes its gold highlight to the nearest edge under Alt (the 0323 gate
  inside `step_feature_pick_for_display_xy`) — no new key handling was needed (0324's transition
  re-fire also carries over for free).
- Escape does not exit measure mode (pre-existing contract), so the pending edge follows the same
  lifecycle as `_measure_p0`: cleared by start/clear/completion.
- Also repaired in passing: `validate_open3d_measure_center_snap_lanes` check #1 needled the
  obsolete literal `_measure_axis_snap_for_pick(self._actor_key(hit_actor), world)` — no such code
  exists at HEAD (verified by grep), so the check was silently failing BEFORE this feature (the
  phase-86 stale-baseline class). Needle updated to the live `(hit_key, world)` form.
