# 0661 — Inspection Part: a 3D object on the object plane with six blow-out axes

**User feature (2026-08-27):** "6 cameras looking at an object 3D rectangular 6-side to
inspect the defect. How to realize this in KrakenOS 3D UI?" → "I want to realize a 3D
object instead of existing 2D object plane. Then blow out 6 optical axis for user to
place lens and cameras."

## Phase 1 (this commit) — see docs/inspection_cell_multi_station.md

A W × H × D box whose ACTIVE face coincides with the object plane (centre = object
point, outward normal = the station axis object→lens); the box extends behind the
plane. Six dotted, pickable blow-out axes from every face centre along its outward
normal. Right-click the box → "Inspect <Face> (w × h)" re-poses the box so that face
is on the object plane (Front/Back W×H, Left/Right D×H, Top/Bottom W×D); "Solve FOV to
the inspected face" solves the object plane to the face +5%. Actions → "Inspection
Part (3D object)…" dialog. Persisted as `inspection_part` in the layout settings.

Design constraint honoured: the sequential row chain stays ONE object → ONE image;
the part re-targets the chain per face, and multi-station composition (six chains in
one view, per-station transforms — the two-arm precedent) is phase 2.

## Verified

Pure geometry (active face on plane; opposite faces antiparallel one extent apart;
adjacent orthogonal; right-handed frames; box behind the plane; 6 axes, 1 active;
re-target to Top gives W×D; garbage normalizes). Real scene (Basler_Telecentric):
7 actors + 6 axis records; "Solve FOV to this face" → 63 × 42 mm fills the sensor;
re-target to Top re-poses; layout file round-trips the spec. Render eyeballed:
translucent box at the object plane, active face green with the rays landing on it,
dashed axes out of the other faces. Guard phase 495.
