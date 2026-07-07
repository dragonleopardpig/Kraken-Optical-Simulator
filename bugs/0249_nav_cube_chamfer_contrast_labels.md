# 0249 — Navigation cube: oversized labels, low face contrast, non-chamfered edges/corners

User flag (`attachment/recorded_bug_repros/flag_20260707_151527_059/description.txt`):

> the text in the cube is too big. The color of the cube for each surface has low
> contrast difference. The edge if can be clicked, should be "chamfered". If corner
> can be clicked, chamfered it as well.

Follow-up (same session): *"the orange rotation arrow should have a curved segment
attached to the arrow."*

This is polish on the shipped nav cube (bugs/0156). Four asks + one follow-up:

1. **Labels too big** — face text overflowed each face.
2. **Low per-surface contrast** — every face was the same pale blue-grey.
3. **Chamfer the clickable edges** — the 12 edge orientations were already pickable
   (as threshold bands near the sharp cube edges) but had no visible target.
4. **Chamfer the clickable corners** — same for the 8 corner orientations.
5. **Curved roll arrow** — the orange roll handles were bare triangles; make them read
   as *rotation* (an arc segment with the arrowhead on its end).

## Root cause

The cube was drawn as a **plain sharp unit cube** (`vtkCubeSource`, one uniform colour
`0.86,0.90,0.97`) with a transparent `vtkAnnotatedCubeActor` on top for the letters
(`SetFaceTextScale(0.42)`). A left-click picked the opaque cube and ran
`classify_pick(GetPickPosition())`, which *carved* the flat face into face / edge / corner
bands by a distance threshold. So edges and corners were reachable, but:

* there was **no visual chamfer** — nothing on the sharp cube showed the user where the
  edge/corner click targets were;
* all six faces shared **one colour**, so surfaces read as low-contrast;
* the label scale **overflowed** the face.

## Fix

**Geometry (VTK-free, `services/nav_cube_orientation.py`).** New `chamfered_cube_facets(half,
face_fraction)` returns a FreeCAD-style chamfered cube: 24 shared vertices and **26 flat
facets** — 6 face quads, 12 bevelled-edge quads, 8 cut-corner triangles — one per
orientation, each carrying its `{-1,0,1}^3` sign and wound so its polygon normal points
outward. `face_fraction=0.72` keeps 72 % of each face flat, the rest becomes the bevel.

**Cube mesh + picking (`services/nav_cube_widget.py`, `_build_chamfered_actor`).** The cube
is now one `vtkPolyData` built from those facets, with a **per-cell colour** by orientation
kind — faces lightest, edges mid, corners darkest — plus a dark outline on every facet, so
the three clickable regions read as distinct (ask 2) and the bevels/corners are visible
(asks 3-4). The facet cell-id → sign table is stored as `self._cell_signs`, so a pick is an
**exact lookup**: `GetCellId() -> self._cell_signs[cid] -> orientation_pose(sign)`
(`classify_pick` kept only as an out-of-range fallback). Clicking a face is still
byte-identical to the matching toolbar preset (guard G).

**Labels (`_build_annotated_labels`).** The `vtkAnnotatedCubeActor` is reused for the CAD
words only: text scale `0.42 -> 0.22` (ask 1), letters given a **solid dark fill** (each
face text property) instead of thin outlines so they stay legible at the smaller size, and
the label overlay floated `1.015x` outward so it neither z-fights the coplanar face facet
nor pokes far past the silhouette.

**Curved roll arrows (`_roll_arrow_actor`).** Each orange roll handle is now a **curved arc
ribbon** (triangulated) capped by a **tangential arrowhead** at the sweep end — a rotation
glyph, not a bare triangle (ask 5). The four blue orbit arrows stay as edge triangles.

All visual parameters are module constants (`_FACE_FRACTION`, `_FACE_TEXT_SCALE`,
`_COLOR_FACE/_EDGE/_CORNER/_OUTLINE`) tuned against an offscreen render.

## Guard

`validate_open3d_nav_cube_geometry` (display-free, penta **Phase 225**) checks:

* **A** — `chamfered_cube_facets(0.5, 0.72)` yields exactly 24 vertices and 26 facets.
* **B** — the facets partition into 6 faces + 12 edges + 8 corners.
* **C** — the 26 facet signs are exactly the 26 `ORIENTATION_KEYS` (each once, none dup).
* **D** — every facet is wound outward (`normal · sign > 0`).
* **E** — every facet is planar.
* **F** — every facet centroid `classify_pick`s back to its own sign (cell-id lookup
  agrees with the facet's geometric orientation).
* **G** — the six face facets still equal the cardinal toolbar presets (`_FACE_POSE`).
* **H** — source contract: the widget builds `self._cell_signs` from
  `chamfered_cube_facets`, resolves a pick by `GetCellId()` → `self._cell_signs`, and uses
  the curved `_roll_arrow_actor` for the roll handles.

## Notes

* The visual half (label size, per-kind contrast, chamfer proportions, curved arrows) was
  verified from an **offscreen Xvfb render** (`/tmp/navcube_render3.png`) — the geometry
  guard cannot see pixels.
* The far-side labels poke a hair past the cube silhouette at extreme zoom, because the
  full-cube label overlay is slightly larger than the (corner-cut) chamfered silhouette.
  Cosmetic and invisible at the native on-screen size; left as-is rather than replacing the
  annotated-cube labels with per-face billboard text (much larger rewrite, no real gain).
* In-app eyeball still owed for hover/drag feel (headless can't drive the embedded-VTK
  hover/pick), but the pick math and mesh are proven headless.
