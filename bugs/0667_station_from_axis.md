# 0667 — The blow-out axis is the station handle

**User (2026-08-31):** "My intention was to change the existing 2D object plane to 3D
6-sided object, 6 optical axis creation, add components on each axis independently."
The first two were direct matches (0661/0666); the third had the right capability but
an indirect gesture — components per axis live in that face's station layout, and one
had to build/slot layouts by hand or via the solver. This closes the gesture gap.

## Shipped

- **Right-click a blow-out axis** → its own menu: *Create/Open station for this
  face…* / *Inspect this face (re-target THIS chain)* / *Solve FOV to the inspected
  face*. The generic axis menu (0638) routes `inspection_part_face` records here.
- `open_station_for_face(face)`: opens the linked station if the cell knows one;
  otherwise CREATES it — seeded from the current scene with the part re-targeted
  onto the face (same part, a working chain to adapt) — at
  `attachment/cells/<stem>/station_<face>.py`, links BOTH stations into the cell
  (the seed scene keeps its own face), writes `<stem>.cell.json` beside them, and
  loads the new station. Opening twice never re-creates.
- The part right-click menu gains *Create/Open station for the inspected face…*.
- **A lens import no longer deletes the part**: importing a lens replaces the whole
  layout, so an enabled `inspection_part_spec` is snapshotted and re-applied — the
  first thing a user does on a fresh station used to silently remove its part.

## The workflow now ("add components on each axis")

Enable the part once → right-click any of the six axes → *Create/Open station* →
you are ON that axis's chain with the part in view → import/swap lens, camera, LED →
Save Layout → the Cell View (watching the files) re-composes. The cell json created
along the way is loadable in the Inspection Cell dialog at any time.

## Verified

Guard `validate_open3d_0667_station_from_axis` (penta phase 500): create writes the
station + cell json and loads it with the part on the face; both stations linked;
idempotent open (mtime unchanged); the part survives the lens import; menu wiring.
