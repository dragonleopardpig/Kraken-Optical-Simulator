# 0358 — Dedicated "Measure E/E" button (edge-to-edge like CAD), plain Measure untouched

**Flag:** 20260719_203757_779 — "Click measure --> Alt click highlight an edge, but second click
always snap to the optical axis. I think add another measurement button to measure edge to edge or
face to face distance just like the normal CAD software. Don't change the current Measure button."

**Status:** SHIPPED 2026-07-19 (edge-to-edge; face-to-face is the noted follow-up).

## What happened in the flag

The first Alt+click armed the edge, but the second click arrived WITHOUT Alt (or off an edge), so
it fell into the plain point path whose always-on bugs/0115 axis snap pulled it onto the optical
axis — an edge→axis measurement instead of edge→edge.

## What ships

A second toolbar button **"Measure E/E"** (top toolbar + Live Controls) arming
`_measure_entity_mode` on top of the normal measure flow: EVERY click is an edge pick (no Alt
needed), the axis-snap point path is unreachable, and a miss says "click ON an edge" instead of
recording a snapped point. Two picks reduce via the 0353 closest-pair machinery; Clear and the
plain Measure button behave exactly as before (`start_measure_entity_pick` delegates to
`start_measure_pick` then arms the mode; both clear paths reset it).

## Follow-up

Face-to-face picks (click two FACES → perpendicular/closest distance) — needs a face-outline
entity fallback in `_measure_resolve_edge` with ordered-loop closest-pair support in
`services/measure_edge_pick`. Not started.
