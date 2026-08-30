# 0666 — A STEP of the real part sizes the six-face model and replaces the box

**User (2026-08-30):** "proceed" on the STEP part import (phase 3 of the multi-station
cell).

## Shipped

The Inspection Part spec gains `step_path` (project-relative when inside the project).
The STEP's native bounding box supplies W×H×D (x→W, y→H, z→D, +z = Front) so the
six-face / six-axis model, the face re-targeting, the cell composition and the cell
solve are all unchanged; the real mesh is drawn where the box was:

- **Station scene** (`_add_inspection_part_glyphs`): the mesh is placed by
  `part_mesh_world` — native AABB centre → the part centre, native axes → the part frame
  (`part_frame`, factored out of `face_frames`) — so the STEP's +z face lies on the
  object plane; the box stays as a faint hull; the green active-face outline and the
  six dotted axes stay.
- **Cell view**: the mesh is drawn at the cell origin (the cell frame IS the part's
  native frame), loaded through the first station's editor.
- **Cell STEP**: the part shape itself (`_read_step_shape`, AABB-centred) replaces the
  box primitive in the compound.
- **Dialogs**: *Inspection Part* and *Inspection Cell* both take a Part STEP
  (Browse → dims from the bounds).

## Verified

Pure: `part_frame` ≡ `face_frames` (R, centre; corners unchanged), bounds → dims,
portable path, mesh AABB centre → part centre, the STEP's +z face on the Front plane
(offset 1e-16). Real: the Basler body as a stand-in part — station scene rendered with
the part on the object plane (eyeballed), a one-station cell composes with the part
mesh and exports a cell STEP embedding it. Guard
`validate_open3d_0666_inspection_part_step` (penta phase 499).

## Open

Picked planar regions (arbitrary faces of a non-box part as inspection planes);
shared illumination; station labels.
