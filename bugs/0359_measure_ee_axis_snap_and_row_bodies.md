# 0359 — Measure E/E: hover still shows the axis snap; promoted (row-actor) bodies unmeasurable

**Flag:** 20260719_205024_892 (build 5a955e86) — "the Measure E/E not behaving like normal distance
measurement of CAD software. Still showing optical axis snap."

**Status:** root-caused 2026-07-19, NOT yet fixed. Two defects:

## 1. The hover still runs the plain axis-snap flow in entity mode

`_update_measure_hover_highlight` does not know about `_measure_entity_mode`: it resolves the
point snap, calls `_measure_axis_snap_for_pick`, and draws the orange "X" marker AT THE OPTICAL
AXIS — so while aiming, the user watches the axis-snap marker even though the click would pick an
edge. Fix: in entity mode the hover must resolve `_measure_resolve_edge` instead — highlight the
candidate edge (the gold outline), NO axis-snapped X marker, and the rubber-band preview should
run from the armed edge's closest point.

## 2. `_measure_resolve_edge` only works on STEP-overlay bodies

The resolver maps `hit_key` through `_actor_step_map` and returns None for ROW actors — but the
promoted BS cube (and every promoted optical solid) is a row actor. On the user's scene E/E
therefore reports "no drawn edge" on the very bodies they want to measure. Fix: for
`_actor_row_map` hits, resolve the promoted row's STEP label (invert the
`_promoted_optical_solid_row_index` mapping / the promote-arc provenance) and feed the same
`_step_component_edge_outline` path; a row with no step label falls back to the analytic-face
outline machinery.

## Acceptance (CAD feel)

Arm E/E → hover highlights the edge under the cursor (no axis X) → click, click the opposite
edge → dimension reads the clear width; works identically on STEP overlays AND promoted solids.
Guard: extend `validate_open3d_measure_edge_pick` with an entity-hover needle + a row-actor
resolution case; keep plain Measure byte-identical.
