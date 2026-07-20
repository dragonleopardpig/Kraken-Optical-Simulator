# 0367 — Measure E/E: second click strands the armed edge, no dimension

**Flag:** 20260720_094011_070 (build 075317c1) — "Measure E/E not working after clicking edge and
edge." Screenshot: one armed orange edge on the camera body, no dimension line; interaction_mode
still "measure" (the pair never completed). **Status:** FIXED 2026-07-20 (phase-311... measure-edge
guard, phase 306).

## Root cause

The E/E completion required the SECOND click to resolve another DRAWN edge via
`_measure_resolve_edge` (`_step_component_edge_outline` + `nearest_display_edge`, 14 px tolerance).
On a big STEP body (the HR25xCXP camera) the drawn feature/rim edge set is sparse relative to the
visible silhouette, so a click that looked "on an edge" landed >14 px from any *drawn* segment →
`_measure_resolve_edge` returned None → `_on_measure_edge_pick` was never called → the armed edge
stayed (orange) with no feedback path forward. A throw in the reduce could strand it the same way
(the pending edge was cleared AFTER the closest-pair call).

## Fix

1. **Point fallback (never stranded):** in the E/E / Alt-edge click handler, when no drawn edge is
   under the cursor, fall back to the snapped POINT (`_measure_resolve_snap`, NO axis snap). An
   armed edge then completes edge→point (CAD measures edge→face too); with `_measure_p0` set it
   completes point→point; in entity mode with nothing armed it arms a point. Every entity click now
   makes progress. (Alt mode with nothing armed still keeps "aim for an edge".)
2. **Strand-proof:** `_on_measure_edge_pick` clears the pending edge BEFORE the reduce and wraps it
   in try/except (degenerate second edge → the new edge's own endpoints), so a throw can never
   leave a stuck armed edge.

Guard: `validate_open3d_measure_edge_pick` gains a degenerate-second-edge strand-proof case + the
point-fallback / clear-before-reduce source needles.
