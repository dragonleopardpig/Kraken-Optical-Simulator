# Inspection Cell — a 3D part with six camera stations

User request (2026-08-27): *"6 cameras looking at an object 3D rectangular 6-side to
inspect the defect."* → *"I want to realize a 3D object instead of existing 2D object
plane. Then blow out 6 optical axis for user to place lens and cameras."*

## The constraint the design respects

A KrakenOS layout is ONE imaging chain: Object row → optics → Image. That engine is
correct and battle-tested (solves, mount law, overlays, exports all assume it). The
cell is therefore built **around** it, on the precedent of the two-arm architecture
(`project_two_arm_display_fold`: per-arm SEQUENTIAL traces composed by display
transforms) — never by teaching the row chain about six objects.

## Phase 1 — SHIPPED (0661): the part + blow-out axes inside a station

`KrakenOS/UI/services/inspection_part.py`

- **Model:** a W × H × D box. Its **active face coincides with the object plane** —
  face centre at the object point, outward normal along the station axis
  (object → lens). The box extends behind the plane. So the current layout IS the
  station for that face; the object plane's size is the face's size.
- **Blow-out axes:** every face gets a dotted, pickable optical-axis record
  (`axis_kind = inspection_part_face`, `axis:part:<face>`) from its centre along its
  outward normal — the user sees where the other five stations sit; the Measure
  tool and axis-snap verbs work on them like any axis.
- **UI:** Actions → *Inspection Part (3D object)…* (enable, W/H/D, face, reach, *Apply +
  Solve FOV to this face*); right-click the box → *Inspect <Face> (w × h)* for all six,
  *Solve FOV to the inspected face*, *Settings…*. "Inspect this face" re-poses the box
  so that face sits on the object plane (Front/Back = W×H, Left/Right = D×H,
  Top/Bottom = W×D).
- **Persistence:** `inspection_part` in the layout settings (round-trips).
- **Guard:** phase 495 (`validate_open3d_0661_inspection_part`).

Workflow today: design each face's station in its own layout with the part enabled
on that face (opposite faces share a design → three layouts for a box), solve the FOV
to the face, verify with the overlays, export STEP per station, assemble in CAD.

## Phase 2 — SHIPPED v1 (0663, phase 496): the cell view (six chains, one scene)

Implemented in `KrakenOS/UI/services/inspection_cell.py`; Actions → *Inspection Cell (6
stations)…*. The design below is what shipped; the embedded (Tk) view and
double-click-to-edit remain phase 3.

- **Cell file** (`*.cell.json`): the part spec + `stations: {face: layout_path}`.
- **Composition:** for each station, load its layout headlessly, build its scene
  bundle, and render its actors into ONE renderer under a rigid transform
  T_face that maps the station's object point → the face centre and its object axis
  → the face's outward normal (the `_mesh_with_world_transform` machinery used by the
  display fold). Per-station traces stay sequential and independent — exactly the
  two-arm pattern.
- **Editing:** double-click a station → opens its own layout editor (all existing
  tools); the cell view re-composes on save. No new placement machinery needed:
  "place lens and camera on the face axis" = design that face's station.
- **Cell export:** composite STEP (all stations + the part) and six-view DXF of the
  cell; interference report between station bodies (bounds first, mesh later).
- **Guard:** composite pose invariants (each station's object plane lands on its
  face; axes coincide), export round-trip.

## Phase 3 — embedded view SHIPPED (0664, phase 497); the rest open

`KrakenOS/UI/panels/inspection_cell_window.py`: Tk/VTK window, transplanted composition,
double-click a station to open its layout, re-compose on save (mtime watch).

### Cell-level solve — SHIPPED (0665, phase 498)

`services/inspection_cell_solve.py`: part + defect size → camera + lens per face (height-aware m,
fixed-magnification lenses judged at their own field, telecentric preferred) → station layouts
built by the importers → cell file. Dialog section "Solve stations from the part + defect size".

### STEP part import — SHIPPED (0666, phase 499)

`inspection_part.step_path`: the real part's STEP; bounds → W×H×D (x→W, y→H, z→D, +z=Front); the
mesh replaces the box in the station scene, the cell view and the cell STEP.

### Axis = station handle — SHIPPED (0667, phase 500)

"Add components on each axis independently", as one gesture: right-click a blow-out
axis → *Create/Open station for this face…* (`open_station_for_face`). It opens the
cell-linked station if one exists; otherwise it creates
`attachment/cells/<stem>/station_<face>.py` seeded from the current scene with the
part re-targeted onto the face, links BOTH stations into `<stem>.cell.json` beside
it, and loads the new station. The axis menu also offers *Inspect this face
(re-target THIS chain)* and *Solve FOV*. A lens import replaces the whole layout, so
it now carries an enabled `inspection_part` across — a fresh station no longer loses
its part on the first import.

Workflow: enable the part once → right-click an axis → Create/Open station → import
lens/camera/LED on that chain → Save → the Cell View re-composes.

### Remaining

- Non-flat parts: faces become picked planar regions of the part STEP.
- Shared illumination: one LED lighting several faces; ray-level cross-talk checks.
- Station labels in the cell view.
