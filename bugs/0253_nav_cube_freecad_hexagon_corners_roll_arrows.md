# 0253 — Navigation cube: FreeCAD-style hexagon corners + concentric roll arrows

User flags (2026-07-08, "Next fix"):

> 1. Note the 2 orange rotation arrows, they look like "ears", a bit awkward. Can make them
>    look like `attachment/freecad.png` style? Notice the arrow pointing direction, and the
>    arrow segment align with the "Top" edge. The 2 arrows located at the middle of the Up and
>    Left/Right arrow.
> 2. The Corner is triangle, can make them same as FreeCAD hexagonal style? It is bigger,
>    easier to click.

Two cosmetic asks, both measured against FreeCAD's navigation cube (`attachment/freecad.png`).

## Item 2 — corners: triangle → hexagon

**Before.** `chamfered_cube_facets` kept each face as a **square** (half-width `f = 0.72·A`),
bevelled the 12 edges into quads, and cut each corner into a small **triangle** joining the
three adjacent face corners `(A,f,f)`, `(f,A,f)`, `(f,f,A)`. 24 shared vertices.

**Why it looked wrong.** FreeCAD cuts the corners *back* far enough that each face becomes an
**octagon**, each edge a **rectangle**, and each corner a **hexagon**. The KrakenOS triangle was
much smaller (a corner click target ~1/6 the area) and didn't read like FreeCAD's.

**Fix.** `chamfered_cube_facets(half, face_fraction, corner_fraction)` now builds the true
FreeCAD chamfer with two knobs:
* `face_fraction` (0.74) → the octagon's flat half-width `p = 0.74·A`.
* `corner_fraction` (0.44) → the corner cut starts `q = 0.44·A` from each axis.

Every vertex is a signed permutation of the magnitudes `(A, p, q)` (all distinct) ⇒ exactly
`3!·2³ = 48` vertices, each shared by one face octagon, one edge rectangle and one corner
hexagon. The corner hexagon's 6 vertices are the six signed permutations of `(A, p, q)`,
ordered so the boundary alternates a face-octagon diagonal edge with an edge-bevel edge. The
facet **order** (6 face, 12 edge, 8 corner), the 26 **signs**, outward winding, planarity and
the centroid→sign classification are all preserved, so the cell-id → sign pick table is
unchanged. The corner hexagon is **~6.0×** the area of the old triangle — a much bigger click
target.

The widget just passes the new `corner_fraction` (`_CORNER_FRACTION = 0.44`, `_FACE_FRACTION`
0.72→0.74) and already meshes each facet as a `VTK_POLYGON` of `len(idxs)` points, so octagons
/ rectangles / hexagons render with no widget change. Labels are unaffected (they live on a
separate `vtkAnnotatedCubeActor`).

## Item 1 — roll arrows: "ears" → FreeCAD arcs

**Before.** The two orange roll handles were **small arcs** (radius 0.28) perched at
`(±0.46, 0.88)` — they read as awkward "ears" on top of the cube.

**Fix.** They are now big arcs **concentric with the cube** (centred on the origin = the screen
centre, which is exactly what a roll about the sight line spins around), sitting just outside
the cube silhouette:
* `_ROLL_ARROW_RADIUS = 1.18`, `_ROLL_ARROW_WIDTH = 0.17`, with a chunky tangential arrowhead
  (`_ROLL_ARROW_HEAD_LEN/HALF = 0.30/0.20`).
* `roll_ccw` sweeps `110°→150°` (upper-**left**, flanking the Up arrow, head points **down-left**
  along the top edge); `roll_cw` sweeps `70°→30°` (upper-**right**, head **down-right**). Each
  arc's mid-angle sits between the Up arrow (90°) and the Left/Right arrow (180°/0°) — "the
  middle of the Up and Left/Right arrow".

**Follow-up (same day, after in-app "they look correct, but can make the rotation arrow shorter?").**
Each arc's sweep was trimmed 60°→**40°**, kept centred on the same mid-angles (130°/50°), so the tails
pull further from the Up arrow and the heads stop short of the Left/Right arrows — visibly shorter, same
concentric FreeCAD look. The guard now pins `sweep ≤ 45°` per arc (the user has asked twice for a short
rotation arc: bugs/0250 "curve segment too much", then this trim).

`_roll_arrow_actor` dropped its `(cx, cy)` offset (it's origin-centred now) and takes just
`(a0, a1, color)`. The head direction is the arc tangent at the `a1` end, so it points down
along the top edge as asked. The click/hover semantics (roll_ccw = left, roll_cw = right) are
unchanged — only the glyph moved and grew.

## Guards

* `validate_open3d_nav_cube_freecad_style` (display-free, penta **Phase 229**, new): facet
  shapes are 8/4/6 over 48 vertices; each corner hexagon is the canonical `(A,p,q)`-permutation
  cut (planar, outward, centroid-classifies); the hexagon is ≥ 2× the legacy triangle; and the
  roll-arrow source contract is concentric (`_ROLL_ARROW_RADIUS ≥ 1.0`, no `cx/cy`) with the two
  specs flanking the top.
* `validate_open3d_nav_cube_geometry` (bugs/0249, penta Phase 225) updated: 24→48 vertices and a
  new per-kind side-count assertion (face 8 / edge 4 / corner 6). Partition, signs, outward,
  planar, centroid and face-preset checks still pass unchanged.
* `validate_open3d_nav_cube_orientation` unchanged and still green (the pose math is untouched).

## Notes

* Eyeballed from an offscreen two-renderer render (cube renderer + arrow renderer, the widget's
  real constants/colours and the roll spans read straight from the widget source): the octagon
  faces / rectangle edges / big hexagon corners and the two concentric orange arcs flanking the
  Up arrow match `attachment/freecad.png`. The *live* embedded-VTK feel (hover/click on the new
  facets and arcs) is still owed an in-app eyeball — headless can't drive the Tk-embedded pane.
* Purely cosmetic: no optics, camera-pose or pick-semantics change. Corner **clicks** still land
  on the ISO per-octant view (bugs/0252); only the facet a corner click *targets* got bigger.
